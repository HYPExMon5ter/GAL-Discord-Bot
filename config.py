# config.py

import asyncio
import logging
import os
from typing import Dict, Any

import aiohttp
import discord
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==========================================
# ENVIRONMENT VARIABLE VALIDATION
# ==========================================

# Discord bot token - required for authentication
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Optional API keys and services
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Discord application ID - required for slash commands
APPLICATION_ID = os.getenv("APPLICATION_ID")
if not APPLICATION_ID:
    raise ValueError("APPLICATION_ID environment variable is required")

# Validate APPLICATION_ID format
try:
    int(APPLICATION_ID)
except ValueError:
    raise ValueError("APPLICATION_ID must be a valid integer")


# ==========================================
# BOT CONSTANTS CONFIGURATION
# ==========================================

class BotConstants:
    """Centralized bot configuration constants for easy maintenance."""

    # Discord role names used by the bot
    ALLOWED_ROLES = ["Admin", "Moderator", "GAL Helper"]  # Roles that can use staff commands
    REGISTERED_ROLE = "Registered"  # Role given to registered users
    CHECKED_IN_ROLE = "Checked In"  # Role given to checked-in users
    ANGEL_ROLE = "Angels"  # Role for registration access

    # Discord channel names used by the bot
    CHECK_IN_CHANNEL = "✔check-in"  # Check-in channel name
    REGISTRATION_CHANNEL = "🎫registration"  # Registration channel name
    LOG_CHANNEL_NAME = "bot-log"  # Bot logging channel name

    # Notification settings
    PING_USER = "<@162359821100646401>"  # User ID to ping for critical errors

    # Cache and refresh settings
    CACHE_REFRESH_SECONDS = 600  # Cache refresh interval (10 minutes)

    # Test guild configuration
    TEST_GUILD_ID = "1385739351505240074"  # Guild ID that uses test sheets


# Legacy constants for backward compatibility
# These allow existing code to work without changes
ALLOWED_ROLES = BotConstants.ALLOWED_ROLES
CHECK_IN_CHANNEL = BotConstants.CHECK_IN_CHANNEL
REGISTRATION_CHANNEL = BotConstants.REGISTRATION_CHANNEL
CHECKED_IN_ROLE = BotConstants.CHECKED_IN_ROLE
REGISTERED_ROLE = BotConstants.REGISTERED_ROLE
ANGEL_ROLE = BotConstants.ANGEL_ROLE
LOG_CHANNEL_NAME = BotConstants.LOG_CHANNEL_NAME
PING_USER = BotConstants.PING_USER
CACHE_REFRESH_SECONDS = BotConstants.CACHE_REFRESH_SECONDS


# ==========================================
# CONFIGURATION FILE LOADING
# ==========================================

