# helpers/channel_helpers.py

import logging
from typing import Optional, List, Dict, Any, Tuple

import discord

from config import REGISTRATION_CHANNEL, CHECK_IN_CHANNEL, ANGEL_ROLE, REGISTERED_ROLE
from .logging_helper import BotLogger
from .error_handler import ErrorHandler, ErrorCategory, ErrorSeverity


class ChannelError(Exception):
    """Custom exception for channel-related errors."""

    def __init__(self, message: str, channel_name: str = "", guild: discord.Guild = None):
        super().__init__(message)
        self.channel_name = channel_name
        self.guild = guild


class ChannelManager:
    """
    Comprehensive channel management system with permission handling.

    This class provides static methods for managing Discord channel visibility,
    permissions, and bulk operations across guilds.
    """

    @staticmethod
    def get_channel_and_role(guild: discord.Guild, channel_type: str) -> Tuple[
        Optional[discord.TextChannel], Optional[discord.Role]]:
        """
        Get the channel and associated role for a given channel type.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"

        Returns:
            Tuple of (channel, role) or (None, None) if not found
        """
        if not guild:
            return None, None

        if channel_type == "registration":
            channel = discord.utils.get(guild.channels, name=REGISTRATION_CHANNEL)
            role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        elif channel_type == "checkin":
            channel = discord.utils.get(guild.channels, name=CHECK_IN_CHANNEL)
            role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        else:
            BotLogger.warning(f"Unknown channel type: {channel_type}", "CHANNEL_MGR")
            return None, None

        return channel, role

    @staticmethod
    def is_channel_open(channel: discord.TextChannel, role: discord.Role) -> bool:
        """
        Check if a channel is open (visible) to a specific role.

        Args:
            channel: Discord text channel
            role: Discord role to check permissions for

        Returns:
            True if role can view the channel, False otherwise
        """
        if not channel or not role:
            return False

        try:
            overwrites = channel.overwrites_for(role)
            return overwrites.view_channel is True
        except Exception as e:
            BotLogger.error(f"Error checking channel visibility for {channel.name}: {e}", "CHANNEL_MGR")
            return False

    @staticmethod
    async def set_channel_visibility(
            channel: discord.TextChannel,
            role: discord.Role,
            visible: bool,
            ping_role: bool = False
    ) -> bool:
        """
        Set channel visibility for a specific role.

        Args:
            channel: Discord text channel
            role: Discord role
            visible: True to make visible, False to hide
            ping_role: True to ping role when opening channel

        Returns:
            True if permissions were changed, False if already in desired state
        """
        if not channel or not role:
            return False

        try:
            # Check current state
            current_visible = ChannelManager.is_channel_open(channel, role)
            if current_visible == visible:
                BotLogger.debug(f"Channel {channel.name} already has desired visibility: {visible}", "CHANNEL_MGR")
                return False

            # Get current overwrites
            overwrites = channel.overwrites_for(role)
            overwrites.view_channel = visible

            # Apply changes
            await channel.set_permissions(
                role,
                overwrite=overwrites,
                reason=f"GAL Bot: {'Opened' if visible else 'Closed'} channel for {role.name}"
            )

            action = "opened" if visible else "closed"
            BotLogger.info(f"{action.capitalize()} channel {channel.name} for {role.name}", "CHANNEL_MGR")

            # Ping role if requested and opening
            if visible and ping_role:
                try:
                    await ChannelManager._ping_role_safely(channel, role)
                except Exception as e:
                    BotLogger.warning(f"Failed to ping role {role.name}: {e}", "CHANNEL_MGR")

            return True

        except discord.Forbidden:
            BotLogger.error(f"No permission to modify {channel.name}", "CHANNEL_MGR")
            return False
        except Exception as e:
            BotLogger.error(f"Error setting channel visibility: {e}", "CHANNEL_MGR")
            return False

    @staticmethod
    async def _ping_role_safely(channel: discord.TextChannel, role: discord.Role) -> bool:
        """
        Safely ping a role in a channel with automatic cleanup.

        Args:
            channel: Discord text channel
            role: Discord role to ping

        Returns:
            True if ping was successful, False otherwise
        """
        try:
            # Send ping message
            ping_message = await channel.send(f"{role.mention} Channel is now open!")

            # Delete the ping message after a short delay
            import asyncio
            await asyncio.sleep(2)
            await ping_message.delete()

            BotLogger.debug(f"Successfully pinged {role.name} in {channel.name}", "CHANNEL_MGR")
            return True

        except Exception as e:
            BotLogger.error(f"Error pinging role {role.name}: {e}", "CHANNEL_MGR")
            return False

    @staticmethod
    async def toggle_channel_visibility(
            guild: discord.Guild,
            channel_type: str,
            ping_role: bool = True
    ) -> Optional[bool]:
        """
        Toggle channel visibility for a specific channel type.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"
            ping_role: True to ping role when opening

        Returns:
            True if channel is now open, False if closed, None if failed
        """
        try:
            channel, role = ChannelManager.get_channel_and_role(guild, channel_type)

            if not channel or not role:
                BotLogger.warning(f"Could not find channel/role for {channel_type} in {guild.name}", "CHANNEL_MGR")
                return None

            # Get current state and toggle
            is_open = ChannelManager.is_channel_open(channel, role)
            new_state = not is_open

            # Apply the toggle
            changed = await ChannelManager.set_channel_visibility(channel, role, new_state, ping_role)

            if changed:
                return new_state
            else:
                return is_open  # Return current state if no change

        except Exception as e:
            BotLogger.error(f"Error toggling {channel_type} channel: {e}", "CHANNEL_MGR")
            return None

    @staticmethod
    def get_channel_state(guild: discord.Guild) -> Dict[str, Any]:
        """
        Get current state of all managed channels.

        Args:
            guild: Discord guild

        Returns:
            Dict with channel state information
        """
        state = {
            "registration_open": False,
            "checkin_open": False,
            "registration_exists": False,
            "checkin_exists": False,
            "guild_id": guild.id,
            "guild_name": guild.name
        }

        try:
            # Check registration channel
            reg_channel, reg_role = ChannelManager.get_channel_and_role(guild, "registration")
            state["registration_exists"] = bool(reg_channel and reg_role)

            if reg_channel and reg_role:
                state["registration_open"] = ChannelManager.is_channel_open(reg_channel, reg_role)

            # Check check-in channel
            checkin_channel, checkin_role = ChannelManager.get_channel_and_role(guild, "checkin")
            state["checkin_exists"] = bool(checkin_channel and checkin_role)

            if checkin_channel and checkin_role:
                state["checkin_open"] = ChannelManager.is_channel_open(checkin_channel, checkin_role)

        except Exception as e:
            BotLogger.error(f"Error getting channel state for {guild.name}: {e}", "CHANNEL_MGR")
            state["error"] = str(e)

        return state


