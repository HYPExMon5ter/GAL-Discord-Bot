# config.py

import asyncio
import logging
import os
from typing import Dict, Any

import aiohttp
import discord
import yaml
from dotenv import load_dotenv

load_dotenv()

# Environment variable validation
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
APPLICATION_ID = os.getenv("APPLICATION_ID")

if not APPLICATION_ID:
    raise ValueError("APPLICATION_ID environment variable is required")


# Bot constants - centralized for easier maintenance
class BotConstants:
    """Centralized bot configuration constants."""

    # Roles
    ALLOWED_ROLES = ["Admin", "Moderator", "GAL Helper"]
    REGISTERED_ROLE = "Registered"
    CHECKED_IN_ROLE = "Checked In"
    ANGEL_ROLE = "Angels"

    # Channels
    CHECK_IN_CHANNEL = "✔check-in"
    REGISTRATION_CHANNEL = "🎫registration"
    LOG_CHANNEL_NAME = "bot-log"

    # Other settings
    PING_USER = "<@162359821100646401>"
    CACHE_REFRESH_SECONDS = 600  # 10 minutes


# Legacy constants for backward compatibility
ALLOWED_ROLES = BotConstants.ALLOWED_ROLES
CHECK_IN_CHANNEL = BotConstants.CHECK_IN_CHANNEL
REGISTRATION_CHANNEL = BotConstants.REGISTRATION_CHANNEL
CHECKED_IN_ROLE = BotConstants.CHECKED_IN_ROLE
REGISTERED_ROLE = BotConstants.REGISTERED_ROLE
ANGEL_ROLE = BotConstants.ANGEL_ROLE
LOG_CHANNEL_NAME = BotConstants.LOG_CHANNEL_NAME
PING_USER = BotConstants.PING_USER
CACHE_REFRESH_SECONDS = BotConstants.CACHE_REFRESH_SECONDS