def load_config() -> Dict[str, Any]:
    """
    Load and validate configuration from config.yaml.
    """
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Validate required sections exist
        required_sections = ["embeds", "sheet_configuration"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate sheet configuration modes
        sheet_config = config["sheet_configuration"]
        required_modes = ["normal", "doubleup"]
        for mode in required_modes:
            if mode not in sheet_config:
                raise ValueError(f"Missing sheet configuration for mode: {mode}")

        return config

    except FileNotFoundError:
        raise FileNotFoundError("config.yaml file not found")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config.yaml: {e}")


# Load main configuration data
_FULL_CFG = load_config()
EMBEDS_CFG = _FULL_CFG.get("embeds", {})
SHEET_CONFIG = _FULL_CFG.get("sheet_configuration", {})


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def hex_to_color(s: str) -> discord.Color:
    """
    Convert hex color string to Discord Color object.
    """
    try:
        return discord.Color(int(s.lstrip("#"), 16))
    except (ValueError, TypeError):
        logging.warning(f"Invalid color hex: {s}, using default blue")
        return discord.Color.blurple()


def embed_from_cfg(key: str, **kwargs) -> discord.Embed:
    """
    Create Discord embed from configuration with variable substitution.
    Supports special handling for toggled embeds based on visibility state.
    """
    data = EMBEDS_CFG.get(key, {})

    # Handle missing embed configuration
    if not data:
        logging.warning(f"No embed configuration found for key: {key}")
        return discord.Embed(
            title="Configuration Error",
            description="Embed not found",
            color=discord.Color.red()
        )

    # Special handling for channel toggle embeds
    # These have different descriptions based on visibility state
    if key.endswith("_toggled") and "visible" in kwargs:
        visible = kwargs.pop("visible")
        desc_key = "description_visible" if visible else "description_hidden"
        color_key = "color_visible" if visible else "color_hidden"

        desc = data.get(desc_key, "\u200b")
        color = hex_to_color(data.get(color_key, "#000000"))
        title = data.get("title", "")

        return discord.Embed(title=title, description=desc, color=color)

    # Standard embed creation with variable substitution
    raw_title = data.get("title", "")
    title = raw_title.format(**kwargs) if raw_title else ""

    raw_desc = data.get("description", "")
    try:
        description = raw_desc.format(**kwargs) if raw_desc else "\u200b"
    except KeyError as ex:
        # Handle missing format variables gracefully
        missing = str(ex).strip("'")
        logging.warning(f"Missing format key '{missing}' for embed '{key}'. Available: {list(kwargs.keys())}")
        description = raw_desc or "\u200b"

    color = hex_to_color(data.get("color", "#3498db"))
    return discord.Embed(title=title, description=description, color=color)


def get_sheet_settings(mode: str, guild_id: str = None) -> Dict[str, Any]:
    """
    Get sheet configuration for specified mode with test/production URL selection.
    """
    if mode not in SHEET_CONFIG:
        logging.warning(f"Unknown sheet mode '{mode}', falling back to 'normal'")
        mode = "normal"

    settings = SHEET_CONFIG.get(mode, SHEET_CONFIG.get("normal", {})).copy()

    # Determine which sheet URL to use based on guild ID
    if guild_id == BotConstants.TEST_GUILD_ID:
        # Use test sheet URL for test guild
        if "test_sheet_url" in settings:
            settings["sheet_url"] = settings["test_sheet_url"]
            logging.debug(f"Using test sheet URL for guild {guild_id}")
        else:
            logging.warning(f"No test_sheet_url configured for mode {mode}, using production")
    else:
        # Use production sheet URL for all other guilds
        if "prod_sheet_url" in settings:
            settings["sheet_url"] = settings["prod_sheet_url"]
        # If no prod_sheet_url, fall back to sheet_url (backward compatibility)
        elif "sheet_url" not in settings:
            logging.error(f"No sheet URL configured for mode {mode}")

    return settings


def col_to_index(col: str) -> int:
    """
    Convert Excel column letter(s) to 1-based index.
    Supports single letters (A-Z) and multiple letters (AA, AB, etc.).
    """
    if not col or not isinstance(col, str):
        raise ValueError(f"Invalid column identifier: {col}")

    col = col.upper().strip()
    idx = 0

    # Convert each letter to its position value
    for ch in col:
        if not ch.isalpha():
            raise ValueError(f"Invalid column letter: {ch}")
        idx = idx * 26 + (ord(ch) - ord("A") + 1)

    return idx


# ==========================================
# COMMAND ID MANAGEMENT FOR HELP SYSTEM
# ==========================================

# Global storage for Discord command IDs
# Used to create clickable command links in help messages
GAL_COMMAND_IDS: Dict[str, int] = {}


class APIError(Exception):
    """Custom exception for Discord API-related errors."""
    pass


async def fetch_application_commands(bot) -> list:
    """
    Fetch application commands from Discord API with comprehensive error handling.
    """
    if not bot.application_id:
        raise APIError("Bot application ID not available")

    url = f"https://discord.com/api/v10/applications/{bot.application_id}/commands"
    headers = {"Authorization": f"Bot {bot.http.token}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    commands = await resp.json()
                    logging.info(f"Successfully fetched {len(commands)} application commands")
                    return commands
                elif resp.status == 401:
                    raise APIError("Bot token is invalid or missing permissions")
                else:
                    error_text = await resp.text()
                    raise APIError(f"API request failed with status {resp.status}: {error_text}")

    except aiohttp.ClientError as e:
        raise APIError(f"Network error fetching commands: {e}")
    except Exception as e:
        raise APIError(f"Unexpected error fetching commands: {e}")


async def update_gal_command_ids(bot) -> None:
    """
    Update GAL command IDs for help system with comprehensive error handling.
    Fetches both global and guild-specific commands for development environments.
    """
    # Clear existing command IDs
    GAL_COMMAND_IDS.clear()

    try:
        # Allow Discord API time to process command syncing
        await asyncio.sleep(2)

        # Fetch global application commands
        commands = await fetch_application_commands(bot)

        # Fetch guild-specific commands if in development mode
        dev_guild_id = os.getenv("DEV_GUILD_ID")
        if dev_guild_id:
            guild_commands_url = f"https://discord.com/api/v10/applications/{bot.application_id}/guilds/{dev_guild_id}/commands"
            headers = {"Authorization": f"Bot {bot.http.token}"}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(guild_commands_url, headers=headers) as resp:
                        if resp.status == 200:
                            guild_commands = await resp.json()
                            commands.extend(guild_commands)
                            logging.info(f"Fetched {len(guild_commands)} guild-specific commands")
                        else:
                            logging.warning(f"Failed to fetch guild commands: HTTP {resp.status}")
            except Exception as e:
                logging.warning(f"Failed to fetch guild commands: {e}")

        # Find the GAL command group and extract subcommand IDs
        gal_command = next((cmd for cmd in commands if cmd["name"] == "gal" and cmd["type"] == 1), None)

        if not gal_command:
            logging.warning("GAL command not found in application commands - this is normal on first run")
            # Set placeholder IDs for help command functionality
            default_subcommands = [
                "toggle", "event", "registeredlist", "reminder", "cache",
                "validate", "placements", "reload", "help"
            ]
            for subcommand in default_subcommands:
                GAL_COMMAND_IDS[subcommand] = 0
            return

        # Extract subcommand IDs from the GAL command group
        gal_id = int(gal_command["id"])
        subcommand_count = 0

        for option in gal_command.get("options", []):
            if option["type"] == 1:  # Subcommand type
                GAL_COMMAND_IDS[option["name"]] = gal_id
                subcommand_count += 1

        if subcommand_count > 0:
            logging.info(f"Updated {subcommand_count} GAL command IDs: {list(GAL_COMMAND_IDS.keys())}")
        else:
            logging.warning("No GAL subcommands found in command structure")

    except APIError as e:
        logging.error(f"Failed to update GAL command IDs: {e}")
    except Exception as e:
        logging.error(f"Unexpected error updating GAL command IDs: {e}")


def get_cmd_id(name: str) -> int:
    """
    Get Discord command ID for help system link generation.
    """
    return GAL_COMMAND_IDS.get(name, 0)


# ==========================================
# CONFIGURATION VALIDATION
# ==========================================

def validate_configuration() -> None:
    """
    Validate critical configuration settings to prevent runtime errors.
    Checks for required embed keys and sheet configuration completeness.
    """
    errors = []

    # Validate required embed configurations
    required_embeds = [
        # Basic bot operation embeds
        "registration", "registration_closed", "checkin", "checkin_closed",
        "permission_denied", "error", "checked_in", "checked_out",

        # Team-specific embeds for double-up mode
        "max_teams_reached", "team_full", "waitlist_added", "waitlist_registered",

        # Registration embeds
        "register_success_normal", "register_success_doubleup",
        "unregister_success", "unregister_not_registered"
    ]

    missing_embeds = [key for key in required_embeds if key not in EMBEDS_CFG]
    if missing_embeds:
        errors.append(f"Missing required embeds: {missing_embeds}")

    # Validate sheet configuration for each mode
    for mode in ["normal", "doubleup"]:
        if mode not in SHEET_CONFIG:
            errors.append(f"Missing sheet configuration for mode: {mode}")
            continue

        mode_config = SHEET_CONFIG[mode]

        # Base required fields for all modes
        required_fields = [
            "header_line_num", "max_players", "discord_col",
            "ign_col", "registered_col", "checkin_col"
        ]

        # Additional requirements for double-up mode
        if mode == "doubleup":
            required_fields.extend(["max_per_team", "team_col"])

        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in mode_config]
        if missing_fields:
            errors.append(f"Missing fields in {mode} sheet config: {missing_fields}")

        # Validate sheet URL configuration
        has_sheet_url = "sheet_url" in mode_config
        has_prod_url = "prod_sheet_url" in mode_config
        has_test_url = "test_sheet_url" in mode_config

        if not (has_sheet_url or has_prod_url):
            errors.append(f"Missing sheet URL configuration in {mode} mode (need either sheet_url or prod_sheet_url)")

    # Report all validation errors at once
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_msg)


# ==========================================
# INITIALIZATION
# ==========================================

# Validate configuration immediately on import
# This ensures problems are caught early in the startup process
validate_configuration()
logging.info("Configuration loaded and validated successfully")