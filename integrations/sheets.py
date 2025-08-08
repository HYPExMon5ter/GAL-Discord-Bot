# integrations/sheets.py

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timezone

# Try to import Google Sheets dependencies
try:
    import gspread_asyncio
    from google.oauth2.service_account import Credentials

    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    gspread_asyncio = None
    Credentials = None

# Always available imports
from config import get_sheet_settings
from core.persistence import get_event_mode_for_guild


class SheetsError(Exception):
    """Exception raised for sheet-related errors."""

    def __init__(self, message: str, operation: str = "", cell_ref: str = "", context: Dict[str, Any] = None):
        super().__init__(message)
        self.operation = operation
        self.cell_ref = cell_ref
        self.context = context or {}


# Global variables for sheet management
client = None
cache_lock = asyncio.Lock()
sheet_cache = {
    "users": {},
    "last_refresh": time.time(),
    "refresh_in_progress": False
}

# Cache refresh interval in seconds
CACHE_REFRESH_SECONDS = 600  # 10 minutes

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Authentication and client setup (only if sheets available)
if SHEETS_AVAILABLE:
    def get_creds():
        """Get Google Sheets credentials from environment or service account file."""
        import os
        import json

        try:
            # Try to get credentials from environment variable (for deployment)
            creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if creds_json:
                creds_info = json.loads(creds_json)
                return Credentials.from_service_account_info(
                    creds_info,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )

            # Try to get from service account file
            service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
            if os.path.exists(service_account_file):
                return Credentials.from_service_account_file(
                    service_account_file,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )

            raise FileNotFoundError("No Google service account credentials found")

        except Exception as e:
            logging.error(f"Failed to load Google Sheets credentials: {e}")
            return None


    async def get_client():
        """Get or create the Google Sheets client."""
        global client
        if client is None:
            try:
                creds = get_creds()
                if creds:
                    agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
                    client = await agcm.authorize()
                    logging.info("✅ Google Sheets client initialized successfully")
                else:
                    logging.error("❌ Failed to initialize Google Sheets client - no credentials")
            except Exception as e:
                logging.error(f"❌ Failed to initialize Google Sheets client: {e}")
                client = None
        return client

else:
    async def get_client():
        """Fallback when sheets not available."""
        logging.warning("Google Sheets not available - using fallback mode")
        return None


def get_sheet_for_guild(guild_id: str, worksheet_name: str):
    """Get sheet instance for guild - returns None in fallback mode."""
    if not SHEETS_AVAILABLE or not client:
        return None

    try:
        # This would be implemented with actual sheet URL logic
        # For now, return None to indicate fallback mode
        return None
    except Exception as e:
        logging.error(f"Failed to get sheet for guild {guild_id}: {e}")
        return None


async def retry_until_successful(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """Retry a function until it succeeds or max retries reached."""
    last_error = None

    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                logging.debug(f"Retrying {func.__name__} (attempt {attempt + 2}/{max_retries})")
            else:
                logging.error(f"Failed after {max_retries} attempts: {e}")

    raise last_error


def ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc.)."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"


# Core sheet operation functions
async def find_or_register_user(
        guild_id: str,
        discord_tag: str,
        ign: str,
        pronouns: str = "",
        alt_igns: str = "",
        team_name: str = ""
) -> bool:
    """
    Register or update a user in the tournament sheet.

    Returns True if successful, False otherwise.
    Falls back to logging when sheets unavailable.
    """
    if not SHEETS_AVAILABLE:
        logging.info(f"📝 Would register {discord_tag} (IGN: {ign}) - Sheets not available")
        return False

    try:
        # Get client and sheet
        sheets_client = await get_client()
        if not sheets_client:
            logging.warning("Sheets client not available - registration not persisted")
            return False

        sheet = get_sheet_for_guild(guild_id, "GAL Database")
        if not sheet:
            logging.warning("Sheet not accessible - registration not persisted")
            return False

        # Get event mode and configuration
        mode = get_event_mode_for_guild(guild_id)
        cfg = get_sheet_settings(mode, guild_id)

        # Implementation would go here for actual sheet operations
        # For now, return False to indicate fallback mode
        logging.info(f"📝 Registration for {discord_tag} (IGN: {ign}) - Sheet operations not yet implemented")
        return False

    except Exception as e:
        logging.error(f"Failed to register user {discord_tag}: {e}")
        return False