# Standalone helper functions for backward compatibility
async def open_channel_immediate(guild: discord.Guild, channel_type: str, ping_role: bool = True) -> bool:
    """
    Open a channel immediately.

    Args:
        guild: Discord guild
        channel_type: Either "registration" or "checkin"
        ping_role: True to ping role when opening

    Returns:
        True if successful, False otherwise
    """
    try:
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)

        if not channel or not role:
            BotLogger.warning(f"Could not find channel/role for {channel_type} in {guild.name}", "CHANNEL_HELPERS")
            return False

        # Open the channel
        changed = await ChannelManager.set_channel_visibility(channel, role, True, ping_role)

        if changed:
            BotLogger.info(f"Opened {channel_type} channel in {guild.name}", "CHANNEL_HELPERS")

        return True

    except Exception as e:
        BotLogger.error(f"Error opening {channel_type} channel: {e}", "CHANNEL_HELPERS")
        return False


async def close_channel_immediate(guild: discord.Guild, channel_type: str) -> bool:
    """
    Close a channel immediately.

    Args:
        guild: Discord guild
        channel_type: Either "registration" or "checkin"

    Returns:
        True if successful, False otherwise
    """
    try:
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)

        if not channel or not role:
            BotLogger.warning(f"Could not find channel/role for {channel_type} in {guild.name}", "CHANNEL_HELPERS")
            return False

        # Close the channel (no pinging)
        changed = await ChannelManager.set_channel_visibility(channel, role, False, False)

        if changed:
            BotLogger.info(f"Closed {channel_type} channel in {guild.name}", "CHANNEL_HELPERS")

        return True

    except Exception as e:
        BotLogger.error(f"Error closing {channel_type} channel: {e}", "CHANNEL_HELPERS")
        return False


