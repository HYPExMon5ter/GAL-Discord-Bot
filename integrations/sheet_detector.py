# integrations/sheet_detector.py

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from rapidfuzz import fuzz, process

from config import get_sheet_settings, col_to_index
from core.persistence import get_event_mode_for_guild
from utils.feature_flags import sheets_refactor_enabled

# Column mapping cache file
COLUMN_CACHE_FILE = "storage/column_mappings.json"


@dataclass
class ColumnDetection:
    """Represents a detected column with confidence score."""
    column_letter: str
    column_index: int
    confidence_score: float
    detection_method: str
    header_value: str


@dataclass
class ColumnMapping:
    """Represents a complete column mapping configuration."""
    discord_column: Optional[str] = None
    ign_column: Optional[str] = None
    alt_ign_column: Optional[str] = None
    pronouns_column: Optional[str] = None
    registered_column: Optional[str] = None
    checkin_column: Optional[str] = None
    team_column: Optional[str] = None
    custom_columns: Dict[str, str] = None

    def __post_init__(self):
        if self.custom_columns is None:
            self.custom_columns = {}


class SheetColumnDetector:
    """
    Intelligent column detection system for Google Sheets.
    """

    # Detection patterns for different column types
    COLUMN_PATTERNS = {
        "discord": [
            "discord", "discord:", "discord tag", "discord name", "discord user", "discord username"
        ],
        "ign": [
            "username", "ign", "game_name", "summoner", "riot_id", "riot id",
            "game name", "summoner name", "in game name", "player name"
        ],
        "alt_ign": [
            "alt", "alternative", "alt ign", "alternative ign", "alt username", "alternative username",
            "alt usernames", "alternative usernames", "backup", "secondary", "smurf"
        ],
        "pronouns": [
            "pronouns", "prefs", "gender", "they/them", "he/him", "she/her",
            "pronoun", "preferred pronouns"
        ],
        "registered": [
            "registered", "signed", "confirmed", "status", "reg", "registration",
            "signed up", "registered status", "confirmation"
        ],
        "checkin": [
            "checkin", "checked", "present", "attendance", "ci", "check in",
            "checked in", "check-in", "arrival", "present status"
        ],
        "team": [
            "team", "squad", "group", "partner", "team name", "duo", "pair",
            "teammate", "partner name"
        ]
    }

    def __init__(self):
        self.detection_cache = {}

    async def detect_columns(self, guild_id: str, force_refresh: bool = False) -> Dict[str, ColumnDetection]:
        """
        Detect all column mappings for a guild.
        """
        if not sheets_refactor_enabled():
            logging.info(
                "Sheet column detection skipped for guild %s; feature flag disabled",
                guild_id,
            )
            return {}

        cache_key = f"{guild_id}_{get_event_mode_for_guild(guild_id)}"

        if not force_refresh and cache_key in self.detection_cache:
            return self.detection_cache[cache_key]

        try:
            # Import locally to avoid circular imports
            from integrations.sheets import get_sheet_for_guild, retry_until_successful

            # Get sheet and headers
            mode = get_event_mode_for_guild(guild_id)
            settings = get_sheet_settings(mode)
            sheet = await get_sheet_for_guild(guild_id, "GAL Database")

            header_line = settings.get("header_line_num", 1)

            # Get all headers from the sheet in a single batch operation
            from integrations.sheet_optimizer import detect_columns_optimized
            max_columns = 50  # Reasonable limit
            headers = await detect_columns_optimized(sheet, header_line, max_columns)
            logging.info(f"Fetched {len(headers)} headers using optimized detection")

            # Detect each column type
            detections = {}

            # Use config values as hints if available
            config_hints = self._get_config_hints(settings)

            for column_type, patterns in self.COLUMN_PATTERNS.items():
                if column_type == "team" and mode != "doubleup":
                    continue  # Skip team detection in normal mode

                detection = self._detect_column_type(
                    headers, patterns, column_type, config_hints.get(column_type)
                )

                if detection:
                    detections[column_type] = detection

            self.detection_cache[cache_key] = detections
            logging.info(f"Detected {len(detections)} columns for guild {guild_id}")

            return detections

        except Exception as e:
            logging.error(f"Failed to detect columns for guild {guild_id}: {e}")
            return {}

    def _detect_column_type(
        self,
        headers: List[Tuple[str, int, str]],
        patterns: List[str],
        column_type: str,
        config_hint: Optional[str] = None
    ) -> Optional[ColumnDetection]:
        """
        Detect a specific column type from headers.
        """
        # First, check if config hint matches any header
        if config_hint:
            for col_letter, col_idx, header in headers:
                if header.lower() == config_hint.lower():
                    return ColumnDetection(
                        column_letter=col_letter,
                        column_index=col_idx,
                        confidence_score=1.0,
                        detection_method="config_hint",
                        header_value=header
                    )

        # Use fuzzy matching on headers
        header_texts = [header for _, _, header in headers if header]

        if not header_texts:
            return None

        # Try each pattern
        best_match = None
        best_score = 0

        for pattern in patterns:
            result = process.extractOne(
                pattern,
                header_texts,
                scorer=fuzz.partial_ratio,
                score_cutoff=60  # Minimum confidence threshold
            )

            if result and result[1] > best_score:
                best_score = result[1]
                best_match = result

        if best_match:
            matched_header, score, _ = best_match
            # Find the corresponding column info
            for col_letter, col_idx, header in headers:
                if header == matched_header:
                    confidence = min(score / 100.0, 1.0)

                    return ColumnDetection(
                        column_letter=col_letter,
                        column_index=col_idx,
                        confidence_score=confidence,
                        detection_method="fuzzy_match",
                        header_value=header
                    )

        return None

    def _get_config_hints(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract column hints from existing config settings.
        """
        hints = {}

        mapping = {
            "discord": "discord_col",
            "ign": "ign_col",
            "alt_ign": "alt_ign_col",
            "pronouns": "pronouns_col",
            "registered": "registered_col",
            "checkin": "checkin_col",
            "team": "team_col"
        }

        for column_type, config_key in mapping.items():
            if config_key in settings:
                hints[column_type] = settings[config_key]

        return hints

    def _index_to_column(self, index: int) -> str:
        """
        Convert column index to letter (1=A, 2=B, etc.).
        """
        result = ""
        while index > 0:
            index -= 1
            result = chr(ord('A') + (index % 26)) + result
            index //= 26
        return result

    def get_confidence_level(self, score: float) -> str:
        """
        Convert confidence score to human-readable level.
        """
        if score >= 0.9:
            return "High"
        elif score >= 0.7:
            return "Medium"
        elif score >= 0.5:
            return "Low"
        else:
            return "Very Low"

    async def validate_detection(self, guild_id: str, detection: ColumnDetection) -> bool:
        """
        Validate a detection by checking sample data in the column.
        """
        try:
            # Import locally to avoid circular imports
            from integrations.sheets import get_sheet_for_guild, retry_until_successful

            mode = get_event_mode_for_guild(guild_id)
            settings = get_sheet_settings(mode)
            sheet = await get_sheet_for_guild(guild_id, "GAL Database")

            col_letter = detection.column_letter
            header_line = settings.get("header_line_num", 1)

            # Check a few sample rows for reasonable data
            sample_rows = [header_line + 1, header_line + 2, header_line + 3]

            for row in sample_rows:
                try:
                    cell = await retry_until_successful(sheet.acell, f"{col_letter}{row}")
                    value = str(cell.value).strip() if cell.value else ""

                    # Basic validation based on column type
                    if not self._validate_cell_value(detection, value):
                        return False

                except Exception:
                    continue  # Skip if we can't read a cell

            return True

        except Exception as e:
            logging.warning(f"Failed to validate detection {detection.column_letter}: {e}")
            return True  # Assume valid if we can't check

    def _validate_cell_value(self, detection: ColumnDetection, value: str) -> bool:
        """
        Validate if a cell value makes sense for the detected column type.
        """
        if not value:
            return True  # Empty values are okay

        # This is a simplified validation - could be enhanced
        if detection.column_letter in ["A", "B", "C"]:  # Common data columns
            return len(value) > 0
        elif detection.column_letter in ["F", "G", "J", "K"]:  # Boolean columns
            return value.upper() in ["TRUE", "FALSE", "YES", "NO", "1", "0", ""]

        return True


# Global detector instance
detector = SheetColumnDetector()


async def detect_sheet_columns(guild_id: str, force_refresh: bool = False) -> Dict[str, ColumnDetection]:
    """
    Convenience function to detect columns for a guild.
    """
    return await detector.detect_columns(guild_id, force_refresh)


async def get_column_mapping(guild_id: str, force_redetect: bool = False) -> ColumnMapping:
    """
    Get the complete column mapping for a guild, using cache when available.
    
    Args:
        guild_id: Guild ID
        force_redetect: If True, bypass cache and re-detect columns
    """
    # Check file cache first (unless force redetect)
    if not force_redetect:
        cached = await load_cached_column_mapping(guild_id)
        if cached:
            return cached
    
    # Not in cache or force redetect - try persistence cache
    from core.persistence import get_guild_data

    guild_data = get_guild_data(guild_id)
    saved_mapping = guild_data.get("column_mapping")

    if saved_mapping:
        return ColumnMapping(**saved_mapping)

    # Fall back to detection
    detections = await detect_sheet_columns(guild_id)

    mapping = ColumnMapping()

    if "discord" in detections:
        mapping.discord_column = detections["discord"].column_letter
    if "ign" in detections:
        mapping.ign_column = detections["ign"].column_letter
    if "alt_ign" in detections:
        mapping.alt_ign_column = detections["alt_ign"].column_letter
    if "pronouns" in detections:
        mapping.pronouns_column = detections["pronouns"].column_letter
    if "registered" in detections:
        mapping.registered_column = detections["registered"].column_letter
    if "checkin" in detections:
        mapping.checkin_column = detections["checkin"].column_letter
    if "team" in detections:
        mapping.team_column = detections["team"].column_letter

    return mapping


async def load_cached_column_mapping(guild_id: str) -> Optional[ColumnMapping]:
    """Load column mapping from file cache."""
    try:
        if not os.path.exists(COLUMN_CACHE_FILE):
            return None
            
        with open(COLUMN_CACHE_FILE, 'r') as f:
            data = json.load(f)
            
        if guild_id not in data:
            return None
            
        cached = data[guild_id]
        mapping = ColumnMapping()
        mapping.discord_column = cached.get("discord_column")
        mapping.ign_column = cached.get("ign_column")
        mapping.pronouns_column = cached.get("pronouns_column")
        mapping.alt_ign_column = cached.get("alt_ign_column")
        mapping.registered_column = cached.get("registered_column")
        mapping.checkin_column = cached.get("checkin_column")
        mapping.team_column = cached.get("team_column")
        
        # Verify we have required columns
        if not mapping.discord_column or not mapping.ign_column:
            logging.warning(f"Cached mapping for guild {guild_id} missing required columns")
            return None
        
        logging.info(f"✅ Loaded cached column mapping for guild {guild_id}")
        return mapping
        
    except Exception as e:
        logging.warning(f"Failed to load cached column mapping for guild {guild_id}: {e}")
        return None


async def save_cached_column_mapping(guild_id: str, mapping: ColumnMapping, sheet_url: str):
    """Save column mapping to file cache."""
    try:
        # Ensure storage directory exists
        Path("storage").mkdir(exist_ok=True)
        
        # Load existing data
        data = {}
        if os.path.exists(COLUMN_CACHE_FILE):
            with open(COLUMN_CACHE_FILE, 'r') as f:
                data = json.load(f)
        
        # Update with new mapping
        data[guild_id] = {
            "discord_column": mapping.discord_column,
            "ign_column": mapping.ign_column,
            "pronouns_column": mapping.pronouns_column,
            "alt_ign_column": mapping.alt_ign_column,
            "registered_column": mapping.registered_column,
            "checkin_column": mapping.checkin_column,
            "team_column": mapping.team_column,
            "last_updated": datetime.utcnow().isoformat(),
            "sheet_url": sheet_url
        }
        
        # Write back to file
        with open(COLUMN_CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        logging.info(f"✅ Saved cached column mapping for guild {guild_id}")
        
    except Exception as e:
        logging.error(f"Failed to save cached column mapping for guild {guild_id}: {e}")


async def clear_cached_column_mapping(guild_id: str):
    """Clear cached column mapping (for /gal cache command)."""
    try:
        if not os.path.exists(COLUMN_CACHE_FILE):
            return
            
        with open(COLUMN_CACHE_FILE, 'r') as f:
            data = json.load(f)
        
        if guild_id in data:
            del data[guild_id]
            
        with open(COLUMN_CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        logging.info(f"✅ Cleared cached column mapping for guild {guild_id}")
        
    except Exception as e:
        logging.error(f"Failed to clear cached column mapping for guild {guild_id}: {e}")


async def save_column_mapping(guild_id: str, mapping: ColumnMapping) -> None:
    """
    Save column mapping to persistence.
    """
    from core.persistence import update_guild_data

    mapping_dict = {
        "discord_column": mapping.discord_column,
        "ign_column": mapping.ign_column,
        "alt_ign_column": mapping.alt_ign_column,
        "pronouns_column": mapping.pronouns_column,
        "registered_column": mapping.registered_column,
        "checkin_column": mapping.checkin_column,
        "team_column": mapping.team_column,
        "custom_columns": mapping.custom_columns
    }

    update_guild_data(guild_id, {"column_mapping": mapping_dict})
    
    # Also save to file cache for persistence across restarts
    mode = get_event_mode_for_guild(guild_id)
    cfg = get_sheet_settings(mode)
    sheet_url = cfg.get("sheet_url_dev") or cfg.get("sheet_url_prod")
    await save_cached_column_mapping(guild_id, mapping, sheet_url)
    
    logging.info(f"Saved column mapping for guild {guild_id}")


async def ensure_column_mappings_initialized(guild_id: str) -> bool:
    """
    Ensure column mappings are detected and saved for a guild.
    Returns True if mappings exist or were created successfully.
    """
    # Check if mappings already exist
    existing_mapping = await get_column_mapping(guild_id)
    if existing_mapping and existing_mapping.discord_column:
        logging.info(f"Column mappings already exist for guild {guild_id}")
        return True
    
    logging.info(f"Detecting column mappings for guild {guild_id}")
    
    # Detect columns from sheet
    detections = await detect_sheet_columns(guild_id, force_refresh=True)
    
    if not detections:
        logging.error(f"Failed to detect columns for guild {guild_id}")
        return False
    
    # Create mapping from detections
    mapping = ColumnMapping()
    if "discord" in detections:
        mapping.discord_column = detections["discord"].column_letter
    if "ign" in detections:
        mapping.ign_column = detections["ign"].column_letter
    if "registered" in detections:
        mapping.registered_column = detections["registered"].column_letter
    if "checkin" in detections:
        mapping.checkin_column = detections["checkin"].column_letter
    if "team" in detections:
        mapping.team_column = detections["team"].column_letter
    if "alt_ign" in detections:
        mapping.alt_ign_column = detections["alt_ign"].column_letter
    if "pronouns" in detections:
        mapping.pronouns_column = detections["pronouns"].column_letter
    
    # Save the mapping
    await save_column_mapping(guild_id, mapping)
    
    logging.info(f"Column mappings saved for guild {guild_id}: "
                f"discord={mapping.discord_column}, ign={mapping.ign_column}, "
                f"registered={mapping.registered_column}")
    
    return True
