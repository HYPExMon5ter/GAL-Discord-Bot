# core/events.py - Fixed with complete error handling

import asyncio
import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz
import logging
import traceback

from core.persistence import set_schedule, get_schedule, get_persisted_msg
from config import (
    REGISTRATION_CHANNEL, CHECK_IN_CHANNEL, ANGEL_ROLE,
    REGISTERED_ROLE, LOG_CHANNEL_NAME, embed_from_cfg,
    _FULL_CFG, update_gal_command_ids
)
from integrations.sheets import refresh_sheet_cache, cache_refresh_loop

# Import helpers
from helpers import ChannelManager, ConfigManager, EmbedHelper

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
        return ChannelManager.get_channel_and_role(guild, "registration")
    else:
        return ChannelManager.get_channel_and_role(guild, "checkin")


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

    channel = ChannelManager.get_channel(guild, channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        changed = await ChannelManager.set_channel_visibility(channel, role, True, ping_role)
        if changed:
            # Update all embeds immediately after opening
            await EmbedHelper.update_all_guild_embeds(guild)
            # Import locally to avoid circular import
            from utils.utils import update_dm_action_views
            await update_dm_action_views(guild)

            # Log the opening
            logging.info(f"Opened {channel_name} channel for guild {guild.id}")

        # Clear persisted open time so it won't fire again
        if channel_name == REGISTRATION_CHANNEL:
            set_schedule(guild.id, "registration_open", None)
        elif channel_name == CHECK_IN_CHANNEL:
            set_schedule(guild.id, "checkin_open", None)


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

    channel = ChannelManager.get_channel(guild, channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        changed = await ChannelManager.set_channel_visibility(channel, role, False, False)
        if changed:
            # Update all embeds immediately after closing
            await EmbedHelper.update_all_guild_embeds(guild)
            # Import locally to avoid circular import
            from utils.utils import update_dm_action_views
            await update_dm_action_views(guild)

            # Log the closing
            logging.info(f"Closed {channel_name} channel for guild {guild.id}")

        # Clear persisted close time so it won't fire again
        if channel_name == REGISTRATION_CHANNEL:
            set_schedule(guild.id, "registration_close", None)
        elif channel_name == CHECK_IN_CHANNEL:
            set_schedule(guild.id, "checkin_close", None)


async def _handle_event_schedule(bot, event, is_edit: bool):
    etype = match_event_type(event.name)
    if not etype:
        return

    guild = event.guild
    key = (guild.id, event.id)
    open_time = event.start_time and event.start_time.astimezone(ZoneInfo("UTC"))
    close_time = event.end_time and event.end_time.astimezone(ZoneInfo("UTC"))

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
    set_schedule(guild.id, f"{etype}_open", open_time.isoformat() if open_time else None)
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

    # Log creation/edit in the log channel with proper formatting
    log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_ch:
        open_ts = int(event.start_time.timestamp()) if event.start_time else None
        close_ts = int(event.end_time.timestamp()) if event.end_time else None
        key_name = "schedule_edited" if is_edit else "schedule_created"

        # Build close string for the embed
        close_str = f"\nCloses at: <t:{close_ts}:F>" if close_ts else ""

        embed = embed_from_cfg(
            key_name,
            type=etype.capitalize(),
            event=event.name,
            open_ts=open_ts,
            close_ts=close_ts,
            close_str=close_str
        )
        await log_ch.send(embed=embed)


def setup_events(bot: commands.Bot):
    @bot.event
    async def on_ready():
        print(f"[on_ready] Logged in as {bot.user}")
        logging.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")

        try:
            # Update command IDs first
            print("[on_ready] Starting command ID update...")
            await update_gal_command_ids(bot)
            print("[on_ready] • GAL_COMMAND_IDs populated, help links ready")

            # per-guild startup
            for guild in bot.guilds:
                try:
                    logging.info(f"Processing guild: {guild.name} ({guild.id})")

                    # Refresh cache for this guild
                    print(f"[on_ready] Refreshing cache for guild {guild.name}...")
                    await refresh_sheet_cache(bot=bot)
                    print(f"[on_ready] • Cache refreshed for guild {guild.name} ({guild.id})")

                    # Test import of views
                    print("[on_ready] Testing view imports...")
                    try:
                        from core.views import RegistrationView, CheckInView, PersistentRegisteredListView
                        print("[on_ready] • View imports successful")
                    except Exception as e:
                        print(f"[on_ready] ERROR importing views: {e}")
                        logging.error(f"Failed to import views: {e}")
                        traceback.print_exc()
                        continue

                    # Add persistent registered list view
                    print("[on_ready] Adding PersistentRegisteredListView...")
                    try:
                        bot.add_view(PersistentRegisteredListView(guild))
                        print(f"[on_ready] • Added PersistentRegisteredListView for guild {guild.name}")
                    except Exception as e:
                        print(f"[on_ready] ERROR adding PersistentRegisteredListView: {e}")
                        logging.error(f"Failed to add PersistentRegisteredListView: {e}")
                        traceback.print_exc()

                    # Add registration view if exists
                    print("[on_ready] Checking registration view...")
                    try:
                        reg_chan_id, reg_msg_id = get_persisted_msg(guild.id, "registration")
                        print(f"[on_ready] Registration persisted: chan_id={reg_chan_id}, msg_id={reg_msg_id}")
                        if reg_chan_id and reg_msg_id:
                            bot.add_view(RegistrationView(reg_msg_id, guild))
                            print(f"[on_ready] • Added persistent RegistrationView for message {reg_msg_id}")
                        else:
                            print("[on_ready] • No registration message to attach view to")
                    except Exception as e:
                        print(f"[on_ready] ERROR with registration view: {e}")
                        logging.error(f"Failed to add registration view: {e}")
                        traceback.print_exc()

                    # Add check-in view if exists
                    print("[on_ready] Checking check-in view...")
                    try:
                        ci_chan_id, ci_msg_id = get_persisted_msg(guild.id, "checkin")
                        print(f"[on_ready] Check-in persisted: chan_id={ci_chan_id}, msg_id={ci_msg_id}")
                        if ci_chan_id and ci_msg_id:
                            bot.add_view(CheckInView(guild))
                            print(f"[on_ready] • Added persistent CheckInView for message {ci_msg_id}")
                        else:
                            print("[on_ready] • No check-in message to attach view to")
                    except Exception as e:
                        print(f"[on_ready] ERROR with check-in view: {e}")
                        logging.error(f"Failed to add check-in view: {e}")
                        traceback.print_exc()

                    # Update all embeds - use the helper
                    print("[on_ready] Updating embeds...")
                    try:
                        embed_results = await EmbedHelper.update_all_guild_embeds(guild)
                        print(f"[on_ready] • Live embeds updated for guild {guild.name}: {embed_results}")
                    except Exception as e:
                        print(f"[on_ready] ERROR updating embeds: {e}")
                        logging.error(f"Failed to update embeds: {e}")
                        traceback.print_exc()

                    print(f"[on_ready] Completed processing for guild {guild.name}")

                except Exception as e:
                    print(f"[on_ready] ERROR processing guild {guild.name}: {e}")
                    logging.error(f"Failed to process guild {guild.name}: {e}")
                    traceback.print_exc()

            # Apply rich presence using ConfigManager
            print("[on_ready] Setting rich presence...")
            try:
                await ConfigManager.apply_rich_presence(bot)
                print(f"[on_ready] • Rich presence set")
            except Exception as e:
                print(f"[on_ready] ERROR setting rich presence: {e}")
                logging.error(f"Failed to set rich presence: {e}")
                traceback.print_exc()

            # Start cache refresh loop if not already running
            print("[on_ready] Starting cache refresh loop...")
            try:
                if not hasattr(bot, '_cache_refresh_task'):
                    bot._cache_refresh_task = asyncio.create_task(cache_refresh_loop(bot))
                    print("[on_ready] • Started cache refresh background task")
                else:
                    print("[on_ready] • Cache refresh task already running")
            except Exception as e:
                print(f"[on_ready] ERROR starting cache refresh: {e}")
                logging.error(f"Failed to start cache refresh loop: {e}")
                traceback.print_exc()

            logging.info("Bot on_ready completed successfully")
            print("[on_ready] ✅ Bot is fully ready!")

        except Exception as e:
            print(f"[on_ready] CRITICAL ERROR: {e}")
            logging.error(f"Critical error in on_ready: {e}")
            traceback.print_exc()

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
        set_schedule(guild.id, f"{etype}_open", None)
        set_schedule(guild.id, f"{etype}_close", None)

        # Send deletion embed
        log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_ch:
            open_ts = int(event.start_time.timestamp()) if event.start_time else None
            close_ts = int(event.end_time.timestamp()) if event.end_time else None
            embed = embed_from_cfg(
                "schedule_deleted",
                type=etype.capitalize(),
                event=event.name,
                open_ts=open_ts,
                close_ts=close_ts
            )
            await log_ch.send(embed=embed)