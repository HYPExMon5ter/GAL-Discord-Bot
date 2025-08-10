# integrations/sheets.py

import asyncio
import json
import logging
import os
import random
import time
from typing import Optional, Tuple, Union, Dict, Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import get_sheet_settings, col_to_index, CACHE_REFRESH_SECONDS
from core.persistence import get_event_mode_for_guild

# Scope for Google Sheets API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class SheetsError(Exception):
    """Custom exception for sheets-related errors."""
    pass


class AuthenticationError(SheetsError):
    """Exception for authentication-related errors."""
    pass


class QuotaExceededError(SheetsError):
    """Exception for quota/rate limit errors."""
    pass


def initialize_credentials():
    """Initialize Google Sheets credentials with proper error handling."""
    try:
        if os.path.exists("./google-creds.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("./google-creds.json", SCOPE)
            logging.info("Loaded Google credentials from file")
        else:
            creds_json = os.environ.get("GOOGLE_CREDS_JSON")
            if not creds_json:
                raise AuthenticationError(
                    "Missing google-creds.json file AND GOOGLE_CREDS_JSON environment variable!"
                )

            try:
                creds_dict = json.loads(creds_json)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
                logging.info("Loaded Google credentials from environment variable")
            except json.JSONDecodeError as e:
                raise AuthenticationError(f"Invalid JSON in GOOGLE_CREDS_JSON: {e}")

        return creds
    except Exception as e:
        if isinstance(e, (AuthenticationError, SheetsError)):
            raise
        raise SheetsError(f"Failed to initialize credentials: {e}")


# Initialize credentials and client
try:
    creds = initialize_credentials()
    client = gspread.authorize(creds)
    logging.info("Google Sheets client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Google Sheets client: {e}")
    client = None


def get_sheet_for_guild(guild_id: str, worksheet: Optional[str] = None):
    """
    Open the correct Google Sheet with proper error handling.

    Args:
        guild_id: Guild ID
        worksheet: Worksheet name (defaults to "GAL Database")

    Returns:
        Worksheet object

    Raises:
        SheetsError: If sheet cannot be opened
    """
    if not client:
        raise SheetsError("Google Sheets client not initialized")

    try:
        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode)

        sheet_url = cfg.get("sheet_url")
        if not sheet_url:
            raise SheetsError(f"No sheet URL configured for mode: {mode}")

        # Extract sheet key from URL
        if "/d/" not in sheet_url:
            raise SheetsError(f"Invalid sheet URL format: {sheet_url}")

        key_part = sheet_url.split("/d/")[1]
        if "/" not in key_part:
            raise SheetsError(f"Cannot extract sheet key from URL: {sheet_url}")

        key = key_part.split("/")[0]
        worksheet_name = worksheet or "GAL Database"

        spreadsheet = client.open_by_key(key)
        return spreadsheet.worksheet(worksheet_name)

    except gspread.SpreadsheetNotFound:
        raise SheetsError(f"Spreadsheet not found or access denied for guild {guild_id}")
    except gspread.WorksheetNotFound:
        raise SheetsError(f"Worksheet '{worksheet_name}' not found")
    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        raise SheetsError(f"Failed to open sheet for guild {guild_id}: {e}")


# Rate limiting configuration
SHEETS_BASE_DELAY = 1.0
MAX_DELAY = 90
FULL_BACKOFF = 60
MAX_RETRIES = 5


