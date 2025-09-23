# helpers/role_helpers.py

import logging
from typing import Optional, List

import discord

from config import get_allowed_roles, get_registered_role, get_checked_in_role


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
        allowed_roles = get_allowed_roles()
        return any(role.name in allowed_roles for role in member.roles)

    @staticmethod
    def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
        """Check interaction.user's roles for permission."""
        member = getattr(interaction, "user", getattr(interaction, "author", None))
        return hasattr(member, "roles") and RoleManager.has_any_allowed_role(member)

    @staticmethod
    def is_registered(member: discord.Member) -> bool:
        """Check if member is registered."""
        return RoleManager.has_role(member, get_registered_role())

    @staticmethod
    def is_checked_in(member: discord.Member) -> bool:
        """Check if member is checked in."""
        return RoleManager.has_role(member, get_checked_in_role())

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
    async def bulk_role_update(member: discord.Member, add_roles: List[str], remove_roles: List[str]) -> dict:
        """
        Efficiently update multiple roles in one API call using Discord.py v2 features.

        Args:
            member: The Discord member to update
            add_roles: List of role names to add
            remove_roles: List of role names to remove

        Returns:
            dict: Summary of changes made
        """
        try:
            guild = member.guild
            current_roles = set(member.roles)

            # Get role objects for roles to add
            roles_to_add = []
            for role_name in add_roles:
                role = RoleManager.get_role(guild, role_name)
                if role and role not in current_roles:
                    roles_to_add.append(role)

            # Get role objects for roles to remove
            roles_to_remove = []
            for role_name in remove_roles:
                role = RoleManager.get_role(guild, role_name)
                if role and role in current_roles:
                    roles_to_remove.append(role)

            # Calculate new role set efficiently
            new_roles = (current_roles | set(roles_to_add)) - set(roles_to_remove)

            # Only make API call if there are actual changes
            if new_roles != current_roles:
                await member.edit(roles=list(new_roles))

                return {
                    "success": True,
                    "added": [role.name for role in roles_to_add],
                    "removed": [role.name for role in roles_to_remove],
                    "changes_made": len(roles_to_add) + len(roles_to_remove)
                }
            else:
                return {
                    "success": True,
                    "added": [],
                    "removed": [],
                    "changes_made": 0
                }

        except discord.Forbidden:
            logging.error(f"Missing permissions to update roles for {member}")
            return {"success": False, "error": "Missing permissions"}
        except discord.HTTPException as e:
            logging.error(f"Discord API error updating roles for {member}: {e}")
            return {"success": False, "error": f"API error: {e}"}
        except Exception as e:
            logging.error(f"Unexpected error updating roles for {member}: {e}")
            return {"success": False, "error": f"Unexpected error: {e}"}

    @staticmethod
    async def sync_user_roles(member: discord.Member, is_registered: bool, is_checked_in: bool) -> None:
        """
        Sync member's roles based on their registration/check-in status using optimized bulk operations.
        This ensures Discord roles always match the sheet data with minimal API calls.
        """
        try:
            # Get the role names
            reg_role_name = get_registered_role()
            ci_role_name = get_checked_in_role()

            # Verify roles exist
            reg_role = RoleManager.get_role(member.guild, reg_role_name)
            ci_role = RoleManager.get_role(member.guild, ci_role_name)

            if not reg_role:
                logging.warning(f"Registered role '{reg_role_name}' not found in guild {member.guild.name}")
                return

            if not ci_role:
                logging.warning(f"Checked-in role '{ci_role_name}' not found in guild {member.guild.name}")
                return

            # Determine current role state
            has_reg_role = reg_role in member.roles
            has_ci_role = ci_role in member.roles

            # Determine desired role state
            should_have_ci = is_registered and is_checked_in

            # Build role changes for bulk update
            add_roles = []
            remove_roles = []

            # Handle registered role
            if is_registered and not has_reg_role:
                add_roles.append(reg_role_name)
            elif not is_registered and has_reg_role:
                remove_roles.append(reg_role_name)

            # Handle checked-in role (can only be checked in if registered)
            if should_have_ci and not has_ci_role:
                add_roles.append(ci_role_name)
            elif not should_have_ci and has_ci_role:
                remove_roles.append(ci_role_name)

            # Use bulk update for efficiency (single API call)
            if add_roles or remove_roles:
                result = await RoleManager.bulk_role_update(member, add_roles, remove_roles)

                if result["success"] and result["changes_made"] > 0:
                    changes = []
                    if result["added"]:
                        changes.append(f"Added: {', '.join(result['added'])}")
                    if result["removed"]:
                        changes.append(f"Removed: {', '.join(result['removed'])}")

                    logging.debug(f"Role sync for {member}: {' | '.join(changes)}")
                elif not result["success"]:
                    logging.error(f"Failed to sync roles for {member}: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logging.error(f"Unexpected error syncing roles for {member}: {e}")
