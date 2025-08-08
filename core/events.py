# core/events.py

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from config import CHECK_IN_CHANNEL, REGISTRATION_CHANNEL
from core.persistence import get_persisted_msg
from helpers import BotLogger, ErrorHandler, ErrorCategory, ErrorSeverity

# Import functions with error handling
try:
    from integrations.sheets import refresh_sheet_cache
except ImportError:
    BotLogger.warning("Sheet cache refresh not available in events", "EVENTS")


    async def refresh_sheet_cache(*args, **kwargs):
        pass

try:
    from helpers import EmbedHelper
except ImportError:
    BotLogger.warning("EmbedHelper not available in events", "EVENTS")
    EmbedHelper = None

try:
    from config import update_gal_command_ids
except ImportError:
    try:
        from utils.utils import update_gal_command_ids
    except ImportError:
        BotLogger.warning("Command ID updates not available in events", "EVENTS")


        async def update_gal_command_ids(*args, **kwargs):
            pass


async def cache_refresh_loop(bot: commands.Bot):
    """Background task for periodic cache refresh."""
    while not getattr(bot, '_shutdown_requested', False):
        try:
            await asyncio.sleep(600)  # Wait 10 minutes

            if getattr(bot, '_shutdown_requested', False):
                break

            BotLogger.info("Starting periodic cache refresh", "CACHE_REFRESH")
            await refresh_sheet_cache(bot=bot)
            BotLogger.success("Periodic cache refresh completed", "CACHE_REFRESH")

        except asyncio.CancelledError:
            BotLogger.info("Cache refresh loop cancelled", "CACHE_REFRESH")
            break
        except Exception as e:
            BotLogger.error(f"Cache refresh loop error: {e}", "CACHE_REFRESH")


async def _startup_initialization(bot: commands.Bot):
    """
    Handle startup initialization that must occur after the bot is ready.
    This runs as a separate background task after Discord connection is established.
    """
    BotLogger.info("Starting background initialization process", "STARTUP")

    try:
        # Command system setup
        BotLogger.info("Updating Discord command IDs for help system", "STARTUP")
        await update_gal_command_ids(bot)
        BotLogger.success("Command IDs updated successfully", "STARTUP")

        # Guild processing with enhanced error handling
        for guild in bot.guilds:
            guild_name = guild.name
            BotLogger.info(f"Initializing guild: {guild_name}", "STARTUP")

            try:
                # Import views with error handling
                try:
                    from core.views import RegistrationView, CheckInView, PersistentRegisteredListView
                    BotLogger.debug(f"Successfully imported view classes for {guild_name}", "STARTUP")
                except ImportError as e:
                    BotLogger.error(f"Failed to import view classes for {guild_name}: {e}", "STARTUP")
                    continue

                # Add persistent registered list view (always available) - FIXED: Add custom_id and timeout=None
                try:
                    list_view = PersistentRegisteredListView(guild)
                    # Make sure the view is persistent by setting timeout to None in the view itself
                    bot.add_view(list_view)
                    BotLogger.debug(f"Added PersistentRegisteredListView for {guild_name}", "STARTUP")
                except Exception as e:
                    BotLogger.error(f"Failed to add PersistentRegisteredListView for {guild_name}: {e}", "STARTUP")

                # Add registration view if persisted message exists
                try:
                    reg_channel_id, reg_msg_id = get_persisted_msg(guild.id, "registration")
                    if reg_channel_id and reg_msg_id:
                        bot.add_view(RegistrationView(reg_msg_id, guild))
                        BotLogger.debug(f"Added RegistrationView for {guild_name}", "STARTUP")
                except Exception as e:
                    BotLogger.error(f"Failed to add RegistrationView for {guild_name}: {e}", "STARTUP")

                # Add check-in view if persisted message exists
                try:
                    checkin_channel_id, checkin_msg_id = get_persisted_msg(guild.id, "checkin")
                    if checkin_channel_id and checkin_msg_id:
                        bot.add_view(CheckInView(guild))
                        BotLogger.debug(f"Added CheckInView for {guild_name}", "STARTUP")
                except Exception as e:
                    BotLogger.error(f"Failed to add CheckInView for {guild_name}: {e}", "STARTUP")

            except Exception as e:
                BotLogger.error(f"Guild initialization failed for {guild_name}: {e}", "STARTUP")
                continue

        # Cache refresh loop setup
        BotLogger.info("Setting up cache refresh background task", "STARTUP")
        try:
            if not hasattr(bot, '_cache_refresh_task'):
                bot._cache_refresh_task = asyncio.create_task(cache_refresh_loop(bot))
                BotLogger.success("Started cache refresh background task", "STARTUP")
            else:
                BotLogger.debug("Cache refresh task already running", "STARTUP")
        except Exception as e:
            BotLogger.error(f"Failed to start cache refresh loop: {e}", "STARTUP")

        # Initial cache refresh
        BotLogger.info("Starting initial cache refresh (this may take a moment)", "STARTUP")
        try:
            await refresh_sheet_cache(bot=bot)
            BotLogger.success("Initial cache refresh completed successfully", "STARTUP")
        except Exception as e:
            BotLogger.error(f"Initial cache refresh failed: {e}", "STARTUP")

        # Embed updates
        BotLogger.info("Updating all guild embeds with fresh data", "STARTUP")
        try:
            for guild in bot.guilds:
                if EmbedHelper:
                    embed_results = await EmbedHelper.update_all_guild_embeds(guild)
                    successful_updates = sum(1 for success in embed_results.values() if success)
                    total_embeds = len(embed_results)
                    BotLogger.info(
                        f"Updated embeds for {guild.name}: {successful_updates}/{total_embeds} successful",
                        "STARTUP"
                    )
                else:
                    BotLogger.debug(f"Skipping embed updates for {guild.name} - EmbedHelper not available", "STARTUP")
        except Exception as e:
            BotLogger.error(f"Failed to update embeds during startup: {e}", "STARTUP")

        # Startup completion
        BotLogger.success("Background initialization completed successfully!", "STARTUP")

    except Exception as e:
        BotLogger.error(f"Critical error during background initialization: {e}", "STARTUP")
        BotLogger.error(f"Startup traceback: {traceback.format_exc()}", "STARTUP")


