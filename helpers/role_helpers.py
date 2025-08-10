# helpers/role_helpers.py

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
        """
        # Handle registered role
        if is_registered and not RoleManager.is_registered(member):
            await RoleManager.add_role(member, REGISTERED_ROLE)
        elif not is_registered and RoleManager.is_registered(member):
            await RoleManager.remove_role(member, REGISTERED_ROLE)

        # Handle checked-in role (can't be checked in without being registered)
        if is_checked_in and is_registered and not RoleManager.is_checked_in(member):
            await RoleManager.add_role(member, CHECKED_IN_ROLE)
        elif (not is_checked_in or not is_registered) and RoleManager.is_checked_in(member):
            await RoleManager.remove_role(member, CHECKED_IN_ROLE)

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