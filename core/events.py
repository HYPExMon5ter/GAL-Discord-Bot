# core/events.py

import asyncio
import logging
import traceback
from datetime import datetime  # Only needed for fromisoformat parsing
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from rapidfuzz import fuzz

from config import (
    embed_from_cfg, update_gal_command_ids, get_log_channel_name, get_unified_channel_name, _FULL_CFG
)
from core.persistence import set_schedule, persisted, save_persisted
from helpers.schedule_helpers import ScheduleHelper

# In-memory caches for events
scheduled_event_cache: dict = {}
open_tasks: dict = {}
close_tasks: dict = {}

# Track recent pings to prevent spam
recent_pings: dict = {}  # guild_id -> timestamp


def match_event_type(name: str) -> str | None:
    """Match Discord event name to system type."""
    lc = name.lower()
    for kw in ("registration", "register", "reg"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "registration"
    for kw in ("check-in", "checkin", "check in", "check"):
        if fuzz.partial_ratio(lc, kw) >= 80:
            return "checkin"
    return None


async def schedule_system_open(
        bot,
        guild: discord.Guild,
        system_type: str,  # "registration" or "checkin"
        open_time: datetime,
        is_scheduled_event: bool = True
):
    """Schedule a system to open at a specific time."""
    now = discord.utils.utcnow()
    wait = (open_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    guild_id = str(guild.id)
    if guild_id not in persisted:
        persisted[guild_id] = {}

    # Clear the schedule FIRST to prevent duplicate executions
    set_schedule(guild.id, f"{system_type}_open", None)

    # Update state
    if system_type == "registration":
        persisted[guild_id]["registration_open"] = True
    elif system_type == "checkin":
        persisted[guild_id]["checkin_open"] = True

    save_persisted(persisted)

    # Update the unified channel with Components V2
    from core.components_traditional import update_unified_channel
    await update_unified_channel(guild)

    # Log if scheduled event
    if is_scheduled_event:
        log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())
        if log_channel:
            open_ts = int(open_time.timestamp())
            embed = embed_from_cfg(
                "schedule_open",
                type=system_type.capitalize(),
                event=f"{system_type.capitalize()} Event",
                open_ts=open_ts,
                close_str=""
            )
            await log_channel.send(embed=embed)

    # Send role ping to unified channel (if enabled) - with spam prevention
    unified_channel = discord.utils.get(guild.text_channels, name=get_unified_channel_name())
    if unified_channel:
        roles_config = _FULL_CFG.get("roles", {})
        now_timestamp = discord.utils.utcnow().timestamp()

        # Check if we recently pinged for this guild (within 30 seconds)
        last_ping = recent_pings.get(guild.id, 0)
        if now_timestamp - last_ping < 30:
            logging.info(f"Skipping ping for {system_type} in {guild.name} - recently pinged")
        else:
            ping_sent = False

            if system_type == "registration" and roles_config.get("ping_on_registration_open", True):
                # Ping Angels role when registration opens
                angel_role_name = roles_config.get("angel_role", "Angels")
                angel_role = discord.utils.get(guild.roles, name=angel_role_name)
                if angel_role:
                    ping_msg = await unified_channel.send(f"🎫 **Registration is now OPEN!** {angel_role.mention}")
                    ping_sent = True
                    # Delete ping message after 5 seconds to avoid clutter
                    await asyncio.sleep(5)
                    try:
                        await ping_msg.delete()
                    except discord.NotFound:
                        pass
                else:
                    logging.warning(f"Angel role '{angel_role_name}' not found in guild {guild.name}")

            elif system_type == "checkin" and roles_config.get("ping_on_checkin_open", True):
                # Ping Registered role when check-in opens
                registered_role_name = roles_config.get("registered_role", "Registered")
                registered_role = discord.utils.get(guild.roles, name=registered_role_name)
                if registered_role:
                    ping_msg = await unified_channel.send(f"✅ **Check-in is now OPEN!** {registered_role.mention}")
                    ping_sent = True
                    # Delete ping message after 5 seconds to avoid clutter
                    await asyncio.sleep(5)
                    try:
                        await ping_msg.delete()
                    except discord.NotFound:
                        pass
                else:
                    logging.warning(f"Registered role '{registered_role_name}' not found in guild {guild.name}")

            # Update last ping time if we sent a ping
            if ping_sent:
                recent_pings[guild.id] = now_timestamp

                # Clean up old entries (older than 5 minutes) to prevent memory leaks
                cutoff = now_timestamp - 300  # 5 minutes
                recent_pings.clear()  # Simple cleanup - clear all since we only care about recent pings
                recent_pings[guild.id] = now_timestamp

    logging.info(f"Opened {system_type} for guild {guild.id}")


async def schedule_system_close(
        bot,
        guild: discord.Guild,
        system_type: str,  # "registration" or "checkin"
        close_time: datetime,
        is_scheduled_event: bool = True
):
    """Schedule a system to close at a specific time."""
    now = discord.utils.utcnow()
    wait = (close_time - now).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    guild_id = str(guild.id)
    if guild_id not in persisted:
        persisted[guild_id] = {}

    # Clear the schedule FIRST to prevent duplicate executions
    set_schedule(guild.id, f"{system_type}_close", None)

    # Update state
    if system_type == "registration":
        persisted[guild_id]["registration_open"] = False
    elif system_type == "checkin":
        persisted[guild_id]["checkin_open"] = False

    save_persisted(persisted)

    # Update the unified channel with Components V2
    from core.components_traditional import update_unified_channel
    await update_unified_channel(guild)

    # Log if scheduled event
    if is_scheduled_event:
        log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())
        if log_channel:
            close_ts = int(close_time.timestamp())
            embed = embed_from_cfg(
                "schedule_close",
                type=system_type.capitalize(),
                event=f"{system_type.capitalize()} Event",
                close_ts=close_ts
            )
            await log_channel.send(embed=embed)

    logging.info(f"Closed {system_type} for guild {guild.id}")