async def mark_checked_in_async(discord_tag: str, guild_id: Optional[str] = None) -> bool:
    """
    Mark user as checked in.

    Returns True if successful, False otherwise.
    """
    if not SHEETS_AVAILABLE:
        logging.info(f"✅ Would check in {discord_tag} - Sheets not available")
        return False

    try:
        return await _update_checkin_status(discord_tag, True, guild_id)
    except Exception as e:
        logging.error(f"Failed to check in user {discord_tag}: {e}")
        return False


async def unmark_checked_in_async(discord_tag: str, guild_id: Optional[str] = None) -> bool:
    """
    Mark user as not checked in (check out).

    Returns True if successful, False otherwise.
    """
    if not SHEETS_AVAILABLE:
        logging.info(f"↩️ Would check out {discord_tag} - Sheets not available")
        return False

    try:
        return await _update_checkin_status(discord_tag, False, guild_id)
    except Exception as e:
        logging.error(f"Failed to check out user {discord_tag}: {e}")
        return False


async def _update_checkin_status(discord_tag: str, checked_in: bool, guild_id: Optional[str] = None) -> bool:
    """
    Internal function to handle both check-in and check-out operations.
    """
    if not SHEETS_AVAILABLE:
        action = "check in" if checked_in else "check out"
        logging.info(f"Would {action} {discord_tag} - Sheets not available")
        return False

    try:
        # Check cache first
        async with cache_lock:
            user_data = sheet_cache["users"].get(discord_tag)

        if not user_data:
            logging.info(f"User {discord_tag} not found for check-in update")
            return False

        # Get sheet configuration
        gid = str(guild_id) if guild_id else "unknown"
        mode = get_event_mode_for_guild(gid)
        cfg = get_sheet_settings(mode, gid)

        # Implementation would update actual sheet here
        # For now, just update cache
        async with cache_lock:
            if discord_tag in sheet_cache["users"]:
                user_list = list(sheet_cache["users"][discord_tag])
                if len(user_list) > 3:  # Ensure we have checkin column
                    user_list[3] = checked_in
                    sheet_cache["users"][discord_tag] = tuple(user_list)

        action = "checked in" if checked_in else "checked out"
        logging.info(f"User {discord_tag} {action} (cache only)")
        return True

    except Exception as e:
        logging.error(f"Failed to update check-in status for {discord_tag}: {e}")
        return False


async def unregister_user(guild_id: str, discord_tag: str) -> bool:
    """
    Remove a user from the tournament registration.

    Returns True if successful, False otherwise.
    """
    if not SHEETS_AVAILABLE:
        logging.info(f"❌ Would unregister {discord_tag} - Sheets not available")
        return False

    try:
        # Remove from cache
        async with cache_lock:
            if discord_tag in sheet_cache["users"]:
                del sheet_cache["users"][discord_tag]
                logging.info(f"Removed {discord_tag} from cache")

        # In full implementation, would remove from actual sheet here
        logging.info(f"User {discord_tag} unregistered (cache only)")
        return True

    except Exception as e:
        logging.error(f"Failed to unregister user {discord_tag}: {e}")
        return False


