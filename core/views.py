# core/views.py
"""
Discord UI Views and Components for GAL Bot.

This module contains all Discord UI components including buttons, modals, and views
that handle user interactions throughout the bot. It provides comprehensive error
handling, validation, and logging for all user interactions.

Key Features:
- Registration and check-in workflows with validation
- Team name similarity checking and suggestions
- DM-based user actions with permission checking
- Administrative controls with proper authorization
- Comprehensive error handling and user feedback
- Graceful degradation when dependencies are unavailable

All views inherit from base classes that provide consistent error handling,
logging, and permission validation throughout the application.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Union

import discord
from rapidfuzz import process, fuzz

from config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE, get_sheet_settings,
    ALLOWED_ROLES
)
from core.persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild, get_schedule,
)

# Import helpers with graceful fallbacks
try:
    from helpers.logging_helper import BotLogger
except ImportError:
    BotLogger = None
    logging.warning("BotLogger not available, using standard logging")

# Import helpers with graceful fallbacks
ErrorHandler = None
ErrorCategory = None
ErrorSeverity = None
ErrorContext = None

try:
    from helpers.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext

    _has_error_handler = True
except ImportError:
    _has_error_handler = False
    logging.warning("ErrorHandler not available, using fallback implementation")


# Always create fallback classes to ensure they exist
class ErrorSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory:
    DISCORD_API = "discord_api"
    USER_INPUT = "user_input"
    PERMISSIONS = "permissions"
    VALIDATION = "validation"
    SHEETS = "sheets"


class ErrorContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# Create ErrorHandler if not imported
if not _has_error_handler:
    class ErrorHandler:
        @staticmethod
        async def handle_interaction_error(interaction, error, operation, **kwargs):
            if BotLogger:
                BotLogger.error(f"Error in {operation}: {error}", "ERROR_HANDLER")
            else:
                logging.error(f"Error in {operation}: {error}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=embed_from_cfg("error"),
                        ephemeral=True
                    )
                elif interaction.followup:
                    await interaction.followup.send(
                        embed=embed_from_cfg("error"),
                        ephemeral=True
                    )
            except Exception:
                pass

        @staticmethod
        def wrap_callback(operation_name: str):
            """Decorator for wrapping callbacks with error handling."""

            def decorator(func):
                async def wrapper(self, interaction):
                    try:
                        await func(self, interaction)
                    except Exception as e:
                        await ErrorHandler.handle_interaction_error(
                            interaction, e, operation_name
                        )

                return wrapper

            return decorator

# Create fallback classes if imports failed
if ErrorHandler is None:
    class ErrorSeverity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


    class ErrorCategory:
        DISCORD_API = "discord_api"
        USER_INPUT = "user_input"
        PERMISSIONS = "permissions"
        VALIDATION = "validation"
        SHEETS = "sheets"


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

            # Try to respond to the user if possible
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=embed_from_cfg("error"),
                        ephemeral=True
                    )
                elif interaction.followup:
                    await interaction.followup.send(
                        embed=embed_from_cfg("error"),
                        ephemeral=True
                    )
            except Exception:
                pass  # Ignore if we can't respond

        @staticmethod
        def wrap_callback(operation_name: str):
            """Decorator for wrapping callbacks with error handling."""

            def decorator(func):
                async def wrapper(self, interaction):
                    try:
                        await func(self, interaction)
                    except Exception as e:
                        await ErrorHandler.handle_interaction_error(
                            interaction, e, operation_name
                        )

                return wrapper

            return decorator

# Import helper modules with comprehensive fallbacks
RoleManager = None
ChannelManager = None
SheetOperations = None
Validators = None

try:
    from helpers import RoleManager, ChannelManager, SheetOperations, Validators

    if BotLogger:
        BotLogger.info("✅ Helper modules imported successfully", "VIEWS")
    else:
        logging.info("✅ Helper modules imported successfully")
except ImportError:
    if BotLogger:
        BotLogger.warning("Helper modules not available, using fallback implementations", "VIEWS")
    else:
        logging.warning("Helper modules not available, using fallback implementations")

# Create fallback implementations if imports failed
if RoleManager is None:
    class RoleManager:
        @staticmethod
        async def add_role(member, role_name):
            try:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role:
                    await member.add_roles(role, reason="Bot role assignment")
                    return True
                return False
            except Exception as e:
                if BotLogger:
                    BotLogger.error(f"Failed to add role {role_name} to {member}: {e}", "ROLE_MANAGER")
                return False

        @staticmethod
        async def remove_role(member, role_name):
            try:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role and role in member.roles:
                    await member.remove_roles(role, reason="Bot role removal")
                    return True
                return False
            except Exception as e:
                if BotLogger:
                    BotLogger.error(f"Failed to remove role {role_name} from {member}: {e}", "ROLE_MANAGER")
                return False

        @staticmethod
        async def remove_roles(member, role_names):
            success_count = 0
            for role_name in role_names:
                if await RoleManager.remove_role(member, role_name):
                    success_count += 1
            return success_count == len(role_names)

        @staticmethod
        def has_allowed_role_from_interaction(interaction):
            try:
                return any(role.name in ALLOWED_ROLES for role in interaction.user.roles)
            except Exception:
                return False

if ChannelManager is None:
    class ChannelManager:
        @staticmethod
        def get_channel_state(guild):
            try:
                reg_ch = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
                angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
                reg_open = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

                ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
                reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
                ci_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

                return {'registration_open': reg_open, 'checkin_open': ci_open}
            except Exception:
                return {'registration_open': True, 'checkin_open': True}

if SheetOperations is None:
    class SheetOperations:
        @staticmethod
        async def get_user_data(discord_tag, guild_id):
            return None

        @staticmethod
        async def get_all_registered_users(guild_id):
            return []

        @staticmethod
        async def batch_update_cells(guild_id, updates, row):
            return True

if Validators is None:
    class ValidationResult:
        def __init__(self, is_valid=True, embed_key="", message=""):
            self.is_valid = is_valid
            self.embed_key = embed_key
            self.message = message

        def to_embed(self):
            return embed_from_cfg(self.embed_key if self.embed_key else "error")


    class Validators:
        @staticmethod
        async def validate_registration_capacity(guild_id, team_name=None, exclude_discord_tag=None):
            return None  # No capacity errors in fallback mode

        @staticmethod
        def validate_registration_status(member, require_registered=False):
            if not require_registered:
                return True
            reg_role = discord.utils.get(member.guild.roles, name=REGISTERED_ROLE)
            return reg_role in member.roles if reg_role else False

        @staticmethod
        def validate_checkin_status(member, require_not_checked_in=False):
            if not require_not_checked_in:
                return True
            ci_role = discord.utils.get(member.guild.roles, name=CHECKED_IN_ROLE)
            return ci_role not in member.roles if ci_role else True

        @staticmethod
        async def validate_and_respond(interaction, *validations):
            return all(validations)

# Import embed helpers with fallbacks
EmbedHelper = None
log_error = None

try:
    from helpers.embed_helpers import EmbedHelper, log_error

    if BotLogger:
        BotLogger.info("✅ EmbedHelper imported successfully", "VIEWS")
    else:
        logging.info("✅ EmbedHelper imported successfully")
except ImportError:
    if BotLogger:
        BotLogger.warning("EmbedHelper not available, using fallback implementation", "VIEWS")
    else:
        logging.warning("EmbedHelper not available, using fallback implementation")

# Create fallback implementations if imports failed
if EmbedHelper is None:
    class EmbedHelper:
        @staticmethod
        async def update_all_guild_embeds(guild):
            return {'registration': False, 'checkin': False}

        @staticmethod
        async def update_persisted_embed(guild, persist_key, update_func, error_context):
            return False

        @staticmethod
        async def create_persisted_embed(guild, channel, embed, view, persist_key, pin=True, announce_pin=True):
            return None

        @staticmethod
        async def refresh_dm_views_for_users(guild, discord_tags=None):
            return 0

if log_error is None:
    async def log_error(bot, guild, message, level="Error"):
        if BotLogger:
            BotLogger.error(message, "VIEWS")
        else:
            logging.error(message)

# Import sheet integration functions with comprehensive fallbacks
try:
    from integrations.sheets import (
        find_or_register_user, get_sheet_for_guild, retry_until_successful,
        mark_checked_in_async, unmark_checked_in_async, unregister_user,
        refresh_sheet_cache, reset_checked_in_roles_and_sheet,
        reset_registered_roles_and_sheet, cache_lock, sheet_cache
    )
except ImportError:
    if BotLogger:
        BotLogger.warning("Sheet integrations not available, using fallbacks", "VIEWS")
    else:
        logging.warning("Sheet integrations not available, using fallbacks")


    # Create comprehensive fallback implementations
    async def find_or_register_user(discord_tag, ign, guild_id=None, team_name=None):
        return 1  # Dummy row number


    async def get_sheet_for_guild(guild_id, sheet_name):
        return None


    async def retry_until_successful(func, *args, **kwargs):
        return []


    async def mark_checked_in_async(discord_tag, guild_id=None):
        return True


    async def unmark_checked_in_async(discord_tag, guild_id=None):
        return True


    async def unregister_user(discord_tag, guild_id=None):
        return True


    async def refresh_sheet_cache(bot=None):
        pass


    async def reset_checked_in_roles_and_sheet(guild, channel):
        return 0


    async def reset_registered_roles_and_sheet(guild, channel):
        return 0


    cache_lock = asyncio.Lock()
    sheet_cache = {"users": {}}

# Import utility functions with comprehensive fallbacks
try:
    from utils.utils import (
        toggle_checkin_for_member, send_reminder_dms,
        hyperlink_lolchess_profile, resolve_member, toggle_persisted_channel
    )
except ImportError:
    if BotLogger:
        BotLogger.warning("Utility functions not available, using fallback implementations", "VIEWS")
    else:
        logging.warning("Utility functions not available, using fallback implementations")


    async def toggle_checkin_for_member(interaction, async_func, embed_key):
        """Fallback implementation for check-in toggle."""
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)

            member = interaction.user
            discord_tag = str(member)
            guild_id = str(interaction.guild.id)

            # Try to perform the sheet operation
            success = await async_func(discord_tag, guild_id=guild_id)

            if success:
                # Update role based on the embed key
                if embed_key == "checked_in":
                    await RoleManager.add_role(member, CHECKED_IN_ROLE)
                elif embed_key == "checked_out":
                    await RoleManager.remove_role(member, CHECKED_IN_ROLE)

                # Send success response
                embed = embed_from_cfg(embed_key)
                await interaction.followup.send(embed=embed, ephemeral=True)

                # Update embeds
                await EmbedHelper.update_all_guild_embeds(interaction.guild)
            else:
                # Send error response
                await interaction.followup.send(
                    embed=embed_from_cfg("error"),
                    ephemeral=True
                )

        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Check-in toggle failed: {e}", "UTILS_FALLBACK")
            await interaction.followup.send(
                embed=embed_from_cfg("error"),
                ephemeral=True
            )


    async def send_reminder_dms(client, guild, dm_embed, view_cls):
        """Fallback implementation for sending reminder DMs."""
        try:
            # Get registered but not checked-in users
            reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)

            if not reg_role:
                return []

            # Find users who need reminders
            targets = []
            for member in reg_role.members:
                if not ci_role or ci_role not in member.roles:
                    targets.append(member)

            # Send DMs
            dmmed = []
            for member in targets:
                try:
                    view = view_cls(guild, member)
                    await member.send(embed=dm_embed, view=view)
                    dmmed.append(str(member))
                except discord.Forbidden:
                    # User has DMs disabled
                    continue
                except Exception:
                    # Other error sending DM
                    continue

            return dmmed

        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Send reminder DMs failed: {e}", "UTILS_FALLBACK")
            return []


    async def hyperlink_lolchess_profile(discord_tag, guild_id):
        """Fallback implementation - no-op."""
        pass


    def resolve_member(guild, discord_tag):
        """Fallback implementation for resolving members."""
        try:
            # Try exact match first
            member = guild.get_member_named(discord_tag)
            if member:
                return member

            # Try by display name
            for member in guild.members:
                if str(member) == discord_tag:
                    return member

            return None
        except Exception:
            return None


    async def toggle_persisted_channel(interaction, persist_key, channel_name, role_name, ping_role=False):
        """Fallback implementation for channel toggle."""
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)

            guild = interaction.guild
            channel = discord.utils.get(guild.channels, name=channel_name)
            role = discord.utils.get(guild.roles, name=role_name)

            if not channel or not role:
                await interaction.followup.send(
                    embed=embed_from_cfg("error"),
                    ephemeral=True
                )
                return

            # Get current permissions
            overwrites = channel.overwrites_for(role)
            current_visibility = overwrites.read_messages

            # Toggle visibility
            new_visibility = not current_visibility if current_visibility is not None else True
            overwrites.read_messages = new_visibility

            # Update channel permissions
            await channel.set_permissions(role, overwrite=overwrites)

            # Send confirmation
            action = "opened" if new_visibility else "closed"
            embed = embed_from_cfg(
                "channel_toggled",
                visible=new_visibility,
                channel=channel_name,
                action=action
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Update embeds
            await EmbedHelper.update_all_guild_embeds(guild)

        except discord.Forbidden:
            await interaction.followup.send(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Channel toggle failed: {e}", "UTILS_FALLBACK")
            await interaction.followup.send(
                embed=embed_from_cfg("error"),
                ephemeral=True
            )


class ViewError(Exception):
    """Custom exception for view-related errors with context."""

    def __init__(self, message: str, view_name: str = "", user_id: int = None):
        super().__init__(message)
        self.view_name = view_name
        self.user_id = user_id


class BaseView(discord.ui.View):
    """
    Base view class with comprehensive error handling and logging.

    All views should inherit from this class to ensure consistent
    error handling, timeout management, and logging throughout the application.
    """

    def __init__(self, timeout: Optional[float] = None):
        """Initialize base view with optional timeout and logging setup."""
        super().__init__(timeout=timeout)
        self.view_name = self.__class__.__name__

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        """Handle view errors consistently across all views."""
        try:
            error_context = {
                'view_name': self.view_name,
                'user_id': interaction.user.id,
                'guild_id': interaction.guild.id if interaction.guild else None,
                'item_type': type(item).__name__
            }

            if BotLogger:
                BotLogger.error(f"View error in {self.view_name}: {error}", "VIEWS", extra_data=error_context)
            else:
                logging.error(f"View error in {self.view_name}: {error}")

            # Try to respond to the user if possible
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=embed_from_cfg("error"),
                    ephemeral=True
                )
            elif interaction.followup:
                await interaction.followup.send(
                    embed=embed_from_cfg("error"),
                    ephemeral=True
                )

        except Exception as e:
            # Last resort logging
            logging.critical(f"Critical error in view error handler: {e}")

    async def on_timeout(self):
        """Handle view timeouts by disabling all items."""
        try:
            self.disable_all_items()
            if BotLogger:
                BotLogger.debug(f"View {self.view_name} timed out", "VIEWS")
        except Exception as e:
            if BotLogger:
                BotLogger.warning(f"Error handling timeout for {self.view_name}: {e}", "VIEWS")

    def disable_all_items(self):
        """Disable all interactive items in the view."""
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True


class BaseButton(discord.ui.Button):
    """
    Base button class with consistent styling and error handling.

    Provides common functionality for all button interactions including
    permission validation and error handling.
    """

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Perform basic interaction validation before button callback."""
        try:
            # Basic validation - can be overridden in subclasses
            return True
        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Interaction check failed: {e}", "VIEWS")
            return False


