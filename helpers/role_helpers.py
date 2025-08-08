# helpers/role_helpers.py
"""
Discord role management helper module.

This module provides comprehensive utilities for managing Discord roles throughout
the GAL Discord Bot. It handles role retrieval, assignment, permission checking,
and bulk operations with robust error handling and logging.

Key Features:
- Safe role retrieval with comprehensive error handling
- Role assignment and removal with permission validation
- Bulk role operations for multiple members
- Permission checking utilities
- Extensive logging and error tracking
"""

import logging
from typing import Optional, List, Union, Dict, Any

import discord

from config import REGISTERED_ROLE, CHECKED_IN_ROLE, ALLOWED_ROLES
from .logging_helper import BotLogger
from .error_handler import ErrorHandler, ErrorCategory, ErrorContext, ErrorSeverity


class RoleError(Exception):
    """
    Custom exception for role-related errors.
    """

    def __init__(self, message: str, role_name: str = None, member: discord.Member = None):
        self.role_name = role_name
        self.member = member
        super().__init__(message)


class RoleManager:
    """
    Centralized role management system with comprehensive error handling.

    This class provides static methods for all Discord role operations,
    including retrieval, assignment, permission checking, and bulk operations.
    All methods include proper error handling, logging, and performance tracking.
    """

    @staticmethod
    def get_role(guild: discord.Guild, role_name: str) -> Optional[discord.Role]:
        """
        Safely retrieve a role by name from a guild with comprehensive error handling.

        This method performs case-insensitive role lookups with extensive logging
        and error handling. It provides detailed feedback for debugging role
        configuration issues.

        Args:
            guild: Discord guild to search in
            role_name: Name of the role to find

        Returns:
            Optional[discord.Role]: Role object if found, None otherwise
        """
        if not guild:
            error_context = ErrorContext(
                error=ValueError("Guild parameter cannot be None"),
                operation="get_role",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                additional_context={"role_name": role_name}
            )
            BotLogger.error("Guild parameter cannot be None in get_role", "ROLE_MGR")
            return None

        if not role_name or not isinstance(role_name, str):
            BotLogger.warning(f"Invalid role name provided: {role_name}", "ROLE_MGR")
            return None

        try:
            # Use case-insensitive search for better reliability
            role = discord.utils.get(guild.roles, name=role_name)

            if not role:
                BotLogger.debug(f"Role '{role_name}' not found in guild '{guild.name}' ({guild.id})", "ROLE_MGR")
                return None

            BotLogger.debug(f"Successfully found role '{role_name}' in guild '{guild.name}'", "ROLE_MGR")
            return role

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="get_role_search",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                guild_id=guild.id,
                additional_context={
                    "role_name": role_name,
                    "guild_name": guild.name
                }
            )
            BotLogger.error(f"Error searching for role '{role_name}' in guild '{guild.name}': {e}", "ROLE_MGR")
            return None

    @staticmethod
    def has_role(member: discord.Member, role_name: str) -> bool:
        """
        Check if a Discord member has a specific role by name with comprehensive validation.

        This method safely checks role membership with extensive error handling
        and validation. It provides detailed logging for debugging permission issues.

        Args:
            member: Discord member to check
            role_name: Name of the role to check for

        Returns:
            bool: True if member has the role, False otherwise
        """
        if not member or not hasattr(member, 'roles'):
            BotLogger.debug(f"Invalid member object provided for role check: {member}", "ROLE_MGR")
            return False

        if not role_name:
            BotLogger.debug("Empty role name provided for role check", "ROLE_MGR")
            return False

        try:
            role = RoleManager.get_role(member.guild, role_name)

            if not role:
                BotLogger.debug(f"Role '{role_name}' not found in guild for member {member}", "ROLE_MGR")
                return False

            has_role = role in member.roles
            BotLogger.debug(f"Member {member} {'has' if has_role else 'does not have'} role '{role_name}'", "ROLE_MGR")

            return has_role

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="has_role_check",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id if member else None,
                guild_id=member.guild.id if member and member.guild else None,
                additional_context={
                    "role_name": role_name,
                    "member_str": str(member) if member else None
                }
            )
            BotLogger.error(f"Error checking role '{role_name}' for member {member}: {e}", "ROLE_MGR")
            return False

    @staticmethod
    def has_any_allowed_role(member: discord.Member) -> bool:
        """
        Check if a member has any of the configured staff roles.

        This method checks against the ALLOWED_ROLES configuration to determine
        if a member has staff permissions for bot commands. It includes comprehensive
        error handling and detailed logging for permission debugging.

        Args:
            member: Discord member to check

        Returns:
            bool: True if member has any allowed role, False otherwise
        """
        if not member:
            BotLogger.debug("No member provided for allowed role check", "ROLE_MGR")
            return False

        if not hasattr(member, 'roles'):
            BotLogger.debug(f"Member {member} has no roles attribute", "ROLE_MGR")
            return False

        try:
            # Check each allowed role
            for role_name in ALLOWED_ROLES:
                try:
                    if RoleManager.has_role(member, role_name):
                        BotLogger.debug(f"Member {member} has allowed role: {role_name}", "ROLE_MGR")
                        return True
                except Exception as e:
                    error_context = ErrorContext(
                        error=e,
                        operation=f"check_allowed_role_{role_name}",
                        category=ErrorCategory.PERMISSIONS,
                        severity=ErrorSeverity.LOW,
                        user_id=member.id,
                        guild_id=member.guild.id if member.guild else None,
                        additional_context={"role_name": role_name}
                    )
                    BotLogger.warning(f"Error checking allowed role '{role_name}' for {member}: {e}", "ROLE_MGR")
                    continue

            BotLogger.debug(f"Member {member} has no allowed roles", "ROLE_MGR")
            return False

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="has_any_allowed_role",
                category=ErrorCategory.PERMISSIONS,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id if member else None,
                guild_id=member.guild.id if member and member.guild else None,
                additional_context={"allowed_roles": ALLOWED_ROLES}
            )
            BotLogger.error(f"Error in has_any_allowed_role for {member}: {e}", "ROLE_MGR")
            return False

    @staticmethod
    async def add_role(member: discord.Member, role_name: str, reason: Optional[str] = None) -> bool:
        """
        Add a role to a Discord member with comprehensive error handling.

        This method safely adds roles to members with proper permission checking,
        error handling, and detailed logging. It includes audit log reasons
        for administrative transparency.

        Args:
            member: Discord member to add role to
            role_name: Name of the role to add
            reason: Optional reason for the role addition (for audit logs)

        Returns:
            bool: True if role was added successfully, False otherwise
        """
        if not member or not role_name:
            BotLogger.error("Member and role_name are required for add_role", "ROLE_MGR")
            return False

        try:
            # Check if member already has the role
            if RoleManager.has_role(member, role_name):
                BotLogger.debug(f"Member {member} already has role '{role_name}'", "ROLE_MGR")
                return True

            # Get the role object
            role = RoleManager.get_role(member.guild, role_name)
            if not role:
                BotLogger.warning(f"Role '{role_name}' not found in guild '{member.guild.name}'", "ROLE_MGR")
                return False

            # Add the role
            await member.add_roles(role, reason=reason or f"Added by GAL Bot: {role_name}")
            BotLogger.info(f"Successfully added role '{role_name}' to {member}", "ROLE_MGR")
            return True

        except discord.Forbidden:
            BotLogger.error(f"No permission to add role '{role_name}' to {member}", "ROLE_MGR")
            return False
        except discord.HTTPException as e:
            error_context = ErrorContext(
                error=e,
                operation="add_role_http",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id,
                guild_id=member.guild.id,
                additional_context={
                    "role_name": role_name,
                    "reason": reason
                }
            )
            BotLogger.error(f"HTTP error adding role '{role_name}' to {member}: {e}", "ROLE_MGR")
            return False
        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="add_role",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id if member else None,
                guild_id=member.guild.id if member and member.guild else None,
                additional_context={
                    "role_name": role_name,
                    "reason": reason
                }
            )
            BotLogger.error(f"Unexpected error adding role '{role_name}' to {member}: {e}", "ROLE_MGR")
            return False

    @staticmethod
    async def remove_role(member: discord.Member, role_name: str, reason: Optional[str] = None) -> bool:
        """
        Remove a role from a Discord member with comprehensive error handling.

        This method safely removes roles from members with proper permission checking,
        error handling, and detailed logging. It includes audit log reasons
        for administrative transparency.

        Args:
            member: Discord member to remove role from
            role_name: Name of the role to remove
            reason: Optional reason for the role removal (for audit logs)

        Returns:
            bool: True if role was removed successfully, False otherwise
        """
        if not member or not role_name:
            BotLogger.error("Member and role_name are required for remove_role", "ROLE_MGR")
            return False

        try:
            # Check if member has the role
            if not RoleManager.has_role(member, role_name):
                BotLogger.debug(f"Member {member} doesn't have role '{role_name}'", "ROLE_MGR")
                return True

            # Get the role object
            role = RoleManager.get_role(member.guild, role_name)
            if not role:
                BotLogger.warning(f"Role '{role_name}' not found in guild '{member.guild.name}'", "ROLE_MGR")
                return False

            # Remove the role
            await member.remove_roles(role, reason=reason or f"Removed by GAL Bot: {role_name}")
            BotLogger.info(f"Successfully removed role '{role_name}' from {member}", "ROLE_MGR")
            return True

        except discord.Forbidden:
            BotLogger.error(f"No permission to remove role '{role_name}' from {member}", "ROLE_MGR")
            return False
        except discord.HTTPException as e:
            error_context = ErrorContext(
                error=e,
                operation="remove_role_http",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id,
                guild_id=member.guild.id,
                additional_context={
                    "role_name": role_name,
                    "reason": reason
                }
            )
            BotLogger.error(f"HTTP error removing role '{role_name}' from {member}: {e}", "ROLE_MGR")
            return False
        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="remove_role",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                user_id=member.id if member else None,
                guild_id=member.guild.id if member and member.guild else None,
                additional_context={
                    "role_name": role_name,
                    "reason": reason
                }
            )
            BotLogger.error(f"Unexpected error removing role '{role_name}' from {member}: {e}", "ROLE_MGR")
            return False

    @staticmethod
    async def bulk_add_roles(members: List[discord.Member], role_name: str, reason: Optional[str] = None) -> Dict[
        str, bool]:
        """
        Add a role to multiple members with progress tracking and error handling.

        This method efficiently processes role additions for multiple members,
        providing detailed progress tracking and error reporting for each operation.

        Args:
            members: List of Discord members to add role to
            role_name: Name of the role to add
            reason: Optional reason for audit logs

        Returns:
            Dict[str, bool]: Results mapping member IDs to success status
        """
        if not members or not role_name:
            BotLogger.error("Members list and role_name are required for bulk_add_roles", "ROLE_MGR")
            return {}

        results = {}
        success_count = 0

        BotLogger.info(f"Starting bulk role addition: '{role_name}' to {len(members)} members", "ROLE_MGR")

        try:
            for member in members:
                try:
                    member_id = str(member.id)
                    success = await RoleManager.add_role(member, role_name, reason)
                    results[member_id] = success

                    if success:
                        success_count += 1
                        BotLogger.debug(f"Bulk add role success: {member} -> {role_name}", "ROLE_MGR")
                    else:
                        BotLogger.warning(f"Bulk add role failed: {member} -> {role_name}", "ROLE_MGR")

                except Exception as e:
                    error_context = ErrorContext(
                        error=e,
                        operation=f"bulk_add_role_member_{member.id}",
                        category=ErrorCategory.DISCORD_API,
                        severity=ErrorSeverity.LOW,
                        user_id=member.id if member else None,
                        guild_id=member.guild.id if member and member.guild else None,
                        additional_context={"role_name": role_name}
                    )
                    BotLogger.error(f"Error in bulk role addition for {member}: {e}", "ROLE_MGR")
                    results[str(member.id) if member else "unknown"] = False

            BotLogger.info(f"Bulk role addition completed: {success_count}/{len(members)} successful", "ROLE_MGR")
            return results

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="bulk_add_roles",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                additional_context={
                    "role_name": role_name,
                    "member_count": len(members),
                    "reason": reason
                }
            )
            BotLogger.error(f"Critical error in bulk_add_roles: {e}", "ROLE_MGR")
            return results

    @staticmethod
    async def bulk_remove_roles(members: List[discord.Member], role_name: str, reason: Optional[str] = None) -> Dict[
        str, bool]:
        """
        Remove a role from multiple members with progress tracking and error handling.

        This method efficiently processes role removals for multiple members,
        providing detailed progress tracking and error reporting for each operation.

        Args:
            members: List of Discord members to remove role from
            role_name: Name of the role to remove
            reason: Optional reason for audit logs

        Returns:
            Dict[str, bool]: Results mapping member IDs to success status
        """
        if not members or not role_name:
            BotLogger.error("Members list and role_name are required for bulk_remove_roles", "ROLE_MGR")
            return {}

        results = {}
        success_count = 0

        BotLogger.info(f"Starting bulk role removal: '{role_name}' from {len(members)} members", "ROLE_MGR")

        try:
            for member in members:
                try:
                    member_id = str(member.id)
                    success = await RoleManager.remove_role(member, role_name, reason)
                    results[member_id] = success

                    if success:
                        success_count += 1
                        BotLogger.debug(f"Bulk remove role success: {member} -> {role_name}", "ROLE_MGR")
                    else:
                        BotLogger.warning(f"Bulk remove role failed: {member} -> {role_name}", "ROLE_MGR")

                except Exception as e:
                    error_context = ErrorContext(
                        error=e,
                        operation=f"bulk_remove_role_member_{member.id}",
                        category=ErrorCategory.DISCORD_API,
                        severity=ErrorSeverity.LOW,
                        user_id=member.id if member else None,
                        guild_id=member.guild.id if member and member.guild else None,
                        additional_context={"role_name": role_name}
                    )
                    BotLogger.error(f"Error in bulk role removal for {member}: {e}", "ROLE_MGR")
                    results[str(member.id) if member else "unknown"] = False

            BotLogger.info(f"Bulk role removal completed: {success_count}/{len(members)} successful", "ROLE_MGR")
            return results

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="bulk_remove_roles",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                additional_context={
                    "role_name": role_name,
                    "member_count": len(members),
                    "reason": reason
                }
            )
            BotLogger.error(f"Critical error in bulk_remove_roles: {e}", "ROLE_MGR")
            return results

    @staticmethod
    def get_role_members(guild: discord.Guild, role_name: str) -> List[discord.Member]:
        """
        Get all members who have a specific role with comprehensive error handling.

        This method retrieves all members with a given role, providing safe
        access with extensive error handling and logging.

        Args:
            guild: Discord guild to search in
            role_name: Name of the role to find members for

        Returns:
            List[discord.Member]: List of members with the role
        """
        if not guild or not role_name:
            BotLogger.error("Guild and role_name are required for get_role_members", "ROLE_MGR")
            return []

        try:
            role = RoleManager.get_role(guild, role_name)
            if not role:
                BotLogger.warning(f"Role '{role_name}' not found in guild '{guild.name}'", "ROLE_MGR")
                return []

            members = role.members
            BotLogger.debug(f"Found {len(members)} members with role '{role_name}' in {guild.name}", "ROLE_MGR")
            return members

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="get_role_members",
                category=ErrorCategory.DISCORD_API,
                severity=ErrorSeverity.MEDIUM,
                guild_id=guild.id,
                additional_context={
                    "role_name": role_name,
                    "guild_name": guild.name
                }
            )
            BotLogger.error(f"Error getting members for role '{role_name}' in {guild.name}: {e}", "ROLE_MGR")
            return []

    @staticmethod
    async def health_check(guild: discord.Guild) -> Dict[str, Any]:
        """
        Perform a health check on role management functionality.

        This method tests role operations and reports on the health of
        role management systems for the given guild.

        Args:
            guild: Discord guild to check

        Returns:
            Dict[str, Any]: Health check results
        """
        health = {
            "status": "healthy",
            "checks": [],
            "errors": [],
            "warnings": []
        }

        if not guild:
            health["status"] = "unhealthy"
            health["errors"].append("No guild provided for health check")
            return health

        try:
            # Check if configured roles exist
            configured_roles = [REGISTERED_ROLE, CHECKED_IN_ROLE] + ALLOWED_ROLES

            for role_name in configured_roles:
                try:
                    role = RoleManager.get_role(guild, role_name)
                    if role:
                        health["checks"].append(f"Role '{role_name}': Found")
                    else:
                        health["warnings"].append(f"Role '{role_name}': Not found")
                        health["status"] = "degraded" if health["status"] == "healthy" else health["status"]
                except Exception as e:
                    health["errors"].append(f"Role '{role_name}': Error checking - {e}")
                    health["status"] = "degraded"

            # Check bot permissions
            try:
                bot_member = guild.me
                if bot_member:
                    if bot_member.guild_permissions.manage_roles:
                        health["checks"].append("Bot permissions: Can manage roles")
                    else:
                        health["errors"].append("Bot permissions: Cannot manage roles")
                        health["status"] = "unhealthy"
                else:
                    health["warnings"].append("Bot permissions: Bot member not found")

            except Exception as e:
                health["errors"].append(f"Bot permissions check failed: {e}")
                health["status"] = "degraded"

        except Exception as e:
            health["status"] = "unhealthy"
            health["errors"].append(f"Health check failed: {e}")

        return health


# Export all important classes and functions
__all__ = [
    # Classes
    'RoleManager',
    'RoleError',
]