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

DATABASE_URL = os.getenv("DATABASE_URL")
APPLICATION_ID = os.getenv("APPLICATION_ID")

if not APPLICATION_ID:
    raise ValueError("APPLICATION_ID environment variable is required")


# Load configuration
def load_config() -> Dict[str, Any]:
    """Load and validate configuration from config.yaml."""
    try:
        # Look for config.yaml relative to this file's location
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
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


def get_live_graphics_settings() -> Dict[str, str]:
    """Get live graphics dashboard configuration settings."""
    return {
        "base_url": os.getenv("LIVE_GFX_BASE_URL", "http://localhost:5173"),
        "token": os.getenv("LIVE_GFX_TOKEN", "supersecrettoken")
    }


def get_ping_user() -> str:
    """Get ping user from config."""
    return _FULL_CFG.get("ping_user", "<@162359821100646401>")


def get_log_channel_name() -> str:
    """Get log channel name from config."""
    return _FULL_CFG.get("channels", {}).get("log_channel", "bot-log")


def get_unified_channel_name() -> str:
    """Get unified channel name from config."""
    return _FULL_CFG.get("channels", {}).get("unified_channel", "🎫registration")


# Onboarding configuration helpers
def get_onboard_config() -> Dict[str, Any]:
    """Get onboard configuration from config."""
    return _FULL_CFG.get("onboard", {})


def get_onboard_main_channel() -> str:
    """Get onboard main channel name from config."""
    return get_onboard_config().get("main_channel", "welcome")


def get_onboard_review_channel() -> str:
    """Get onboard review channel name from config."""
    return get_onboard_config().get("review_channel", "onboard-review")


def get_onboard_approval_role() -> str:
    """Get role to assign on onboard approval from config."""
    return get_onboard_config().get("role_on_approve", "Angels")


def onboard_embed_from_cfg(key: str, **kwargs) -> discord.Embed:
    """
    Create Discord embed from onboard configuration.
    """
    onboard_cfg = get_onboard_config()
    embed_data = onboard_cfg.get("embeds", {}).get(key, {})

    if not embed_data:
        logging.warning(f"No onboard embed configuration found for key: {key}")
        return discord.Embed(
            title="Configuration Error",
            description="Onboard embed not found",
            color=discord.Color.red()
        )

    # Get title
    raw_title = embed_data.get("title", "")
    title = raw_title.format(**kwargs) if raw_title else ""

    # Get description
    raw_desc = embed_data.get("description", "")
    try:
        description = raw_desc.format(**kwargs) if raw_desc else "\u200b"
    except KeyError as ex:
        missing = str(ex).strip("'")
        if kwargs:
            logging.warning(
                f"Missing format key '{missing}' for onboard embed '{key}'. Available: {list(kwargs.keys())}")
        description = raw_desc or "\u200b"

    # Get footer
    raw_footer = embed_data.get("footer", "")
    footer = raw_footer.format(**kwargs) if raw_footer else None

    # Get color
    color = hex_to_color(embed_data.get("color", "#3498db"))

    # Create embed
    embed = discord.Embed(title=title, description=description, color=color)
    if footer:
        embed.set_footer(text=footer)

    return embed


def hex_to_color(s: str) -> discord.Color:
    """Convert hex string to Discord Color object with Discord.py v2 constants support."""
    # First try Discord.py v2 color constants for common colors
    color_map = {
        "red": discord.Color.red(),
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "purple": discord.Color.purple(),
        "magenta": discord.Color.magenta(),
        "gold": discord.Color.gold(),
        "orange": discord.Color.orange(),
        "blurple": discord.Color.blurple(),
        "greyple": discord.Color.greyple(),
        "dark_theme": discord.Color.dark_theme(),
        "yellow": discord.Color.yellow(),
        "pink": discord.Color.brand_red(),
        "teal": discord.Color.teal(),
        "dark_red": discord.Color.dark_red(),
        "dark_blue": discord.Color.dark_blue(),
        "dark_green": discord.Color.dark_green(),
        "dark_purple": discord.Color.dark_purple(),
        "dark_magenta": discord.Color.dark_magenta(),
        "dark_gold": discord.Color.dark_gold(),
        "dark_orange": discord.Color.dark_orange(),
        "dark_teal": discord.Color.dark_teal(),
        "darker_grey": discord.Color.darker_grey(),
        "light_grey": discord.Color.light_grey()
    }

    # Check if it's a named color constant
    if s and s.lower() in color_map:
        return color_map[s.lower()]

    # Fall back to hex parsing
    try:
        return discord.Color(int(s.lstrip("#"), 16))
    except (ValueError, TypeError):
        logging.warning(f"Invalid color hex: {s}, using default blurple")
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
        # Only require essential fields - column assignments are now managed by persistence system
        essential = ["header_line_num", "max_players"]

        # Also require sheet URLs
        if "sheet_url_dev" not in mode_config:
            errors.append(f"Missing sheet_url_dev in {mode}")
        if "sheet_url_prod" not in mode_config:
            errors.append(f"Missing sheet_url_prod in {mode}")

        missing = [f for f in essential if f not in mode_config]
        if missing:
            errors.append(f"Missing fields in {mode}: {missing}")

        # Log that column assignments are now managed by persistence
        logging.info(f"[CONFIG] Column assignments for {mode} mode are now managed by persistence system")

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

