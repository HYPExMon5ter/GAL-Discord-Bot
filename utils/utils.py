# utils/utils.py

"""
Utility functions for the GAL Discord Bot.

This module provides reusable utility functions for common operations
such as role management, channel toggling, and member resolution.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

import discord

# Import configuration
from config import (
    ALLOWED_ROLES,
    CHECKED_IN_ROLE,
    REGISTERED_ROLE,
    CHECK_IN_CHANNEL,
    REGISTRATION_CHANNEL,
    ANGEL_ROLE,
    embed_from_cfg,
    get_sheet_settings, EMBEDS_CFG, hex_to_color
)
from helpers import ErrorSeverity, ErrorContext, ErrorHandler, ErrorCategory

# Import logging helper
try:
    from helpers.logging_helper import BotLogger
except ImportError:
    BotLogger = None
    import logging

# Import helpers for role and embed management
try:
    from helpers.role_manager import RoleManager
except ImportError:
    RoleManager = None

try:
    from helpers.embed_helper import EmbedHelper
except ImportError:
    EmbedHelper = None


# Custom exceptions for utility operations
class UtilsError(Exception):
    """Base exception for utility operations."""
    pass


class MemberNotFoundError(UtilsError):
    """Exception raised when a member cannot be found."""
    pass


class RoleNotFoundError(UtilsError):
    """Exception raised when a role cannot be found."""
    pass


# Event mode management
_event_modes = {}  # Guild ID -> Event Mode mapping


def get_event_mode_for_guild(guild_id: str) -> str:
    """
    Get the current event mode for a guild.

    Args:
        guild_id: Discord guild ID

    Returns:
        Event mode string ('normal' or 'doubleup')
    """
    return _event_modes.get(guild_id, "normal")


def set_event_mode_for_guild(guild_id: str, mode: str) -> None:
    """
    Set the event mode for a guild.

    Args:
        guild_id: Discord guild ID
        mode: Event mode ('normal' or 'doubleup')
    """
    _event_modes[guild_id] = mode
    if BotLogger:
        BotLogger.info(f"Set event mode for guild {guild_id} to {mode}", "UTILS")


# Role checking utilities
def has_allowed_role(member: discord.Member, required_roles: List[str] = None) -> bool:
    """
    Check if a member has any of the allowed roles.

    Args:
        member: Discord member to check
        required_roles: Optional list of specific roles to check for

    Returns:
        True if member has any allowed role, False otherwise
    """
    if not member:
        return False

    roles_to_check = required_roles or ALLOWED_ROLES

    for role in member.roles:
        if role.name in roles_to_check:
            return True

    return False


def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
    """
    Check if the interaction user has any of the allowed roles.

    Args:
        interaction: Discord interaction

    Returns:
        True if user has allowed role, False otherwise
    """
    if not interaction.guild:
        return False

    member = interaction.user
    if isinstance(member, discord.User):
        member = interaction.guild.get_member(member.id)

    return has_allowed_role(member)


# Channel management utilities
async def toggle_persisted_channel(
        interaction: discord.Interaction,
        persist_key: str,
        channel_name: str,
        role_name: str,
        ping_role: bool = False
) -> None:
    """
    Toggle channel visibility and update persisted embeds.
    Includes comprehensive error handling and proper embed updates.
    """
    try:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=embed_from_cfg("error", message="This command must be used in a server."),
                ephemeral=True
            )
            return

        # Find channel and role
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        role = discord.utils.get(guild.roles, name=role_name)

        if not channel:
            BotLogger.error(f"Channel {channel_name} not found in {guild.name}", "TOGGLE")
            await interaction.response.send_message(
                embed=embed_from_cfg("channel_not_found", channel=channel_name),
                ephemeral=True
            )
            return

        if not role:
            BotLogger.error(f"Role {role_name} not found in {guild.name}", "TOGGLE")
            await interaction.response.send_message(
                embed=embed_from_cfg("error", message=f"Role '{role_name}' not found."),
                ephemeral=True
            )
            return

        # Get current visibility
        overwrites = channel.overwrites_for(role)
        is_currently_visible = overwrites.view_channel if overwrites.view_channel is not None else False

        BotLogger.debug(f"Channel {channel_name} currently visible: {is_currently_visible}", "TOGGLE")

        # Toggle the permission
        try:
            await channel.set_permissions(
                role,
                view_channel=not is_currently_visible,
                reason=f"Toggled by {interaction.user}"
            )
            BotLogger.info(f"Toggled {channel_name} visibility to {not is_currently_visible}", "TOGGLE")

        except discord.Forbidden:
            BotLogger.error(f"No permission to toggle {channel_name}", "TOGGLE")
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
            return
        except Exception as e:
            BotLogger.error(f"Failed to toggle channel permissions: {e}", "TOGGLE")
            await interaction.response.send_message(
                embed=embed_from_cfg("error", message="Failed to toggle channel."),
                ephemeral=True
            )
            return

        # Build response embed with correct description
        if persist_key == "registration":
            embed_key = "registration_channel_toggled"
        else:
            embed_key = "checkin_channel_toggled"

        embed_config = EMBEDS_CFG.get(embed_key, {})

        # Channel is NOW visible (was hidden)
        if not is_currently_visible:
            title = embed_config.get("title", "Channel Toggled")
            description = embed_config.get("description_visible", "Channel is now visible.")
            color = embed_config.get("color_visible", "#2ecc71")

            # Ping role if requested and channel is being opened
            if ping_role:
                try:
                    ping_msg = await channel.send(f"{role.mention} The channel is now open!")
                    # Delete after 5 seconds
                    await ping_msg.delete(delay=5)
                except Exception as e:
                    BotLogger.warning(f"Could not send ping: {e}", "TOGGLE")

        else:  # Channel is NOW hidden (was visible)
            title = embed_config.get("title", "Channel Toggled")
            description = embed_config.get("description_hidden", "Channel is now hidden.")
            color = embed_config.get("color_hidden", "#e67e22")

        # Send response
        response_embed = discord.Embed(
            title=title,
            description=description,
            color=hex_to_color(color)
        )

        await interaction.response.send_message(embed=response_embed, ephemeral=True)

        # Update the persisted embed to reflect new state
        try:
            from core.persistence import get_persisted_msg

            channel_id, msg_id = get_persisted_msg(guild.id, persist_key)
            if channel_id and msg_id:
                target_channel = guild.get_channel(channel_id)
                if target_channel:
                    BotLogger.debug(f"Updating persisted embed for {persist_key}", "TOGGLE")

                    # Import update functions
                    if persist_key == "registration":
                        from core.views import update_registration_embed
                        await update_registration_embed(target_channel, msg_id, guild)
                    else:  # checkin
                        from core.views import update_checkin_embed
                        await update_checkin_embed(target_channel, msg_id, guild)

                    BotLogger.debug(f"Successfully updated persisted embed", "TOGGLE")
            else:
                BotLogger.warning(f"No persisted message found for {persist_key}", "TOGGLE")

        except Exception as e:
            BotLogger.error(f"Failed to update persisted embed: {e}", "TOGGLE")
            # Don't fail the whole operation if embed update fails

    except Exception as e:
        error_context = ErrorContext(
            error=e,
            operation="toggle_persisted_channel",
            category=ErrorCategory.CHANNEL_MANAGEMENT,
            severity=ErrorSeverity.MEDIUM,
            guild_id=interaction.guild.id if interaction.guild else None,
            user_id=interaction.user.id,
            additional_context={
                "persist_key": persist_key,
                "channel_name": channel_name,
                "role_name": role_name
            }
        )
        await ErrorHandler._log_error_structured(error_context, True, True)

        # Try to send error response if not already responded
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=embed_from_cfg("error", message="An error occurred while toggling the channel."),
                    ephemeral=True
                )
        except:
            pass


# Member resolution utilities
async def resolve_member(
        guild: discord.Guild,
        identifier: str
) -> Optional[discord.Member]:
    """
    Resolve a member from various identifier formats.

    Args:
        guild: Discord guild
        identifier: Member ID, mention, or name#discriminator

    Returns:
        Discord member if found, None otherwise
    """
    if not guild or not identifier:
        return None

    # Try to parse as member ID
    try:
        member_id = int(identifier.strip("<@!>"))
        member = guild.get_member(member_id)
        if member:
            return member
    except ValueError:
        pass

    # Try to find by name#discriminator
    if "#" in identifier:
        member = guild.get_member_named(identifier)
        if member:
            return member

    # Try to find by display name or username
    identifier_lower = identifier.lower()
    for member in guild.members:
        if (member.display_name.lower() == identifier_lower or
                member.name.lower() == identifier_lower):
            return member

    return None


# DM utilities
async def send_reminder_dms(
        guild: discord.Guild,
        members: List[discord.Member],
        embed_key: str,
        context: str = "reminder"
) -> Dict[str, Any]:
    """
    Send reminder DMs to multiple members.

    Args:
        guild: Discord guild context
        members: List of members to send DMs to
        embed_key: Configuration key for embed content
        context: Context for logging

    Returns:
        Dict with successful and total_attempted counts
    """
    results = {"successful": 0, "total_attempted": len(members)}

    if BotLogger:
        BotLogger.info(f"Sending {context} DMs to {len(members)} members", "UTILS")

    for member in members:
        try:
            # Create reminder embed
            embed = embed_from_cfg(embed_key, guild_name=guild.name)

            # Send DM
            await member.send(embed=embed)
            results["successful"] += 1

        except discord.Forbidden:
            if BotLogger:
                BotLogger.debug(f"Cannot DM {member.name} (DMs closed)", "UTILS")
        except Exception as e:
            if BotLogger:
                BotLogger.warning(f"Failed to DM {member.name}: {e}", "UTILS")

    if BotLogger:
        BotLogger.info(f"DM results: {results['successful']}/{results['total_attempted']} successful", "UTILS")

    return results


# Check-in management utilities
async def toggle_checkin_for_member(
        interaction: discord.Interaction,
        async_func: callable,
        embed_key: str
) -> None:
    """
    Toggle check-in status for a member with sheet and role updates.

    This function handles the complete check-in/out process including:
    - Deferring the interaction response
    - Calling the sheet operation function
    - Updating Discord roles
    - Sending appropriate embed responses
    - Updating channel embeds

    Args:
        interaction: Discord interaction
        async_func: Async function to update sheet (mark_checked_in_async or unmark_checked_in_async)
        embed_key: Configuration key for success embed ("checked_in" or "checked_out")
    """
    try:
        # Defer response for processing
        await interaction.response.defer(ephemeral=True, thinking=True)

        member = interaction.user
        discord_tag = str(member)
        guild_id = str(interaction.guild.id)

        # Try to perform the sheet operation
        success = await async_func(discord_tag, guild_id=guild_id)

        if success:
            # Update role based on the embed key
            if embed_key == "checked_in":
                # Add checked-in role
                if RoleManager:
                    await RoleManager.add_role(member, CHECKED_IN_ROLE)
                else:
                    # Fallback to direct role management
                    role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
                    if role and role not in member.roles:
                        await member.add_roles(role, reason="Checked in via bot")

            elif embed_key == "checked_out":
                # Remove checked-in role
                if RoleManager:
                    await RoleManager.remove_role(member, CHECKED_IN_ROLE)
                else:
                    # Fallback to direct role management
                    role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
                    if role and role in member.roles:
                        await member.remove_roles(role, reason="Checked out via bot")

            # Send success response
            embed = embed_from_cfg(embed_key)
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Update channel embeds if EmbedHelper is available
            if EmbedHelper:
                await EmbedHelper.update_all_guild_embeds(interaction.guild)

            if BotLogger:
                BotLogger.info(
                    f"Successfully toggled check-in for {member.name} ({embed_key})",
                    "CHECKIN_TOGGLE"
                )
        else:
            # Send error response
            await interaction.followup.send(
                embed=embed_from_cfg("error", message="Failed to update check-in status."),
                ephemeral=True
            )

            if BotLogger:
                BotLogger.warning(
                    f"Sheet operation failed for {member.name} ({embed_key})",
                    "CHECKIN_TOGGLE"
                )

    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Check-in toggle failed: {e}", "CHECKIN_TOGGLE")

        try:
            await interaction.followup.send(
                embed=embed_from_cfg("error", message="An error occurred while processing your request."),
                ephemeral=True
            )
        except:
            pass  # Interaction may have timed out


# DM action view utilities
async def update_dm_action_views(
        guild: discord.Guild,
        members: List[discord.Member]
) -> Dict[str, int]:
    """
    Update DM action views for members.

    Args:
        guild: Discord guild
        members: List of members to update views for

    Returns:
        Dict with update statistics
    """
    stats = {"updated": 0, "failed": 0}

    for member in members:
        try:
            # This would typically update any active DM views
            # Implementation depends on view tracking system
            stats["updated"] += 1
        except Exception as e:
            stats["failed"] += 1
            if BotLogger:
                BotLogger.warning(f"Failed to update DM view for {member.name}: {e}", "DM_VIEWS")

    return stats


# LOLChess integration utilities
async def hyperlink_lolchess_profile(
        discord_tag: str,
        guild_id: str
) -> Optional[str]:
    """
    Generate a hyperlinked LOLChess profile for a user.

    Args:
        discord_tag: Discord username#discriminator
        guild_id: Discord guild ID

    Returns:
        Hyperlinked string if user found, None otherwise
    """
    try:
        # This would typically look up the user's IGN from sheets
        # and create a markdown hyperlink to their LOLChess profile
        # Placeholder implementation
        return None
    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error creating LOLChess link: {e}", "LOLCHESS")
        return None


# Channel embed update helper
async def update_channel_embed(
        channel: discord.TextChannel,
        message_id: int,
        guild: discord.Guild,
        persist_key: str
) -> None:
    """
    Update a persisted channel embed based on channel state.

    Args:
        channel: Discord text channel
        message_id: Message ID to update
        guild: Discord guild
        persist_key: Key identifying the embed type
    """
    try:
        # Determine channel state
        if persist_key == "registration":
            role_name = ANGEL_ROLE
            embed_open_key = "registration"
            embed_closed_key = "registration_closed"
        else:  # checkin
            role_name = REGISTERED_ROLE
            embed_open_key = "checkin"
            embed_closed_key = "checkin_closed"

        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            overwrites = channel.overwrites_for(role)
            is_open = overwrites.view_channel
        else:
            is_open = False

        # Create appropriate embed
        embed = embed_from_cfg(embed_open_key if is_open else embed_closed_key)

        # Update message
        message = await channel.fetch_message(message_id)
        await message.edit(embed=embed)

    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error updating channel embed: {e}", "EMBED_UPDATE")


# Health check for utils module
async def validate_utils_health() -> Dict[str, Any]:
    """
    Validate the health of the utils module.

    Returns:
        Dictionary with health status information
    """
    health = {
        "status": True,
        "warnings": [],
        "functions_available": [],
        "dependencies": {}
    }

    # Check available functions
    functions = [
        "has_allowed_role",
        "has_allowed_role_from_interaction",
        "toggle_persisted_channel",
        "resolve_member",
        "send_reminder_dms",
        "toggle_checkin_for_member",
        "update_dm_action_views",
        "hyperlink_lolchess_profile",
        "get_event_mode_for_guild",
        "set_event_mode_for_guild"
    ]

    for func_name in functions:
        if func_name in globals():
            health["functions_available"].append(func_name)

    # Check dependencies
    health["dependencies"]["BotLogger"] = BotLogger is not None
    health["dependencies"]["RoleManager"] = RoleManager is not None
    health["dependencies"]["EmbedHelper"] = EmbedHelper is not None

    # Add warnings for missing dependencies
    if not BotLogger:
        health["warnings"].append("BotLogger not available, using standard logging")
    if not RoleManager:
        health["warnings"].append("RoleManager not available, using direct role management")
    if not EmbedHelper:
        health["warnings"].append("EmbedHelper not available, embed updates may be limited")

    return health


# Export all utility functions
__all__ = [
    # Role utilities
    "has_allowed_role",
    "has_allowed_role_from_interaction",

    # Channel utilities
    "toggle_persisted_channel",

    # Member utilities
    "resolve_member",

    # DM utilities
    "send_reminder_dms",
    "update_dm_action_views",

    # Check-in utilities
    "toggle_checkin_for_member",

    # LOLChess utilities
    "hyperlink_lolchess_profile",

    # Event mode utilities
    "get_event_mode_for_guild",
    "set_event_mode_for_guild",

    # Health check
    "validate_utils_health",

    # Exceptions
    "UtilsError",
    "MemberNotFoundError",
    "RoleNotFoundError"
]