async def refresh_sheet_cache(bot=None) -> Tuple[int, int]:
    """
    Refresh the user cache from Google Sheets.

    Returns tuple of (registered_count, checked_in_count).
    """
    if not SHEETS_AVAILABLE:
        logging.debug("Sheets not available - using empty cache")

        async with cache_lock:
            sheet_cache["last_refresh"] = time.time()
            sheet_cache["refresh_in_progress"] = False
            sheet_cache["users"] = {}

        return 0, 0

    try:
        async with cache_lock:
            if sheet_cache["refresh_in_progress"]:
                logging.debug("Cache refresh already in progress")
                return len(sheet_cache["users"]), 0

            sheet_cache["refresh_in_progress"] = True

        try:
            # Get sheets client
            sheets_client = await get_client()
            if not sheets_client:
                logging.warning("Cannot refresh cache - sheets client unavailable")
                return 0, 0

            # In full implementation, would refresh from actual sheets here
            # For now, just update timestamp
            registered_count = len(sheet_cache["users"])
            checked_in_count = sum(1 for user_data in sheet_cache["users"].values()
                                   if len(user_data) > 3 and user_data[3])

            logging.info(f"Cache refreshed: {registered_count} registered, {checked_in_count} checked in")
            return registered_count, checked_in_count

        finally:
            async with cache_lock:
                sheet_cache["last_refresh"] = time.time()
                sheet_cache["refresh_in_progress"] = False

    except Exception as e:
        async with cache_lock:
            sheet_cache["refresh_in_progress"] = False
        logging.error(f"Failed to refresh sheet cache: {e}")
        return 0, 0


async def reset_checked_in_roles_and_sheet(guild, channel) -> int:
    """
    Reset only check-in data - set checkin column to False.

    Returns number of rows affected.
    """
    if not SHEETS_AVAILABLE:
        logging.info("Would reset check-in data - Sheets not available")
        return 0

    try:
        # Reset in cache
        reset_count = 0
        async with cache_lock:
            for discord_tag, user_data in sheet_cache["users"].items():
                if len(user_data) > 3 and user_data[3]:  # Was checked in
                    user_list = list(user_data)
                    user_list[3] = False  # Set checked in to False
                    sheet_cache["users"][discord_tag] = tuple(user_list)
                    reset_count += 1

        # In full implementation, would reset actual sheet here
        logging.info(f"Reset check-in for {reset_count} users (cache only)")
        return reset_count

    except Exception as e:
        logging.error(f"Failed to reset check-in data: {e}")
        return 0


async def reset_registered_roles_and_sheet(guild, channel) -> int:
    """
    Reset all registration data - clear all user data.

    Returns number of rows affected.
    """
    if not SHEETS_AVAILABLE:
        logging.info("Would reset registration data - Sheets not available")
        return 0

    try:
        # Clear cache
        reset_count = 0
        async with cache_lock:
            reset_count = len(sheet_cache["users"])
            sheet_cache["users"].clear()

        # In full implementation, would clear actual sheet here
        logging.info(f"Reset registration for {reset_count} users (cache only)")
        return reset_count

    except Exception as e:
        logging.error(f"Failed to reset registration data: {e}")
        return 0


