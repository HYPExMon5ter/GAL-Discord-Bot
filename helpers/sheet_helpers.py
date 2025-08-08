# helpers/sheet_helpers.py
"""
Google Sheets operations helper module.

This module provides comprehensive utilities for interacting with Google Sheets
used by the GAL Discord Bot. It handles user data management, team operations,
batch updates, and statistical queries with robust error handling and caching.

Key Features:
- Individual and batch cell updates with retry logic
- Comprehensive user data retrieval with safe defaults
- Team management for double-up mode events
- Statistical queries with filtering capabilities
- Cache-aware operations with thread safety
- Extensive error handling and logging
"""

from typing import Dict, List, Optional, Tuple, Any
import asyncio

from config import get_sheet_settings, col_to_index
from core.persistence import get_event_mode_for_guild
from helpers.logging_helper import BotLogger
from helpers.error_handler import ErrorHandler, ErrorCategory, ErrorContext
from integrations.sheets import (
    retry_until_successful, get_sheet_for_guild,
    cache_lock, sheet_cache
)


class SheetOperationError(Exception):
    """Custom exception for sheet operation errors."""

    def __init__(self, message: str, operation: str = "", cell_ref: str = "", context: Dict[str, Any] = None):
        """
        Initialize sheet operation error with context.

        Args:
            message: Error description
            operation: Operation that failed (update, read, etc.)
            cell_ref: Cell reference that caused the error
            context: Additional error context
        """
        super().__init__(message)
        self.operation = operation
        self.cell_ref = cell_ref
        self.context = context or {}