async def complete_registration(
        interaction: discord.Interaction,
        ign: str,
        pronouns: str,
        team_name: str | None,
        alt_igns: str,
        reg_modal: "RegistrationModal"
):
    """
    Complete the user registration process with comprehensive validation and error handling.

    This function handles the core registration logic including capacity validation,
    waitlist management, sheet operations, role assignment, and embed updates.

    Args:
        interaction: Discord interaction object
        ign: In-game name
        pronouns: User pronouns (will be auto-capitalized)
        team_name: Team name for doubleup events
        alt_igns: Alternative in-game names
        reg_modal: Registration modal instance for context
    """
    try:
        # Defer response if not already done to prevent timeout
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        # Resolve context with fallbacks
        guild = getattr(reg_modal, "guild", None) or interaction.guild
        member = getattr(reg_modal, "member", None) or interaction.user
        discord_tag = str(member)
        gid = str(guild.id)

        # Auto-capitalize pronouns - split by "/" and capitalize each part
        if pronouns:
            pronouns_parts = pronouns.split("/")
            pronouns = "/".join(part.strip().capitalize() for part in pronouns_parts)

        # Log registration attempt
        if BotLogger:
            BotLogger.info(
                f"Registration attempt: User={discord_tag} IGN={ign!r} Team={team_name!r} Guild={guild.name}",
                "REGISTRATION")
        else:
            logging.info(f"[REGISTER] Guild={guild.name}({gid}) User={discord_tag} IGN={ign!r} Team={team_name!r}")

        # Validate registration capacity
        capacity_error = await Validators.validate_registration_capacity(
            gid, team_name, exclude_discord_tag=discord_tag
        )

        if capacity_error:
            # Handle capacity-related errors (full registration, team full, etc.)
            if capacity_error.embed_key == "registration_full":
                # Try waitlist functionality if available
                try:
                    from helpers.waitlist_helpers import WaitlistManager

                    existing_position = await WaitlistManager.get_waitlist_position(gid, discord_tag)

                    if existing_position:
                        # Update existing waitlist entry
                        await WaitlistManager.update_waitlist_entry(
                            gid, discord_tag, ign, pronouns, team_name, alt_igns
                        )

                        waitlist_embed = discord.Embed(
                            title="📋 Waitlist Updated",
                            description=f"Your waitlist information has been updated.\n\n"
                                        f"You remain at position **#{existing_position}** in the waitlist.",
                            color=discord.Color.blue()
                        )
                        return await interaction.followup.send(embed=waitlist_embed, ephemeral=True)
                    else:
                        # Add to waitlist
                        position = await WaitlistManager.add_to_waitlist(
                            guild, member, ign, pronouns, team_name, alt_igns
                        )

                        mode = get_event_mode_for_guild(gid)
                        cfg = get_sheet_settings(mode)
                        max_players = cfg.get("max_players", 0)

                        waitlist_embed = embed_from_cfg(
                            "waitlist_added",
                            position=position,
                            max_players=max_players
                        )
                        return await interaction.followup.send(embed=waitlist_embed, ephemeral=True)

                except ImportError:
                    # Waitlist not available, show regular capacity error
                    pass

            # Show capacity error
            return await interaction.followup.send(
                embed=capacity_error.to_embed() if hasattr(capacity_error, 'to_embed') else embed_from_cfg(
                    "registration_full"),
                ephemeral=True
            )

        # Remove from waitlist if they were on it
        try:
            from helpers.waitlist_helpers import WaitlistManager
            await WaitlistManager.remove_from_waitlist(gid, discord_tag)
        except ImportError:
            pass

        # Get event mode
        mode = get_event_mode_for_guild(gid)

        # Register/update user in sheet
        row = await find_or_register_user(
            discord_tag,
            ign,
            guild_id=gid,
            team_name=(team_name if mode == "doubleup" else None)
        )

        # Prepare sheet updates
        updates = {}
        sheet_settings = get_sheet_settings(mode)

        if 'pronouns_col' in sheet_settings:
            updates[sheet_settings['pronouns_col']] = pronouns
        if alt_igns and 'alt_ign_col' in sheet_settings:
            updates[sheet_settings['alt_ign_col']] = alt_igns
        if mode == "doubleup" and team_name and 'team_col' in sheet_settings:
            updates[sheet_settings['team_col']] = team_name

        # Update sheet with batch operation
        if updates:
            await SheetOperations.batch_update_cells(gid, updates, row)

        # Assign registered role
        await RoleManager.add_role(member, REGISTERED_ROLE)

        # Update all guild embeds
        await EmbedHelper.update_all_guild_embeds(guild)

        # Send success confirmation
        ok_key = f"register_success_{mode}"
        success_embed = embed_from_cfg(
            ok_key,
            ign=ign,
            team_name=(team_name or "–")
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)

        # Hyperlink IGN in lolchess (if available)
        await hyperlink_lolchess_profile(discord_tag, gid)

        if BotLogger:
            BotLogger.info(f"Registration successful: {discord_tag} in guild {guild.name}", "REGISTRATION")
        else:
            logging.info(f"[REGISTER SUCCESS] {discord_tag} in guild {guild.name}")

        # Process waitlist if someone can be promoted
        try:
            from helpers.waitlist_helpers import WaitlistManager
            await WaitlistManager.process_waitlist(guild)
        except ImportError:
            pass

    except Exception as e:
        # Comprehensive error handling
        await ErrorHandler.handle_interaction_error(
            interaction, e, "Registration",
            f"Failed to complete registration. Please try again."
        )


