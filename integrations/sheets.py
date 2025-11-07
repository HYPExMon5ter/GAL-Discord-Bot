# integrations/sheets.py

import asyncio
import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import get_sheet_settings, col_to_index, get_registered_role, get_checked_in_role
from core.persistence import get_event_mode_for_guild
from integrations.sheet_cache_manager import SheetCacheManager
from integrations.sheet_integration import SheetIntegrationHelper
from integrations.sheet_optimizer import (
    fetch_required_columns_batch,
    update_cells_batch,
    detect_columns_optimized,
)
from utils.feature_flags import (
    deployment_stage,
    rollout_flags_snapshot,
    sheets_refactor_enabled,
)
from utils.logging_utils import SecureLogger

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


logger = SecureLogger(__name__)


# Use the new SheetCacheManager for all environments
cache_manager = SheetCacheManager(
    ttl_seconds=int(os.getenv("SHEET_CACHE_TTL", "600"))
)
logger.info(
    "Using SheetCacheManager (stage=%s, flags=%s)",
    deployment_stage(),
    rollout_flags_snapshot(),
)

sheet_cache = cache_manager.data
cache_lock = cache_manager.lock


async def fetch_required_columns(
    sheet,
    column_indexes: Dict[str, int],
    header_row: int,
    max_players: int,
) -> Dict[str, List[str]]:
    """Fetch required columns using the new batch implementation."""
    return await fetch_required_columns_batch(sheet, column_indexes, header_row, max_players)


async def apply_sheet_updates(sheet, updates: List[Tuple[str, Any]]) -> bool:
    """Apply sheet updates using the new batch implementation."""
    return await update_cells_batch(sheet, updates)


def initialize_credentials():
    """Initialize Google Sheets credentials with proper error handling."""
    try:
        # Try multiple possible locations for the credentials file
        creds_file_paths = [
            "./google-creds.json",  # Current directory
            os.path.join(os.getcwd(), "google-creds.json"),  # Absolute path from current working directory
            os.path.join(os.path.dirname(__file__), "..", "google-creds.json"),  # Relative to this file's location
        ]
        
        creds_file = None
        for path in creds_file_paths:
            if os.path.exists(path):
                creds_file = path
                logger.debug(f"Found credentials file at: {path}")
                break
        
        if creds_file:
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPE)
            logger.info(f"Loaded Google credentials from file: {creds_file}")
        else:
            logger.debug(f"Credentials file not found in any of these locations: {creds_file_paths}")
            creds_json = os.environ.get("GOOGLE_CREDS_JSON")
            if not creds_json:
                raise AuthenticationError(
                    "Missing google-creds.json file AND GOOGLE_CREDS_JSON environment variable!"
                )

            try:
                creds_dict = json.loads(creds_json)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
                logger.info("Loaded Google credentials from environment variable")
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
    logger.info("Google Sheets client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Google Sheets client: {e}")
    client = None


async def get_sheet_for_guild(guild_id: str, worksheet: str | None = None):
    """
    Open the correct Google Sheet with proper error handling.
    """
    if not client:
        raise SheetsError("Google Sheets client not initialized")

    try:
        mode = get_event_mode_for_guild(guild_id)

        # Use the new environment-aware function
        from config import get_sheet_url_for_environment
        sheet_url = get_sheet_url_for_environment(mode)

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

        # Add retry logic for transient failures
        max_retries = 3
        for attempt in range(max_retries):
            try:
                spreadsheet = client.open_by_key(key)
                return spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited, wait and retry
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise

    except gspread.SpreadsheetNotFound:
        logger.error(f"Spreadsheet not found or access denied for guild {guild_id}")
        raise SheetsError(f"Spreadsheet not found or access denied for guild {guild_id}")
    except gspread.WorksheetNotFound:
        logger.error(f"Worksheet '{worksheet_name}' not found for guild {guild_id}")
        raise SheetsError(f"Worksheet '{worksheet_name}' not found")
    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        logger.error(f"Failed to open sheet for guild {guild_id}: {e}", exc_info=True)
        raise SheetsError(f"Failed to open sheet for guild {guild_id}: {e}")


# Rate limiting configuration
SHEETS_BASE_DELAY = 1.0
MAX_DELAY = 90
FULL_BACKOFF = 60
MAX_RETRIES = 5


