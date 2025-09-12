# config.py

import asyncio
import logging
import os
import time
from typing import Dict, Any, List

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

# Load configuration
def load_config() -> Dict[str, Any]:
    """Load and validate configuration from config.yaml."""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Validate required sections
        required_sections = ["embeds", "sheet_configuration", "channels", "roles"]
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


# Role configuration from config
def get_allowed_roles() -> List[str]:
    """Get allowed roles from config."""
    return _FULL_CFG.get("roles", {}).get("allowed_roles", ["Admin", "Moderator", "GAL Helper"])


def get_registered_role() -> str:
    """Get registered role name from config."""
    return _FULL_CFG.get("roles", {}).get("registered_role", "Registered")


def get_checked_in_role() -> str:
    """Get checked-in role name from config."""
    return _FULL_CFG.get("roles", {}).get("checked_in_role", "Checked In")


def get_angel_role() -> str:
    """Get angel role name from config."""
    return _FULL_CFG.get("roles", {}).get("angel_role", "Angels")


def get_ping_user() -> str:
    """Get ping user from config."""
    return _FULL_CFG.get("ping_user", "<@162359821100646401>")


def get_log_channel_name() -> str:
    """Get log channel name from config."""
    return _FULL_CFG.get("channels", {}).get("log_channel", "bot-log")


def get_unified_channel_name() -> str:
    """Get unified channel name from config."""
    return _FULL_CFG.get("channels", {}).get("unified_channel", "🎫registration")


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
        # Only warn if we actually have kwargs to format with
        # Skip warning for known registration placeholders that are added later
        registration_placeholders = {'spots_remaining', 'max_players', 'total_players',
                                     'max_teams', 'total_teams', 'teams_remaining'}
        if missing not in registration_placeholders and kwargs:
            logging.warning(f"Missing format key '{missing}' for embed '{key}'. Available: {list(kwargs.keys())}")
        # Return raw description without formatting if keys are missing
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


def get_sheet_url_for_environment(mode: str) -> str:
    """
    Get the appropriate sheet URL based on environment (dev/prod).
    Supports both old format (sheet_url) and new format (sheet_url_prod/dev).
    """
    is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
    dev_guild_id = os.getenv("DEV_GUILD_ID")

    settings = get_sheet_settings(mode)

    # Determine which URL to use
    if is_production:
        url_key = "sheet_url_prod"
    else:
        url_key = "sheet_url_dev"

    # Try to get the environment-specific URL
    url = settings.get(url_key)

    # Fall back to legacy "sheet_url" if new keys don't exist
    if not url:
        url = settings.get("sheet_url")
        if not url:
            # If no URL found at all, raise error
            raise ValueError(f"No sheet URL found for mode {mode} (checked {url_key} and sheet_url)")

    # Only log once per unique mode+env combination within a time window
    cache_key = f"{mode}_{url_key}"
    now = time.time()

    # Use a simple in-memory cache to prevent duplicate logs
    if not hasattr(get_sheet_url_for_environment, "_log_cache"):
        get_sheet_url_for_environment._log_cache = {}

    last_logged = get_sheet_url_for_environment._log_cache.get(cache_key, 0)
    if now - last_logged > 60:  # Only log once per minute per mode+env
        logging.info(f"Using {'production' if is_production else 'development'} sheet for mode {mode}")
        get_sheet_url_for_environment._log_cache[cache_key] = now

    return url


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
            for subcommand in ["toggle", "event", "registeredlist", "reminder", "cache", "config",
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

    # Check required embed keys (basic ones only)
    required_embeds = [
        "permission_denied", "error"
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

        # Check for URLs (either format)
        has_urls = ("sheet_url_prod" in mode_config or
                    "sheet_url_dev" in mode_config or
                    "sheet_url" in mode_config)

        if not has_urls:
            errors.append(f"Missing sheet URLs for {mode} mode")

        # Check essential fields
        essential = ["header_line_num", "max_players", "discord_col",
                     "ign_col", "registered_col", "checkin_col"]
        if mode == "doubleup":
            essential.append("team_col")

        missing = [f for f in essential if f not in mode_config]
        if missing:
            errors.append(f"Missing fields in {mode}: {missing}")

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)


def merge_config_on_deployment():
    """
    Merge new config keys from default without overwriting user customizations.
    Called during bot startup to ensure all required keys exist.
    """
    import os

    # Only run in production
    if os.getenv("RAILWAY_ENVIRONMENT_NAME") != "production":
        return

    try:
        # Load current user config
        with open("config.yaml", "r", encoding="utf-8") as f:
            user_config_text = f.read()

        # Parse to check structure
        import yaml
        user_config = yaml.safe_load(user_config_text)

        # Define required keys with their default values
        required_keys = {
            "cache_refresh_seconds": 600,
            "current_mode": "doubleup"
        }

        # Check and add missing root keys
        modified = False
        for key, default_value in required_keys.items():
            if key not in user_config:
                user_config[key] = default_value
                modified = True
                logging.info(f"Added missing config key: {key} = {default_value}")

        # Ensure embed placeholders exist for registration
        if "embeds" in user_config and "registration" in user_config["embeds"]:
            reg_desc = user_config["embeds"]["registration"].get("description", "")
            # Check if placeholders are missing
            if "{spots_remaining}" not in reg_desc and "{max_players}" not in reg_desc:
                # Add capacity line if completely missing
                if "Capacity:" not in reg_desc:
                    new_desc = reg_desc.rstrip()
                    if not new_desc.endswith("\n"):
                        new_desc += "\n"
                    new_desc += "\n📊 **Capacity:** {spots_remaining} of {max_players} spots available\n"
                    user_config["embeds"]["registration"]["description"] = new_desc
                    modified = True
                    logging.info("Added capacity placeholders to registration embed")

        # Save if modified
        if modified:
            # Use single backup file
            import shutil
            shutil.copy("config.yaml", "config_backup_latest.yaml")

            # Write merged config
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logging.info("Config updated with new required keys, backup saved as config_backup_latest.yaml")

            # Reload the config in memory
            global _FULL_CFG, EMBEDS_CFG, SHEET_CONFIG
            _FULL_CFG = load_config()
            EMBEDS_CFG = _FULL_CFG.get("embeds", {})
            SHEET_CONFIG = _FULL_CFG.get("sheet_configuration", {})

    except Exception as e:
        logging.error(f"Failed to merge config on deployment: {e}")
        # Don't crash the bot, just continue with existing config


# Validate configuration on import
validate_configuration()

# Merge any new required keys on production deployment
merge_config_on_deployment()

logging.info("Configuration loaded and validated successfully")