class ChannelCheckInButton(BaseButton):
    """Button for checking in via channel interface."""

    def __init__(self):
        super().__init__(
            label="Check In",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id="channel_checkin_btn"
        )

    @ErrorHandler.wrap_callback("Check-In")
    async def callback(self, interaction: discord.Interaction):
        """Handle channel-based check-in with comprehensive validation."""
        member = interaction.user
        guild = interaction.guild

        if BotLogger:
            BotLogger.info(f"Check-in attempt: {member} in {guild.name}", "CHECKIN")
        else:
            logging.info(f"[CHECK-IN] Guild={guild.name}({guild.id}) User={member}")

        # Validate user status before proceeding
        validations = [
            Validators.validate_registration_status(member, require_registered=True),
            Validators.validate_checkin_status(member, require_not_checked_in=True)
        ]

        if not await Validators.validate_and_respond(interaction, *validations):
            return

        # Perform check-in using the utility helper
        await toggle_checkin_for_member(
            interaction,
            mark_checked_in_async,
            "checked_in"
        )


class ChannelCheckOutButton(BaseButton):
    """Button for checking out via channel interface."""

    def __init__(self):
        super().__init__(
            label="Check Out",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id="channel_checkout_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle channel-based check-out with validation."""
        member = interaction.user
        guild = interaction.guild

        if BotLogger:
            BotLogger.info(f"Check-out attempt: {member} in {guild.name}", "CHECKIN")
        else:
            logging.info(f"[CHECK-OUT] Guild={guild.name}({guild.id}) User={member}")

        # Validate user is registered
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        if not reg_role or reg_role not in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"),
                ephemeral=True
            )

        # Validate user is currently checked in
        ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        if not ci_role or ci_role not in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"),
                ephemeral=True
            )

        # Perform check-out
        await toggle_checkin_for_member(
            interaction,
            unmark_checked_in_async,
            "checked_out"
        )


