# gal_discord_bot/events.py

import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz

from persistence import (
    set_schedule
)
from config import (
    REGISTRATION_CHANNEL,
    CHECK_IN_CHANNEL,
    ANGEL_ROLE,
    REGISTERED_ROLE,
    LOG_CHANNEL_NAME,
    embed_from_cfg,
    _FULL_CFG,
    update_gal_command_ids
)
from utils import update_dm_action_views
from sheets import refresh_sheet_cache
from views import update_live_embeds, PersistentRegisteredListView

# In‐memory caches for events
scheduled_event_cache: dict = {}
open_tasks: dict = {}
close_tasks: dict = {}

def match_event_type(name: str) -> str | None:
    lc = name.lower()
    for kw in ("registration", "register", "reg"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "registration"
    for kw in ("check-in", "checkin", "check in", "check"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "checkin"
    return None

def get_channel_and_role(guild: discord.Guild, etype: str):
    if etype == "registration":
        return (
            discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL),
            discord.utils.get(guild.roles,         name=ANGEL_ROLE)
        )
    else:
        return (
            discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL),
            discord.utils.get(guild.roles,         name=REGISTERED_ROLE)
        )

async def schedule_channel_open(
    bot,
    guild: discord.Guild,
    channel_name: str,
    role_name: str,
    open_time: datetime,
    ping_role: bool = True
):
    now = datetime.now(ZoneInfo("UTC"))
    wait = (open_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role    = discord.utils.get(guild.roles,        name=role_name)
    if channel and role:
        perms = channel.overwrites_for(role)
        if not perms.view_channel:
            perms.view_channel = True
            await channel.set_permissions(role, overwrite=perms)
            await update_live_embeds(guild)
            if ping_role:
                await channel.send(f"{role.mention}", delete_after=3)
            await update_dm_action_views(guild)

        # Clear persisted open time so it won't fire again
        set_schedule(guild.id, f"{channel_name}_open", None)

async def schedule_channel_close(
    bot,
    guild: discord.Guild,
    channel_name: str,
    role_name: str,
    close_time: datetime
):
    now = datetime.now(ZoneInfo("UTC"))
    wait = (close_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role    = discord.utils.get(guild.roles,        name=role_name)
    if channel and role:
        perms = channel.overwrites_for(role)
        if perms.view_channel:
            perms.view_channel = False
            await channel.set_permissions(role, overwrite=perms)
            await update_live_embeds(guild)
            await update_dm_action_views(guild)

        # Clear persisted close time so it won't fire again
        set_schedule(guild.id, f"{channel_name}_close", None)

async def _handle_event_schedule(bot, event, is_edit: bool):
    etype = match_event_type(event.name)
    if not etype:
        return

    guild = event.guild
    key   = (guild.id, event.id)
    open_time  = event.start_time and event.start_time.astimezone(ZoneInfo("UTC"))
    close_time = event.end_time   and event.end_time.astimezone(ZoneInfo("UTC"))

    # If nothing changed, skip
    if scheduled_event_cache.get(key) == (open_time, close_time):
        return
    scheduled_event_cache[key] = (open_time, close_time)

    # Cancel any existing tasks
    for suffix, tasks in (("open", open_tasks), ("close", close_tasks)):
        tkey = (guild.id, event.id, suffix)
        if tkey in tasks and not tasks[tkey].done():
            tasks[tkey].cancel()
            del tasks[tkey]

    # Persist both times
    set_schedule(guild.id, f"{etype}_open",  open_time.isoformat()  if open_time  else None)
    set_schedule(guild.id, f"{etype}_close", close_time.isoformat() if close_time else None)

    # Schedule open
    ch, role = get_channel_and_role(guild, etype)
    now = datetime.now(ZoneInfo("UTC"))
    if ch and role:
        # Open
        if open_time and open_time > now:
            open_tasks[(guild.id, event.id, "open")] = asyncio.create_task(
                schedule_channel_open(bot, guild, ch.name, role.name, open_time)
            )
        else:
            # Fire immediately (no ping)
            await schedule_channel_open(bot, guild, ch.name, role.name, now, ping_role=False)

        # Close
        if close_time and close_time > now:
            close_tasks[(guild.id, event.id, "close")] = asyncio.create_task(
                schedule_channel_close(bot, guild, ch.name, role.name, close_time)
            )
        else:
            # Fire immediately
            await schedule_channel_close(bot, guild, ch.name, role.name, now)

    # Log creation/edit in the log channel with real placeholders
    log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_ch:
        open_ts  = int(event.start_time.timestamp()) if event.start_time else None
        close_ts = int(event.end_time.timestamp())   if event.end_time   else None
        key_name = "schedule_edited" if is_edit else "schedule_created"
        embed = embed_from_cfg(
            key_name,
            type=etype.capitalize(),
            event=event.name,
            open_ts=open_ts,
            close_ts=close_ts
        )
        await log_ch.send(embed=embed)

def setup_events(bot: commands.Bot):
    @bot.event
    async def on_ready():
        print(f"[on_ready] Logged in as {bot.user}")

        await update_gal_command_ids(bot)
        print("[on_ready] • GAL_COMMAND_IDS populated, help links ready")

        # per-guild startup
        for guild in bot.guilds:
            await refresh_sheet_cache(bot=bot)
            print(f"[on_ready] • Cache refreshed for guild {guild.name} ({guild.id})")

            # rehydrate views & embeds
            bot.add_view(PersistentRegisteredListView(guild))
            await update_live_embeds(guild)
            print(f"[on_ready] • Live embeds updated for guild {guild.name}")

            # re-schedule any existing scheduled_events
            for se in guild.scheduled_events:
                await _handle_event_schedule(bot, se, is_edit=False)
                print(f"[on_ready] • Scheduled event re-registered: {se.name}")

        # rich presence
        presence_cfg = _FULL_CFG.get("rich_presence", {})
        p_type = presence_cfg.get("type", "PLAYING").upper()
        p_msg = presence_cfg.get("message", "")
        if p_type == "LISTENING":
            activity = discord.Activity(type=discord.ActivityType.listening, name=p_msg)
        elif p_type == "WATCHING":
            activity = discord.Activity(type=discord.ActivityType.watching, name=p_msg)
        else:
            activity = discord.Game(name=p_msg)
        await bot.change_presence(activity=activity)
        print(f"[on_ready] • Rich presence set: {p_type} {p_msg}")

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
        # Cancel tasks
        for suffix, tasks in (("open", open_tasks), ("close", close_tasks)):
            key = (guild.id, event.id, suffix)
            if key in tasks and not tasks[key].done():
                tasks[key].cancel()
                del tasks[key]
        scheduled_event_cache.pop((guild.id, event.id), None)

        # Clear persisted schedules
        set_schedule(guild.id, f"{etype}_open",  None)
        set_schedule(guild.id, f"{etype}_close", None)

        # Send deletion embed
        log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_ch:
            open_ts  = int(event.start_time.timestamp()) if event.start_time else None
            close_ts = int(event.end_time.timestamp())   if event.end_time   else None
            embed = embed_from_cfg(
                "schedule_deleted",
                type=etype.capitalize(),
                event=event.name,
                open_ts=open_ts,
                close_ts=close_ts
            )
            await log_ch.send(embed=embed)