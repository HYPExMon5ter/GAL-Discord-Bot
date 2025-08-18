# helpers/role_helpers.py
import logging
from typing import Optional, List

import discord

from config import REGISTERED_ROLE, CHECKED_IN_ROLE, ALLOWED_ROLES


class RoleManager:
    """Manages role operations for the GAL bot."""

    @staticmethod
    def get_role(guild: discord.Guild, role_name: str) -> Optional[discord.Role]:
        """Get a role by name from guild."""
        return discord.utils.get(guild.roles, name=role_name)

    @staticmethod
    def has_role(member: discord.Member, role_name: str) -> bool:
        """Check if member has a specific role by name."""
        role = RoleManager.get_role(member.guild, role_name)
        return role in member.roles if role else False

    @staticmethod
    def has_any_allowed_role(member: discord.Member) -> bool:
        """Check if member has any staff/allowed role."""
        return any(role.name in ALLOWED_ROLES for role in member.roles)

    @staticmethod
    def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
        """Check interaction.user's roles for permission."""
        member = getattr(interaction, "user", getattr(interaction, "author", None))
        return hasattr(member, "roles") and RoleManager.has_any_allowed_role(member)

    @staticmethod
    async def add_role(member: discord.Member, role_name: str) -> bool:
        """
        Add a role to member by name.
        """
        if RoleManager.has_role(member, role_name):
            return False

        role = RoleManager.get_role(member.guild, role_name)
        if role:
            await member.add_roles(role)
            return True
        return False

    @staticmethod
    async def remove_role(member: discord.Member, role_name: str) -> bool:
        """
        Remove a role from member by name.
        """
        if not RoleManager.has_role(member, role_name):
            return False

        role = RoleManager.get_role(member.guild, role_name)
        if role:
            await member.remove_roles(role)
            return True
        return False

    @staticmethod
    async def remove_roles(member: discord.Member, role_names: List[str]) -> int:
        """
        Remove multiple roles from member.
        """
        roles_to_remove = []
        for role_name in role_names:
            role = RoleManager.get_role(member.guild, role_name)
            if role and role in member.roles:
                roles_to_remove.append(role)

        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        return len(roles_to_remove)

    @staticmethod
    def is_registered(member: discord.Member) -> bool:
        """Check if member is registered."""
        return RoleManager.has_role(member, REGISTERED_ROLE)

    @staticmethod
    def is_checked_in(member: discord.Member) -> bool:
        """Check if member is checked in."""
        return RoleManager.has_role(member, CHECKED_IN_ROLE)

    @staticmethod
    async def sync_user_roles(member: discord.Member, is_registered: bool, is_checked_in: bool) -> None:
        """
        Sync member's roles based on their registration/check-in status.
        This ensures Discord roles always match the sheet data.
        """
        try:
            # Get the role objects
            reg_role = RoleManager.get_role(member.guild, REGISTERED_ROLE)
            ci_role = RoleManager.get_role(member.guild, CHECKED_IN_ROLE)

            if not reg_role:
                logging.warning(f"Registered role '{REGISTERED_ROLE}' not found in guild {member.guild.name}")
                return

            if not ci_role:
                logging.warning(f"Checked-in role '{CHECKED_IN_ROLE}' not found in guild {member.guild.name}")
                return

            # Track what changes we're making for logging
            changes = []

            # Handle registered role
            has_reg_role = reg_role in member.roles
            if is_registered and not has_reg_role:
                await member.add_roles(reg_role)
                changes.append(f"Added {REGISTERED_ROLE}")
            elif not is_registered and has_reg_role:
                await member.remove_roles(reg_role)
                changes.append(f"Removed {REGISTERED_ROLE}")

            # Handle checked-in role (can't be checked in without being registered)
            has_ci_role = ci_role in member.roles

            # Logic: User should have checked-in role ONLY if both registered AND checked in
            should_have_ci = is_registered and is_checked_in

            if should_have_ci and not has_ci_role:
                await member.add_roles(ci_role)
                changes.append(f"Added {CHECKED_IN_ROLE}")
            elif not should_have_ci and has_ci_role:
                await member.remove_roles(ci_role)
                changes.append(f"Removed {CHECKED_IN_ROLE}")

            # Log changes if any were made
            if changes:
                logging.debug(f"Role sync for {member}: {', '.join(changes)}")

        except discord.Forbidden:
            logging.error(f"Missing permissions to sync roles for {member}")
        except discord.HTTPException as e:
            logging.error(f"Discord API error syncing roles for {member}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error syncing roles for {member}: {e}")

    @staticmethod
    async def count_members_with_role(guild: discord.Guild, role_name: str) -> int:
        """Count members with a specific role."""
        role = RoleManager.get_role(guild, role_name)
        return len(role.members) if role else 0

    @staticmethod
    async def get_members_with_role(guild: discord.Guild, role_name: str) -> List[discord.Member]:
        """Get all members with a specific role."""
        role = RoleManager.get_role(guild, role_name)
        return role.members if role else []

    @staticmethod
    async def remove_role_from_all(guild: discord.Guild, role_name: str) -> int:
        """
        Remove a role from all members who have it.
        """
        role = RoleManager.get_role(guild, role_name)
        if not role:
            return 0

        count = 0
        for member in role.members:
            await member.remove_roles(role)
            count += 1

        return count