class DMUnregisterButton(BaseButton):
    """DM button for unregistering users with comprehensive error handling."""

    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id=f"dm_unreg_{guild.id}_{member.id}"
        )
        self.guild = guild
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        """Handle DM-based unregistration with channel state checking."""
        try:
            # Check if registration channel is open
            reg_channel = discord.utils.get(self.guild.text_channels, name=REGISTRATION_CHANNEL)
            angel_role = discord.utils.get(self.guild.roles, name=ANGEL_ROLE)

            if reg_channel and angel_role:
                overwrites = reg_channel.overwrites_for(angel_role)
                if not overwrites.view_channel:
                    # Registration is closed
                    await interaction.response.send_message(
                        embed=embed_from_cfg("registration_closed"),
                        ephemeral=True
                    )
                    return

            # Defer response for processing
            await interaction.response.defer(ephemeral=True, thinking=True)

            discord_tag = str(self.member)
            guild_id = str(self.guild.id)

            # Check if user is in waitlist first
            try:
                from helpers.waitlist_helpers import WaitlistManager
                waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

                if waitlist_position:
                    # Remove from waitlist
                    await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)

                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="✅ Removed from Waitlist",
                            description=f"You have been removed from the waitlist (you were position #{waitlist_position}).",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )

                    # Remove the view from the original message
                    await interaction.message.edit(view=None)
                    return
            except ImportError:
                pass

            # Attempt to unregister from sheet
            ok = await unregister_user(discord_tag, guild_id=guild_id)

            if ok:
                # Remove roles
                await RoleManager.remove_roles(self.member, [REGISTERED_ROLE, CHECKED_IN_ROLE])

                # Update embeds
                await EmbedHelper.update_all_guild_embeds(self.guild)

                # Process waitlist
                try:
                    from helpers.waitlist_helpers import WaitlistManager
                    await WaitlistManager.process_waitlist(self.guild)
                except ImportError:
                    pass

                # Send success message
                await interaction.followup.send(
                    embed=embed_from_cfg("unregister_success"),
                    ephemeral=True
                )

                # Remove the view from the original message
                await interaction.message.edit(view=None)
            else:
                # Send error message
                await interaction.followup.send(
                    embed=embed_from_cfg("unregister_not_registered"),
                    ephemeral=True
                )

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "DM Unregister"
            )