async def toggle_channel_visibility(guild: discord.Guild, channel_type: str, ping_role: bool = True) -> Optional[bool]:
    """
    Toggle channel visibility.

    Args:
        guild: Discord guild
        channel_type: Either "registration" or "checkin"
        ping_role: True to ping role when opening

    Returns:
        True if now open, False if now closed, None if failed
    """
    return await ChannelManager.toggle_channel_visibility(guild, channel_type, ping_role)


def get_channel_state(guild: discord.Guild) -> Dict[str, Any]:
    """
    Get current state of all managed channels.

    Args:
        guild: Discord guild

    Returns:
        Dict with channel state information
    """
    return ChannelManager.get_channel_state(guild)


def validate_channel_configuration(guild: discord.Guild) -> Dict[str, Any]:
    """
    Validate channel configuration for a guild.

    Args:
        guild: Discord guild

    Returns:
        Dict with validation results
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "channels": {},
        "roles": {}
    }

    try:
        # Check registration channel and role
        reg_channel, reg_role = ChannelManager.get_channel_and_role(guild, "registration")

        validation["channels"]["registration"] = {
            "exists": bool(reg_channel),
            "name": REGISTRATION_CHANNEL,
            "found_name": reg_channel.name if reg_channel else None
        }

        validation["roles"]["angel"] = {
            "exists": bool(reg_role),
            "name": ANGEL_ROLE,
            "found_name": reg_role.name if reg_role else None
        }

        if not reg_channel:
            validation["errors"].append(f"Registration channel '{REGISTRATION_CHANNEL}' not found")
            validation["valid"] = False

        if not reg_role:
            validation["errors"].append(f"Angel role '{ANGEL_ROLE}' not found")
            validation["valid"] = False

        # Check check-in channel and role
        checkin_channel, checkin_role = ChannelManager.get_channel_and_role(guild, "checkin")

        validation["channels"]["checkin"] = {
            "exists": bool(checkin_channel),
            "name": CHECK_IN_CHANNEL,
            "found_name": checkin_channel.name if checkin_channel else None
        }

        validation["roles"]["registered"] = {
            "exists": bool(checkin_role),
            "name": REGISTERED_ROLE,
            "found_name": checkin_role.name if checkin_role else None
        }

        if not checkin_channel:
            validation["errors"].append(f"Check-in channel '{CHECK_IN_CHANNEL}' not found")
            validation["valid"] = False

        if not checkin_role:
            validation["errors"].append(f"Registered role '{REGISTERED_ROLE}' not found")
            validation["valid"] = False

        # Check bot permissions
        if reg_channel and guild.me:
            bot_perms = reg_channel.permissions_for(guild.me)
            if not bot_perms.manage_permissions:
                validation["warnings"].append("Bot lacks 'Manage Permissions' for registration channel")

        if checkin_channel and guild.me:
            bot_perms = checkin_channel.permissions_for(guild.me)
            if not bot_perms.manage_permissions:
                validation["warnings"].append("Bot lacks 'Manage Permissions' for check-in channel")

    except Exception as e:
        validation["errors"].append(f"Validation error: {e}")
        validation["valid"] = False

    return validation


# Export all functions
__all__ = [
    # Main class
    'ChannelManager',

    # Standalone functions
    'open_channel_immediate',
    'close_channel_immediate',
    'toggle_channel_visibility',
    'get_channel_state',
    'validate_channel_configuration',

    # Exception class
    'ChannelError'
]