def setup_events(bot: commands.Bot):
    """
    Set up all Discord event handlers for the bot with comprehensive error handling.
    Registers event listeners for bot lifecycle and scheduled events.
    """

    @bot.event
    async def on_ready():
        """
        Called when the bot successfully connects to Discord.
        Initiates non-blocking background initialization.
        """
        try:
            BotLogger.success(f"🤖 {bot.user} has connected to Discord!", "BOT_READY")
            BotLogger.info(f"Bot ID: {bot.user.id}", "BOT_READY")
            BotLogger.info(f"Connected to {len(bot.guilds)} guild(s)", "BOT_READY")

            # Log guild information
            for guild in bot.guilds:
                member_count = guild.member_count or len(guild.members)
                BotLogger.info(f"  - {guild.name} (ID: {guild.id}, Members: {member_count})", "BOT_READY")

            # Set bot status
            activity = discord.Activity(type=discord.ActivityType.watching, name="for GAL tournaments")
            await bot.change_presence(activity=activity)

            # Mark as ready and start background initialization - FIXED: Use correct attribute name
            if hasattr(bot, '_bot_is_ready'):
                bot._bot_is_ready = True
            if hasattr(bot, '_health_status'):
                bot._health_status["bot_ready"] = True

            # Start background initialization (non-blocking)
            asyncio.create_task(_startup_initialization(bot))

            # Send startup logs to guilds
            startup_info = {
                "bot_name": bot.user.name,
                "bot_id": bot.user.id,
                "guild_count": len(bot.guilds),
                "startup_duration": 0.0  # Will be updated by main bot class
            }

            for guild in bot.guilds:
                try:
                    await BotLogger.send_startup_log(guild, startup_info)
                except Exception as e:
                    BotLogger.debug(f"Could not send startup log to {guild.name}: {e}", "BOT_READY")

        except Exception as e:
            if ErrorHandler:
                await ErrorHandler.handle_interaction_error(
                    None, e, "on_ready",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.DISCORD_API
                )
            else:
                BotLogger.error(f"Error in on_ready event: {e}", "BOT_READY")

    @bot.event
    async def on_guild_scheduled_event_create(event):
        """Handle creation of scheduled events with intelligent channel management."""
        try:
            BotLogger.info(f"Scheduled event created: '{event.name}' in {event.guild.name}", "SCHEDULED_EVENT")

            # Import channel helpers with error handling
            try:
                from helpers import ChannelManager, open_channel_immediate

                # Auto-open registration for tournament events
                if any(keyword in event.name.lower() for keyword in ['tournament', 'gal', 'tft']):
                    await open_channel_immediate(event.guild, "registration", ping_role=True)
                    BotLogger.info(f"Auto-opened registration for tournament event: {event.name}", "SCHEDULED_EVENT")

            except ImportError:
                BotLogger.debug("Channel management not available for scheduled events", "SCHEDULED_EVENT")

        except Exception as e:
            BotLogger.error(f"Error handling scheduled event creation: {e}", "SCHEDULED_EVENT")

    @bot.event
    async def on_guild_scheduled_event_update(before, after):
        """Handle updates to scheduled events with status-based channel management."""
        try:
            if before.status != after.status:
                BotLogger.info(
                    f"Event '{after.name}' status changed: {before.status.name} → {after.status.name}",
                    "SCHEDULED_EVENT"
                )

                # Import channel helpers with error handling
                try:
                    from helpers import ChannelManager, open_channel_immediate, close_channel_immediate

                    # Handle tournament events
                    if any(keyword in after.name.lower() for keyword in ['tournament', 'gal', 'tft']):
                        if after.status == discord.EventStatus.active:
                            # Event started - open check-in
                            await open_channel_immediate(after.guild, "checkin", ping_role=True)
                            BotLogger.info(f"Auto-opened check-in for active tournament: {after.name}",
                                           "SCHEDULED_EVENT")
                        elif after.status in [discord.EventStatus.completed, discord.EventStatus.cancelled]:
                            # Event ended - close channels
                            await close_channel_immediate(after.guild, "registration")
                            await close_channel_immediate(after.guild, "checkin")
                            BotLogger.info(f"Auto-closed channels for ended tournament: {after.name}",
                                           "SCHEDULED_EVENT")

                except ImportError:
                    BotLogger.debug("Channel management not available for event updates", "SCHEDULED_EVENT")

        except Exception as e:
            BotLogger.error(f"Error handling scheduled event update: {e}", "SCHEDULED_EVENT")

    @bot.event
    async def on_member_join(member):
        """Handle new member joins with DM action view updates."""
        try:
            BotLogger.info(f"New member joined {member.guild.name}: {member.name}", "MEMBER_JOIN")

            # Update DM action views if available
            try:
                from utils.utils import update_dm_action_views
                await update_dm_action_views(member.guild, [member])
                BotLogger.debug(f"Updated DM action views for new member: {member.name}", "MEMBER_JOIN")
            except ImportError:
                BotLogger.debug("DM action view updates not available", "MEMBER_JOIN")

        except Exception as e:
            BotLogger.error(f"Error handling member join: {e}", "MEMBER_JOIN")

    @bot.event
    async def on_member_remove(member):
        """Handle member leaves with cleanup."""
        try:
            BotLogger.info(f"Member left {member.guild.name}: {member.name}", "MEMBER_LEAVE")

            # Could add cleanup logic here if needed
            # e.g., remove from tournaments, update sheets, etc.

        except Exception as e:
            BotLogger.error(f"Error handling member leave: {e}", "MEMBER_LEAVE")

    @bot.event
    async def on_application_command_error(interaction: discord.Interaction, error: Exception):
        """Handle slash command errors with comprehensive logging and user feedback."""
        try:
            if ErrorHandler:
                await ErrorHandler.handle_interaction_error(
                    interaction, error, "slash_command",
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.USER_INPUT
                )
            else:
                BotLogger.error(f"Slash command error: {error}", "COMMAND_ERROR")

                # Send basic error response if not already responded
                if not interaction.response.is_done():
                    try:
                        await interaction.response.send_message(
                            "❌ An error occurred while processing your command. Please try again.",
                            ephemeral=True
                        )
                    except Exception:
                        pass  # Interaction might have expired

        except Exception as e:
            BotLogger.error(f"Error in command error handler: {e}", "COMMAND_ERROR")

    @bot.event
    async def on_error(event, *args, **kwargs):
        """Handle general bot errors."""
        try:
            BotLogger.error(f"Bot event error in '{event}': {args}, {kwargs}", "BOT_ERROR")
        except Exception as e:
            BotLogger.error(f"Error in error handler: {e}", "BOT_ERROR")

    BotLogger.info("Event handlers registered successfully", "EVENTS")


# Export the setup function
__all__ = ['setup_events']