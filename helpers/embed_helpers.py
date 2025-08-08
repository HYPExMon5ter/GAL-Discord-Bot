# helpers/embed_helpers.py
"""
Discord embed management helper module.

This module provides comprehensive utilities for managing Discord embeds throughout
the GAL Discord Bot. It handles embed creation, updates, persistence, and user
notification systems with robust error handling and logging.

Key Features:
- Persisted embed management with automatic updates
- Error logging with channel and console fallbacks
- DM action view refreshing for user notifications
- Registration list formatting with intelligent color cycling
- Guild-wide embed synchronization with batch operations
- Comprehensive error handling and recovery mechanisms

The module is designed to be resilient and gracefully handle missing dependencies
while maintaining core functionality.
"""

import logging
import random
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List, Any, Union

import discord

from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER
from core.persistence import get_persisted_msg, set_persisted_msg

# Import helpers with fallbacks for graceful degradation
try:
    from helpers.logging_helper import BotLogger
except ImportError:
    BotLogger = None
    logging.warning("BotLogger not available, using standard logging")

try:
    from helpers.error_handler import ErrorHandler, ErrorCategory, ErrorContext, ErrorSeverity
except ImportError:
    # Create minimal fallbacks
    class ErrorSeverity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


    class ErrorCategory:
        DISCORD_API = "discord_api"
        PERMISSIONS = "permissions"
        UNKNOWN = "unknown"


    class ErrorContext:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


    class ErrorHandler:
        @staticmethod
        async def handle_interaction_error(interaction, error, operation, **kwargs):
            if BotLogger:
                BotLogger.error(f"Error in {operation}: {error}", "ERROR_HANDLER")
            else:
                logging.error(f"Error in {operation}: {error}")


    logging.warning("ErrorHandler not available, using fallback implementations")


class EmbedError(Exception):
    """
    Custom exception for embed-related errors.

    Provides specific context for embed operations that fail, allowing
    for better error handling and user feedback in the bot.
    """

    def __init__(self, message: str, embed_key: str = "", context: Dict[str, Any] = None):
        """
        Initialize embed error with detailed context information.

        Args:
            message: Human-readable error description
            embed_key: Configuration key that failed (if applicable)
            context: Additional error context for debugging
        """
        super().__init__(message)
        self.embed_key = embed_key
        self.context = context or {}


async def log_error(bot: Optional[discord.Client], guild: Optional[discord.Guild],
                    message: str, level: str = "Error") -> None:
    """
    Log error messages to both Discord channel and console with fallback handling.

    This function provides a centralized way to log errors throughout the bot,
    with automatic fallback to console logging if Discord logging fails.

    Args:
        bot: Discord bot client (can be None)
        guild: Discord guild context (can be None)
        message: Error message to log
        level: Severity level ("Error", "Warning", "Info")
    """
    # Log to console first as a fallback
    log_func = getattr(logging, level.lower(), logging.error)
    log_func(f"[{level.upper()}] {message}")

    # Attempt Discord channel logging if guild is available
    if guild:
        try:
            log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
            if not log_channel:
                if BotLogger:
                    BotLogger.warning(f"Log channel '{LOG_CHANNEL_NAME}' not found in guild {guild.name}",
                                      "EMBED_HELPER")
                return

            # Create structured log embed
            embed = embed_from_cfg("error")
            if not embed.description:
                embed.description = message
            else:
                embed.description = embed.description.format(message=message)

            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="GAL Bot")

            # Add ping for critical errors
            content = PING_USER if level == "Error" else None

            await log_channel.send(content=content, embed=embed)

        except discord.Forbidden:
            if BotLogger:
                BotLogger.warning(f"No permission to send to log channel in {guild.name}", "EMBED_HELPER")
        except discord.HTTPException as e:
            if BotLogger:
                BotLogger.warning(f"HTTP error sending to log channel: {e}", "EMBED_HELPER")
        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Unexpected error logging to channel: {e}", "EMBED_HELPER")
            else:
                logging.error(f"Failed to log to Discord channel: {e}")


