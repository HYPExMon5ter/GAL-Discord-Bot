# helpers/validation_helpers.py

from typing import Optional, Tuple

import discord

from config import embed_from_cfg, get_sheet_settings
from core.persistence import get_event_mode_for_guild
from integrations.sheets import cache_lock, sheet_cache
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
        Properly handles team limits and suggests existing teams when max teams reached.
        """
        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)
        max_players = cfg.get("max_players", 0)

        # Get current registration count
        total_registered = await SheetOperations.count_by_criteria(
            guild_id, registered=True
        )

        # Exclude current user if updating
        if exclude_discord_tag:
            user_data = await SheetOperations.get_user_data(exclude_discord_tag, guild_id)
            if user_data and user_data["registered"]:
                total_registered -= 1

        # Check total player capacity
        if total_registered >= max_players:
            return ValidationError("registration_full", max_players=max_players)

        # For double-up mode, check team-specific constraints
        if mode == "doubleup" and team_name:
            max_per_team = cfg.get("max_per_team", 2)
            max_teams = max_players // max_per_team  # Calculate max teams from max players

            # Count current members in this specific team (case-insensitive)
            team_count = 0
            team_exists = False
            team_member_counts = {}

            async with cache_lock:
                for tag, tpl in sheet_cache["users"].items():
                    # Check if user is registered and has a team
                    if str(tpl[2]).upper() == "TRUE" and len(tpl) > 4 and tpl[4]:
                        team_lower = tpl[4].lower()
                        if team_lower not in team_member_counts:
                            team_member_counts[team_lower] = {"count": 0, "original": tpl[4]}
                        team_member_counts[team_lower]["count"] += 1

                        if team_lower == team_name.lower():
                            team_exists = True
                            team_count = team_member_counts[team_lower]["count"]

            # Exclude current user if they're already on this team
            if exclude_discord_tag:
                user_data = await SheetOperations.get_user_data(exclude_discord_tag, guild_id)
                if user_data and user_data["registered"] and user_data.get("team"):
                    if user_data.get("team").lower() == team_name.lower():
                        team_count -= 1
                    # Adjust team counts if user is changing teams
                    old_team_lower = user_data.get("team").lower()
                    if old_team_lower in team_member_counts:
                        team_member_counts[old_team_lower]["count"] -= 1

            # Check if team is full
            if team_count >= max_per_team:
                return ValidationError(
                    "team_full",
                    team_name=team_name,
                    max_per_team=max_per_team
                )

            # If this is a NEW team (doesn't exist yet), check if we're at max teams
            if not team_exists:
                # Count unique teams (excluding empty teams)
                num_teams = len([t for t, data in team_member_counts.items() if data["count"] > 0])

                # If we're at max teams, return teams with space for dropdown
                if num_teams >= max_teams:
                    # Get teams that have space
                    teams_with_space = []

                    for team_lower, data in team_member_counts.items():
                        if data["count"] < max_per_team and data["count"] > 0:
                            teams_with_space.append(data["original"])

                    # Sort teams alphabetically
                    teams_with_space.sort(key=lambda x: x.lower())

                    # Return error with teams list
                    return ValidationError(
                        "max_teams_reached",
                        max_teams=max_teams,
                        teams_with_space=teams_with_space  # Pass as list, not string
                    )

        return None

    @staticmethod
    def validate_staff_permission(
            interaction: discord.Interaction
    ) -> Optional[ValidationError]:
        """
        Validate if user has staff permissions.
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
        """
        valid_modes = ["normal", "doubleup"]
        if mode.lower() not in valid_modes:
            return ValidationError(
                "event_mode_invalid",
                allowed=" or ".join(valid_modes)
            )
        return None