async def retry_until_successful(fn, *args, **kwargs):
    """
    Retry function with exponential backoff and comprehensive error handling.
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
                    logger.warning(f"Quota exceeded, waiting {wait_time:.1f}s (attempt {attempts})")
                    await asyncio.sleep(wait_time)
                    delay = FULL_BACKOFF
                else:
                    wait_time = delay + random.uniform(0, 0.5)
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s (attempt {attempts})")
                    await asyncio.sleep(wait_time)
                    delay = min(delay * 2, MAX_DELAY)

            # Check for authentication errors
            elif "401" in str(e) or "unauthorized" in err_str:
                raise AuthenticationError(f"Authentication failed: {e}")

            # Check for other HTTP errors
            elif any(code in str(e) for code in ["400", "403", "404", "500", "502", "503"]):
                if attempts >= MAX_RETRIES - 1:
                    raise SheetsError(f"HTTP error after {attempts} attempts: {e}")
                logger.warning(f"HTTP error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)

            # For other errors, fail immediately on critical ones
            elif "connection" in err_str or "timeout" in err_str:
                if attempts >= MAX_RETRIES - 1:
                    raise SheetsError(f"Connection error after {attempts} attempts: {e}")
                logger.warning(f"Connection error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)
            else:
                # Unknown error, don't retry
                raise SheetsError(f"Unexpected error: {e}")

    # All retries exhausted
    raise SheetsError(f"All {MAX_RETRIES} retries exhausted. Last error: {last_error}")


async def refresh_sheet_cache(bot=None, *, force: bool = False) -> Tuple[int, int]:
    """
    Refresh the sheet cache with comprehensive error handling.
    Synchronizes Discord roles with sheet data after refresh.
    Processes waitlist after cache update to fill any open spots.
    
    Phase 2 Integration: Now integrates with the new DAL for event broadcasting
    and unified cache management while maintaining backward compatibility.
    """
    # Only log at start if this is not a recursive call
    if not hasattr(sheet_cache, "_skip_waitlist_processing"):
        logger.debug("[CACHE] Starting refresh_sheet_cache")
        if not force and not cache_manager.is_stale():
            logger.debug("[CACHE] Cache is fresh; skipping refresh")
            return 0, len(sheet_cache.get("users", {}))
    
    # Legacy adapter completely removed - using direct cache access only
    adapter = None

    # Store guild reference for later use
    guild = None
    roles_synced = 0

    # Do the cache refresh inside the lock
    async with cache_lock:
        try:
            # Get guild information - properly resolve from bot
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                logger.debug("[CACHE] Getting guild information...")

            # Properly get guild from bot
            if bot and hasattr(bot, "guilds") and bot.guilds:
                guild = bot.guilds[0]  # Get first guild
                gid = str(guild.id)
            else:
                # Try to get guild ID from environment for dev mode
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if dev_guild_id:
                    gid = dev_guild_id
                    # Try to get guild object if bot is available
                    if bot:
                        guild = bot.get_guild(int(dev_guild_id))
                else:
                    # Fallback but log warning
                    gid = "unknown"
                    logger.warning("[CACHE] No guild available for cache refresh - using 'unknown'")

            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                logger.debug(f"[CACHE] Guild ID: {gid}")

            mode = get_event_mode_for_guild(gid)
            cfg, col_indexes = await SheetIntegrationHelper.get_sheet_and_column_config(gid)

            # Validate configuration using column config from persistence
            column_config = await SheetIntegrationHelper.get_column_config(gid)
            is_valid, missing_columns = SheetIntegrationHelper.validate_required_columns(column_config, mode)
            if not is_valid:
                logger.error(f"[CACHE] Missing required columns: {missing_columns}")
                logger.error(f"[CACHE] Column config: {column_config}")
                logger.error(f"[CACHE] This can be fixed by running /gal config and using the Detect button")
                raise SheetsError(f"Missing required columns: {missing_columns}")

            maxp = cfg.get("max_players", 9999)
            # AWAIT the async function
            sheet = await get_sheet_for_guild(gid, "GAL Database")

            # Get column indexes from integration helper
            hline = cfg["header_line_num"]
            dc = col_indexes.get("discord_idx")
            ic = col_indexes.get("ign_idx")
            ac = col_indexes.get("alt_idx")
            pc = col_indexes.get("pronouns_idx")
            rc = col_indexes.get("registered_idx")
            cc = col_indexes.get("checkin_idx")
            tc = col_indexes.get("team_idx")

            # Validate that we have the required column indexes
            required_indexes = ["discord_idx", "ign_idx", "registered_idx", "checkin_idx"]
            missing_indexes = [idx for idx in required_indexes if idx not in col_indexes]
            if missing_indexes:
                raise SheetsError(f"Missing column indexes: {missing_indexes}")

            if mode == "doubleup" and "team_idx" not in col_indexes:
                raise SheetsError("Team column index missing for doubleup mode")

            # Fetch all required columns in a single batch operation
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                logger.debug("[CACHE] Fetching sheet columns (optimized batch)...")
            try:
                # Prepare column indexes for batch fetching
                column_indexes = {
                    "discord_idx": dc,
                    "ign_idx": ic,
                    "alt_idx": ac,
                    "pronouns_idx": pc,
                    "registered_idx": rc,
                    "checkin_idx": cc
                }

                if tc:
                    column_indexes["team_idx"] = tc

                # Fetch all columns in one API call
                batch_data = await fetch_required_columns(sheet, column_indexes, hline, maxp)

                # Extract column data
                discord_col = batch_data.get("discord_idx", [])
                ign_col = batch_data.get("ign_idx", [])
                alt_col = batch_data.get("alt_idx", [])
                pronouns_col = batch_data.get("pronouns_idx", [])
                reg_col = batch_data.get("registered_idx", [])
                ci_col = batch_data.get("checkin_idx", [])
                team_col = batch_data.get("team_idx", [])

                if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                    logger.debug(f"[CACHE] Successfully fetched {len(batch_data)} columns in batch")

            except Exception as e:
                raise SheetsError(f"Failed to fetch sheet data in batch: {e}")

            # Build new cache mapping
            start = hline
            new_map = {}
            for idx, tag in enumerate(discord_col, start=hline + 1):
                offset = idx - (hline + 1)
                tag = str(tag).strip()

                if not tag:
                    continue

                # Safely get values with bounds checking
                ign = ign_col[offset].strip() if offset < len(ign_col) else ""
                alt = alt_col[offset].strip() if offset < len(alt_col) else ""
                pronouns = pronouns_col[offset].strip() if offset < len(pronouns_col) else ""
                reg_raw = reg_col[offset] if offset < len(reg_col) else ""
                ci_raw = ci_col[offset] if offset < len(ci_col) else ""
                team = team_col[offset].strip() if tc and offset < len(team_col) else ""

                # Standardize to boolean for cache consistency
                reg = str(reg_raw).upper() == "TRUE" if reg_raw else False
                ci = str(ci_raw).upper() == "TRUE" if ci_raw else False

                # Store as tuple: (row, ign, registered, checked_in, team, alt_ign, pronouns)
                new_map[tag] = (idx, ign, reg, ci, team, alt, pronouns)

            # Calculate changes
            old_map = sheet_cache["users"]
            added = set(new_map) - set(old_map)
            removed = set(old_map) - set(new_map)
            changed = {tag for tag in set(new_map) & set(old_map) if new_map[tag] != old_map[tag]}

            # Check if any registered users were removed (indicating unregistrations)
            unregistered_users = []
            for tag in removed:
                old_reg = old_map[tag][2]
                # Handle both boolean and string consistently
                was_registered = old_reg if isinstance(old_reg, bool) else str(old_reg).upper() == "TRUE"
                if was_registered:
                    unregistered_users.append(tag)

            # Also check for users who changed from registered to not registered
            for tag in changed:
                old_data = old_map[tag]
                new_data = new_map[tag]
                # Consistent boolean handling for both old and new data
                old_reg = old_data[2]
                new_reg = new_data[2]
                old_registered = old_reg if isinstance(old_reg, bool) else str(old_reg).upper() == "TRUE"
                new_registered = new_reg if isinstance(new_reg, bool) else str(new_reg).upper() == "TRUE"
                if old_registered and not new_registered:
                    unregistered_users.append(tag)

            # Update cache atomically (already inside outer cache_lock from line 359)
            # NO nested lock acquisition - would cause deadlock!
            sheet_cache["users"] = new_map
            cache_manager.mark_refresh()

            total_changes = len(added) + len(removed) + len(changed)
            total_users = len(new_map)

            logger.info(f"[CACHE] Cache refreshed: {total_changes} changes, {total_users} total users")

            if unregistered_users and not hasattr(sheet_cache, "_skip_waitlist_processing"):
                logger.info(f"[CACHE] Detected {len(unregistered_users)} unregistrations: {unregistered_users}")

        except Exception as e:
            if not hasattr(sheet_cache, "_skip_waitlist_processing"):
                logger.error(f"[CACHE] ERROR in refresh_sheet_cache: {e}")
            if isinstance(e, SheetsError):
                raise
            raise SheetsError(f"Failed to refresh cache: {e}")

    # ROLE SYNCHRONIZATION - After cache is updated, sync all Discord roles
    if guild and not hasattr(sheet_cache, "_skip_waitlist_processing"):
        logger.debug("[CACHE] Synchronizing Discord roles with sheet data...")
        try:
            from helpers import RoleManager
            from utils.utils import resolve_member

            # Get a snapshot of the cache for role sync
            async with cache_lock:
                cache_snapshot = dict(sheet_cache["users"])

            for discord_tag, user_data in cache_snapshot.items():
                try:
                    # Resolve member from discord tag
                    member = resolve_member(guild, discord_tag)

                    if not member:
                        # User not in server, skip
                        continue

                    # Parse registration and check-in status from cache
                    # Cache format: (row, ign, reg_status, ci_status, team, alt_ign, pronouns)
                    _, _, reg_status, ci_status, _, _, _ = user_data
                    is_registered = str(reg_status).upper() == "TRUE"
                    is_checked_in = str(ci_status).upper() == "TRUE"

                    # Sync roles using existing helper
                    await RoleManager.sync_user_roles(member, is_registered, is_checked_in)
                    roles_synced += 1

                except Exception as e:
                    logger.warning(f"Failed to sync roles for {discord_tag}: {e}")
                    continue

            # Also check for users in server who have roles but are not in cache
            # (they might have been manually removed from sheet)
            registered_role = get_registered_role()
            checked_in_role = get_checked_in_role()

            if registered_role or checked_in_role:
                logger.debug("[CACHE] Checking for users with stale roles...")
                cache_discord_tags = set(cache_snapshot.keys())

                # Get all members with registration roles
                members_with_roles = []
                if registered_role:
                    reg_role = discord.utils.get(guild.roles, name=registered_role)
                    if reg_role:
                        members_with_roles.extend(reg_role.members)

                if checked_in_role:
                    ci_role = discord.utils.get(guild.roles, name=checked_in_role)
                    if ci_role:
                        members_with_roles.extend(ci_role.members)

                # Remove duplicates
                members_with_roles = list(set(members_with_roles))

                stale_roles_removed = 0
                for member in members_with_roles:
                    discord_tag = str(member)
                    if discord_tag not in cache_discord_tags:
                        # User has roles but is not in cache, remove roles
                        try:
                            await RoleManager.sync_user_roles(member, False, False)
                            stale_roles_removed += 1
                            logger.debug(f"[CACHE] Removed stale roles from {discord_tag}")
                        except Exception as e:
                            logger.warning(f"Failed to remove stale roles from {discord_tag}: {e}")

                if stale_roles_removed > 0:
                    logger.debug(f"[CACHE] Removed stale roles from {stale_roles_removed} users")
                    roles_synced += stale_roles_removed

            if roles_synced > 0:
                logger.debug(f"[CACHE] Synchronized roles for {roles_synced} users total")
                logger.info(f"Synchronized Discord roles for {roles_synced} users after cache refresh")

        except Exception as e:
            logger.error(f"[CACHE] Failed to synchronize roles after cache refresh: {e}")

    # Process waitlist AFTER releasing the cache lock and syncing roles
    # This is important - we process waitlist if:
    # 1. Users were removed/unregistered (spots opened up)
    # 2. Always check after cache refresh to ensure consistency
    if guild and not hasattr(sheet_cache, "_skip_waitlist_processing"):
        logger.debug("[CACHE] Processing waitlist (after releasing lock)...")
        try:
            from helpers.waitlist_helpers import WaitlistManager

            # Always process waitlist after cache refresh to fill any open spots
            registered_from_waitlist = await WaitlistManager.process_waitlist(guild)

            if registered_from_waitlist:
                logger.info(f"[CACHE] Registered {len(registered_from_waitlist)} users from waitlist")

                # Refresh cache again after waitlist processing to ensure consistency
                logger.info("[CACHE] Refreshing cache again after waitlist processing...")
                # Set flag to skip waitlist processing and reduce logging
                sheet_cache["_skip_waitlist_processing"] = True
                try:
                    await refresh_sheet_cache(bot=bot, force=True)
                finally:
                    # Remove the flag
                    del sheet_cache["_skip_waitlist_processing"]
            else:
                logger.debug("[CACHE] No users registered from waitlist")

        except ImportError as e:
            logger.debug(f"[CACHE] WaitlistManager import failed: {e}")
            logger.debug("WaitlistManager not available, skipping waitlist processing")
        except Exception as e:
            logger.debug(f"[CACHE] Waitlist processing failed: {e}")
            logger.warning(f"Failed to process waitlist: {e}")

    # NOTE: Removed duplicate UI update - let callers handle UI updates
    # This prevents race conditions where cache refresh triggers UI update
    # before the calling function completes its operations

    # Only print completion message if not a recursive call
    if not hasattr(sheet_cache, "_skip_waitlist_processing"):
        logger.debug(f"[CACHE] refresh_sheet_cache complete! (Synced {roles_synced} roles)")

    return total_changes, total_users


async def cache_refresh_loop(bot):
    """Background task to refresh cache periodically."""
    # Get initial refresh interval from config
    from config import _FULL_CFG
    cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)

    # Wait for the initial refresh interval before starting
    await asyncio.sleep(cache_refresh_seconds)

    consecutive_errors = 0
    max_consecutive_errors = 3

    while True:
        try:
            # Process each guild separately to update unified channels
            for guild in bot.guilds:
                await refresh_sheet_cache(bot=bot, force=True)
            logger.debug("Periodic cache refresh completed")
            consecutive_errors = 0  # Reset on success
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Periodic cache refresh failed ({consecutive_errors}/{max_consecutive_errors}): {e}")

            # If too many consecutive errors, wait longer before retrying
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many cache refresh failures, waiting 5 minutes before retry")
                await asyncio.sleep(300)  # 5 minutes
                consecutive_errors = 0  # Reset counter
                continue

        # Re-read cache refresh interval from config in case it changed
        cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)
        await asyncio.sleep(cache_refresh_seconds)


async def find_or_register_user(
        discord_tag: str,
        ign: str,
        guild_id: str | None = None,
        team_name: str | None = None,
        alt_igns: str | None = None,
        pronouns: str | None = None
) -> int:
    """
    Find existing user or register new user with comprehensive error handling.
    """
    if not discord_tag or not ign:
        raise ValueError("Discord tag and IGN are required")

    try:
        # Check cache for existing user
        async with cache_lock:
            existing = sheet_cache["users"].get(discord_tag)

        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        cfg, col_indexes = await SheetIntegrationHelper.get_sheet_and_column_config(gid)
        sheet = await get_sheet_for_guild(gid, "GAL Database")  # ADD AWAIT

        # Update existing user
        if existing:
            row, old_ign, old_reg, old_ci, old_team, old_alt, old_pronouns = existing

            updates_needed = []

            # Collect all updates to do them in a single batch
            batch_updates = []

            if old_ign != ign:
                ign_col = await SheetIntegrationHelper.get_column_letter(gid, "ign_col")
                if ign_col:
                    batch_updates.append((f"{ign_col}{row}", ign))
                    updates_needed.append("IGN")

            if not old_reg:
                reg_col = await SheetIntegrationHelper.get_column_letter(gid, "registered_col")
                if reg_col:
                    batch_updates.append((f"{reg_col}{row}", True))
                    updates_needed.append("registration")

            if mode == "doubleup" and team_name and old_team != team_name:
                team_col = await SheetIntegrationHelper.get_column_letter(gid, "team_col")
                if team_col:
                    batch_updates.append((f"{team_col}{row}", team_name))
                    updates_needed.append("team")

            # Update alt IGNs if provided and different
            if alt_igns is not None and alt_igns != old_alt:
                alt_col = await SheetIntegrationHelper.get_column_letter(gid, "alt_ign_col")
                if alt_col:
                    batch_updates.append((f"{alt_col}{row}", alt_igns))
                    updates_needed.append("alt IGNs")

            # Update pronouns if provided and different
            if pronouns is not None and pronouns != old_pronouns:
                pronouns_col = await SheetIntegrationHelper.get_column_letter(gid, "pronouns_col")
                if pronouns_col:
                    batch_updates.append((f"{pronouns_col}{row}", pronouns))
                    updates_needed.append("pronouns")

            # Execute all updates in a single batch
            if batch_updates:
                success = await apply_sheet_updates(sheet, batch_updates)
                if not success:
                    raise SheetsError("Failed to update user data in batch")

            # Update cache with NEW values (not old ones!)
            sheet_cache["users"][discord_tag] = (
                row, ign, True, old_ci, team_name or old_team, alt_igns if alt_igns is not None else old_alt,
                pronouns if pronouns is not None else old_pronouns
            )

            if updates_needed:
                logger.info(f"Updated existing user {discord_tag}: {', '.join(updates_needed)}")

            return row

        # Register new user
        hline = cfg["header_line_num"]
        maxp = cfg.get("max_players", 9999)
        dc_idx = col_indexes.get("discord_idx")

        if not dc_idx:
            raise SheetsError("Discord column index not found")

        # Fetch discord column only (we just need to find empty rows)
        discord_column_indexes = {"discord_idx": dc_idx}
        discord_data = await fetch_required_columns(sheet, discord_column_indexes, hline, maxp)
        discord_vals = discord_data.get("discord_idx", [])

        # Find first empty slot in the discord column
        target_row = None

        # discord_vals is already post-header, 0-indexed array
        # discord_vals[0] corresponds to row (hline + 1)
        # discord_vals[i] corresponds to row (hline + 1 + i)

        for array_idx in range(len(discord_vals)):
            cell_content = str(discord_vals[array_idx]).strip()
            if not cell_content:
                # Found empty slot - convert array index to actual sheet row number
                target_row = hline + 1 + array_idx
                logger.debug(f"Found empty slot at row {target_row} (array index {array_idx})")
                break

        # Verify the target row is actually empty (safety check for race conditions)
        if target_row:
            try:
                # Read just the discord column cell for this row to verify
                verify_cell = await retry_until_successful(
                    sheet.acell, 
                    f"{await SheetIntegrationHelper.get_column_letter(gid, 'discord_col')}{target_row}"
                )
                
                if verify_cell.value and str(verify_cell.value).strip():
                    # Row is not actually empty, scan for next empty row
                    logger.warning(f"Row {target_row} verification failed, scanning for next empty row")
                    target_row = None
                    
                    # Scan again from where we left off to find next empty row
                    for continue_idx in range(array_idx + 1, len(discord_vals)):
                        cell_content = str(discord_vals[continue_idx]).strip()
                        if not cell_content:
                            target_row = hline + 1 + continue_idx
                            logger.info(f"Found alternative empty slot at row {target_row}")
                            break
                    
            except Exception as e:
                logger.warning(f"Row verification failed: {e}, proceeding with target row {target_row}")

        # Prepare data to write
        writes = {}

        # Get all column letters
        discord_col = await SheetIntegrationHelper.get_column_letter(gid, "discord_col")
        ign_col = await SheetIntegrationHelper.get_column_letter(gid, "ign_col")
        reg_col = await SheetIntegrationHelper.get_column_letter(gid, "registered_col")
        checkin_col = await SheetIntegrationHelper.get_column_letter(gid, "checkin_col")

        if discord_col:
            writes[discord_col] = discord_tag
            logger.info(f"✅ Writing Discord tag to column {discord_col}: {discord_tag}")
        else:
            logger.error(f"❌ discord_col is None! Cannot write Discord tag for {discord_tag}")
            logger.error(f"Column config: {await SheetIntegrationHelper.get_column_config(gid)}")
        if ign_col:
            writes[ign_col] = ign
        if reg_col:
            writes[reg_col] = True
        if checkin_col:
            writes[checkin_col] = False

        if mode == "doubleup":
            team_col = await SheetIntegrationHelper.get_column_letter(gid, "team_col")
            if team_col:
                writes[team_col] = team_name or ""

        # Add alt IGNs and pronouns if columns exist
        alt_col = await SheetIntegrationHelper.get_column_letter(gid, "alt_ign_col")
        if alt_col:
            writes[alt_col] = alt_igns or ""

        pronouns_col = await SheetIntegrationHelper.get_column_letter(gid, "pronouns_col")
        if pronouns_col:
            writes[pronouns_col] = pronouns or ""

        if target_row:
            # Write to existing formatted row using batch update
            updates = [(f"{col}{target_row}", val) for col, val in writes.items()]
            success = await apply_sheet_updates(sheet, updates)
            if not success:
                raise SheetsError("Failed to update user data in batch")
            row = target_row
        else:
            # Append new row using optimized append
            # Convert writes dict to ordered list based on column order
            from integrations.sheet_optimizer import SheetDataOptimizer
            max_idx = max([col_to_index(col) for col in writes.keys()])
            row_vals = [""] * max_idx

            for col, val in writes.items():
                row_vals[col_to_index(col) - 1] = val

            success = await SheetDataOptimizer.append_row_batch(sheet, row_vals, max_idx)
            if not success:
                raise SheetsError("Failed to append new row")

            # Get new row number by fetching just the discord column
            discord_column_indexes = {"discord_idx": dc_idx}
            discord_data = await fetch_required_columns(sheet, discord_column_indexes, hline, maxp + 10)
            discord_vals = discord_data.get("discord_idx", [])
            row = len([v for v in discord_vals if v.strip()]) + hline

        # Update cache
        sheet_cache["users"][discord_tag] = (
            row, ign, True, False, team_name or "", alt_igns or "", pronouns or ""
        )

        logger.info(f"Registered new user {discord_tag} as {ign} in row {row}")
        return row

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to find or register user {discord_tag}: {e}")


async def unregister_user(
        discord_tag: str,
        guild_id: str | None = None
) -> bool:
    """
    Completely remove user from sheet with proper error handling.
    """
    if not discord_tag:
        raise ValueError("Discord tag is required")

    try:
        async with cache_lock:
            user_data = sheet_cache["users"].get(discord_tag)

        if not user_data:
            logger.info(f"User {discord_tag} not found in cache for unregistration")
            return False

        row, _ign, _reg, _ci, _team, _alt, _pronouns = user_data
        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        
        # Get column mappings
        from integrations.sheet_detector import get_column_mapping
        col_mapping = await get_column_mapping(gid)
        
        # FIX: await the async function
        sheet = await get_sheet_for_guild(gid, "GAL Database")

        # Verify user is still in the sheet at expected location
        if not col_mapping.discord_column:
            raise SheetsError("Discord column not found in sheet configuration")
            
        try:
            cell = await retry_until_successful(sheet.acell, f"{col_mapping.discord_column}{row}")
            if cell.value.strip() != discord_tag:
                logger.warning(f"User {discord_tag} not found at expected row {row}")
                return False
        except Exception as e:
            raise SheetsError(f"Failed to verify user location: {e}")

        # Clear all user data using column mappings
        clear_operations = [
            (col_mapping.discord_column, ""),
            (col_mapping.ign_column, ""),
            (col_mapping.pronouns_column, ""),
            (col_mapping.alt_ign_column, ""),
            (col_mapping.registered_column, False),
            (col_mapping.checkin_column, False)
        ]

        if mode == "doubleup" and col_mapping.team_column:
            clear_operations.append((col_mapping.team_column, ""))

        # Execute all clear operations
        for col, value in clear_operations:
            try:
                await retry_until_successful(
                    sheet.update_acell,
                    f"{col}{row}",
                    value
                )
            except Exception as e:
                logger.error(f"Failed to clear {col} for user {discord_tag}: {e}")
                # Continue with other operations

        # Remove from cache
        async with cache_lock:
            sheet_cache["users"].pop(discord_tag, None)

        logger.info(f"Successfully unregistered user {discord_tag}")
        return True

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to unregister user {discord_tag}: {e}")


async def mark_checked_in_async(
        discord_tag: str,
        guild_id: str | None = None
) -> bool:
    """
    Mark user as checked in with proper validation.
    """
    return await _update_checkin_status(discord_tag, True, guild_id)


async def unmark_checked_in_async(
        discord_tag: str,
        guild_id: str | None = None
) -> bool:
    """
    Mark user as not checked in.
    """
    return await _update_checkin_status(discord_tag, False, guild_id)


async def _update_checkin_status(
        discord_tag: str,
        checked_in: bool,
        guild_id: str | None = None
) -> bool:
    """
    Internal function to update check-in status.
    """
    if not discord_tag:
        raise ValueError("Discord tag is required")

    try:
        async with cache_lock:
            user_data = sheet_cache["users"].get(discord_tag)

        if not user_data:
            logger.info(f"User {discord_tag} not found for check-in update")
            return False

        row, ign, reg, current_ci, team, alt, pronouns = user_data

        # Must be registered to check in
        if not reg:
            logger.info(f"User {discord_tag} not registered, cannot update check-in status")
            return False

        # Check if already in desired state
        is_currently_checked_in = str(current_ci).upper() == "TRUE"
        if is_currently_checked_in == checked_in:
            logger.debug(f"User {discord_tag} already in desired check-in state: {checked_in}")
            return True

        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        sheet = await get_sheet_for_guild(gid, "GAL Database")

        # Get checkin column using helper
        checkin_col = await SheetIntegrationHelper.get_column_letter(gid, "checkin_col")
        if not checkin_col:
            raise SheetsError(f"Check-in column not configured for guild {gid}")

        # Update sheet
        await retry_until_successful(
            sheet.update_acell,
            f"{checkin_col}{row}",
            checked_in
        )

        # Update cache
        sheet_cache["users"][discord_tag] = (
            row, ign, reg, checked_in, team, alt, pronouns
        )

        action = "checked in" if checked_in else "checked out"
        logger.info(f"User {discord_tag} successfully {action}")
        return True

    except Exception as e:
        if isinstance(e, (SheetsError, ValueError)):
            raise
        raise SheetsError(f"Failed to update check-in status for {discord_tag}: {e}")


async def reset_registered_roles_and_sheet(guild, channel) -> int:
    """
    Reset all registration data - clear all columns except headers.
    Also removes roles from all members to match the cleared sheet.
    """
    try:
        gid = str(guild.id)
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode)
        # FIX: await the async function
        sheet = await get_sheet_for_guild(gid, "GAL Database")

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
                logger.info(f"Cleared column {col_letter} from row {start_row} to {end_row}")

        # Clear waitlist for this guild
        from helpers.waitlist_helpers import WaitlistManager
        all_data = WaitlistManager._load_waitlist_data()
        if gid in all_data:
            all_data[gid]["waitlist"] = []
            WaitlistManager._save_waitlist_data(all_data)

        # Remove roles from ALL members who have them
        from helpers import RoleManager

        registered_role = RoleManager.get_role(guild, get_registered_role())
        checked_in_role = RoleManager.get_role(guild, get_checked_in_role())

        roles_removed = 0

        if registered_role:
            for member in registered_role.members[:]:  # Use slice to avoid modification during iteration
                try:
                    roles_to_remove = [registered_role]
                    if checked_in_role and checked_in_role in member.roles:
                        roles_to_remove.append(checked_in_role)
                    await member.remove_roles(*roles_to_remove, reason="Registration reset")
                    roles_removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove roles from {member}: {e}")

        # Also check for any orphaned checked-in roles (shouldn't happen but be safe)
        if checked_in_role:
            for member in checked_in_role.members[:]:
                if registered_role not in member.roles:  # Has checked-in but not registered
                    try:
                        await member.remove_roles(checked_in_role, reason="Registration reset - orphaned role")
                        roles_removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove orphaned checked-in role from {member}: {e}")

        # Refresh cache (this will also sync any remaining role discrepancies)
        await refresh_sheet_cache(force=True)

        # Return the number of rows that were cleared
        cleared_rows = max_players
        logger.info(f"Reset registration for {cleared_rows} rows and removed roles from {roles_removed} members")

        return cleared_rows

    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        raise SheetsError(f"Failed to reset registered roles and sheet: {e}")


async def reset_checked_in_roles_and_sheet(guild, channel) -> int:
    """
    Reset only check-in data - set checkin column to False.
    Also removes checked-in role from all members.
    """
    try:
        gid = str(guild.id)
        mode = get_event_mode_for_guild(gid)
        # FIX: await the async function
        sheet = await get_sheet_for_guild(gid, "GAL Database")

        # Get checkin column using helper
        checkin_col = await SheetIntegrationHelper.get_column_letter(gid, "checkin_col")
        if not checkin_col:
            raise SheetsError(f"Check-in column not configured for guild {gid}")

        cfg = get_sheet_settings(mode)
        header_line = cfg["header_line_num"]
        max_players = cfg.get("max_players", 32)

        # Calculate the range to clear: from header_line + 1 to header_line + max_players
        start_row = header_line + 1
        end_row = header_line + max_players

        # Build range from start_row to end_row
        if start_row <= end_row:  # Ensure valid range
            cell_range = f"{checkin_col}{start_row}:{checkin_col}{end_row}"
            cell_list = await retry_until_successful(sheet.range, cell_range)

            # Set all to boolean False
            for cell in cell_list:
                cell.value = False

            await retry_until_successful(sheet.update_cells, cell_list)

        # Remove checked-in role from ALL members who have it
        from helpers import RoleManager

        checked_in_role = RoleManager.get_role(guild, get_checked_in_role())
        roles_removed = 0

        if checked_in_role:
            for member in checked_in_role.members[:]:  # Use slice to avoid modification during iteration
                try:
                    await member.remove_roles(checked_in_role, reason="Check-in reset")
                    roles_removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove checked-in role from {member}: {e}")

        # Refresh cache (this will also sync any remaining role discrepancies)
        await refresh_sheet_cache(force=True)

        cleared_count = max_players
        logger.info(f"Reset check-in for {cleared_count} rows and removed role from {roles_removed} members")

        return cleared_count

    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        raise SheetsError(f"Failed to reset check-in roles and sheet: {e}")