# Configuration loading with validation
def load_config() -> Dict[str, Any]:
    """Load and validate configuration from config.yaml."""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Validate required sections
        required_sections = ["embeds", "sheet_configuration"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate sheet configuration
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


# Load configuration
_FULL_CFG = load_config()
EMBEDS_CFG = _FULL_CFG.get("embeds", {})
SHEET_CONFIG = _FULL_CFG.get("sheet_configuration", {})


def hex_to_color(s: str) -> discord.Color:
    """Convert hex string to Discord Color object."""
    try:
        return discord.Color(int(s.lstrip("#"), 16))
    except (ValueError, TypeError):
        logging.warning(f"Invalid color hex: {s}, using default blue")
        return discord.Color.blurple()


def embed_from_cfg(key: str, **kwargs) -> discord.Embed:
    """
    Create Discord embed from configuration with error handling.

    Args:
        key: Configuration key for the embed
        **kwargs: Variables to format in the embed text

    Returns:
        discord.Embed: Configured embed object
    """
    data = EMBEDS_CFG.get(key, {})

    if not data:
        logging.warning(f"No embed configuration found for key: {key}")
        return discord.Embed(title="Configuration Error", description="Embed not found", color=discord.Color.red())

    # Handle toggled embeds
    if key.endswith("_toggled") and "visible" in kwargs:
        visible = kwargs.pop("visible")
        desc_key = "description_visible" if visible else "description_hidden"
        color_key = "color_visible" if visible else "color_hidden"

        desc = data.get(desc_key, "\u200b")
        color = hex_to_color(data.get(color_key, "#000000"))
        title = data.get("title", "")

        return discord.Embed(title=title, description=desc, color=color)

    # Normal embeds
    raw_title = data.get("title", "")
    title = raw_title.format(**kwargs) if raw_title else ""

    raw_desc = data.get("description", "")
    try:
        description = raw_desc.format(**kwargs) if raw_desc else "\u200b"
    except KeyError as ex:
        missing = str(ex).strip("'")
        logging.warning(f"Missing format key '{missing}' for embed '{key}'. Available: {list(kwargs.keys())}")
        description = raw_desc or "\u200b"

    color = hex_to_color(data.get("color", "#3498db"))
    return discord.Embed(title=title, description=description, color=color)


def get_sheet_settings(mode: str) -> Dict[str, Any]:
    """
    Get sheet configuration for specified mode.
    """
    if mode not in SHEET_CONFIG:
        logging.warning(f"Unknown sheet mode '{mode}', falling back to 'normal'")
        mode = "normal"

    return SHEET_CONFIG.get(mode, SHEET_CONFIG.get("normal", {}))


def col_to_index(col: str) -> int:
    """
    Convert Excel column letter(s) to 1-based index.
    """
    if not col or not isinstance(col, str):
        raise ValueError(f"Invalid column identifier: {col}")

    col = col.upper().strip()
    idx = 0
    for ch in col:
        if not ch.isalpha():
            raise ValueError(f"Invalid column letter: {ch}")
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx


# Command IDs for help system
GAL_COMMAND_IDS: Dict[str, int] = {}


class APIError(Exception):
    """Custom exception for API-related errors."""
    pass


async def fetch_application_commands(bot) -> list:
    """
    Fetch application commands.
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
                    logging.info(f"Fetched {len(commands)} application commands")
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
    Update GAL command IDs for the help command.
    """
    GAL_COMMAND_IDS.clear()

    try:
        # Wait a bit for Discord API to catch up after syncing
        await asyncio.sleep(2)

        commands = await fetch_application_commands(bot)

        # Also try fetching guild-specific commands if in dev mode
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
            except Exception as e:
                logging.warning(f"Failed to fetch guild commands: {e}")

        gal_command = next((cmd for cmd in commands if cmd["name"] == "gal" and cmd["type"] == 1), None)

        if not gal_command:
            logging.warning("GAL command not found in application commands - this is normal on first run")
            # Set placeholder IDs for help command
            for subcommand in ["toggle", "event", "registeredlist", "reminder", "cache", "validate", "placements",
                               "reload", "help"]:
                GAL_COMMAND_IDS[subcommand] = 0
            return

        gal_id = int(gal_command["id"])
        subcommand_count = 0

        for option in gal_command.get("options", []):
            if option["type"] == 1:  # Subcommand
                GAL_COMMAND_IDS[option["name"]] = gal_id
                subcommand_count += 1

        if subcommand_count > 0:
            logging.info(f"Updated {subcommand_count} GAL command IDs: {list(GAL_COMMAND_IDS.keys())}")
        else:
            logging.warning("No GAL subcommands found")

    except APIError as e:
        logging.error(f"Failed to update GAL command IDs: {e}")
    except Exception as e:
        logging.error(f"Unexpected error updating GAL command IDs: {e}")


def get_cmd_id(name: str) -> int:
    """
    Get command ID for help system.
    """
    return GAL_COMMAND_IDS.get(name, 0)


def validate_configuration() -> None:
    """Validate critical configuration settings."""
    errors = []

    # Check required embed keys
    required_embeds = [
        "registration", "registration_closed", "checkin", "checkin_closed",
        "permission_denied", "error", "checked_in", "checked_out"
    ]

    missing_embeds = [key for key in required_embeds if key not in EMBEDS_CFG]
    if missing_embeds:
        errors.append(f"Missing required embeds: {missing_embeds}")

    # Check sheet configuration
    for mode in ["normal", "doubleup"]:
        if mode not in SHEET_CONFIG:
            errors.append(f"Missing sheet configuration for mode: {mode}")
            continue

        mode_config = SHEET_CONFIG[mode]
        required_fields = ["sheet_url", "header_line_num", "max_players"]
        missing_fields = [field for field in required_fields if field not in mode_config]

        if missing_fields:
            errors.append(f"Missing fields in {mode} sheet config: {missing_fields}")

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_msg)


# Validate configuration on import
validate_configuration()
logging.info("Configuration loaded and validated successfully")