# Phase 2 Integration: DAL integration
_dal_adapter = None

async def get_dal_adapter():
    """Get the DAL adapter for Phase 2 integration."""
    global _dal_adapter
    if _dal_adapter is None:
        try:
            from core.data_access.legacy_adapter import get_legacy_adapter
            _dal_adapter = await get_legacy_adapter()
            logging.info("DAL integration initialized for configuration module")
        except ImportError as e:
            logging.warning(f"DAL integration not available: {e}")
            _dal_adapter = None
    return _dal_adapter


# Phase 2: Enhanced configuration functions with DAL integration
async def get_sheet_settings_enhanced(mode: str) -> Dict[str, Any]:
    """
    Enhanced sheet settings function with DAL integration.
    Falls back to legacy system if DAL is not available.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.get_sheet_settings(mode)
    except Exception as e:
        logging.warning(f"DAL get_sheet_settings failed, falling back to legacy: {e}")
    
    # Fallback to legacy implementation
    return get_sheet_settings(mode)


async def get_embed_configuration_enhanced(embed_key: str) -> Dict[str, Any]:
    """
    Enhanced embed configuration function with DAL integration.
    Falls back to legacy system if DAL is not available.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.get_embed_configuration(embed_key)
    except Exception as e:
        logging.warning(f"DAL get_embed_configuration failed, falling back to legacy: {e}")
    
    # Fallback to legacy implementation
    return embed_from_cfg(embed_key)


async def get_role_configuration_enhanced() -> Dict[str, Any]:
    """
    Enhanced role configuration function with DAL integration.
    Falls back to legacy system if DAL is not available.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.get_role_configuration()
    except Exception as e:
        logging.warning(f"DAL get_role_configuration failed, falling back to legacy: {e}")
    
    # Fallback to legacy implementation
    return {
        "allowed_roles": get_allowed_roles(),
        "registered_role": get_registered_role(),
        "checked_in_role": get_checked_in_role()
    }


async def get_channel_configuration_enhanced() -> Dict[str, str]:
    """
    Enhanced channel configuration function with DAL integration.
    Falls back to legacy system if DAL is not available.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.get_channel_configuration()
    except Exception as e:
        logging.warning(f"DAL get_channel_configuration failed, falling back to legacy: {e}")
    
    # Fallback to legacy implementation
    return {
        "log_channel": get_log_channel_name(),
        "unified_channel": get_unified_channel_name()
    }


async def get_configuration_enhanced(key: str, default: Any = None) -> Any:
    """
    Enhanced configuration function with DAL integration.
    Falls back to legacy system if DAL is not available.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            value = await adapter.get_configuration(key)
            return value if value is not None else default
    except Exception as e:
        logging.warning(f"DAL get_configuration failed, falling back to legacy: {e}")
    
    # Fallback to legacy implementation
    if key in _FULL_CFG:
        return _FULL_CFG[key]
    return default


# Phase 2: Configuration validation with DAL integration
async def validate_configuration_enhanced() -> List[str]:
    """
    Enhanced configuration validation with DAL integration.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.validate_configuration()
    except Exception as e:
        logging.warning(f"DAL validate_configuration failed, using legacy: {e}")
    
    # Fallback to legacy implementation
    try:
        validate_configuration()
        return []
    except ValueError as e:
        return [str(e)]


# Phase 2: Configuration export with DAL integration
async def export_configuration_enhanced(guild_id: str = None) -> Dict[str, Any]:
    """
    Enhanced configuration export with DAL integration.
    """
    try:
        adapter = await get_dal_adapter()
        if adapter:
            return await adapter.export_configuration(guild_id)
    except Exception as e:
        logging.warning(f"DAL export_configuration failed, using basic export: {e}")
    
    # Fallback to basic export
    return {
        "timestamp": int(time.time()),
        "version": "1.0",
        "configuration": _FULL_CFG.copy() if not guild_id else {},
        "legacy_mode": True
    }


# Phase 2: Log DAL integration status
async def log_dal_integration_status():
    """Log the current DAL integration status."""
    adapter = await get_dal_adapter()
    if adapter:
        logging.info("Phase 2 DAL integration: ACTIVE")
    else:
        logging.info("Phase 2 DAL integration: NOT AVAILABLE - using legacy configuration")

# Schedule status check (don't await here as this is module-level)
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop and loop.is_running():
    loop.create_task(log_dal_integration_status())


logging.info("Configuration loaded and validated successfully")
