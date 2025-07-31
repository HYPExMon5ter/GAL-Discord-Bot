# helpers/validation_helpers.py
"""
Common validation patterns used throughout the bot.
"""

from typing import Optional, Tuple

import discord

from config import embed_from_cfg, get_sheet_settings
from core.persistence import get_event_mode_for_guild
from .channel_helpers import ChannelManager
from .role_helpers import RoleManager
from .sheet_helpers import SheetOperations


class ValidationError:
    """Represents a validation error with an associated embed."""

    def __init__(self, embed_key: str, **kwargs):
        self.embed_key = embed_key
        self.kwargs = kwargs

    def to_embed(self) -> discord.Embed:
        """Convert to Discord embed."""
        return embed_from_cfg(self.embed_key, **self.kwargs)


class Validators:
    """Common validation patterns for the bot."""

    @staticmethod
    async def validate_registration_capacity(
            guild_id: str,
            team_name: Optional[str] = None,
            exclude_discord_tag: Optional[str] = None
    ) -> Optional[ValidationError]:
        """
        Validate if registration is within capacity limits.

        Args:
            guild_id: Guild ID
            team_name: Team name to check (for double-up mode)
            exclude_discord_tag: Discord tag to exclude from count (for updates)

        Returns:
            ValidationError if capacity exceeded, None if valid
        """
        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)
        max_players = cfg.get("max_players", 0)

        # Check total capacity
        total_registered = await SheetOperations.count_by_criteria(
            guild_id, registered=True
        )

        # Exclude current user if updating
        if exclude_discord_tag:
            user_data = await SheetOperations.get_user_data(exclude_discord_tag, guild_id)
            if user_data and user_data["registered"]:
                total_registered -= 1

        if total_registered >= max_players:
            return ValidationError("registration_full", max_players=max_players)

        # Check team capacity for double-up mode
        if mode == "doubleup" and team_name:
            max_per_team = cfg.get("max_per_team", 2)
            team_count = await SheetOperations.count_by_criteria(
                guild_id, registered=True, team_name=team_name
            )

            # Exclude current user if they're already on this team
            if exclude_discord_tag:
                user_data = await SheetOperations.get_user_data(exclude_discord_tag, guild_id)
                if user_data and user_data["registered"] and user_data.get("team") == team_name:
                    team_count -= 1

            if team_count >= max_per_team:
                return ValidationError(
                    "team_full",
                    team_name=team_name,
                    max_per_team=max_per_team
                )

        return None

    @staticmethod
    def validate_staff_permission(
            interaction: discord.Interaction
    ) -> Optional[ValidationError]:
        """
        Validate if user has staff permissions.

        Returns:
            ValidationError if no permission, None if valid
        """
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            return ValidationError("permission_denied")
        return None

    @staticmethod
    def validate_registration_status(
            member: discord.Member,
            require_registered: bool = True,
            require_not_registered: bool = False
    ) -> Optional[ValidationError]:
        """
        Validate member's registration status.

        Args:
            member: Discord member to check
            require_registered: If True, member must be registered
            require_not_registered: If True, member must NOT be registered

        Returns:
            ValidationError if validation fails, None if valid
        """
        is_registered = RoleManager.is_registered(member)

        if require_registered and not is_registered:
            return ValidationError("checkin_requires_registration")

        if require_not_registered and is_registered:
            return ValidationError("already_registered")

        return None

    @staticmethod
    def validate_checkin_status(
            member: discord.Member,
            require_checked_in: bool = False,
            require_not_checked_in: bool = False
    ) -> Optional[ValidationError]:
        """
        Validate member's check-in status.

        Args:
            member: Discord member to check
            require_checked_in: If True, member must be checked in
            require_not_checked_in: If True, member must NOT be checked in

        Returns:
            ValidationError if validation fails, None if valid
        """
        is_checked_in = RoleManager.is_checked_in(member)

        if require_checked_in and not is_checked_in:
            return ValidationError("not_checked_in")

        if require_not_checked_in and is_checked_in:
            return ValidationError("already_checked_in")

        return None

    @staticmethod
    async def validate_and_respond(
            interaction: discord.Interaction,
            *validations: Optional[ValidationError]
    ) -> bool:
        """
        Run multiple validations and respond with error if any fail.

        Args:
            interaction: Discord interaction
            validations: ValidationError objects or None

        Returns:
            True if all validations passed, False if any failed
        """
        for validation in validations:
            if validation:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        embed=validation.to_embed(),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=validation.to_embed(),
                        ephemeral=True
                    )
                return False
        return True

    @staticmethod
    def validate_channel_and_role(
            guild: discord.Guild,
            channel_name: str,
            role_name: str
    ) -> Tuple[Optional[discord.TextChannel], Optional[discord.Role], Optional[ValidationError]]:
        """
        Validate that both channel and role exist.

        Returns:
            Tuple of (channel, role, error) - error is None if both exist
        """
        channel = ChannelManager.get_channel(guild, channel_name)
        role = RoleManager.get_role(guild, role_name)

        if not channel or not role:
            error = ValidationError(
                "channel_role_not_found",
                channel=channel_name,
                role=role_name
            )
            return None, None, error

        return channel, role, None

    @staticmethod
    def validate_channel_open(
            guild: discord.Guild,
            channel_type: str
    ) -> Optional[ValidationError]:
        """
        Validate that a channel is open.

        Args:
            guild: Discord guild
            channel_type: Either "registration" or "checkin"

        Returns:
            ValidationError if channel is closed, None if open
        """
        channel, role = ChannelManager.get_channel_and_role(guild, channel_type)
        if not channel or not role:
            return ValidationError(
                "channel_not_found",
                channel_type=channel_type
            )

        if not ChannelManager.is_channel_open(channel, role):
            return ValidationError(f"{channel_type}_closed")

        return None

    @staticmethod
    def validate_event_mode(mode: str) -> Optional[ValidationError]:
        """
        Validate event mode value.

        Returns:
            ValidationError if invalid mode, None if valid
        """
        valid_modes = ["normal", "doubleup"]
        if mode.lower() not in valid_modes:
            return ValidationError(
                "event_mode_invalid",
                allowed=" or ".join(valid_modes)
            )
        return None