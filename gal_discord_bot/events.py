# gal_discord_bot/events.py

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from rapidfuzz import fuzz

from gal_discord_bot.config import REGISTRATION_CHANNEL, CHECK_IN_CHANNEL, ANGEL_ROLE, REGISTERED_ROLE, \
    embed_from_cfg, LOG_CHANNEL_NAME, EMBEDS_CFG
from gal_discord_bot.persistence import set_schedule
from gal_discord_bot.sheets import refresh_sheet_cache, cache_refresh_loop
from gal_discord_bot.utils import update_dm_action_views
from gal_discord_bot.views import update_live_embeds, PersistentRegisteredListView

scheduled_event_cache = {}  # key: (guild.id, event.id), value: (open_time, close_time)
open_tasks = {}    # key: (guild.id, event.id, "open"), value: asyncio.Task
close_tasks = {}   # key: (guild.id, event.id, "close"), value: asyncio.Task

def match_event_type(event_name: str):
    event_name_lc = event_name.lower()
    # You can customize the keywords as needed
    registration_keywords = ["registration", "register", "reg"]
    checkin_keywords = ["check-in", "checkin", "check in", "check"]
    for kw in registration_keywords:
        if fuzz.partial_ratio(event_name_lc, kw) >= 80:
            return "registration"
    for kw in checkin_keywords:
        if fuzz.partial_ratio(event_name_lc, kw) >= 80:
            return "checkin"
    return None

def get_log_channel(guild):
    return next((c for c in guild.text_channels if c.name == LOG_CHANNEL_NAME), None)

def get_channel_and_role(guild, event_type):
    if event_type == "registration":
        return (discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL),
                discord.utils.get(guild.roles, name=ANGEL_ROLE))
    elif event_type == "checkin":
        return (discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL),
                discord.utils.get(guild.roles, name=REGISTERED_ROLE))
    return (None, None)

def setup_events(bot):
    @bot.event
    async def on_ready():
        print(f"We are ready to go in, {bot.user.name}")

        # Sync & cache
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
            print(f"Synced commands to guild {guild.id}")
        await refresh_sheet_cache(bot=bot)

        # Ensure persisted embeds and views
        for guild in bot.guilds:
            # … your existing persisted‐embed logic …
            bot.add_view(PersistentRegisteredListView(guild))
            await update_live_embeds(guild)

        # ─── Set Rich Presence from embeds.yaml ───────────────────────
        presence_cfg = EMBEDS_CFG.get("rich_presence", {})
        pres_type = presence_cfg.get("type", "PLAYING").upper()
        pres_msg = presence_cfg.get("message", "")

        if pres_type == "LISTENING":
            activity = discord.Activity(type=discord.ActivityType.listening, name=pres_msg)
        elif pres_type == "WATCHING":
            activity = discord.Activity(type=discord.ActivityType.watching, name=pres_msg)
        else:
            activity = discord.Game(name=pres_msg)

        await bot.change_presence(status=discord.Status.online, activity=activity)

    @bot.event
    async def on_scheduled_event_create(event):
        await _handle_event_schedule(bot, event, is_edit=False)

    @bot.event
    async def on_scheduled_event_update(before, after):
        await _handle_event_schedule(bot, after, is_edit=True)

    @bot.event
    async def on_scheduled_event_delete(event):
        event_type = match_event_type(event.name)
        if not event_type:
            return
        guild = event.guild
        log_channel = get_log_channel(guild)
        cache_key = (guild.id, event.id)
        tkey_open = (guild.id, event.id, "open")
        tkey_close = (guild.id, event.id, "close")
        # Cancel tasks
        for tkey, task in [(tkey_open, open_tasks.get(tkey_open)), (tkey_close, close_tasks.get(tkey_close))]:
            if task and not task.done():
                task.cancel()
                if tkey in open_tasks: del open_tasks[tkey]
                if tkey in close_tasks: del close_tasks[tkey]
        scheduled_event_cache.pop(cache_key, None)
        set_schedule(guild.id, event_type, None)
        if log_channel:
            embed = embed_from_cfg(
                "schedule_deleted",
                type=event_type.capitalize(),
                event=event.name
            )
            await log_channel.send(embed=embed)

async def bot_cache_refresh_loop(bot):
    await cache_refresh_loop(bot)