class EmbedHelper:
    """
    Comprehensive helper class for managing Discord embeds throughout the bot.

    This class provides static methods for creating, updating, and managing
    Discord embeds with robust error handling, persistence management, and
    bulk update capabilities. All methods are designed to gracefully handle
    failures and provide meaningful feedback.
    """

    @staticmethod
    async def update_persisted_embed(
            guild: discord.Guild,
            persist_key: str,
            update_func: Callable,
            error_context: str = "embed update"
    ) -> bool:
        """
        Generic helper to update any persisted embed with comprehensive error handling.

        This method handles the common pattern of updating persisted embeds by:
        1. Retrieving the persisted message IDs from storage
        2. Fetching the Discord channel and message objects
        3. Calling the provided update function with proper error handling
        4. Logging any failures for debugging

        Args:
            guild: Discord guild containing the embed
            persist_key: Storage key for the persisted message (e.g., "registration", "checkin")
            update_func: Async function that takes (channel, msg_id, guild) as parameters
            error_context: Human-readable context for error logging

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Retrieve persisted message information
            chan_id, msg_id = get_persisted_msg(guild.id, persist_key)

            if not chan_id or not msg_id:
                if BotLogger:
                    BotLogger.debug(f"No persisted message found for key '{persist_key}' in guild {guild.name}",
                                    "EMBED_HELPER")
                else:
                    logging.debug(f"No persisted message found for key '{persist_key}' in guild {guild.name}")
                return False

            # Fetch Discord channel object
            channel = guild.get_channel(chan_id)
            if not channel:
                if BotLogger:
                    BotLogger.warning(f"Channel {chan_id} not found for key '{persist_key}' in guild {guild.name}",
                                      "EMBED_HELPER")
                else:
                    logging.warning(f"Channel {chan_id} not found for persist key '{persist_key}'")
                return False

            # Validate channel permissions
            bot_member = guild.me
            if not channel.permissions_for(bot_member).send_messages:
                if BotLogger:
                    BotLogger.warning(f"No permission to send messages in {channel.name} for '{persist_key}'",
                                      "EMBED_HELPER")
                return False

            # Execute the update function
            await update_func(channel, msg_id, guild)

            if BotLogger:
                BotLogger.debug(f"Successfully updated {persist_key} embed in {guild.name}", "EMBED_HELPER")

            return True

        except discord.NotFound:
            # Message was deleted, clear the persistence
            if BotLogger:
                BotLogger.warning(
                    f"Persisted message {msg_id} was deleted for key '{persist_key}', clearing persistence",
                    "EMBED_HELPER")
            # Could add logic here to clear the persisted message from storage
            return False

        except discord.Forbidden:
            if BotLogger:
                BotLogger.error(f"No permission to update {persist_key} embed in {guild.name}", "EMBED_HELPER")
            return False

        except Exception as e:
            await log_error(None, guild, f"[{error_context.upper()}] Failed to update {persist_key} embed: {e}")
            return False

    @staticmethod
    async def update_all_guild_embeds(guild: discord.Guild) -> Dict[str, bool]:
        """
        Update all live embeds for a guild with comprehensive error handling.

        This method provides a centralized way to refresh all persistent embeds
        in a guild, useful for maintaining consistency after data changes.

        Args:
            guild: Discord guild to update embeds for

        Returns:
            Dictionary mapping embed names to their update success status
        """
        if BotLogger:
            BotLogger.info(f"Updating all guild embeds for {guild.name}", "EMBED_HELPER")
        else:
            logging.info(f"Updating all guild embeds for {guild.name}")

        results = {}

        try:
            # Import here to avoid circular imports
            from core.views import update_registration_embed, update_checkin_embed

            # Update registration embed
            results['registration'] = await EmbedHelper.update_persisted_embed(
                guild,
                "registration",
                update_registration_embed,
                "registration update"
            )

            # Update check-in embed
            results['checkin'] = await EmbedHelper.update_persisted_embed(
                guild,
                "checkin",
                update_checkin_embed,
                "checkin update"
            )

            # Log results summary
            successful_updates = sum(1 for success in results.values() if success)
            total_updates = len(results)

            if BotLogger:
                BotLogger.info(
                    f"Guild embed update complete: {successful_updates}/{total_updates} successful for {guild.name}",
                    "EMBED_HELPER")
            else:
                logging.info(f"Guild embed update complete: {successful_updates}/{total_updates} successful")

        except ImportError as e:
            await log_error(None, guild, f"Failed to import embed update functions: {e}")
            # Set all results to False if imports fail
            results = {'registration': False, 'checkin': False}

        except Exception as e:
            await log_error(None, guild, f"Unexpected error updating guild embeds: {e}")
            results = {'registration': False, 'checkin': False}

        return results

    @staticmethod
    async def create_persisted_embed(
            guild: discord.Guild,
            channel: discord.TextChannel,
            embed: discord.Embed,
            view: discord.ui.View,
            persist_key: str,
            pin: bool = True,
            announce_pin: bool = True
    ) -> Optional[discord.Message]:
        """
        Create and persist an embed message with comprehensive error handling.

        This method creates a new embed message, stores its reference for future
        updates, and optionally pins it to the channel with cleanup of pin announcements.

        Args:
            guild: Discord guild context
            channel: Channel to send embed to
            embed: Discord embed to send
            view: UI view to attach to the message
            persist_key: Key to store message reference under
            pin: Whether to pin the message to the channel
            announce_pin: Whether to announce the pin (if False, deletes pin notification)

        Returns:
            The created Discord message, or None if creation failed
        """
        try:
            # Validate permissions before attempting to send
            bot_member = guild.me
            channel_perms = channel.permissions_for(bot_member)

            if not channel_perms.send_messages:
                await log_error(None, guild, f"No permission to send messages in {channel.name}")
                return None

            if pin and not channel_perms.manage_messages:
                if BotLogger:
                    BotLogger.warning(f"No permission to pin messages in {channel.name}, skipping pin", "EMBED_HELPER")
                pin = False

            # Send the embed message
            msg = await channel.send(embed=embed, view=view)

            # Import here to avoid circular imports
            from core.persistence import set_persisted_msg
            set_persisted_msg(guild.id, persist_key, channel.id, msg.id)

            if BotLogger:
                BotLogger.info(f"Created persisted embed for key '{persist_key}' in {channel.name}", "EMBED_HELPER")

            # Handle pinning if requested
            if pin:
                try:
                    await msg.pin()

                    # Clean up pin announcement if requested
                    if not announce_pin:
                        async for m in channel.history(limit=5):
                            if m.type == discord.MessageType.pins_add and m.created_at > msg.created_at:
                                try:
                                    await m.delete()
                                    break
                                except discord.Forbidden:
                                    if BotLogger:
                                        BotLogger.debug("No permission to delete pin announcement", "EMBED_HELPER")
                                except Exception:
                                    # Silently continue if we can't delete the pin message
                                    pass

                except discord.Forbidden:
                    if BotLogger:
                        BotLogger.warning(f"No permission to pin message in {channel.name}", "EMBED_HELPER")
                except Exception as e:
                    if BotLogger:
                        BotLogger.warning(f"Failed to pin message in {channel.name}: {e}", "EMBED_HELPER")

            return msg

        except discord.Forbidden:
            await log_error(None, guild, f"No permission to create embed in {channel.name}")
            return None
        except discord.HTTPException as e:
            await log_error(None, guild, f"HTTP error creating {persist_key} embed: {e}")
            return None
        except Exception as e:
            await log_error(None, guild, f"[CREATE-EMBED-ERROR] Failed to create {persist_key} embed: {e}")
            return None

    @staticmethod
    async def refresh_dm_views_for_users(
            guild: discord.Guild,
            discord_tags: Optional[List[str]] = None
    ) -> int:
        """
        Refresh DM action views for specified users or all cached users.

        This method updates the interactive buttons in users' DMs to reflect
        current server state (e.g., if check-in is open/closed).

        Args:
            guild: Discord guild context
            discord_tags: Optional list of specific discord tags to update.
                         If None, updates all users in cache.

        Returns:
            Number of successfully updated DM views
        """
        try:
            # Handle imports gracefully
            try:
                from integrations.sheets import sheet_cache, cache_lock
                from core.views import DMActionView
            except ImportError as e:
                if BotLogger:
                    BotLogger.warning(f"Required imports not available for DM view refresh: {e}", "EMBED_HELPER")
                return 0

            # Get user list from cache or parameter
            if discord_tags is None:
                try:
                    async with cache_lock:
                        discord_tags = list(sheet_cache["users"].keys())
                except Exception as e:
                    if BotLogger:
                        BotLogger.warning(f"Failed to get user list from cache: {e}", "EMBED_HELPER")
                    return 0

            if not discord_tags:
                if BotLogger:
                    BotLogger.debug("No users to update DM views for", "EMBED_HELPER")
                return 0

            updated = 0
            rem_embed = embed_from_cfg("reminder_dm")
            rem_title = rem_embed.title

            if BotLogger:
                BotLogger.info(f"Refreshing DM views for {len(discord_tags)} users in {guild.name}", "EMBED_HELPER")

            for discord_tag in discord_tags:
                try:
                    # Import resolve_member locally to avoid circular import
                    from utils.utils import resolve_member

                    member = resolve_member(guild, discord_tag)
                    if not member:
                        if BotLogger:
                            BotLogger.debug(f"Member not found in server: {discord_tag}", "EMBED_HELPER")
                        continue

                    # Search for reminder DM and update its view
                    try:
                        dm = await member.create_dm()

                        # Look for the most recent reminder message
                        async for msg in dm.history(limit=50):
                            if (msg.author == guild.me and
                                    msg.embeds and
                                    len(msg.embeds) > 0 and
                                    msg.embeds[0].title == rem_title):

                                await msg.edit(view=DMActionView(guild, member))
                                updated += 1
                                if BotLogger:
                                    BotLogger.debug(f"Updated DM view for {discord_tag}", "EMBED_HELPER")
                                break

                    except discord.Forbidden:
                        # User has DMs disabled - this is expected and not an error
                        if BotLogger:
                            BotLogger.debug(f"Cannot DM user {discord_tag} (DMs disabled or blocked)", "EMBED_HELPER")
                    except discord.HTTPException as e:
                        if BotLogger:
                            BotLogger.warning(f"HTTP error updating DM for {discord_tag}: {e}", "EMBED_HELPER")
                    except Exception as e:
                        if BotLogger:
                            BotLogger.warning(f"Unexpected error updating DM for {discord_tag}: {e}", "EMBED_HELPER")

                except Exception as e:
                    # Log individual user errors but continue processing others
                    if BotLogger:
                        BotLogger.warning(f"Error processing DM view refresh for {discord_tag}: {e}", "EMBED_HELPER")
                    continue

            if BotLogger:
                BotLogger.info(f"Updated {updated} DM views out of {len(discord_tags)} users in {guild.name}",
                               "EMBED_HELPER")

            return updated

        except Exception as e:
            await log_error(None, guild, f"Critical error in refresh_dm_views_for_users: {e}")
            return 0

    @staticmethod
    def build_registration_list_lines(users: List[tuple], mode: str) -> List[str]:
        """
        Build formatted lines for registration list display with intelligent color cycling.

        This method creates visually appealing registration lists that adapt to different
        event modes (normal vs doubleup) with smart emoji assignment for teams.

        Args:
            users: List of tuples containing (discord_tag, ign, team) information
            mode: Event mode ("normal" or "doubleup")

        Returns:
            List of formatted strings ready for embed display
        """
        lines = []

        if not users:
            return ["```\nNo users registered yet.\n```"]

        try:
            if mode == "doubleup":
                # Sort users by team name for better organization
                users.sort(key=lambda x: (x[2] or "No Team").lower())

                # Define team emojis with good variety and visibility
                team_emojis = [
                    "🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚪", "⚫", "🟤",
                    "💙", "💚", "💛", "💜", "🧡", "❤️", "🤍", "🖤", "🤎"
                ]
                used_emojis = []
                team_emoji_map = {}

                # Group users by team first to get full team structure
                teams_data = {}
                for tag, ign, team in users:
                    team_key = team or "No Team"
                    if team_key not in teams_data:
                        teams_data[team_key] = []
                    teams_data[team_key].append((tag, ign))

                # Sort teams by name for consistent display
                sorted_teams = sorted(teams_data.items(), key=lambda x: x[0].lower())

                # Assign emojis with intelligent cycling to avoid adjacent duplicates
                for i, (team, members) in enumerate(sorted_teams):
                    if team not in team_emoji_map:
                        # Smart emoji selection to avoid recent duplicates
                        if len(used_emojis) >= len(team_emojis):
                            # Calculate emojis to avoid for better visual separation
                            avoid_emojis = []

                            # Avoid previous team's emoji
                            if i > 0:
                                prev_team = sorted_teams[i - 1][0]
                                if prev_team in team_emoji_map:
                                    avoid_emojis.append(team_emoji_map[prev_team])

                            # Avoid recently used emojis
                            avoid_emojis.extend(used_emojis[-3:])

                            # Select from available emojis
                            available = [e for e in team_emojis if e not in avoid_emojis]
                            if not available:  # Fallback if all are avoided
                                available = team_emojis

                            emoji = random.choice(available)
                        else:
                            # First pass through emojis
                            emoji = team_emojis[len(used_emojis)]

                        team_emoji_map[team] = emoji
                        used_emojis.append(emoji)

                # Build the formatted output
                for team, members in sorted_teams:
                    emoji = team_emoji_map[team]

                    # Format team header
                    if team == "No Team":
                        team_display = "Unassigned Players"
                    else:
                        team_display = team

                    lines.append(f"{emoji} **{team_display}**")
                    lines.append("```css")

                    # Add team members with proper formatting
                    for tag, ign in sorted(members, key=lambda x: x[0].lower()):
                        lines.append(f"{tag} | {ign}")

                    lines.append("```")

            else:
                # Normal mode - simple numbered list
                lines.append("```css")
                lines.append("# Registered Players")
                lines.append("=" * 40)

                for i, (tag, ign, _) in enumerate(users, 1):
                    lines.append(f"{i:2d}. {tag} | {ign}")

                lines.append("```")

        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Error building registration list lines: {e}", "EMBED_HELPER")
            else:
                logging.error(f"Error building registration list lines: {e}")

            # Return fallback content on error
            return ["```\nError displaying registration list.\n```"]

        return lines

    @staticmethod
    def build_checkin_list_lines(checked_in_users: List[tuple], mode: str) -> List[str]:
        """
        Build formatted lines showing ALL registered users with check-in status.

        This method creates a comprehensive view of registration status, showing
        ready teams first, then non-ready teams, all in a unified list format.

        Args:
            checked_in_users: List of tuples with (tag, user_data) where user_data
                             contains (row, ign, reg, ci, team, alt)
            mode: Event mode ("normal" or "doubleup")

        Returns:
            List of formatted strings ready for embed display
        """
        lines = []

        if not checked_in_users:
            return ["```\nNo registered users found.\n```"]

        def is_true(v) -> bool:
            """Helper to check if a value represents True (case-insensitive)."""
            return str(v).upper() == "TRUE"

        try:
            if mode == "doubleup":
                # Group users by team
                teams = {}
                for tag, user_data in checked_in_users:
                    # user_data is the full tuple (row, ign, reg, ci, team, alt)
                    team_name = user_data[4] if len(user_data) > 4 and user_data[4] else "No Team"

                    if team_name not in teams:
                        teams[team_name] = []
                    teams[team_name].append((tag, user_data))

                # Separate teams into ready and not ready for better organization
                ready_teams = []
                not_ready_teams = []

                for team_name, members in teams.items():
                    # Check team readiness (2+ members AND all checked in)
                    has_enough_members = len(members) >= 2
                    all_checked_in = all(
                        len(member[1]) > 3 and is_true(member[1][3])
                        for member in members
                    )
                    is_ready = has_enough_members and all_checked_in

                    if is_ready:
                        ready_teams.append((team_name, members))
                    else:
                        not_ready_teams.append((team_name, members))

                # Sort each group by team name for consistency
                ready_teams.sort(key=lambda x: x[0].lower())
                not_ready_teams.sort(key=lambda x: x[0].lower())

                # Display ready teams first, then not ready teams
                all_teams = ready_teams + not_ready_teams

                for team_name, members in all_teams:
                    # Determine team readiness status
                    has_enough_members = len(members) >= 2
                    all_checked_in = all(
                        len(member[1]) > 3 and is_true(member[1][3])
                        for member in members
                    )
                    is_ready = has_enough_members and all_checked_in

                    # Format team header with status indicator
                    team_check = "✅ " if is_ready else ""

                    if team_name == "No Team":
                        team_display = f"{team_check}**Unassigned Players**"
                    else:
                        team_display = f"{team_check}**{team_name}**"

                    lines.append(team_display)
                    lines.append("```css")

                    # Add team members with check-in status
                    for tag, tpl in sorted(members, key=lambda x: x[0].lower()):
                        ign = tpl[1] if len(tpl) > 1 else "Unknown"
                        is_checked_in = len(tpl) > 3 and is_true(tpl[3])
                        status = "🟢" if is_checked_in else "🔴"
                        lines.append(f"{status} {tag} | {ign}")

                    lines.append("```")

            else:
                # Normal mode - show all registered users with check-in status
                lines.append("**📋 Player Check-In Status**")
                lines.append("```css")

                for i, (tag, tpl) in enumerate(checked_in_users, 1):
                    ign = tpl[1] if len(tpl) > 1 else "Unknown"
                    is_checked_in = len(tpl) > 3 and is_true(tpl[3])
                    status = "🟢" if is_checked_in else "🔴"
                    lines.append(f"{status} [{i:02d}] {tag} | {ign}")

                lines.append("```")

        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Error building check-in list lines: {e}", "EMBED_HELPER")
            else:
                logging.error(f"Error building check-in list lines: {e}")

            # Return fallback content on error
            return ["```\nError displaying check-in list.\n```"]

        return lines


# Backward compatibility function for existing code
async def create_persisted_embed(guild, channel, embed, view, persist_key, pin=True, announce_pin=True):
    """
    Legacy wrapper for EmbedHelper.create_persisted_embed.

    Maintained for backward compatibility with existing code.
    New code should use EmbedHelper.create_persisted_embed directly.
    """
    return await EmbedHelper.create_persisted_embed(
        guild, channel, embed, view, persist_key, pin, announce_pin
    )