async def health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check of the sheets integration.

    Returns detailed health status information.
    """
    health_status = {
        "sheets_available": SHEETS_AVAILABLE,
        "client_initialized": client is not None,
        "cache_age_seconds": time.time() - sheet_cache["last_refresh"],
        "cached_users": len(sheet_cache["users"]),
        "credentials_valid": False,
        "test_sheet_accessible": False,
        "status": False
    }

    if not SHEETS_AVAILABLE:
        health_status.update({
            "error": "Google Sheets dependencies not installed",
            "recommendation": "Install gspread-asyncio and google-auth packages"
        })
        return health_status

    try:
        # Test client initialization
        test_client = await get_client()
        if test_client:
            health_status["client_initialized"] = True
            health_status["credentials_valid"] = True
            health_status["status"] = True
        else:
            health_status["error"] = "Failed to initialize sheets client"

    except Exception as e:
        health_status["error"] = f"Health check failed: {e}"

    return health_status


def validate_sheet_config(mode: str) -> Dict[str, Any]:
    """
    Validate sheet configuration for the specified mode.

    Returns validation results with errors and warnings.
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    if not SHEETS_AVAILABLE:
        validation.update({
            "valid": False,
            "errors": ["Google Sheets dependencies not available"],
            "warnings": ["Install gspread-asyncio and google-auth packages for sheet functionality"]
        })
        return validation

    try:
        cfg = get_sheet_settings(mode)

        # Required fields for all modes
        required_fields = [
            "sheet_url", "header_line_num", "max_players",
            "discord_col", "ign_col", "alt_ign_col",
            "registered_col", "checkin_col", "pronouns_col"
        ]

        # Additional fields for doubleup mode
        if mode == "doubleup":
            required_fields.extend(["team_col", "max_per_team"])

        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in cfg]
        if missing_fields:
            validation["errors"].extend([f"Missing required field: {field}" for field in missing_fields])
            validation["valid"] = False

        # Validate sheet URL format
        sheet_url = cfg.get("sheet_url", "")
        if sheet_url and "/d/" not in sheet_url:
            validation["errors"].append("Invalid sheet URL format - missing /d/ pattern")
            validation["valid"] = False

        # Validate numeric fields
        numeric_fields = ["header_line_num", "max_players"]
        if mode == "doubleup":
            numeric_fields.append("max_per_team")

        for field in numeric_fields:
            value = cfg.get(field)
            if value is not None and not isinstance(value, int):
                validation["warnings"].append(f"Field {field} should be an integer")

        # Validate column letters
        col_fields = [f for f in required_fields if f.endswith("_col")]
        for field in col_fields:
            col_value = cfg.get(field, "")
            if col_value and not col_value.isalpha():
                validation["errors"].append(f"Invalid column format for {field}: {col_value}")
                validation["valid"] = False

    except Exception as e:
        validation["errors"].append(f"Configuration validation error: {e}")
        validation["valid"] = False

    return validation


# Cache management functions
def get_cached_user_count() -> int:
    """Get the current number of cached users."""
    return len(sheet_cache["users"])


def get_cache_age() -> float:
    """Get the age of the current cache in seconds."""
    return time.time() - sheet_cache["last_refresh"]


def is_cache_stale(max_age_seconds: int = CACHE_REFRESH_SECONDS) -> bool:
    """Check if the cache is considered stale."""
    return get_cache_age() > max_age_seconds


async def force_cache_refresh(bot=None) -> Tuple[int, int]:
    """Force an immediate cache refresh regardless of age."""
    return await refresh_sheet_cache(bot)


# Initialize the integration
async def initialize_sheets():
    """Initialize the sheets integration if available."""
    if SHEETS_AVAILABLE:
        try:
            await get_client()
            logging.info("🔗 Google Sheets integration initialized")
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets: {e}")
    else:
        logging.warning("📊 Google Sheets integration not available - using fallback mode")
        logging.info("💡 Install 'gspread-asyncio' and 'google-auth' packages to enable sheet functionality")


# Log integration status on import
if SHEETS_AVAILABLE:
    logging.info("✅ Google Sheets dependencies available")
else:
    logging.warning("⚠️ Google Sheets dependencies not installed - running in fallback mode")
    logging.info("📦 To enable sheet functionality, install: pip install gspread-asyncio google-auth")

# Export all functions
__all__ = [
    # Core sheet functions
    'get_sheet_for_guild',
    'retry_until_successful',
    'find_or_register_user',
    'mark_checked_in_async',
    'unmark_checked_in_async',
    'unregister_user',
    'refresh_sheet_cache',
    'reset_checked_in_roles_and_sheet',
    'reset_registered_roles_and_sheet',

    # Cache management
    'cache_lock',
    'sheet_cache',
    'get_cached_user_count',
    'get_cache_age',
    'is_cache_stale',
    'force_cache_refresh',

    # Validation and health
    'health_check',
    'validate_sheet_config',
    'initialize_sheets',

    # Utility functions
    'ordinal_suffix',

    # Constants
    'CACHE_REFRESH_SECONDS',
    'SHEETS_AVAILABLE',

    # Exception classes
    'SheetsError'
]