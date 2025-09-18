# helpers/sheet_helpers.py

from typing import Dict, List, Optional, Tuple, Any

from config import get_sheet_settings
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
        """
        try:
            sheet = await get_sheet_for_guild(guild_id, worksheet)
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
        """
        async with cache_lock:
            cache_data = sheet_cache["users"].get(discord_tag)

        if not cache_data:
            return None

        # Safely unpack with defaults
        parts = list(cache_data) + [None] * (7 - len(cache_data))
        row, ign, registered, checked_in, team, alt_ign, pronouns = parts[:7]

        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)

        # Pronouns are now cached, no need to fetch from sheet

        return {
            "row": row,
            "ign": ign or "",
            "alt_ign": alt_ign or "",
            "pronouns": pronouns or "",
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
        """
        count = 0

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
    async def get_all_registered_users(guild_id: str) -> List[Tuple[str, str, str]]:
        """
        Get all registered users with their info.
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
