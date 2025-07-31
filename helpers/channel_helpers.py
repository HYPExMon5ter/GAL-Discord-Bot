# helpers/channel_helpers.py
"""
Centralized channel management utilities.
"""

from typing import Optional, Tuple, Dict

import discord

from config import REGISTRATION_CHANNEL, CHECK_IN_CHANNEL, ANGEL_ROLE, REGISTERED_ROLE
from .role_helpers import RoleManager


class ChannelManager:
    """Manages channel operations for the GAL bot."""

    @staticmethod
    def get_channel(guild: discord.Guild, channel_name: str) -> Optional[discord.TextChannel]:
        """Get a text channel by name."""
        return discord.utils.get(guild.text_channels, name=channel_name)

    @staticmethod
    def get_channel_and_role(
            guild: discord.Guild,
            channel_type: str
    ) -> Tuple[Optional[discord.TextChannel], Optional[discord.Role]]:
        """
        Get channel and associated role based on channel type.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"

        Returns:
            Tuple of (channel, role) or (None, None) if not found
        """
        if channel_type == "registration":
            channel = ChannelManager.get_channel(guild, REGISTRATION_CHANNEL)
            role = RoleManager.get_role(guild, ANGEL_ROLE)
        elif channel_type == "checkin":
            channel = ChannelManager.get_channel(guild, CHECK_IN_CHANNEL)
            role = RoleManager.get_role(guild, REGISTERED_ROLE)
        else:
            return None, None

        return channel, role

    @staticmethod
    def is_channel_open(
            channel: discord.TextChannel,
            role: discord.Role
    ) -> bool:
        """Check if a channel is visible to a specific role."""
        overwrites = channel.overwrites_for(role)
        return bool(overwrites.view_channel)

    @staticmethod
    async def set_channel_visibility(
            channel: discord.TextChannel,
            role: discord.Role,
            visible: bool,
            ping_role: bool = False
    ) -> bool:
        """
        Set channel visibility for a role.

        Args:
            channel: Channel to modify
            role: Role to set permissions for
            visible: Whether channel should be visible
            ping_role: Whether to ping the role when making visible

        Returns:
            True if permissions were changed, False if already in desired state
        """
        overwrites = channel.overwrites_for(role)
        current_visible = bool(overwrites.view_channel)

        if current_visible == visible:
            return False

        overwrites.view_channel = visible
        await channel.set_permissions(role, overwrite=overwrites)

        if visible and ping_role:
            msg = await channel.send(f"{role.mention}")
            try:
                await msg.delete(delay=3)
            except:
                pass

        return True

    @staticmethod
    async def toggle_channel_visibility(
            guild: discord.Guild,
            channel_type: str,
            ping_role: bool = True
    ) -> Optional[bool]:
        """
        Toggle channel visibility for its associated role.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"
            ping_role: Whether to ping role when opening

        Returns:
            True if now visible, False if now hidden, None if channel/role not found
        """
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)
        if not channel or not role:
            return None

        is_open = ChannelManager.is_channel_open(channel, role)
        await ChannelManager.set_channel_visibility(
            channel, role, not is_open, ping_role
        )

        return not is_open

    @staticmethod
    def get_channel_state(guild: discord.Guild) -> Dict[str, bool]:
        """
        Get current state of registration and check-in channels.

        Returns:
            Dict with 'registration_open' and 'checkin_open' booleans
        """
        state = {
            'registration_open': False,
            'checkin_open': False
        }

        # Check registration channel
        reg_channel, reg_role = ChannelManager.get_channel_and_role(guild, "registration")
        if reg_channel and reg_role:
            state['registration_open'] = ChannelManager.is_channel_open(reg_channel, reg_role)

        # Check check-in channel
        ci_channel, ci_role = ChannelManager.get_channel_and_role(guild, "checkin")
        if ci_channel and ci_role:
            state['checkin_open'] = ChannelManager.is_channel_open(ci_channel, ci_role)

        return state

    @staticmethod
    async def open_channel_immediate(
            guild: discord.Guild,
            channel_type: str,
            ping_role: bool = True
    ) -> bool:
        """
        Open a channel immediately.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"
            ping_role: Whether to ping the role

        Returns:
            True if successful, False otherwise
        """
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)
        if not channel or not role:
            return False

        return await ChannelManager.set_channel_visibility(
            channel, role, True, ping_role
        )

    @staticmethod
    async def close_channel_immediate(
            guild: discord.Guild,
            channel_type: str
    ) -> bool:
        """
        Close a channel immediately.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"

        Returns:
            True if successful, False otherwise
        """
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)
        if not channel or not role:
            return False

        return await ChannelManager.set_channel_visibility(
            channel, role, False, False
        )