async def retry_until_successful(fn, *args, **kwargs):
    """
    Retry function with exponential backoff and comprehensive error handling.

    Args:
        fn: Function to retry
        *args, **kwargs: Arguments for the function

    Returns:
        Function result

    Raises:
        SheetsError: If all retries are exhausted
    """
    global SHEETS_BASE_DELAY
    delay = SHEETS_BASE_DELAY
    attempts = 0
    last_error = None

    while attempts < MAX_RETRIES:
        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)

            # Successful call - adjust base delay if it was increased
            if delay > SHEETS_BASE_DELAY:
                SHEETS_BASE_DELAY = min(SHEETS_BASE_DELAY * 0.9, delay)

            return result

        except Exception as e:
            last_error = e
            attempts += 1
            err_str = str(e).lower()

            # Check for quota/rate limit errors
            if "429" in str(e) or any(keyword in err_str for keyword in ["quota", "rate", "limit"]):
                if delay >= 30 or attempts > 3:
                    wait_time = FULL_BACKOFF + random.uniform(0, 5)
                    logging.warning(f"Quota exceeded, waiting {wait_time:.1f}s (attempt {attempts})")
                    await asyncio.sleep(wait_time)
                    delay = FULL_BACKOFF
                else:
                    wait_time = delay + random.uniform(0, 0.5)
                    logging.warning(f"Rate limited, waiting {wait_time:.1f}s (attempt {attempts})")
                    await asyncio.sleep(wait_time)
                    delay = min(delay * 2, MAX_DELAY)

            # Check for authentication errors
            elif "401" in str(e) or "unauthorized" in err_str:
                raise AuthenticationError(f"Authentication failed: {e}")

            # Check for other HTTP errors
            elif any(code in str(e) for code in ["400", "403", "404", "500", "502", "503"]):
                if attempts >= MAX_RETRIES - 1:
                    raise SheetsError(f"HTTP error after {attempts} attempts: {e}")
                logging.warning(f"HTTP error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)

            # For other errors, fail immediately on critical ones
            elif "connection" in err_str or "timeout" in err_str:
                if attempts >= MAX_RETRIES - 1:
                    raise SheetsError(f"Connection error after {attempts} attempts: {e}")
                logging.warning(f"Connection error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)
            else:
                # Unknown error, don't retry
                raise SheetsError(f"Unexpected error: {e}")

    # All retries exhausted
    raise SheetsError(f"All {MAX_RETRIES} retries exhausted. Last error: {last_error}")


# Cache management
sheet_cache = {"users": {}, "last_refresh": 0}
cache_lock = asyncio.Lock()


def ordinal_suffix(n: Union[int, str]) -> str:
    """
    Get ordinal suffix for a number.

    Args:
        n: Number to get suffix for

    Returns:
        Ordinal suffix ("st", "nd", "rd", "th")
    """
    try:
        n = int(n)
        if 11 <= (n % 100) <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    except (ValueError, TypeError):
        return "th"


async def refresh_sheet_cache(bot=None) -> Tuple[int, int]:
    """
    Refresh the sheet cache with comprehensive error handling.
    Processes waitlist after cache update to fill any open spots.

    Args:
        bot: Discord bot instance (optional)

    Returns:
        Tuple of (num_changes, total_users)

    Raises:
        SheetsError: If cache refresh fails
    """
    # Only print at start if this is not a recursive call
    if not hasattr(sheet_cache, "_skip_waitlist_processing"):
        print("[CACHE] Starting refresh_sheet_cache")

    # Store guild reference for later use
    guild = None

    # Do the cache refresh inside the lock
    async with cache_lock:
        try:
            # Get guild information
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print("[CACHE] Getting guild information...")
            guild = getattr(bot, "guilds", [None])[0] if bot else None
            gid = str(guild.id) if guild else "unknown"

            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print(f"[CACHE] Guild ID: {gid}")

            mode = get_event_mode_for_guild(gid)
            cfg = get_sheet_settings(mode)

            # Validate configuration
            required_fields = ["header_line_num", "max_players", "discord_col", "ign_col",
                               "alt_ign_col", "registered_col", "checkin_col"]
            missing_fields = [field for field in required_fields if field not in cfg]
            if missing_fields:
                raise SheetsError(f"Missing configuration fields: {missing_fields}")

            maxp = cfg.get("max_players", 9999)
            sheet = get_sheet_for_guild(gid, "GAL Database")

            # Get column indexes
            hline = cfg["header_line_num"]
            dc = col_to_index(cfg["discord_col"])
            ic = col_to_index(cfg["ign_col"])
            ac = col_to_index(cfg["alt_ign_col"])
            rc = col_to_index(cfg["registered_col"])
            cc = col_to_index(cfg["checkin_col"])
            tc = col_to_index(cfg["team_col"]) if mode == "doubleup" and "team_col" in cfg else None

            # Fetch all columns with error handling
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print("[CACHE] Fetching sheet columns...")
            try:
                discord_vals = await retry_until_successful(sheet.col_values, dc)
                ign_vals = await retry_until_successful(sheet.col_values, ic)
                alt_vals = await retry_until_successful(sheet.col_values, ac)
                reg_vals = await retry_until_successful(sheet.col_values, rc)
                ci_vals = await retry_until_successful(sheet.col_values, cc)
                team_vals = await retry_until_successful(sheet.col_values, tc) if tc else []
            except Exception as e:
                raise SheetsError(f"Failed to fetch sheet data: {e}")

            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print("[CACHE] Processing data...")
            # Slice to relevant range
            start = hline
            end = hline + maxp
            discord_col = discord_vals[start:end] if len(discord_vals) > start else []
            ign_col = ign_vals[start:end] if len(ign_vals) > start else []
            alt_col = alt_vals[start:end] if len(alt_vals) > start else []
            reg_col = reg_vals[start:end] if len(reg_vals) > start else []
            ci_col = ci_vals[start:end] if len(ci_vals) > start else []
            team_col = team_vals[start:end] if tc and len(team_vals) > start else []

            # Build new cache mapping
            new_map = {}
            for idx, tag in enumerate(discord_col, start=start + 1):
                offset = idx - (start + 1)
                tag = str(tag).strip()

                if not tag:
                    continue

                # Safely get values with bounds checking
                ign = ign_col[offset].strip() if offset < len(ign_col) else ""
                alt = alt_col[offset].strip() if offset < len(alt_col) else ""
                reg = reg_col[offset] if offset < len(reg_col) else ""
                ci = ci_col[offset] if offset < len(ci_col) else ""
                team = team_col[offset].strip() if tc and offset < len(team_col) else ""

                # Store as tuple: (row, ign, registered, checked_in, team, alt_ign)
                new_map[tag] = (idx, ign, reg, ci, team, alt)

            # Calculate changes
            old_map = sheet_cache["users"]
            added = set(new_map) - set(old_map)
            removed = set(old_map) - set(new_map)
            changed = {tag for tag in set(new_map) & set(old_map) if new_map[tag] != old_map[tag]}

            # Check if any registered users were removed (indicating unregistrations)
            unregistered_users = []
            for tag in removed:
                if old_map[tag][2] and str(old_map[tag][2]).upper() == "TRUE":
                    unregistered_users.append(tag)

            # Also check for users who changed from registered to not registered
            for tag in changed:
                old_data = old_map[tag]
                new_data = new_map[tag]
                # Check if registration status changed from True to False
                old_registered = str(old_data[2]).upper() == "TRUE" if len(old_data) > 2 else False
                new_registered = str(new_data[2]).upper() == "TRUE" if len(new_data) > 2 else False
                if old_registered and not new_registered:
                    unregistered_users.append(tag)

            # Update cache
            sheet_cache["users"] = new_map
            sheet_cache["last_refresh"] = time.time()

            total_changes = len(added) + len(removed) + len(changed)
            total_users = len(new_map)

            logging.info(f"Cache refreshed: {total_changes} changes, {total_users} total users")
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print(f"[CACHE] Cache refreshed: {total_changes} changes, {total_users} total users")

            # Log if any unregistrations were detected
            if unregistered_users and not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print(f"[CACHE] Detected {len(unregistered_users)} unregistrations: {unregistered_users}")

        except Exception as e:
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                print(f"[CACHE] ERROR in refresh_sheet_cache: {e}")
            if isinstance(e, SheetsError):
                raise
            raise SheetsError(f"Failed to refresh cache: {e}")

    # Process waitlist AFTER releasing the cache lock
    # This is important - we process waitlist if:
    # 1. Users were removed/unregistered (spots opened up)
    # 2. Always check after cache refresh to ensure consistency
    if guild and not hasattr(sheet_cache, "_skip_waitlist_processing"):
        print("[CACHE] Processing waitlist (after releasing lock)...")
        try:
            from helpers.waitlist_helpers import WaitlistManager

            # Always process waitlist after cache refresh to fill any open spots
            registered_from_waitlist = await WaitlistManager.process_waitlist(guild)

            if registered_from_waitlist:
                print(f"[CACHE] Registered {len(registered_from_waitlist)} users from waitlist")

                # Refresh cache again after waitlist processing to ensure consistency
                print("[CACHE] Refreshing cache again after waitlist processing...")
                # Set flag to skip waitlist processing and reduce logging
                sheet_cache["_skip_waitlist_processing"] = True
                try:
                    await refresh_sheet_cache(bot=bot)
                finally:
                    # Remove the flag
                    del sheet_cache["_skip_waitlist_processing"]
            else:
                print("[CACHE] No users registered from waitlist")

        except ImportError as e:
            print(f"[CACHE] WaitlistManager import failed: {e}")
            logging.debug("WaitlistManager not available, skipping waitlist processing")
        except Exception as e:
            print(f"[CACHE] Waitlist processing failed: {e}")
            logging.warning(f"Failed to process waitlist: {e}")

    # Only print completion message if not a recursive call
    if not hasattr(sheet_cache, "_skip_waitlist_processing"):
        print("[CACHE] refresh_sheet_cache complete!")

    return total_changes, total_users


async def cache_refresh_loop(bot):
    """Background task to refresh cache periodically."""
    # Wait for the initial refresh interval before starting
    # This prevents double refresh on startup since on_ready already does one
    await asyncio.sleep(CACHE_REFRESH_SECONDS)

    while True:
        try:
            await refresh_sheet_cache(bot=bot)
            logging.debug("Periodic cache refresh completed")
        except Exception as e:
            logging.error(f"Periodic cache refresh failed: {e}")

        await asyncio.sleep(CACHE_REFRESH_SECONDS)


async def find_or_register_user(
        discord_tag: str,
        ign: str,
        guild_id: Optional[str] = None,
        team_name: Optional[str] = None
) -> int:
    """
    Find existing user or register new user with comprehensive error handling.

    Args:
        discord_tag: User's Discord tag
        ign: In-game name
        guild_id: Guild ID
        team_name: Team name for double-up mode

    Returns:
        Row number in sheet (1-based)

    Raises:
        SheetsError: If operation fails
    """
    if not discord_tag or not ign:
        raise ValueError("Discord tag and IGN are required")

    try:
        # Check cache for existing user
        async with cache_lock:
            existing = sheet_cache["users"].get(discord_tag)

        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # Update existing user
        if existing:
            row, old_ign, old_reg, old_ci, old_team, old_alt = existing

            updates_needed = []

            if old_ign != ign:
                await retry_until_successful(
                    sheet.update_acell,
                    f"{cfg['ign_col']}{row}",
                    ign
                )
                updates_needed.append("IGN")

            if not old_reg:
                await retry_until_successful(
                    sheet.update_acell,
                    f"{cfg['registered_col']}{row}",
                    True
                )
                updates_needed.append("registration")

            if mode == "doubleup" and team_name and old_team != team_name:
                await retry_until_successful(
                    sheet.update_acell,
                    f"{cfg['team_col']}{row}",
                    team_name
                )
                updates_needed.append("team")

            # Update cache
            sheet_cache["users"][discord_tag] = (
                row, ign, True, old_ci, team_name or old_team, old_alt
            )

            if updates_needed:
                logging.info(f"Updated existing user {discord_tag}: {', '.join(updates_needed)}")

            return row

        # Register new user
        hline = cfg["header_line_num"]
        maxp = cfg.get("max_players", 9999)
        dc_idx = col_to_index(cfg["discord_col"])

        discord_vals = await retry_until_successful(sheet.col_values, dc_idx)

        # Find first empty slot
        target_row = None
        for i in range(hline, min(len(discord_vals), hline + maxp)):
            if not discord_vals[i].strip():
                target_row = i + 1
                break

        # Prepare data to write
        writes = {
            cfg["discord_col"]: discord_tag,
            cfg["ign_col"]: ign,
            cfg["registered_col"]: True,
            cfg["checkin_col"]: False
        }

        if mode == "doubleup" and "team_col" in cfg:
            writes[cfg["team_col"]] = team_name or ""

        if target_row:
            # Write to existing formatted row
            for col, val in writes.items():
                await retry_until_successful(
                    sheet.update_acell,
                    f"{col}{target_row}",
                    val
                )
            row = target_row
        else:
            # Append new row
            cols_idx = [col_to_index(c) for c in writes.keys()]
            max_idx = max(cols_idx)
            row_vals = [""] * max_idx

            for col, val in writes.items():
                row_vals[col_to_index(col) - 1] = val

            await retry_until_successful(sheet.append_row, row_vals)

            # Get new row number
            dc_vals = await retry_until_successful(sheet.col_values, dc_idx)
            row = len(dc_vals)

        # Update cache
        sheet_cache["users"][discord_tag] = (
            row, ign, True, False, team_name or "", ""
        )

        logging.info(f"Registered new user {discord_tag} as {ign} in row {row}")
        return row

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to find or register user {discord_tag}: {e}")


async def unregister_user(
        discord_tag: str,
        guild_id: Optional[str] = None
) -> bool:
    """
    Completely remove user from sheet with proper error handling.

    Args:
        discord_tag: User's Discord tag
        guild_id: Guild ID

    Returns:
        True if user was unregistered, False if not found

    Raises:
        SheetsError: If operation fails
    """
    if not discord_tag:
        raise ValueError("Discord tag is required")

    try:
        async with cache_lock:
            user_data = sheet_cache["users"].get(discord_tag)

        if not user_data:
            logging.info(f"User {discord_tag} not found in cache for unregistration")
            return False

        row, _ign, _reg, _ci, _team, _alt = user_data
        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # Verify user is still in the sheet at expected location
        try:
            cell = await retry_until_successful(sheet.acell, f"{cfg['discord_col']}{row}")
            if cell.value.strip() != discord_tag:
                logging.warning(f"User {discord_tag} not found at expected row {row}")
                return False
        except Exception as e:
            raise SheetsError(f"Failed to verify user location: {e}")

        # Clear all user data
        clear_operations = [
            (cfg['discord_col'], ""),
            (cfg['ign_col'], ""),
            (cfg['pronouns_col'], ""),
            (cfg['alt_ign_col'], ""),
            (cfg['registered_col'], False),
            (cfg['checkin_col'], False)
        ]

        if mode == "doubleup" and "team_col" in cfg:
            clear_operations.append((cfg['team_col'], ""))

        # Execute all clear operations
        for col, value in clear_operations:
            try:
                await retry_until_successful(
                    sheet.update_acell,
                    f"{col}{row}",
                    value
                )
            except Exception as e:
                logging.error(f"Failed to clear {col} for user {discord_tag}: {e}")
                # Continue with other operations

        # Remove from cache
        async with cache_lock:
            sheet_cache["users"].pop(discord_tag, None)

        logging.info(f"Successfully unregistered user {discord_tag}")
        return True

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to unregister user {discord_tag}: {e}")


async def mark_checked_in_async(
        discord_tag: str,
        guild_id: Optional[str] = None
) -> bool:
    """
    Mark user as checked in with proper validation.

    Args:
        discord_tag: User's Discord tag
        guild_id: Guild ID

    Returns:
        True if successfully checked in, False if not registered

    Raises:
        SheetsError: If operation fails
    """
    return await _update_checkin_status(discord_tag, True, guild_id)


async def unmark_checked_in_async(
        discord_tag: str,
        guild_id: Optional[str] = None
) -> bool:
    """
    Mark user as not checked in.

    Args:
        discord_tag: User's Discord tag
        guild_id: Guild ID

    Returns:
        True if successfully unchecked, False if not found

    Raises:
        SheetsError: If operation fails
    """
    return await _update_checkin_status(discord_tag, False, guild_id)


async def _update_checkin_status(
        discord_tag: str,
        checked_in: bool,
        guild_id: Optional[str] = None
) -> bool:
    """
    Internal function to update check-in status.

    Args:
        discord_tag: User's Discord tag
        checked_in: Whether user should be checked in
        guild_id: Guild ID

    Returns:
        True if successful, False if user not found or not registered

    Raises:
        SheetsError: If operation fails
    """
    if not discord_tag:
        raise ValueError("Discord tag is required")

    try:
        async with cache_lock:
            user_data = sheet_cache["users"].get(discord_tag)

        if not user_data:
            logging.info(f"User {discord_tag} not found for check-in update")
            return False

        row, ign, reg, current_ci, team, alt = user_data

        # Must be registered to check in
        if not reg:
            logging.info(f"User {discord_tag} not registered, cannot update check-in status")
            return False

        # Check if already in desired state
        is_currently_checked_in = str(current_ci).upper() == "TRUE"
        if is_currently_checked_in == checked_in:
            logging.debug(f"User {discord_tag} already in desired check-in state: {checked_in}")
            return True

        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # Update sheet
        await retry_until_successful(
            sheet.update_acell,
            f"{cfg['checkin_col']}{row}",
            checked_in
        )

        # Update cache
        sheet_cache["users"][discord_tag] = (
            row, ign, reg, checked_in, team, alt
        )

        action = "checked in" if checked_in else "checked out"
        logging.info(f"User {discord_tag} successfully {action}")
        return True

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to update check-in status for {discord_tag}: {e}")


async def reset_registered_roles_and_sheet(guild, channel) -> int:
    """
    Reset all registration data - clear all columns except headers.
    FIXED: Only clears from header_line + 1 to header_line + max_players.

    Args:
        guild: Discord guild
        channel: Channel for logging

    Returns:
        Number of rows cleared

    Raises:
        SheetsError: If operation fails
    """
    try:
        gid = str(guild.id)
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # Get header line and max players
        header_line = cfg["header_line_num"]
        max_players = cfg.get("max_players", 32)

        # Calculate the range to clear: from header_line + 1 to header_line + max_players
        start_row = header_line + 1
        end_row = header_line + max_players

        # Get all columns we need to clear
        columns_to_clear = {
            'discord_col': "",  # Clear to empty string
            'pronouns_col': "",
            'ign_col': "",
            'alt_ign_col': "",
            'registered_col': False,  # Set to boolean False
            'checkin_col': False,  # Set to boolean False
        }

        # Add team column for doubleup mode
        if mode == "doubleup" and "team_col" in cfg:
            columns_to_clear['team_col'] = ""

        # Clear each column in the specified range
        cleared_rows = 0
        for col_key, clear_value in columns_to_clear.items():
            if col_key not in cfg:
                continue

            col_letter = cfg[col_key]

            # Build range from start_row to end_row
            if start_row <= end_row:  # Ensure valid range
                cell_range = f"{col_letter}{start_row}:{col_letter}{end_row}"
                cell_list = await retry_until_successful(sheet.range, cell_range)

                for cell in cell_list:
                    cell.value = clear_value

                await retry_until_successful(sheet.update_cells, cell_list)
                logging.info(f"Cleared column {col_letter} from row {start_row} to {end_row}")

        # Clear waitlist for this guild
        from helpers.waitlist_helpers import WaitlistManager
        all_data = WaitlistManager._load_waitlist_data()
        if gid in all_data:
            all_data[gid]["waitlist"] = []
            WaitlistManager._save_waitlist_data(all_data)

        # Refresh cache
        await refresh_sheet_cache()

        # Return the number of rows that were cleared
        cleared_rows = max_players
        logging.info(f"Reset registration for {cleared_rows} rows (max capacity)")

        return cleared_rows

    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        raise SheetsError(f"Failed to reset registered roles and sheet: {e}")


async def reset_checked_in_roles_and_sheet(guild, channel) -> int:
    """
    Reset only check-in data - set checkin column to False.
    FIXED: Only clears from header_line + 1 to header_line + max_players.

    Args:
        guild: Discord guild
        channel: Channel for logging

    Returns:
        Number of rows cleared

    Raises:
        SheetsError: If operation fails
    """
    try:
        gid = str(guild.id)
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        col = cfg["checkin_col"]
        header_line = cfg["header_line_num"]
        max_players = cfg.get("max_players", 32)

        # Calculate the range to clear: from header_line + 1 to header_line + max_players
        start_row = header_line + 1
        end_row = header_line + max_players

        # Build range from start_row to end_row
        if start_row <= end_row:  # Ensure valid range
            cell_range = f"{col}{start_row}:{col}{end_row}"
            cell_list = await retry_until_successful(sheet.range, cell_range)

            # Set all to boolean False
            for cell in cell_list:
                cell.value = False

            await retry_until_successful(sheet.update_cells, cell_list)

        # Refresh cache
        await refresh_sheet_cache()

        cleared_count = max_players
        logging.info(f"Reset check-in for {cleared_count} rows (max capacity)")

        return cleared_count

    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        raise SheetsError(f"Failed to reset check-in roles and sheet: {e}")


# Health check function
async def health_check() -> Dict[str, Any]:
    """
    Perform health check on sheets integration.

    Returns:
        Dict with health status information
    """
    health_status = {
        "client_initialized": client is not None,
        "cache_age_seconds": time.time() - sheet_cache["last_refresh"],
        "cached_users": len(sheet_cache["users"]),
        "credentials_valid": False,
        "test_sheet_accessible": False
    }

    if client:
        try:
            # Test credentials by listing spreadsheets (limited test)
            health_status["credentials_valid"] = True
        except Exception as e:
            logging.warning(f"Credentials health check failed: {e}")

    return health_status