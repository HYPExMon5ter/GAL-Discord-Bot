# helpers/sheet_helpers.py
"""
Enhanced sheet operations to reduce duplication and improve error handling.
"""

from typing import Dict, List, Optional, Tuple, Any

from config import get_sheet_settings, col_to_index
from core.persistence import get_event_mode_for_guild
from integrations.sheets import retry_until_successful, get_sheet_for_guild, cache_lock, sheet_cache


class SheetOperations:
    """Centralized sheet operations with better error handling."""

    @staticmethod
    async def update_cell(
            guild_id: str,
            col_letter: str,
            row: int,
            value: Any,
            worksheet: str = "GAL Database"
    ) -> bool:
        """
        Update a single cell in the sheet.

        Returns:
            True if successful, False otherwise
        """
        try:
            sheet = get_sheet_for_guild(guild_id, worksheet)
            await retry_until_successful(
                sheet.update_acell,
                f"{col_letter}{row}",
                value
            )
            return True
        except Exception as e:
            print(f"[SHEET UPDATE ERROR] {col_letter}{row} = {value}: {e}")
            return False

    @staticmethod
    async def batch_update_cells(
            guild_id: str,
            updates: Dict[str, Any],
            row: int,
            worksheet: str = "GAL Database"
    ) -> int:
        """
        Batch update multiple cells in the same row.

        Args:
            guild_id: Guild ID
            updates: Dict mapping column letters to values
            row: Row number to update
            worksheet: Sheet name

        Returns:
            Number of successful updates
        """
        success_count = 0

        for col, value in updates.items():
            if await SheetOperations.update_cell(guild_id, col, row, value, worksheet):
                success_count += 1

        return success_count

    @staticmethod
    async def get_user_data(
            discord_tag: str,
            guild_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive user data from cache and sheet.

        Returns:
            Dict with user data or None if not found
        """
        async with cache_lock:
            cache_data = sheet_cache["users"].get(discord_tag)

        if not cache_data:
            return None

        # Safely unpack with defaults
        parts = list(cache_data) + [None] * (6 - len(cache_data))
        row, ign, registered, checked_in, team, alt_ign = parts[:6]

        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)

        # Get pronouns from sheet
        pronouns = ""
        try:
            sheet = get_sheet_for_guild(guild_id)
            cell = await retry_until_successful(sheet.acell, f"{cfg['pronouns_col']}{row}")
            pronouns = cell.value or ""
        except:
            pass

        return {
            "row": row,
            "ign": ign or "",
            "alt_ign": alt_ign or "",
            "pronouns": pronouns,
            "registered": str(registered).upper() == "TRUE",
            "checked_in": str(checked_in).upper() == "TRUE",
            "team": team if mode == "doubleup" else None,
            "discord_tag": discord_tag
        }

    @staticmethod
    async def count_by_criteria(
            guild_id: str,
            registered: Optional[bool] = None,
            checked_in: Optional[bool] = None,
            team_name: Optional[str] = None
    ) -> int:
        """
        Count users matching specific criteria.

        Args:
            guild_id: Guild ID
            registered: Filter by registration status
            checked_in: Filter by check-in status
            team_name: Filter by team name (double-up mode only)

        Returns:
            Count of matching users
        """
        count = 0

        # Don't use async with cache_lock here if we're already in a cache refresh
        # Instead, directly access the cache assuming we already have the lock
        # or make a copy of the data we need

        try:
            # Make a snapshot of the cache data to avoid holding the lock
            cache_data = dict(sheet_cache["users"])
        except:
            # If we can't access it, try with the lock
            async with cache_lock:
                cache_data = dict(sheet_cache["users"])

        for tag, tpl in cache_data.items():
            # Safely unpack with defaults
            parts = list(tpl) + [None] * (6 - len(tpl))
            _, _, reg, ci, team, _ = parts[:6]

            if registered is not None:
                if (str(reg).upper() == "TRUE") != registered:
                    continue

            if checked_in is not None:
                if (str(ci).upper() == "TRUE") != checked_in:
                    continue

            if team_name is not None and len(tpl) > 4:
                if tpl[4] != team_name:
                    continue

            count += 1

        return count

    @staticmethod
    async def get_teams_summary(guild_id: str) -> Dict[str, List[str]]:
        """
        Get a summary of all teams and their members.

        Returns:
            Dict mapping team names to list of member discord tags
        """
        teams = {}
        mode = get_event_mode_for_guild(guild_id)

        if mode != "doubleup":
            return teams

        async with cache_lock:
            for tag, tpl in sheet_cache["users"].items():
                if str(tpl[2]).upper() == "TRUE" and len(tpl) > 4:
                    team = tpl[4] or "No Team"
                    if team not in teams:
                        teams[team] = []
                    teams[team].append(tag)

        return teams

    @staticmethod
    async def clear_column(
            guild_id: str,
            column: str,
            value: Any = False,  # Default to boolean False
            worksheet: str = "GAL Database"
    ) -> int:
        """
        Clear an entire column to a specific value.

        Returns:
            Number of cells updated
        """
        sheet = get_sheet_for_guild(guild_id, worksheet)
        col_idx = col_to_index(column)

        # Get all values to determine range
        vals = await retry_until_successful(sheet.col_values, col_idx)

        # Build range and update
        cell_list = await retry_until_successful(
            sheet.range,
            f"{column}1:{column}{len(vals)}"
        )

        for cell in cell_list:
            cell.value = value

        await retry_until_successful(sheet.update_cells, cell_list)

        # Return count excluding header rows
        cfg = get_sheet_settings(get_event_mode_for_guild(guild_id))
        return max(0, len(vals) - cfg["header_line_num"])

    @staticmethod
    async def find_empty_row(
            guild_id: str,
            start_row: int,
            max_row: int,
            check_column: str = None
    ) -> Optional[int]:
        """
        Find the first empty row within a range.

        Args:
            guild_id: Guild ID
            start_row: Starting row number (inclusive)
            max_row: Maximum row number (inclusive)
            check_column: Column to check for emptiness (defaults to discord_col)

        Returns:
            Row number of first empty row, or None if all full
        """
        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)

        if check_column is None:
            check_column = cfg["discord_col"]

        sheet = get_sheet_for_guild(guild_id)
        col_idx = col_to_index(check_column)

        vals = await retry_until_successful(sheet.col_values, col_idx)

        for row in range(start_row, min(len(vals) + 1, max_row + 1)):
            if row > len(vals) or not vals[row - 1].strip():
                return row

        return None

    @staticmethod
    async def get_all_registered_users(guild_id: str) -> List[Tuple[str, str, str]]:
        """
        Get all registered users with their info.

        Returns:
            List of (discord_tag, ign, team_name) tuples
        """
        users = []
        mode = get_event_mode_for_guild(guild_id)

        async with cache_lock:
            for discord_tag, tpl in sheet_cache["users"].items():
                if str(tpl[2]).upper() == "TRUE":
                    ign = tpl[1]
                    team = tpl[4] if len(tpl) > 4 and mode == "doubleup" else ""
                    users.append((discord_tag, ign, team))

        return users

    @staticmethod
    async def get_all_checked_in_users(guild_id: str) -> List[Tuple[str, tuple]]:
        """
        Get all checked-in users with their full cache data.

        Returns:
            List of (discord_tag, cache_tuple) tuples
        """
        users = []

        async with cache_lock:
            for discord_tag, tpl in sheet_cache["users"].items():
                if str(tpl[2]).upper() == "TRUE" and str(tpl[3]).upper() == "TRUE":
                    users.append((discord_tag, tpl))

        return users

    @staticmethod
    def is_true(value: Any) -> bool:
        """Check if a value represents TRUE in the sheet."""
        return str(value).strip().upper() == "TRUE"

    @staticmethod
    async def get_user_by_ign(guild_id: str, ign: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their IGN.

        Returns:
            User data dict or None if not found
        """
        async with cache_lock:
            for discord_tag, tpl in sheet_cache["users"].items():
                if tpl[1].lower() == ign.lower():
                    return await SheetOperations.get_user_data(discord_tag, guild_id)
        return None