async def _handle_event_schedule(bot, event, is_edit: bool):
    """Handle Discord scheduled event creation/edit."""
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

    # Validate schedule times and log warnings
    try:
        reg_open_ts, reg_close_ts, ci_open_ts, ci_close_ts = ScheduleHelper.get_all_schedule_times(guild.id)
        validation = ScheduleHelper.validate_schedule_times(reg_open_ts, reg_close_ts, ci_open_ts, ci_close_ts)

        if not validation["is_valid"]:
            for warning in validation["warnings"]:
                logging.warning(f"Schedule validation for {guild.name} ({guild.id}): {warning}")
    except Exception as e:
        logging.error(f"Failed to validate schedule times for {guild.name}: {e}")

    now = discord.utils.utcnow()

    # Schedule open
    if open_time and open_time > now:
        open_tasks[(guild.id, event.id, "open")] = asyncio.create_task(
            schedule_system_open(bot, guild, etype, open_time)
        )
    elif open_time and open_time <= now:
        # Fire immediately
        await schedule_system_open(bot, guild, etype, now, is_scheduled_event=False)

    # Schedule close
    if close_time and close_time > now:
        close_tasks[(guild.id, event.id, "close")] = asyncio.create_task(
            schedule_system_close(bot, guild, etype, close_time)
        )
    elif close_time and close_time <= now:
        # Fire immediately
        await schedule_system_close(bot, guild, etype, now, is_scheduled_event=False)

    # Log creation/edit
    log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())
    if log_channel:
        open_ts = int(event.start_time.timestamp()) if event.start_time else None
        close_ts = int(event.end_time.timestamp()) if event.end_time else None
        key_name = "schedule_edited" if is_edit else "schedule_created"

        close_str = f"\nCloses at: <t:{close_ts}:F>" if close_ts else ""

        embed = embed_from_cfg(
            key_name,
            type=etype.capitalize(),
            event=event.name,
            open_ts=open_ts,
            close_ts=close_ts,
            close_str=close_str
        )
        await log_channel.send(embed=embed)

    # Update the unified channel to reflect schedule changes
    from core.components_traditional import update_unified_channel
    await update_unified_channel(guild)