class SheetOperations:
    """
    Enhanced sheet operations with team management and comprehensive error handling.

    This class provides static methods for all Google Sheets interactions,
    including individual cell updates, batch operations, user data management,
    and statistical queries. All operations include proper error handling,
    logging, and cache awareness.
    """

    @staticmethod
    async def update_cell(
            guild_id: str,
            col_letter: str,
            row: int,
            value: Any,
            worksheet: str = "GAL Database"
    ) -> bool:
        """
        Update a single cell in the sheet with comprehensive error handling.

        This method updates a specific cell in the Google Sheet, handling all
        possible error conditions and providing detailed logging for debugging.
        It includes retry logic through the retry_until_successful wrapper.

        Args:
            guild_id: Discord guild ID for sheet identification
            col_letter: Column letter (A, B, C, etc.)
            row: Row number (1-based)
            value: Value to set in the cell
            worksheet: Name of the worksheet to update

        Returns:
            bool: True if update was successful, False otherwise
        """
        if not all([guild_id, col_letter, row]):
            BotLogger.error("Missing required parameters for update_cell", "SHEET_OPS")
            return False

        if not isinstance(row, int) or row < 1:
            BotLogger.error(f"Invalid row number: {row}", "SHEET_OPS")
            return False

        if not col_letter.isalpha():
            BotLogger.error(f"Invalid column letter: {col_letter}", "SHEET_OPS")
            return False

        cell_ref = f"{col_letter}{row}"

        try:
            # Get sheet instance for the guild
            sheet = get_sheet_for_guild(guild_id, worksheet)
            if not sheet:
                BotLogger.error(f"Failed to get sheet for guild {guild_id}, worksheet: {worksheet}", "SHEET_OPS")
                return False

            # Perform the update with retry logic
            await retry_until_successful(
                sheet.update_acell,
                cell_ref,
                value
            )

            BotLogger.info(f"Successfully updated cell {cell_ref} = '{value}' in {worksheet}", "SHEET_OPS")
            return True

        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="sheet_update_cell",
                category=ErrorCategory.SHEETS,
                additional_context={
                    "guild_id": guild_id,
                    "cell_ref": cell_ref,
                    "worksheet": worksheet,
                    "value_type": type(value).__name__
                }
            )
            await ErrorHandler._log_error_structured(error_context, True, True)
            return False

    @staticmethod
    async def batch_update_cells(
            guild_id: str,
            updates: Dict[str, Any],
            row: int,
            worksheet: str = "GAL Database"
    ) -> int:
        """
        Batch update multiple cells in the same row with progress tracking.

        This method efficiently updates multiple cells in a single row, providing
        detailed progress tracking and error reporting for each update operation.
        It continues processing even if individual updates fail.

        Args:
            guild_id: Discord guild ID for sheet identification
            updates: Dictionary mapping column letters to values
            row: Row number to update (1-based)
            worksheet: Name of the worksheet to update

        Returns:
            int: Number of successful updates
        """
        if not all([guild_id, updates, row]):
            BotLogger.error("Missing required parameters for batch_update_cells", "SHEET_OPS")
            return 0

        if not isinstance(updates, dict):
            BotLogger.error(f"Updates parameter must be dict, got: {type(updates)}", "SHEET_OPS")
            return 0

        if not isinstance(row, int) or row < 1:
            BotLogger.error(f"Invalid row number: {row}", "SHEET_OPS")
            return 0

        if not updates:
            BotLogger.warning("Empty updates dictionary provided", "SHEET_OPS")
            return 0

        BotLogger.info(f"Starting batch update of {len(updates)} cells in row {row}", "SHEET_OPS")

        success_count = 0
        failed_updates = []

        # Process each update individually for better error tracking
        for col, value in updates.items():
            try:
                if await SheetOperations.update_cell(guild_id, col, row, value, worksheet):
                    success_count += 1
                    BotLogger.debug(f"Batch update success: {col}{row} = '{value}'", "SHEET_OPS")
                else:
                    failed_updates.append((col, value))
                    BotLogger.warning(f"Batch update failed: {col}{row} = '{value}'", "SHEET_OPS")

            except Exception as e:
                failed_updates.append((col, value))
                BotLogger.error(f"Exception during batch update {col}{row}: {e}", "SHEET_OPS")

        # Log batch results
        if failed_updates:
            BotLogger.warning(f"Batch update completed with {len(failed_updates)} failures: {failed_updates}",
                              "SHEET_OPS")
        else:
            BotLogger.info(f"Batch update completed successfully: {success_count}/{len(updates)} cells updated",
                           "SHEET_OPS")

        return success_count

    @staticmethod
    async def get_user_data(
            discord_tag: str,
            guild_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive user data from cache with safe defaults and validation.

        This method retrieves complete user information from the sheet cache,
        including registration status, team assignments, and additional profile
        data. It provides safe defaults for missing data and validates all
        retrieved information.

        Args:
            discord_tag: Discord user tag (username#discriminator)
            guild_id: Discord guild ID for configuration lookup

        Returns:
            Optional[Dict[str, Any]]: User data dictionary or None if not found
        """
        if not discord_tag or not guild_id:
            BotLogger.error("Missing required parameters for get_user_data", "SHEET_OPS")
            return None

        try:
            # Safely access cache data with lock protection
            async with cache_lock:
                cache_data = sheet_cache["users"].get(discord_tag)

            if not cache_data:
                BotLogger.debug(f"No cache data found for user: {discord_tag}", "SHEET_OPS")
                return None

            # Safely unpack tuple with defaults for missing elements
            parts = list(cache_data) + [None] * (6 - len(cache_data))
            row, ign, registered, checked_in, team, alt_ign = parts[:6]

            # Get event mode and configuration
            mode = get_event_mode_for_guild(guild_id)
            cfg = get_sheet_settings(mode)

            # Get pronouns from sheet with error handling
            pronouns = ""
            try:
                if row and cfg.get('pronouns_col'):
                    sheet = get_sheet_for_guild(guild_id)
                    if sheet:
                        cell = await retry_until_successful(
                            sheet.acell,
                            f"{cfg['pronouns_col']}{row}"
                        )
                        pronouns = cell.value or ""
            except Exception as e:
                BotLogger.warning(f"Failed to get pronouns for {discord_tag}: {e}", "SHEET_OPS")
                pronouns = ""

            # Build comprehensive user data dictionary
            user_data = {
                "row": row,
                "ign": str(ign) if ign else "",
                "alt_ign": str(alt_ign) if alt_ign else "",
                "pronouns": str(pronouns),
                "registered": str(registered).upper() == "TRUE" if registered else False,
                "checked_in": str(checked_in).upper() == "TRUE" if checked_in else False,
                "team": str(team) if team and mode == "doubleup" else None,
                "discord_tag": discord_tag,
                "mode": mode,
                "last_updated": cache_data.get("last_updated") if isinstance(cache_data, dict) else None
            }

            BotLogger.debug(
                f"Retrieved user data for {discord_tag}: registered={user_data['registered']}, checked_in={user_data['checked_in']}",
                "SHEET_OPS")
            return user_data

        except Exception as e:
            BotLogger.error(f"Error getting user data for {discord_tag}: {e}", "SHEET_OPS")
            return None

    @staticmethod
    async def count_by_criteria(
            guild_id: str,
            registered: Optional[bool] = None,
            checked_in: Optional[bool] = None,
            team_name: Optional[str] = None
    ) -> int:
        """
        Count users matching specific criteria with comprehensive filtering.

        This method provides flexible counting capabilities for various user
        states and attributes. It supports filtering by registration status,
        check-in status, and team membership with thread-safe cache access.

        Args:
            guild_id: Discord guild ID for context
            registered: Filter by registration status (None = no filter)
            checked_in: Filter by check-in status (None = no filter)
            team_name: Filter by team name (None = no filter)

        Returns:
            int: Count of users matching the criteria
        """
        if not guild_id:
            BotLogger.error("Guild ID is required for count_by_criteria", "SHEET_OPS")
            return 0

        count = 0
        processed_users = 0

        try:
            # Get thread-safe copy of cache data
            try:
                async with cache_lock:
                    cache_data = dict(sheet_cache["users"])
            except Exception as e:
                BotLogger.error(f"Failed to access cache for counting: {e}", "SHEET_OPS")
                return 0

            if not cache_data:
                BotLogger.warning("No cached user data available for counting", "SHEET_OPS")
                return 0

            # Process each user against criteria
            for tag, tpl in cache_data.items():
                try:
                    processed_users += 1

                    # Safely extract data with defaults
                    parts = list(tpl) + [None] * (6 - len(tpl))
                    _, _, reg, ci, team, _ = parts[:6]

                    # Apply registration filter
                    if registered is not None:
                        user_registered = str(reg).upper() == "TRUE" if reg else False
                        if user_registered != registered:
                            continue

                    # Apply check-in filter
                    if checked_in is not None:
                        user_checked_in = str(ci).upper() == "TRUE" if ci else False
                        if user_checked_in != checked_in:
                            continue

                    # Apply team filter (only if team data exists)
                    if team_name is not None and len(tpl) > 4:
                        user_team = str(team) if team else ""
                        if user_team != team_name:
                            continue

                    # User matches all criteria
                    count += 1

                except Exception as e:
                    BotLogger.warning(f"Error processing user {tag} in count_by_criteria: {e}", "SHEET_OPS")
                    continue

            BotLogger.info(f"Counted {count} users matching criteria out of {processed_users} total users", "SHEET_OPS")
            return count

        except Exception as e:
            BotLogger.error(f"Critical error in count_by_criteria: {e}", "SHEET_OPS")
            return 0

    @staticmethod
    async def get_teams_summary(guild_id: str) -> Dict[str, List[str]]:
        """
        Get a comprehensive summary of all teams and their members.

        This method provides detailed team information for double-up mode events,
        including member lists, registration status, and team statistics. It
        handles unassigned players and provides safe defaults for all scenarios.

        Args:
            guild_id: Discord guild ID for context

        Returns:
            Dict[str, List[str]]: Dictionary mapping team names to member lists
        """
        if not guild_id:
            BotLogger.error("Guild ID is required for get_teams_summary", "SHEET_OPS")
            return {}

        teams = {}
        processed_users = 0

        try:
            # Check if this is a team-based event
            mode = get_event_mode_for_guild(guild_id)
            if mode != "doubleup":
                BotLogger.info(f"Guild {guild_id} is not in doubleup mode, returning empty teams", "SHEET_OPS")
                return {}

            # Get thread-safe copy of cache data
            async with cache_lock:
                cache_data = dict(sheet_cache["users"])

            if not cache_data:
                BotLogger.warning("No cached user data available for teams summary", "SHEET_OPS")
                return {}

            # Process registered users and group by team
            for tag, tpl in cache_data.items():
                try:
                    processed_users += 1

                    # Safely extract data with defaults
                    parts = list(tpl) + [None] * (6 - len(tpl))
                    _, _, registered, _, team, _ = parts[:6]

                    # Only include registered users
                    if not (str(registered).upper() == "TRUE" if registered else False):
                        continue

                    # Determine team assignment
                    team_name = str(team) if team else "Unassigned"

                    # Initialize team list if needed
                    if team_name not in teams:
                        teams[team_name] = []

                    # Add user to team
                    teams[team_name].append(tag)

                except Exception as e:
                    BotLogger.warning(f"Error processing user {tag} in get_teams_summary: {e}", "SHEET_OPS")
                    continue

            # Sort members within each team for consistency
            for team_name in teams:
                teams[team_name].sort()

            team_count = len(teams)
            total_members = sum(len(members) for members in teams.values())

            BotLogger.info(
                f"Generated teams summary: {team_count} teams with {total_members} total members from {processed_users} processed users",
                "SHEET_OPS")

            # Log team distribution for debugging
            if teams:
                team_sizes = {name: len(members) for name, members in teams.items()}
                BotLogger.debug(f"Team sizes: {team_sizes}", "SHEET_OPS")

            return teams

        except Exception as e:
            BotLogger.error(f"Critical error in get_teams_summary: {e}", "SHEET_OPS")
            return {}

    @staticmethod
    def _is_true(value: Any) -> bool:
        """
        Helper function to safely check boolean values from sheet data.

        This method handles various representations of boolean values that
        might come from Google Sheets, including strings, booleans, and None.

        Args:
            value: Value to check for truthiness

        Returns:
            bool: True if value represents a true boolean, False otherwise
        """
        if value is None:
            return False
        return str(value).strip().upper() == "TRUE"

    @staticmethod
    async def get_all_registered_users(guild_id: str) -> List[Tuple[str, str, str]]:
        """
        Get all registered users with their basic information.

        This method retrieves a simplified list of all registered users,
        including their Discord tag, IGN, and team assignment (if applicable).

        Args:
            guild_id: Discord guild ID for context

        Returns:
            List[Tuple[str, str, str]]: List of (discord_tag, ign, team) tuples
        """
        if not guild_id:
            BotLogger.error("Guild ID is required for get_all_registered_users", "SHEET_OPS")
            return []

        users = []

        try:
            mode = get_event_mode_for_guild(guild_id)

            async with cache_lock:
                cache_data = dict(sheet_cache["users"])

            for discord_tag, tpl in cache_data.items():
                try:
                    # Check if user is registered
                    if len(tpl) >= 3 and SheetOperations._is_true(tpl[2]):
                        ign = str(tpl[1]) if len(tpl) > 1 and tpl[1] else "Unknown IGN"
                        team = str(tpl[4]) if len(tpl) > 4 and tpl[4] and mode == "doubleup" else ""
                        users.append((discord_tag, ign, team))

                except Exception as e:
                    BotLogger.warning(f"Error processing registered user {discord_tag}: {e}", "SHEET_OPS")
                    continue

            BotLogger.info(f"Retrieved {len(users)} registered users", "SHEET_OPS")
            return users

        except Exception as e:
            BotLogger.error(f"Error getting all registered users: {e}", "SHEET_OPS")
            return []

    @staticmethod
    async def get_all_checked_in_users(guild_id: str) -> List[Tuple[str, tuple]]:
        """
        Get all checked-in users with their complete cache data.

        This method retrieves all users who are both registered and checked in,
        along with their complete data tuples for detailed processing.

        Args:
            guild_id: Discord guild ID for context

        Returns:
            List[Tuple[str, tuple]]: List of (discord_tag, full_data_tuple) pairs
        """
        if not guild_id:
            BotLogger.error("Guild ID is required for get_all_checked_in_users", "SHEET_OPS")
            return []

        users = []

        try:
            async with cache_lock:
                cache_data = dict(sheet_cache["users"])

            for discord_tag, tpl in cache_data.items():
                try:
                    # Check if user is registered (required for check-in)
                    if (len(tpl) >= 3 and SheetOperations._is_true(tpl[2]) and
                            len(tpl) >= 4 and SheetOperations._is_true(tpl[3])):
                        users.append((discord_tag, tpl))

                except Exception as e:
                    BotLogger.warning(f"Error processing checked-in user {discord_tag}: {e}", "SHEET_OPS")
                    continue

            BotLogger.info(f"Retrieved {len(users)} checked-in users", "SHEET_OPS")
            return users

        except Exception as e:
            BotLogger.error(f"Error getting all checked-in users: {e}", "SHEET_OPS")
            return []

    @staticmethod
    async def validate_sheet_access(guild_id: str, worksheet: str = "GAL Database") -> bool:
        """
        Validate that the bot can access the specified sheet and worksheet.

        This method performs a basic connectivity test to ensure the Google
        Sheets integration is working properly for the specified guild.

        Args:
            guild_id: Discord guild ID
            worksheet: Name of the worksheet to test

        Returns:
            bool: True if sheet is accessible, False otherwise
        """
        if not guild_id:
            BotLogger.error("Guild ID is required for validate_sheet_access", "SHEET_OPS")
            return False

        try:
            sheet = get_sheet_for_guild(guild_id, worksheet)
            if not sheet:
                BotLogger.error(f"Could not get sheet instance for guild {guild_id}", "SHEET_OPS")
                return False

            # Try to read a basic cell (A1) to test connectivity
            await retry_until_successful(sheet.acell, "A1")
            BotLogger.info(f"Sheet access validated for guild {guild_id}, worksheet: {worksheet}", "SHEET_OPS")
            return True

        except Exception as e:
            BotLogger.error(f"Sheet access validation failed for guild {guild_id}: {e}", "SHEET_OPS")
            return False


# Export all important classes and functions
__all__ = [
    # Classes
    'SheetOperations',
    'SheetOperationError',
]