class DMCheckToggleButton(BaseButton):
    """DM button for toggling check-in status with dynamic state management."""

    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild = guild
        self.member = member

        # Determine current state and button configuration
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)

        is_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)
        is_reg = reg_role in member.roles if reg_role else False
        is_ci = ci_role in member.roles if ci_role else False

        label = "Check Out" if is_ci else "Check In"
        style = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        emoji = "❌" if is_ci else "✅"

        super().__init__(
            label=label,
            style=style,
            emoji=emoji,
            custom_id=f"dm_citoggle_{guild.id}_{member.id}",
            disabled=not (is_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle DM-based check-in/out toggle with comprehensive validation."""
        try:
            # Check if check-in channel is open
            ci_ch = discord.utils.get(self.guild.text_channels, name=CHECK_IN_CHANNEL)
            reg_role = discord.utils.get(self.guild.roles, name=REGISTERED_ROLE)

            if ci_ch and reg_role:
                overwrites = ci_ch.overwrites_for(reg_role)
                if not overwrites.view_channel:
                    # Check-in is closed
                    await interaction.response.send_message(
                        embed=embed_from_cfg("checkin_closed"),
                        ephemeral=True
                    )
                    return

            # Validate user is registered
            if not reg_role or reg_role not in self.member.roles:
                return await interaction.response.send_message(
                    embed=embed_from_cfg("checkin_requires_registration"),
                    ephemeral=True
                )

            # Check current check-in status
            ci_role = discord.utils.get(self.guild.roles, name=CHECKED_IN_ROLE)
            is_ci = ci_role in self.member.roles if ci_role else False

            # Prevent redundant actions
            if self.label == "Check In" and is_ci:
                return await interaction.response.send_message(
                    embed=embed_from_cfg("already_checked_in"),
                    ephemeral=True
                )
            if self.label == "Check Out" and not is_ci:
                return await interaction.response.send_message(
                    embed=embed_from_cfg("already_checked_out"),
                    ephemeral=True
                )

            # Defer response for processing
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Perform the sheet and role update
            discord_tag = str(self.member)
            if self.label == "Check In":
                ok = await mark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
                if ok:
                    await RoleManager.add_role(self.member, CHECKED_IN_ROLE)
                    await interaction.followup.send(embed=embed_from_cfg("checked_in"), ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)
            else:
                ok = await unmark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
                if ok:
                    await RoleManager.remove_role(self.member, CHECKED_IN_ROLE)
                    await interaction.followup.send(embed=embed_from_cfg("checked_out"), ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)

            # Update channel embed
            await EmbedHelper.update_persisted_embed(
                self.guild,
                "checkin",
                lambda ch, mid, g: update_checkin_embed(ch, mid, g),
                "checkin update"
            )

            # Update the DM view to reflect new state
            await interaction.message.edit(view=DMActionView(self.guild, self.member))

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "DM Check Toggle"
            )


class ResetCheckInsButton(BaseButton):
    """Administrative button for resetting all check-ins with confirmation."""

    def __init__(self):
        super().__init__(
            label="Reset Check-Ins",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle check-in reset with permission validation and progress reporting."""
        # Validate permissions
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Count how many will be cleared
            checked_in_role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
            cleared_count = len(checked_in_role.members) if checked_in_role else 0

            # Show starting message
            embed_start = embed_from_cfg("resetting", count=cleared_count, role="checked-in")
            await interaction.followup.send(embed=embed_start, ephemeral=True)

            start_time = time.perf_counter()

            # Clear the sheet and roles
            check_in_channel = discord.utils.get(interaction.guild.text_channels, name=CHECK_IN_CHANNEL)
            actual_cleared = await reset_checked_in_roles_and_sheet(interaction.guild, check_in_channel)

            # Remove checked-in role from all members
            if checked_in_role:
                for member in checked_in_role.members:
                    try:
                        await member.remove_roles(checked_in_role, reason="Check-in reset")
                    except discord.Forbidden:
                        if BotLogger:
                            BotLogger.warning(f"No permission to remove role from {member}", "RESET")
                    except Exception as e:
                        if BotLogger:
                            BotLogger.warning(f"Error removing role from {member}: {e}", "RESET")

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # Send completion message
            embed_done = embed_from_cfg("reset_complete", role="Check-in", count=actual_cleared, elapsed=elapsed)
            await interaction.followup.send(embed=embed_done, ephemeral=True)

            # Update embeds and refresh cache
            await update_live_embeds(interaction.guild)
            await refresh_sheet_cache(bot=interaction.client)

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "Reset Check-ins"
            )


class ToggleCheckInButton(BaseButton):
    """Administrative button for toggling check-in channel visibility."""

    def __init__(self):
        super().__init__(
            label="Toggle Check-In Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle check-in channel toggle with permission validation."""
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await toggle_persisted_channel(
            interaction,
            persist_key="checkin",
            channel_name=CHECK_IN_CHANNEL,
            role_name=REGISTERED_ROLE,
            ping_role=True,
        )


class RegisterButton(BaseButton):
    """Button for user registration with modal display."""

    def __init__(self, label="Register", custom_id="register_btn", style=discord.ButtonStyle.success):
        super().__init__(
            label=label,
            style=style,
            emoji="📝",
            custom_id=custom_id
        )

    @ErrorHandler.wrap_callback("Registration")
    async def callback(self, interaction: discord.Interaction):
        """Handle registration button click with data prefilling."""
        try:
            guild_id = str(interaction.guild.id)
            mode = get_event_mode_for_guild(guild_id)
            member = interaction.user
            discord_tag = str(member)

            # Check if user is in waitlist
            try:
                from helpers.waitlist_helpers import WaitlistManager
                waitlist_data = await WaitlistManager.get_waitlist_entry(guild_id, discord_tag)
            except ImportError:
                waitlist_data = None

            # Get user data using the helper (prioritize sheet data over waitlist)
            user_data = await SheetOperations.get_user_data(discord_tag, guild_id)

            # Build the modal with prefilled data
            if user_data:
                # User is registered, use their sheet data
                modal = RegistrationModal(
                    team_field=(mode == "doubleup"),
                    default_ign=user_data.get("ign", ""),
                    default_alt_igns=user_data.get("alt_ign", ""),
                    default_team=user_data.get("team", ""),
                    default_pronouns=user_data.get("pronouns", "")
                )
            elif waitlist_data:
                # User is in waitlist, use their waitlist data
                modal = RegistrationModal(
                    team_field=(mode == "doubleup"),
                    default_ign=waitlist_data.get("ign", ""),
                    default_alt_igns=waitlist_data.get("alt_igns", ""),
                    default_team=waitlist_data.get("team_name", ""),
                    default_pronouns=waitlist_data.get("pronouns", "")
                )
            else:
                # New registration
                modal = RegistrationModal(team_field=(mode == "doubleup"))

            # Attach context for the modal
            modal.guild = interaction.guild
            modal.member = interaction.user

            # Show the modal
            await interaction.response.send_modal(modal)

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "Registration Button"
            )


class UnregisterButton(BaseButton):
    """Button for user unregistration with waitlist handling."""

    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="unregister_btn"
        )

    @ErrorHandler.wrap_callback("Unregister")
    async def callback(self, interaction: discord.Interaction):
        """Handle unregistration with waitlist processing."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            guild = interaction.guild
            member = interaction.user
            discord_tag = str(member)
            guild_id = str(guild.id)

            # Check if user is in waitlist first
            try:
                from helpers.waitlist_helpers import WaitlistManager
                waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

                if waitlist_position:
                    # User is in waitlist, remove them
                    await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="✅ Removed from Waitlist",
                            description=f"You have been removed from the waitlist (you were position #{waitlist_position}).",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
                    return
            except ImportError:
                pass

            # Attempt to unregister from sheet
            ok = await unregister_user(discord_tag, guild_id=guild_id)

            if not ok:
                return await interaction.followup.send(
                    embed=embed_from_cfg("unregister_not_registered"),
                    ephemeral=True
                )

            # Remove roles
            await RoleManager.remove_roles(member, [REGISTERED_ROLE, CHECKED_IN_ROLE])

            # Send confirmation
            await interaction.followup.send(
                embed=embed_from_cfg("unregister_success"),
                ephemeral=True
            )

            if BotLogger:
                BotLogger.info(f"Unregistration successful: {discord_tag} in {guild.name}", "UNREGISTER")
            else:
                logging.info(f"[UNREGISTER SUCCESS] Guild={guild.name}({guild.id}) User={discord_tag}")

            # Update embeds
            await EmbedHelper.update_all_guild_embeds(guild)

            # Process waitlist in case someone can be registered
            try:
                from helpers.waitlist_helpers import WaitlistManager
                await WaitlistManager.process_waitlist(guild)
            except ImportError:
                pass

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "Unregister"
            )


class ToggleRegistrationButton(BaseButton):
    """Administrative button for toggling registration channel visibility."""

    def __init__(self):
        super().__init__(
            label="Toggle Registration Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle registration channel toggle with permission validation."""
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await toggle_persisted_channel(
            interaction,
            persist_key="registration",
            channel_name=REGISTRATION_CHANNEL,
            role_name=ANGEL_ROLE,
            ping_role=True,
        )