def setup_events(bot: commands.Bot):
    """Setup all event handlers for the bot."""

    @bot.event
    async def on_ready():
        """
        Called when the bot has finished logging in and setting up.
        This is the main startup event with Components V2 integration.
        """
        logging.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")

        try:
            # ============================================
            # 1. UPDATE COMMAND IDS
            # ============================================
            await update_gal_command_ids(bot)
            logging.info("Updated GAL command IDs for help system")

            # ============================================
            # 2. PROCESS EACH GUILD
            # ============================================
            for guild in bot.guilds:
                try:
                    logging.info(f"Processing guild: {guild.name} ({guild.id})")

                    # ----------------------------------------
                    # 2a. Refresh Google Sheets Cache
                    # ----------------------------------------
                    from integrations.sheets import refresh_sheet_cache
                    await refresh_sheet_cache(bot=bot)
                    logging.info(f"Cache refreshed for guild {guild.name} ({guild.id})")

                    # ----------------------------------------
                    # 2b. Setup Unified Channel with Components V2
                    # ----------------------------------------
                    from core.components_traditional import setup_unified_channel
                    success = await setup_unified_channel(guild)
                    if success:
                        logging.info(f"✅ Setup unified Components V2 channel for {guild.name}")
                    else:
                        logging.warning(f"⚠️ Failed to setup unified channel for {guild.name}")

                    # ----------------------------------------
                    # 2c. Setup Onboard System
                    # ----------------------------------------
                    from core.onboard import setup_onboard_channel
                    onboard_success = await setup_onboard_channel(guild, bot)
                    if onboard_success:
                        logging.info(f"✅ Setup onboard system for {guild.name}")
                    else:
                        logging.warning(f"⚠️ Failed to setup onboard system for {guild.name}")

                    # ----------------------------------------
                    # 2d. Restore Scheduled Events (if any)
                    # ----------------------------------------
                    from core.persistence import get_schedule

                    # Check for scheduled registration times
                    reg_open_iso = get_schedule(guild.id, "registration_open")
                    reg_close_iso = get_schedule(guild.id, "registration_close")

                    if reg_open_iso:
                        try:
                            reg_open_time = datetime.fromisoformat(reg_open_iso).astimezone(ZoneInfo("UTC"))
                            now = discord.utils.utcnow()

                            if reg_open_time > now:
                                # Schedule for future
                                key = (guild.id, "registration", "open")
                                open_tasks[key] = asyncio.create_task(
                                    schedule_system_open(bot, guild, "registration", reg_open_time)
                                )
                                logging.info(f"Restored registration open schedule for {guild.name}")
                            elif reg_open_time <= now:
                                # Past event - check if already processed
                                guild_id = str(guild.id)
                                if guild_id not in persisted:
                                    persisted[guild_id] = {}

                                current_state = persisted[guild_id].get("registration_open", False)
                                if not current_state:
                                    # Event hasn't been processed yet
                                    persisted[guild_id]["registration_open"] = True
                                    save_persisted(persisted)
                                    logging.info(f"Applied past registration open for {guild.name}")
                                else:
                                    # Already processed, clear the schedule to prevent loops
                                    set_schedule(guild.id, "registration_open", None)
                                    logging.info(
                                        f"Registration already open for {guild.name} - cleared schedule to prevent loops")
                        except Exception as e:
                            logging.error(f"Failed to restore registration open schedule: {e}")

                    if reg_close_iso:
                        try:
                            reg_close_time = datetime.fromisoformat(reg_close_iso).astimezone(ZoneInfo("UTC"))
                            now = discord.utils.utcnow()

                            if reg_close_time > now:
                                # Schedule for future
                                key = (guild.id, "registration", "close")
                                close_tasks[key] = asyncio.create_task(
                                    schedule_system_close(bot, guild, "registration", reg_close_time)
                                )
                                logging.info(f"Restored registration close schedule for {guild.name}")
                            elif reg_close_time <= now:
                                # Past event - check if already processed
                                guild_id = str(guild.id)
                                if guild_id not in persisted:
                                    persisted[guild_id] = {}

                                current_state = persisted[guild_id].get("registration_open", False)
                                if current_state:
                                    # Event hasn't been processed yet - should be closed
                                    persisted[guild_id]["registration_open"] = False
                                    save_persisted(persisted)
                                    logging.info(f"Applied past registration close for {guild.name}")
                                else:
                                    # Already processed, clear the schedule to prevent loops
                                    set_schedule(guild.id, "registration_close", None)
                                    logging.info(
                                        f"Registration already closed for {guild.name} - cleared schedule to prevent loops")
                        except Exception as e:
                            logging.error(f"Failed to restore registration close schedule: {e}")

                    # Check for scheduled check-in times
                    ci_open_iso = get_schedule(guild.id, "checkin_open")
                    ci_close_iso = get_schedule(guild.id, "checkin_close")

                    if ci_open_iso:
                        try:
                            ci_open_time = datetime.fromisoformat(ci_open_iso).astimezone(ZoneInfo("UTC"))
                            now = discord.utils.utcnow()

                            if ci_open_time > now:
                                # Schedule for future
                                key = (guild.id, "checkin", "open")
                                open_tasks[key] = asyncio.create_task(
                                    schedule_system_open(bot, guild, "checkin", ci_open_time)
                                )
                                logging.info(f"Restored check-in open schedule for {guild.name}")
                            elif ci_open_time <= now:
                                # Past event - check if already processed
                                guild_id = str(guild.id)
                                if guild_id not in persisted:
                                    persisted[guild_id] = {}

                                current_state = persisted[guild_id].get("checkin_open", False)
                                if not current_state:
                                    # Event hasn't been processed yet
                                    persisted[guild_id]["checkin_open"] = True
                                    save_persisted(persisted)
                                    logging.info(f"Applied past check-in open for {guild.name}")
                                else:
                                    # Already processed, clear the schedule to prevent loops
                                    set_schedule(guild.id, "checkin_open", None)
                                    logging.info(
                                        f"Check-in already open for {guild.name} - cleared schedule to prevent loops")
                        except Exception as e:
                            logging.error(f"Failed to restore check-in open schedule: {e}")

                    if ci_close_iso:
                        try:
                            ci_close_time = datetime.fromisoformat(ci_close_iso).astimezone(ZoneInfo("UTC"))
                            now = discord.utils.utcnow()

                            if ci_close_time > now:
                                # Schedule for future
                                key = (guild.id, "checkin", "close")
                                close_tasks[key] = asyncio.create_task(
                                    schedule_system_close(bot, guild, "checkin", ci_close_time)
                                )
                                logging.info(f"Restored check-in close schedule for {guild.name}")
                            elif ci_close_time <= now:
                                # Past event - check if already processed
                                guild_id = str(guild.id)
                                if guild_id not in persisted:
                                    persisted[guild_id] = {}

                                current_state = persisted[guild_id].get("checkin_open", False)
                                if current_state:
                                    # Event hasn't been processed yet - should be closed
                                    persisted[guild_id]["checkin_open"] = False
                                    save_persisted(persisted)
                                    logging.info(f"Applied past check-in close for {guild.name}")
                                else:
                                    # Already processed, clear the schedule to prevent loops
                                    set_schedule(guild.id, "checkin_close", None)
                                    logging.info(
                                        f"Check-in already closed for {guild.name} - cleared schedule to prevent loops")
                        except Exception as e:
                            logging.error(f"Failed to restore check-in close schedule: {e}")

                    # ----------------------------------------
                    # 2d. Process Waitlist (if any spots available)
                    # ----------------------------------------
                    try:
                        from helpers.waitlist_helpers import WaitlistManager
                        registered = await WaitlistManager.process_waitlist(guild)
                        if registered:
                            logging.info(f"Auto-registered {len(registered)} users from waitlist in {guild.name}")
                    except Exception as e:
                        logging.warning(f"Failed to process waitlist for {guild.name}: {e}")

                except Exception as e:
                    logging.error(f"Failed to process guild {guild.name}: {e}")
                    traceback.print_exc()

            # ============================================
            # 3. SET BOT RICH PRESENCE
            # ============================================
            from helpers import ConfigManager
            try:
                await ConfigManager.apply_rich_presence(bot)
                logging.info("Rich presence set successfully")
            except Exception as e:
                logging.error(f"Failed to set rich presence: {e}")

            # ============================================
            # 4. START BACKGROUND TASKS
            # ============================================

            # Start cache refresh loop
            try:
                from integrations.sheets import cache_refresh_loop
                if not hasattr(bot, '_cache_refresh_task'):
                    bot._cache_refresh_task = asyncio.create_task(cache_refresh_loop(bot))
                    logging.info("Started cache refresh background task")
            except Exception as e:
                logging.error(f"Failed to start cache refresh loop: {e}")

            # ============================================
            # 5. LOG STARTUP SUMMARY
            # ============================================
            logging.info("=" * 50)
            logging.info("✅ Bot is fully ready with Components V2!")
            logging.info(f"Connected to {len(bot.guilds)} guild(s)")
            logging.info(f"Using unified channel with Components V2")
            logging.info(f"Cache refresh interval: {persisted.get('cache_refresh_seconds', 600)}s")
            logging.info("=" * 50)

        except Exception as e:
            logging.error(f"Critical error in on_ready: {e}")
            traceback.print_exc()

    @bot.event
    async def on_scheduled_event_create(event):
        """Handle Discord scheduled event creation."""
        await _handle_event_schedule(bot, event, is_edit=False)

    @bot.event
    async def on_scheduled_event_update(_, event):
        """Handle Discord scheduled event update."""
        await _handle_event_schedule(bot, event, is_edit=True)

    @bot.event
    async def on_scheduled_event_delete(event):
        """Handle Discord scheduled event deletion."""
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
        log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())
        if log_channel:
            open_ts = int(event.start_time.timestamp()) if event.start_time else None
            close_ts = int(event.end_time.timestamp()) if event.end_time else None
            embed = embed_from_cfg(
                "schedule_deleted",
                type=etype.capitalize(),
                event=event.name,
                open_ts=open_ts,
                close_ts=close_ts
            )
            await log_channel.send(embed=embed)

        # Update the unified channel to reflect the change
        from core.components_traditional import update_unified_channel
        await update_unified_channel(guild)

    @bot.event
    async def on_guild_join(new_guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logging.info(f"Joined new guild: {new_guild.name} ({new_guild.id})")

        try:
            # Initialize for new guild
            from integrations.sheets import refresh_sheet_cache
            await refresh_sheet_cache(bot=bot)

            # Setup unified channel
            from core.components_traditional import setup_unified_channel
            await setup_unified_channel(new_guild)

            logging.info(f"Initialized Components V2 for new guild {new_guild.name}")
        except Exception as e:
            logging.error(f"Failed to initialize new guild {new_guild.name}: {e}")

    @bot.event
    async def on_guild_remove(old_guild: discord.Guild):
        """Called when the bot is removed from a guild."""
        logging.info(f"Removed from guild: {old_guild.name} ({old_guild.id})")

        # Cancel any scheduled tasks for this guild
        guild_id = old_guild.id
        for key in list(open_tasks.keys()):
            if key[0] == guild_id:
                if not open_tasks[key].done():
                    open_tasks[key].cancel()
                del open_tasks[key]

        for key in list(close_tasks.keys()):
            if key[0] == guild_id:
                if not close_tasks[key].done():
                    close_tasks[key].cancel()
                del close_tasks[key]

    @bot.event
    async def on_member_join(member: discord.Member):
        """Called when a member joins the guild."""
        # Check if they're in the sheet cache and sync roles
        try:
            from integrations.sheets import sheet_cache, cache_lock
            from helpers import RoleManager

            discord_tag = str(member)

            async with cache_lock:
                user_data = sheet_cache["users"].get(discord_tag)

            if user_data:
                # User is in our database, sync their roles
                _, _, reg, ci, _, _, _ = user_data
                is_registered = str(reg).upper() == "TRUE"
                is_checked_in = str(ci).upper() == "TRUE"

                await RoleManager.sync_user_roles(member, is_registered, is_checked_in)
                logging.info(f"Synced roles for returning member {discord_tag}")
        except Exception as e:
            logging.error(f"Failed to sync roles for new member {member}: {e}")

    @bot.event
    async def on_member_remove(member: discord.Member):
        """Called when a member leaves the guild."""
        logging.info(f"Member left: {member} from {member.guild.name}")

        # Note: We don't remove them from the sheet, they might come back
        # Their registration stays intact

    @bot.event
    async def on_error(event_method: str, *args, **kwargs):
        """Global error handler for events."""
        logging.error(f"Error in {event_method}", exc_info=True)