async def _handle_event_schedule(bot, event, is_edit):
    event_type = match_event_type(event.name)
    if not event_type:
        return
    guild = event.guild
    log_channel = get_log_channel(guild)
    cache_key = (guild.id, event.id)
    open_time = event.start_time and event.start_time.astimezone()
    close_time = event.end_time and event.end_time.astimezone()
    changed = (
        cache_key not in scheduled_event_cache or
        scheduled_event_cache[cache_key] != (open_time, close_time)
    )
    if not changed:
        return  # No change, so skip everything!

    scheduled_event_cache[cache_key] = (open_time, close_time)

    # Cancel any previous open/close tasks for this event
    tkey_open = (guild.id, event.id, "open")
    tkey_close = (guild.id, event.id, "close")
    for tkey, task in [(tkey_open, open_tasks.get(tkey_open)), (tkey_close, close_tasks.get(tkey_close))]:
        if task and not task.done():
            task.cancel()
            if tkey in open_tasks: del open_tasks[tkey]
            if tkey in close_tasks: del close_tasks[tkey]

    set_schedule(guild.id, event_type, open_time.isoformat() if open_time else None)
    channel, role = get_channel_and_role(guild, event_type)
    now = datetime.now(ZoneInfo("UTC"))
    # Only schedule if future
    if channel and role and open_time and open_time > now:
        task = asyncio.create_task(
            schedule_channel_open(bot, guild, channel.name, role.name, open_time)
        )
        open_tasks[tkey_open] = task
    if channel and role and close_time and close_time > now:
        task = asyncio.create_task(
            schedule_channel_close(bot, guild, channel.name, role.name, close_time)
        )
        close_tasks[tkey_close] = task

    if log_channel:
        close_str = f"\nClose at: <t:{int(event.end_time.timestamp())}:F>" if event.end_time else ""
        embed_key = "schedule_edited" if is_edit else "schedule_created"
        embed = embed_from_cfg(
            embed_key,
            type=event_type.capitalize(),
            event=event.name,
            open_ts=int(event.start_time.timestamp()),
            close_str=close_str,
        )
        await log_channel.send(embed=embed)

async def schedule_channel_open(bot, guild, channel_name, role_name, open_time, ping_role=True):
    from gal_discord_bot.views import update_live_embeds
    now = datetime.now(ZoneInfo("UTC"))
    wait_seconds = (open_time - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        overwrites = channel.overwrites_for(role)
        if overwrites.view_channel:
            print(f"[Schedule] Channel '{channel_name}' already open for role '{role_name}', skipping open and ping.")
            return
        overwrites.view_channel = True
        await channel.set_permissions(role, overwrite=overwrites)
        print(f"[Schedule] Channel '{channel_name}' opened for role '{role_name}'.")
        await update_live_embeds(guild)
        log_channel = get_log_channel(guild)
        if log_channel:
            embed = embed_from_cfg(
                "schedule_open",
                type=channel_name.capitalize(),
                time=datetime.now().strftime("%Y-%m-%d %I:%M %p %Z")
            )
            await log_channel.send(embed=embed)
        if ping_role:
            await channel.send(f"{role.mention}", delete_after=3)
        # refresh DMs
        await update_dm_action_views(guild)

async def schedule_channel_close(bot, guild, channel_name, role_name, close_time):
    from gal_discord_bot.views import update_live_embeds
    now = datetime.now(ZoneInfo("UTC"))
    wait_seconds = (close_time - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        overwrites = channel.overwrites_for(role)
        if not overwrites.view_channel:
            print(f"[Schedule] Channel '{channel_name}' is already closed for role '{role_name}', skipping close.")
            return
        overwrites.view_channel = False
        await channel.set_permissions(role, overwrite=overwrites)
        print(f"[Schedule] Channel '{channel_name}' closed for role '{role_name}'.")
        await update_live_embeds(guild)
        # refresh DMs
        await update_dm_action_views(guild)
        log_channel = get_log_channel(guild)
        if log_channel:
            embed = embed_from_cfg(
                "schedule_close",
                type=channel_name.capitalize(),
                close_ts=int(datetime.now().timestamp())
            )
            await log_channel.send(embed=embed)
    # Always clear the schedule when done closing
    key = "registration" if channel_name == REGISTRATION_CHANNEL else "checkin"
    set_schedule(guild.id, key, None)