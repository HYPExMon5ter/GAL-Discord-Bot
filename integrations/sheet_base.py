# integrations/sheet_base.py

import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Any, Optional, Tuple

import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import get_sheet_settings, col_to_index, get_registered_role, get_checked_in_role
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
        logging.error(f"Spreadsheet not found or access denied for guild {guild_id}")
        raise SheetsError(f"Spreadsheet not found or access denied for guild {guild_id}")
    except gspread.WorksheetNotFound:
        logging.error(f"Worksheet '{worksheet_name}' not found for guild {guild_id}")
        raise SheetsError(f"Worksheet '{worksheet_name}' not found")
    except Exception as e:
        if isinstance(e, SheetsError):
            raise
        logging.error(f"Failed to open sheet for guild {guild_id}: {e}", exc_info=True)
        raise SheetsError(f"Failed to open sheet for guild {guild_id}: {e}")


# Import utility functions to avoid circular imports
from integrations.sheet_utils import retry_until_successful, index_to_column


# Cache management
sheet_cache = {"users": {}, "last_refresh": 0}
cache_lock = asyncio.Lock()