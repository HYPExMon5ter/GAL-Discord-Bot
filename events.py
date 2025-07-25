# gal_discord_bot/events.py

import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz

from config import (
    REGISTRATION_CHANNEL, CHECK_IN_CHANNEL,
    ANGEL_ROLE, REGISTERED_ROLE,
    embed_from_cfg, LOG_CHANNEL_NAME
)
from persistence import (
    set_schedule, get_schedule,
    get_event_mode_for_guild
)
from sheets import refresh_sheet_cache
from utils import update_dm_action_views
from views import update_live_embeds, PersistentRegisteredListView

# In-memory caches
scheduled_event_cache: dict = {}
open_tasks: dict = {}
close_tasks: dict = {}

def match_event_type(name: str) -> str | None:
    lc = name.lower()
    for kw in ("registration", "register", "reg"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "registration"
    for kw in ("check-in","checkin","check in","check"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "checkin"
    return None

def get_channel_and_role(guild, etype):
    if etype == "registration":
        return (
            discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL),
            discord.utils.get(guild.roles,         name=ANGEL_ROLE)
        )
    return (
        discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL),
        discord.utils.get(guild.roles,         name=REGISTERED_ROLE)
    )

async def schedule_channel_open(bot, guild, channel_name, role_name, open_time, ping_role=True):
    """Fires at open_time, then clears the persisted open_schedule."""
    now = datetime.now(ZoneInfo("UTC"))
    wait = (open_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    ch   = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles,        name=role_name)
    if ch and role:
        perms = ch.overwrites_for(role)
        if not perms.view_channel:
            perms.view_channel = True
            await ch.set_permissions(role, overwrite=perms)
            await update_live_embeds(guild)
            # ping once
            if ping_role:
                await ch.send(f"{role.mention}", delete_after=3)
            await update_dm_action_views(guild)

        # Clear the stored open timestamp
        set_schedule(guild.id, f"{channel_name}_open", None)

async def schedule_channel_close(bot, guild, channel_name, role_name, close_time):
    """Fires at close_time, then clears the persisted close_schedule."""
    now = datetime.now(ZoneInfo("UTC"))
    wait = (close_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    ch   = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles,        name=role_name)
    if ch and role:
        perms = ch.overwrites_for(role)
        if perms.view_channel:
            perms.view_channel = False
            await ch.set_permissions(role, overwrite=perms)
            await update_live_embeds(guild)
            await update_dm_action_views(guild)

        # Clear the stored close timestamp
        set_schedule(guild.id, f"{channel_name}_close", None)

async def _handle_event_schedule(bot, event, is_edit: bool):
    etype      = match_event_type(event.name)
    if not etype:
        return

    guild      = event.guild
    cache_key  = (guild.id, event.id)
    open_time  = event.start_time and event.start_time.astimezone(ZoneInfo("UTC"))
    close_time = event.end_time   and event.end_time.astimezone(ZoneInfo("UTC"))

    # Skip if nothing changed
    if scheduled_event_cache.get(cache_key) == (open_time, close_time):
        return
    scheduled_event_cache[cache_key] = (open_time, close_time)

    # Cancel existing tasks
    for suffix, tasks in (("open", open_tasks), ("close", close_tasks)):
        key = (guild.id, event.id, suffix)
        if key in tasks and not tasks[key].done():
            tasks[key].cancel()
            del tasks[key]

    # Persist both times
    set_schedule(guild.id, f"{etype}_open",  open_time.isoformat() if open_time  else None)
    set_schedule(guild.id, f"{etype}_close", close_time.isoformat() if close_time else None)

    # Schedule open
    ch, role = get_channel_and_role(guild, etype)
    now = datetime.now(ZoneInfo("UTC"))
    if ch and role:
        # Open
        if open_time and open_time > now:
            key = (guild.id, event.id, "open")
            open_tasks[key] = asyncio.create_task(
                schedule_channel_open(bot, guild, ch.name, role.name, open_time)
            )
        else:
            # Already past: fire immediately (no ping)
            await schedule_channel_open(bot, guild, ch.name, role.name, now, ping_role=False)

        # Close
        if close_time and close_time > now:
            key = (guild.id, event.id, "close")
            close_tasks[key] = asyncio.create_task(
                schedule_channel_close(bot, guild, ch.name, role.name, close_time)
            )
        else:
            # Already past: fire immediately
            await schedule_channel_close(bot, guild, ch.name, role.name, now)

    # Log creation/edit
    log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_ch:
        embed_key = "schedule_edited" if is_edit else "schedule_created"
        embed = embed_from_cfg(
            embed_key,
            type=etype.capitalize(),
            event=event.name,
            open_ts=int(event.start_time.timestamp()),
            close_ts=int(event.end_time.timestamp()) if event.end_time else None
        )
        await log_ch.send(embed=embed)

def setup_events(bot):
    @bot.event
    async def on_ready():
        print(f"We are ready to go in, {bot.user}")
        # sync & prime cache
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
            await refresh_sheet_cache(bot=bot)
        # re-register views & live embeds
        for guild in bot.guilds:
            bot.add_view(PersistentRegisteredListView(guild))
            await update_live_embeds(guild)
        # rehydrate all Scheduled Events
        for guild in bot.guilds:
            for se in guild.scheduled_events:
                await _handle_event_schedule(bot, se, is_edit=False)

    @bot.event
    async def on_scheduled_event_create(event):
        await _handle_event_schedule(bot, event, is_edit=False)

    @bot.event
    async def on_scheduled_event_update(_, event):
        await _handle_event_schedule(bot, event, is_edit=True)

    @bot.event
    async def on_scheduled_event_delete(event):
        etype = match_event_type(event.name)
        if not etype:
            return
        guild = event.guild
        # cancel tasks
        for suffix, tasks in (("open", open_tasks), ("close", close_tasks)):
            key = (guild.id, event.id, suffix)
            if key in tasks and not tasks[key].done():
                tasks[key].cancel()
                del tasks[key]
        scheduled_event_cache.pop((guild.id, event.id), None)
        set_schedule(guild.id, etype, None)
        log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_ch:
            embed = embed_from_cfg(
                "schedule_deleted",
                type=etype.capitalize(),
                event=event.name
            )
            await log_ch.send(embed=embed)