class ResetRegistrationButton(BaseButton):
    """Administrative button for resetting all registrations with comprehensive cleanup."""

    def __init__(self):
        super().__init__(
            label="Reset Registrations",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle registration reset with full cleanup and progress reporting."""
        # Permission validation
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            guild = interaction.guild
            reg_channel = interaction.channel
            guild_id = str(guild.id)

            # Count registered members for progress reporting
            registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            checked_in_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
            cleared_count = len(registered_role.members) if registered_role else 0

            # Show starting message
            resetting = embed_from_cfg("resetting", role="registered", count=cleared_count)
            await interaction.response.send_message(embed=resetting, ephemeral=True)

            # Record start time for performance tracking
            start_time = time.perf_counter()

            # Clear the sheet & cache
            cleared = await reset_registered_roles_and_sheet(guild, reg_channel)

            # Remove roles from all members
            if registered_role:
                for member in registered_role.members:
                    try:
                        roles_to_remove = [registered_role]
                        if checked_in_role and checked_in_role in member.roles:
                            roles_to_remove.append(checked_in_role)
                        await member.remove_roles(*roles_to_remove, reason="Registration reset")
                    except discord.Forbidden:
                        if BotLogger:
                            BotLogger.warning(f"No permission to remove roles from {member}", "RESET")
                    except Exception as e:
                        if BotLogger:
                            BotLogger.warning(f"Error removing roles from {member}: {e}", "RESET")

            # Clear the waitlist for this guild
            try:
                from helpers.waitlist_helpers import WaitlistManager
                all_data = WaitlistManager._load_waitlist_data()
                if guild_id in all_data:
                    all_data[guild_id]["waitlist"] = []
                    WaitlistManager._save_waitlist_data(all_data)
            except ImportError:
                pass

            elapsed = time.perf_counter() - start_time

            # Clean up extra bot messages (keep the pinned "live" one)
            main_chan_id, main_msg_id = get_persisted_msg(guild_id, "registration")
            deleted_messages = 0

            async for msg in reg_channel.history(limit=100):
                if (msg.author.bot and
                        msg.id != main_msg_id and
                        msg.embeds and
                        not msg.pinned):
                    try:
                        await msg.delete()
                        deleted_messages += 1
                    except discord.Forbidden:
                        break  # Stop if we don't have permission
                    except Exception:
                        pass  # Continue on other errors

            # Update the live registration embed
            await update_live_embeds(guild)

            # Send completion confirmation
            complete_embed = embed_from_cfg(
                "reset_complete",
                role="Registration",
                count=cleared,
                elapsed=elapsed
            )
            await interaction.followup.send(embed=complete_embed, ephemeral=True)

            # Refresh cache to match the reset state
            await refresh_sheet_cache(bot=interaction.client)

            if BotLogger:
                BotLogger.info(
                    f"Registration reset completed: {cleared} users, {deleted_messages} messages cleaned, {elapsed:.2f}s",
                    "RESET")

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "Reset Registration"
            )


class ReminderButton(BaseButton):
    """Administrative button for sending reminder DMs to unchecked users."""

    def __init__(self):
        super().__init__(
            label="Send Reminders",
            style=discord.ButtonStyle.primary,
            emoji="📨",
            custom_id="reminder_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle sending reminder DMs with comprehensive reporting."""
        # Check permissions
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            return await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Send reminders to unchecked-in users
            dm_embed = embed_from_cfg("reminder_dm")
            guild = interaction.guild

            dmmed = await send_reminder_dms(
                client=interaction.client,
                guild=guild,
                dm_embed=dm_embed,
                view_cls=DMActionView
            )

            # Report results
            count = len(dmmed)
            users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd."
            result_embed = embed_from_cfg("reminder_public", count=count, users=users_list)
            await interaction.followup.send(embed=result_embed, ephemeral=True)

        except Exception as e:
            await ErrorHandler.handle_interaction_error(
                interaction, e, "Send Reminders"
            )


class RegistrationModal(discord.ui.Modal):
    """
    Registration modal with comprehensive validation and team name similarity checking.

    This modal handles user registration including IGN, pronouns, team names (for doubleup),
    and alternative IGNs. It includes intelligent team name suggestion functionality.
    """

    def __init__(
            self,
            *,
            team_field: bool = False,
            default_ign: str | None = None,
            default_alt_igns: str | None = None,
            default_team: str | None = None,
            default_pronouns: str | None = None,
            bypass_similarity: bool = False
    ):
        super().__init__(title="Register for the Event")
        self.bypass_similarity = bypass_similarity

        # In-Game Name (required)
        self.ign_input = discord.ui.TextInput(
            label="In-Game Name",
            placeholder="Enter your TFT IGN",
            required=True,
            default=default_ign or ""
        )
        self.add_item(self.ign_input)

        # Alternative IGN(s) (optional)
        self.alt_ign_input = discord.ui.TextInput(
            label="Alternative IGN(s)",
            placeholder="Comma-separated alt IGNs (optional)",
            required=False,
            default=default_alt_igns or ""
        )
        self.add_item(self.alt_ign_input)

        # Team Name (doubleup only) - WITH 20 CHARACTER LIMIT
        self.team_input = None
        if team_field:
            self.team_input = discord.ui.TextInput(
                label="Team Name",
                placeholder="Your Team Name (max 20 characters)",
                required=True,
                default=default_team or "",
                max_length=20
            )
            self.add_item(self.team_input)

        # Pronouns (optional)
        self.pronouns_input = discord.ui.TextInput(
            label="Pronouns",
            placeholder="e.g. She/Her, He/Him, They/Them",
            required=False,
            default=default_pronouns or ""
        )
        self.add_item(self.pronouns_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission with validation and team name similarity checking."""
        try:
            guild = interaction.guild
            user = interaction.user
            guild_id = str(guild.id)
            discord_tag = str(user)
            mode = get_event_mode_for_guild(guild_id)
            ign = self.ign_input.value

            # Auto-capitalize pronouns
            if self.pronouns_input.value:
                pronouns_parts = self.pronouns_input.value.split("/")
                pronouns = "/".join(part.strip().capitalize() for part in pronouns_parts)
            else:
                pronouns = ""

            team_value = self.team_input.value if self.team_input else None
            alt_igns = self.alt_ign_input.value.strip() if self.alt_ign_input else None

            # Check if registration is open
            reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
            angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)

            await interaction.response.defer(ephemeral=True, thinking=True)

            if reg_channel and angel_role:
                overwrites = reg_channel.overwrites_for(angel_role)
                if not overwrites.view_channel:
                    embed = embed_from_cfg("registration_closed")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

            # Team name similarity checking for doubleup mode
            if (mode == "doubleup" and
                    team_value and
                    not getattr(self, "bypass_similarity", False)):

                try:
                    sheet = await get_sheet_for_guild(guild_id, "GAL Database")
                    if sheet:
                        team_col_raw = await retry_until_successful(sheet.col_values, 9)
                        user_team_value = team_value.strip().lower()

                        # Build normalized team list (case-insensitive)
                        norm_to_original = {}
                        team_col = []
                        for t in team_col_raw[2:]:  # Skip headers
                            if t and t.strip():
                                normalized = t.strip().lower()
                                if normalized != user_team_value:
                                    team_col.append(normalized)
                                    norm_to_original[normalized] = t.strip()

                        # Check for similar team names using fuzzy matching
                        result = process.extractOne(
                            user_team_value, team_col, scorer=fuzz.ratio, score_cutoff=75
                        )
                        suggested_team = norm_to_original[result[0]] if result else None

                        if suggested_team:
                            # Show team name choice modal
                            await interaction.followup.send(
                                embed=discord.Embed(
                                    title="Similar Team Found",
                                    description=f"Did you mean **{suggested_team}**?\n\n"
                                                f"Click **Use Suggested** to use the located team name, or **Keep Mine** to register your entered team name.",
                                    color=discord.Color.blurple()
                                ),
                                view=TeamNameChoiceView(self, ign, pronouns, suggested_team, team_value),
                                ephemeral=True
                            )
                            return
                except Exception as e:
                    # If similarity checking fails, proceed with registration
                    if BotLogger:
                        BotLogger.warning(f"Team similarity check failed: {e}", "REGISTRATION")

            # Proceed with registration
            await complete_registration(
                interaction,
                ign,
                pronouns,
                team_value,
                alt_igns,
                self
            )

        except Exception as e:
            await log_error(interaction.client, interaction.guild, f"[REGISTER-MODAL-ERROR] {e}")


class TeamNameChoiceView(BaseView):
    """View for handling team name similarity choices with timeout handling."""

    def __init__(self, reg_modal, ign, pronouns, suggested_team, user_team):
        super().__init__(timeout=60)
        self.reg_modal = reg_modal
        self.ign = ign
        self.pronouns = pronouns
        self.suggested_team = suggested_team
        self.user_team = user_team

    @discord.ui.button(label="Use Suggested", style=discord.ButtonStyle.success, emoji="✅")
    async def use_suggested(self, interaction, button):
        """Handle using the suggested team name."""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Complete registration with suggested team
        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.suggested_team,
            self.reg_modal.alt_ign_input.value.strip(),
            self.reg_modal
        )

    @discord.ui.button(label="Keep My Team Name", style=discord.ButtonStyle.secondary, emoji="📝")
    async def keep_mine(self, interaction, button):
        """Handle keeping the user's original team name."""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Complete registration with user's team name
        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.user_team,
            self.reg_modal.alt_ign_input.value.strip(),
            self.reg_modal
        )

    async def on_timeout(self):
        """Handle timeout by disabling all items."""
        for item in self.children:
            item.disabled = True


class CheckInView(BaseView):
    """
    Main check-in view with dynamic button configuration based on channel state.

    This view adapts its buttons based on whether the check-in channel is open
    or closed, providing appropriate administrative and user controls.
    """

    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

        # Determine channel state
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        if is_open:
            # Channel is open - show user and admin controls
            self.add_item(ChannelCheckInButton())
            self.add_item(ChannelCheckOutButton())
            self.add_item(ReminderButton())
            self.add_item(ToggleCheckInButton())
        else:
            # Channel is closed - show admin controls only
            self.add_item(ResetCheckInsButton())
            self.add_item(ToggleCheckInButton())


class RegistrationView(BaseView):
    """
    Main registration view with dynamic button configuration based on channel state.

    This view adapts its buttons based on whether the registration channel is open
    or closed, providing appropriate user and administrative controls.
    """

    def __init__(self, embed_message_id: int | None, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

        # Determine channel state
        reg_ch = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        is_open = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

        if is_open:
            # Channel is open - show user and admin controls
            self.add_item(RegisterButton())
            self.add_item(UnregisterButton())
            self.add_item(ToggleRegistrationButton())
        else:
            # Channel is closed - show admin controls only
            self.add_item(ResetRegistrationButton())
            self.add_item(ToggleRegistrationButton())


class DMActionView(BaseView):
    """
    DM action view for providing users with registration and check-in controls via DM.

    This view dynamically configures available actions based on the user's current
    status and server channel states.
    """

    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(timeout=None)
        self.guild = guild
        self.member = member

        # Check channel states
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        is_registered = reg_role in member.roles if reg_role else False

        if is_registered:
            # User is registered - show unregister and check-in controls
            unreg_btn = DMUnregisterButton(guild, member)
            self.add_item(unreg_btn)

            ci_btn = DMCheckToggleButton(guild, member)
            ci_btn.disabled = not ci_open
            self.add_item(ci_btn)


class PersistentRegisteredListView(BaseView):
    """Simple persistent view for registered user lists with reminder functionality."""

    def __init__(self, guild):
        super().__init__(timeout=None)
        self.add_item(ReminderButton())


async def update_live_embeds(guild):
    """
    Update all live embeds for a guild.

    This is a convenience wrapper around EmbedHelper.update_all_guild_embeds
    for backward compatibility with existing code.
    """
    return await EmbedHelper.update_all_guild_embeds(guild)


async def update_registration_embed(
        channel: discord.TextChannel,
        msg_id: int,
        guild: discord.Guild
):
    """
    Update the registration embed with current registration data and formatting.

    This function handles the complex logic of building registration lists,
    managing capacity information, and updating the embed with current data.
    """
    try:
        # Determine channel state
        is_open = ChannelManager.get_channel_state(guild)['registration_open']

        # Get base embed configuration
        key = "registration" if is_open else "registration_closed"
        base = embed_from_cfg(key)

        # Fetch the message
        try:
            msg = await channel.fetch_message(msg_id)
        except discord.NotFound:
            if BotLogger:
                BotLogger.warning(f"Registration message {msg_id} not found in {channel.name}", "EMBED_UPDATE")
            return
        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Could not fetch registration message {msg_id}: {e}", "EMBED_UPDATE")
            return

        # If closed, just update with base embed
        if not is_open:
            return await msg.edit(embed=base, view=RegistrationView(msg_id, guild))

        # Build open registration embed with user data
        mode = get_event_mode_for_guild(str(guild.id))
        users = await SheetOperations.get_all_registered_users(str(guild.id))

        total_players = len(users)
        total_teams = len({t for _, _, t in users if t}) if mode == "doubleup" else 0

        # Build description with schedule information
        desc = base.description or ""
        close_iso = get_schedule(guild.id, "registration_close")
        if close_iso:
            ts = int(datetime.fromisoformat(close_iso).timestamp())
            desc += f" \n⏰ Registration closes at <t:{ts}:F>"
        desc += "\n\n"

        # Build formatted user list
        lines = EmbedHelper.build_registration_list_lines(users, mode)

        # Create the final embed
        embed = discord.Embed(
            title=base.title,
            description=desc + ("\n".join(lines) if lines else ""),
            color=base.color
        )

        # Add footer with statistics
        if total_players > 0:
            footer_parts = [f"👤 Players: {total_players}"]
            if mode == "doubleup":
                footer_parts.append(f"👥 Teams: {total_teams}")
            embed.set_footer(text=" • ".join(footer_parts))

        await msg.edit(embed=embed, view=RegistrationView(msg_id, guild))

    except Exception as e:
        await log_error(None, guild, f"Failed to update registration embed: {e}")


async def update_checkin_embed(
        channel: discord.TextChannel,
        msg_id: int,
        guild: discord.Guild
):
    """
    Update the check-in embed with current check-in data and team readiness status.

    This function builds comprehensive check-in displays including individual status,
    team readiness (for doubleup), and progress statistics.
    """
    try:
        # Determine channel state
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        # Get base embed configuration
        key = "checkin" if is_open else "checkin_closed"
        base = embed_from_cfg(key)

        # Fetch the message
        try:
            msg = await channel.fetch_message(msg_id)
        except discord.NotFound:
            if BotLogger:
                BotLogger.warning(f"Check-in message {msg_id} not found in {channel.name}", "EMBED_UPDATE")
            return
        except Exception as e:
            if BotLogger:
                BotLogger.error(f"Could not fetch check-in message {msg_id}: {e}", "EMBED_UPDATE")
            return

        # If closed, show base embed
        if not is_open:
            embed = discord.Embed(
                title=base.title,
                description=base.description or "",
                color=base.color
            )
            return await msg.edit(embed=embed, view=CheckInView(guild))

        # Build open check-in embed with user data
        desc = base.description or ""
        close_iso = get_schedule(guild.id, "checkin_close")
        if close_iso:
            ts = int(datetime.fromisoformat(close_iso).timestamp())
            desc += f" \n⏰ Check-in closes at <t:{ts}:t>"
        desc += "\n\n"

        # Get user data from cache
        async with cache_lock:
            entries = list(sheet_cache["users"].items())

        def is_true(v):
            return str(v).upper() == "TRUE"

        # Filter for registered users
        all_registered = [
            (tag, tpl) for tag, tpl in entries
            if len(tpl) > 2 and is_true(tpl[2])
        ]

        # Calculate check-in statistics
        checked_in = [
            (tag, tpl) for tag, tpl in entries
            if len(tpl) > 3 and is_true(tpl[2]) and is_true(tpl[3])
        ]

        total_reg = len(all_registered)
        total_ci = len(checked_in)

        mode = get_event_mode_for_guild(str(guild.id))

        # Calculate team statistics for doubleup mode
        if mode == "doubleup":
            teams_data = {}
            for tag, tpl in all_registered:
                team_name = tpl[4] if len(tpl) > 4 and tpl[4] else "No Team"
                if team_name not in teams_data:
                    teams_data[team_name] = []
                teams_data[team_name].append((tag, tpl))

            fully_checked_teams = 0
            total_teams = len(teams_data)

            for team_name, members in teams_data.items():
                if len(members) >= 2:
                    team_fully_checked = all(
                        len(member_data) > 3 and is_true(member_data[3])
                        for tag, member_data in members
                    )

                    if team_fully_checked:
                        fully_checked_teams += 1
        else:
            total_teams = 0
            fully_checked_teams = 0

        # Build formatted check-in list
        lines = EmbedHelper.build_checkin_list_lines(all_registered, mode)

        # Create the final embed
        new_desc = desc + ("\n".join(lines) if lines else "")
        embed = discord.Embed(
            title=base.title,
            description=new_desc,
            color=base.color
        )

        # Build footer with comprehensive statistics
        footer_parts = [f"👤 Checked-In: {total_ci}/{total_reg}"]

        if mode == "doubleup":
            footer_parts.append(f"👥 Teams Ready: {fully_checked_teams}/{total_teams}")

        if total_reg > 0:
            percentage = (total_ci / total_reg) * 100
            footer_parts.append(f"📊 {percentage:.0f}%")

        embed.set_footer(text=" • ".join(footer_parts))

        # Create view with conditional reminder button
        view = CheckInView(guild)

        # Remove reminder button if everyone is checked in
        if total_reg > 0 and total_ci == total_reg:
            new_view = BaseView(timeout=None)
            for item in view.children:
                if not isinstance(item, ReminderButton):
                    new_view.add_item(item)
            view = new_view

        await msg.edit(embed=embed, view=view)

    except Exception as e:
        await log_error(None, guild, f"Failed to update check-in embed: {e}")


# Legacy function for backward compatibility
async def create_persisted_embed(guild, channel, embed, view, persist_key, pin=True, announce_pin=True):
    """
    Legacy wrapper for EmbedHelper.create_persisted_embed.

    Maintained for backward compatibility with existing code.
    New code should use EmbedHelper.create_persisted_embed directly.
    """
    return await EmbedHelper.create_persisted_embed(
        guild, channel, embed, view, persist_key, pin, announce_pin
    )


# Additional utility functions for view management
async def refresh_all_views_for_guild(guild: discord.Guild) -> Dict[str, Any]:
    """
    Refresh all views and embeds for a specific guild.

    This function provides a comprehensive refresh of all interactive elements
    including embeds, views, and DM notifications for a guild.

    Args:
        guild: Discord guild to refresh views for

    Returns:
        Dictionary with refresh results and statistics
    """
    try:
        results = {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "embeds_updated": {},
            "dm_views_refreshed": 0,
            "errors": [],
            "success": True
        }

        # Update all guild embeds
        embed_results = await EmbedHelper.update_all_guild_embeds(guild)
        results["embeds_updated"] = embed_results

        # Refresh DM views for all users
        dm_refresh_count = await EmbedHelper.refresh_dm_views_for_users(guild)
        results["dm_views_refreshed"] = dm_refresh_count

        # Check for any failures
        if not any(embed_results.values()):
            results["errors"].append("All embed updates failed")
            results["success"] = False

        if BotLogger:
            BotLogger.info(f"View refresh completed for {guild.name}: {results}", "VIEW_REFRESH")

        return results

    except Exception as e:
        error_result = {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "embeds_updated": {},
            "dm_views_refreshed": 0,
            "errors": [f"Critical error: {e}"],
            "success": False
        }

        if BotLogger:
            BotLogger.error(f"View refresh failed for {guild.name}: {e}", "VIEW_REFRESH")

        return error_result


def get_view_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status of the views module.

    This function checks the availability and functionality of all view
    components and their dependencies.

    Returns:
        Dictionary with detailed health information
    """
    health = {
        "status": "healthy",
        "warnings": [],
        "errors": [],
        "dependencies": {},
        "view_classes": {},
        "button_classes": {}
    }

    # Check core dependencies
    dependencies = {
        "BotLogger": BotLogger is not None,
        "ErrorHandler": ErrorHandler is not None,
        "RoleManager": RoleManager is not None,
        "ChannelManager": ChannelManager is not None,
        "SheetOperations": SheetOperations is not None,
        "Validators": Validators is not None,
        "EmbedHelper": EmbedHelper is not None
    }

    for dep_name, available in dependencies.items():
        health["dependencies"][dep_name] = available
        if not available:
            health["warnings"].append(f"{dep_name} not available, using fallback")

    # Check view classes
    view_classes = {
        "BaseView": BaseView,
        "CheckInView": CheckInView,
        "RegistrationView": RegistrationView,
        "DMActionView": DMActionView,
        "TeamNameChoiceView": TeamNameChoiceView,
        "RegistrationModal": RegistrationModal
    }

    for view_name, view_class in view_classes.items():
        try:
            health["view_classes"][view_name] = {
                "available": view_class is not None,
                "has_timeout_handler": hasattr(view_class, 'on_timeout'),
                "has_error_handler": hasattr(view_class, 'on_error')
            }
        except Exception as e:
            health["view_classes"][view_name] = {"error": str(e)}
            health["errors"].append(f"Error checking {view_name}: {e}")

    # Check button classes
    button_classes = {
        "BaseButton": BaseButton,
        "RegisterButton": RegisterButton,
        "UnregisterButton": UnregisterButton,
        "ChannelCheckInButton": ChannelCheckInButton,
        "ChannelCheckOutButton": ChannelCheckOutButton,
        "DMUnregisterButton": DMUnregisterButton,
        "DMCheckToggleButton": DMCheckToggleButton,
        "ResetCheckInsButton": ResetCheckInsButton,
        "ResetRegistrationButton": ResetRegistrationButton,
        "ToggleCheckInButton": ToggleCheckInButton,
        "ToggleRegistrationButton": ToggleRegistrationButton,
        "ReminderButton": ReminderButton
    }

    for button_name, button_class in button_classes.items():
        try:
            health["button_classes"][button_name] = {
                "available": button_class is not None,
                "has_callback": hasattr(button_class, 'callback'),
                "has_interaction_check": hasattr(button_class, 'interaction_check')
            }
        except Exception as e:
            health["button_classes"][button_name] = {"error": str(e)}
            health["errors"].append(f"Error checking {button_name}: {e}")

    # Determine overall health status
    if health["errors"]:
        health["status"] = "error"
    elif health["warnings"]:
        health["status"] = "degraded"

    return health


# Export validation for module health checking
def validate_views_module() -> bool:
    """
    Validate that the views module is properly configured and functional.

    This function performs basic validation to ensure the module can
    function correctly with available dependencies.

    Returns:
        True if module is functional, False otherwise
    """
    try:
        # Check critical classes are available
        critical_classes = [BaseView, BaseButton, RegisterButton, CheckInView, RegistrationView]
        if not all(cls is not None for cls in critical_classes):
            return False

        # Check that embed functions are callable
        if not callable(embed_from_cfg):
            return False

        # Check that we have some form of error handling
        if ErrorHandler is None and BotLogger is None:
            return False

        return True

    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Views module validation failed: {e}", "MODULE_VALIDATION")
        else:
            logging.error(f"Views module validation failed: {e}")
        return False


# Initialize module validation on import
if __name__ != "__main__":
    try:
        if validate_views_module():
            if BotLogger:
                BotLogger.success("Views module initialized successfully", "MODULE_INIT")
            else:
                logging.info("Views module initialized successfully")
        else:
            if BotLogger:
                BotLogger.warning("Views module initialized with limited functionality", "MODULE_INIT")
            else:
                logging.warning("Views module initialized with limited functionality")
    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Views module initialization error: {e}", "MODULE_INIT")
        else:
            logging.error(f"Views module initialization error: {e}")