# utils/utils.py

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any, Union, Tuple

import aiohttp
import discord
from discord.ext import commands

from config import (
    ALLOWED_ROLES, ANGEL_ROLE, REGISTERED_ROLE,
    embed_from_cfg, GAL_COMMAND_IDS
)

# Import helpers with error handling
try:
    from helpers import BotLogger, ErrorHandler, ErrorCategory, ErrorSeverity
except ImportError:
    BotLogger = None
    ErrorHandler = None

    # Fallback logging
    import logging

    logging.basicConfig(level=logging.INFO)

try:
    from core.persistence import get_persisted_msg, set_persisted_msg
except ImportError:
    def get_persisted_msg(*args, **kwargs):
        return None, None


    def set_persisted_msg(*args, **kwargs):
        pass


# Exception classes
class UtilsError(Exception):
    """Base exception for utils-related errors."""
    pass


class MemberNotFoundError(UtilsError):
    """Raised when a member cannot be found."""
    pass


class ChannelOperationError(UtilsError):
    """Raised when channel operations fail."""
    pass


# Core utility functions
def has_allowed_role(member: discord.Member) -> bool:
    """Check if member has any allowed staff role."""
    if not member or not hasattr(member, 'roles'):
        return False

    return any(role.name in ALLOWED_ROLES for role in member.roles)


def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
    """Check if interaction user has allowed role."""
    if not interaction.user or not hasattr(interaction.user, 'roles'):
        return False

    return has_allowed_role(interaction.user)


async def resolve_member(guild: discord.Guild, identifier: str) -> Optional[discord.Member]:
    """
    Resolve a member from various identifier formats.

    Args:
        guild: Discord guild to search in
        identifier: Member ID, mention, username, or display name

    Returns:
        Discord member if found, None otherwise
    """
    if not guild or not identifier:
        return None

    try:
        # Try by ID first (most reliable)
        if identifier.isdigit():
            return guild.get_member(int(identifier))

        # Try mention format
        if identifier.startswith('<@') and identifier.endswith('>'):
            user_id = identifier[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            if user_id.isdigit():
                return guild.get_member(int(user_id))

        # Try username or display name
        identifier = identifier.lower()
        for member in guild.members:
            if (member.name.lower() == identifier or
                    member.display_name.lower() == identifier):
                return member

        return None

    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error resolving member '{identifier}': {e}", "UTILS")
        return None


async def toggle_persisted_channel(
        guild: discord.Guild,
        channel_name: str,
        role_name: str
) -> bool:
    """
    Toggle channel visibility for a specific role.

    Args:
        guild: Discord guild
        channel_name: Name of channel to toggle
        role_name: Name of role to toggle access for

    Returns:
        True if toggle was successful, False otherwise
    """
    try:
        # Find channel and role
        channel = discord.utils.get(guild.channels, name=channel_name)
        role = discord.utils.get(guild.roles, name=role_name)

        if not channel or not role:
            if BotLogger:
                BotLogger.warning(f"Channel '{channel_name}' or role '{role_name}' not found in {guild.name}", "UTILS")
            return False

        # Get current permissions
        overwrites = channel.overwrites_for(role)
        current_visibility = overwrites.read_messages

        # Toggle visibility
        new_visibility = not current_visibility if current_visibility is not None else True
        overwrites.read_messages = new_visibility

        # Update channel permissions
        await channel.set_permissions(role, overwrite=overwrites)

        action = "opened" if new_visibility else "closed"
        if BotLogger:
            BotLogger.info(f"{action.capitalize()} {channel_name} for {role_name} in {guild.name}", "UTILS")

        return True

    except discord.Forbidden:
        if BotLogger:
            BotLogger.error(f"No permission to modify {channel_name} in {guild.name}", "UTILS")
        return False
    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error toggling {channel_name}: {e}", "UTILS")
        return False


async def send_reminder_dms(
        guild: discord.Guild,
        members: List[discord.Member],
        embed_key: str,
        context: str = "reminder"
) -> Dict[str, int]:
    """
    Send reminder DMs to a list of members.

    Args:
        guild: Discord guild context
        members: List of members to send DMs to
        embed_key: Configuration key for embed content
        context: Context for logging

    Returns:
        Dict with successful and total_attempted counts
    """
    results = {"successful": 0, "total_attempted": len(members)}

    if BotLogger:
        BotLogger.info(f"Sending {context} DMs to {len(members)} members", "UTILS")

    for member in members:
        try:
            # Create reminder embed
            embed = embed_from_cfg(embed_key, guild_name=guild.name)

            # Send DM
            await member.send(embed=embed)
            results["successful"] += 1

        except discord.Forbidden:
            if BotLogger:
                BotLogger.debug(f"Cannot DM {member.name} (DMs closed)", "UTILS")
        except Exception as e:
            if BotLogger:
                BotLogger.warning(f"Failed to DM {member.name}: {e}", "UTILS")

    if BotLogger:
        BotLogger.info(f"DM results: {results['successful']}/{results['total_attempted']} successful", "UTILS")

    return results


async def toggle_checkin_for_member(
        member: discord.Member,
        check_in: bool = True
) -> bool:
    """
    Toggle check-in status for a member.

    Args:
        member: Discord member
        check_in: True to check in, False to check out

    Returns:
        True if successful, False otherwise
    """
    try:
        role_name = "Checked In"
        role = discord.utils.get(member.guild.roles, name=role_name)

        if not role:
            if BotLogger:
                BotLogger.warning(f"Role '{role_name}' not found in {member.guild.name}", "UTILS")
            return False

        if check_in:
            # Add role if not present
            if role not in member.roles:
                await member.add_roles(role, reason="Checked in via bot")
                if BotLogger:
                    BotLogger.info(f"Checked in {member.name}", "UTILS")
        else:
            # Remove role if present
            if role in member.roles:
                await member.remove_roles(role, reason="Checked out via bot")
                if BotLogger:
                    BotLogger.info(f"Checked out {member.name}", "UTILS")

        return True

    except discord.Forbidden:
        if BotLogger:
            BotLogger.error(f"No permission to modify roles for {member.name}", "UTILS")
        return False
    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error toggling check-in for {member.name}: {e}", "UTILS")
        return False


async def update_dm_action_views(
        guild: discord.Guild,
        members: List[discord.Member]
) -> Dict[str, int]:
    """
    Update DM action views for members.

    Args:
        guild: Discord guild context
        members: List of members to update views for

    Returns:
        Dict with successful and total_attempted counts
    """
    results = {"successful": 0, "total_attempted": len(members)}

    # Import here to avoid circular imports
    try:
        from core.views import DMActionView
    except ImportError:
        if BotLogger:
            BotLogger.warning("DMActionView not available for DM updates", "UTILS")
        return results

    for member in members:
        try:
            view = DMActionView(guild)
            embed = embed_from_cfg("dm_action_menu", guild_name=guild.name)

            await member.send(embed=embed, view=view)
            results["successful"] += 1

        except discord.Forbidden:
            if BotLogger:
                BotLogger.debug(f"Cannot DM {member.name} (DMs closed)", "UTILS")
        except Exception as e:
            if BotLogger:
                BotLogger.warning(f"Failed to update DM view for {member.name}: {e}", "UTILS")

    return results


def hyperlink_lolchess_profile(ign: str, region: str = "na") -> str:
    """
    Create a markdown hyperlink to a LoLChess profile.

    Args:
        ign: In-game name
        region: Server region (default: na)

    Returns:
        Markdown hyperlink string
    """
    if not ign:
        return "N/A"

    # Clean IGN by removing discriminator if present
    clean_ign = ign.split('#')[0] if '#' in ign else ign

    # Build URL
    url = f"https://lolchess.gg/profile/{region.lower()}/{clean_ign}"

    if BotLogger:
        BotLogger.debug(f"Built LoLChess URL: {url}", "UTILS")

    return f"[{clean_ign}]({url})"


# MISSING FUNCTION - Added to fix import errors
async def update_gal_command_ids(bot: commands.Bot):
    """
    Update GAL command IDs for help system integration.

    This function fetches Discord command IDs and stores them for creating
    clickable command links in help messages.
    """
    if BotLogger:
        BotLogger.info("Updating GAL command IDs for help system", "UTILS")

    try:
        # Clear existing command IDs
        GAL_COMMAND_IDS.clear()

        # Allow Discord API time to process command syncing
        await asyncio.sleep(2)

        # Fetch application commands
        commands = await _fetch_application_commands(bot)

        # Fetch guild-specific commands if in development mode
        dev_guild_id = os.getenv("DEV_GUILD_ID")
        if dev_guild_id:
            guild_commands = await _fetch_guild_commands(bot, dev_guild_id)
            if guild_commands:
                commands.extend(guild_commands)

        # Find the GAL command group
        gal_command = next((cmd for cmd in commands if cmd["name"] == "gal" and cmd["type"] == 1), None)

        if not gal_command:
            if BotLogger:
                BotLogger.warning("GAL command not found - setting placeholder IDs", "UTILS")

            # Set placeholder IDs for help functionality
            default_subcommands = [
                "toggle", "event", "registeredlist", "reminder", "cache",
                "validate", "placements", "reload", "help"
            ]
            for subcommand in default_subcommands:
                GAL_COMMAND_IDS[subcommand] = 0
            return

        # Extract subcommand IDs
        gal_id = int(gal_command["id"])
        subcommand_count = 0

        for option in gal_command.get("options", []):
            if option["type"] == 1:  # Subcommand type
                GAL_COMMAND_IDS[option["name"]] = gal_id
                subcommand_count += 1

        if BotLogger:
            if subcommand_count > 0:
                BotLogger.info(f"Updated {subcommand_count} GAL command IDs: {list(GAL_COMMAND_IDS.keys())}", "UTILS")
            else:
                BotLogger.warning("No GAL subcommands found in command structure", "UTILS")

    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Failed to update GAL command IDs: {e}", "UTILS")
        if ErrorHandler:
            await ErrorHandler.handle_interaction_error(
                None, e, "update_gal_command_ids",
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.DISCORD_API
            )


async def _fetch_application_commands(bot: commands.Bot) -> List[Dict]:
    """Fetch application commands from Discord API."""
    try:
        url = f"https://discord.com/api/v10/applications/{bot.application_id}/commands"
        headers = {"Authorization": f"Bot {bot.http.token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    commands = await resp.json()
                    if BotLogger:
                        BotLogger.info(f"Successfully fetched {len(commands)} application commands", "UTILS")
                    return commands
                else:
                    if BotLogger:
                        BotLogger.warning(f"Failed to fetch application commands: HTTP {resp.status}", "UTILS")
                    return []
    except Exception as e:
        if BotLogger:
            BotLogger.error(f"Error fetching application commands: {e}", "UTILS")
        return []


async def _fetch_guild_commands(bot: commands.Bot, guild_id: str) -> List[Dict]:
    """Fetch guild-specific commands from Discord API."""
    try:
        url = f"https://discord.com/api/v10/applications/{bot.application_id}/guilds/{guild_id}/commands"
        headers = {"Authorization": f"Bot {bot.http.token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    guild_commands = await resp.json()
                    if BotLogger:
                        BotLogger.info(f"Fetched {len(guild_commands)} guild-specific commands", "UTILS")
                    return guild_commands
                else:
                    if BotLogger:
                        BotLogger.warning(f"Failed to fetch guild commands: HTTP {resp.status}", "UTILS")
                    return []
    except Exception as e:
        if BotLogger:
            BotLogger.warning(f"Failed to fetch guild commands: {e}", "UTILS")
        return []


# Health validation function
async def validate_utils_health() -> Dict[str, Any]:
    """
    Validate utils system health and functionality.

    Returns:
        Dict with health status information
    """
    health = {
        "status": True,
        "warnings": [],
        "errors": [],
        "functions_available": {},
        "imports_successful": {}
    }

    # Test core imports
    try:
        from config import embed_from_cfg
        health["imports_successful"]["config"] = True
    except ImportError:
        health["imports_successful"]["config"] = False
        health["warnings"].append("Config module not fully available")

    try:
        from helpers import BotLogger
        health["imports_successful"]["helpers"] = True
    except ImportError:
        health["imports_successful"]["helpers"] = False
        health["warnings"].append("Helpers module not available")

    # Test critical functions
    test_functions = [
        "has_allowed_role", "resolve_member", "toggle_persisted_channel",
        "send_reminder_dms", "hyperlink_lolchess_profile", "update_gal_command_ids"
    ]

    for func_name in test_functions:
        try:
            func = globals().get(func_name)
            health["functions_available"][func_name] = func is not None and callable(func)
        except Exception:
            health["functions_available"][func_name] = False

    # Test URL building functionality
    try:
        test_ign = "TestUser#1234"
        result = hyperlink_lolchess_profile(test_ign)
        if BotLogger:
            BotLogger.debug(f"Cleaned IGN: '{test_ign}' -> 'TestUser'", "UTILS")
            BotLogger.debug(f"Built LoLChess URL: https://lolchess.gg/profile/na/TestUser", "UTILS")
        health["url_building_test"] = "successful"
    except Exception as e:
        health["warnings"].append(f"URL building test failed: {e}")
        health["url_building_test"] = "failed"

    # Overall health assessment
    missing_functions = [k for k, v in health["functions_available"].items() if not v]
    if missing_functions:
        health["warnings"].append(f"Missing functions: {missing_functions}")

    failed_imports = [k for k, v in health["imports_successful"].items() if not v]
    if failed_imports:
        health["warnings"].append(f"Failed imports: {failed_imports}")

    return health


def _initialize_utils_module():
    """Initialize the utils module with basic health checks."""
    try:
        # Test critical imports
        from helpers import BotLogger
        from config import embed_from_cfg

        if BotLogger:
            BotLogger.debug("Utils module initialized successfully", "MODULE_INIT")

    except ImportError as e:
        logging.error(f"Failed to initialize utils module: {e}")
        raise


# Export public interface
__all__ = [
    # Core functions
    'has_allowed_role',
    'has_allowed_role_from_interaction',
    'toggle_persisted_channel',
    'resolve_member',
    'send_reminder_dms',
    'toggle_checkin_for_member',
    'update_dm_action_views',
    'hyperlink_lolchess_profile',
    'update_gal_command_ids',  # Added missing function

    # Exception classes
    'UtilsError',
    'MemberNotFoundError',
    'ChannelOperationError',

    # Health and validation
    'validate_utils_health'
]

# Initialize module on import
try:
    _initialize_utils_module()
except Exception as init_error:
    logging.error(f"Critical error during utils module initialization: {init_error}")
    # Don't prevent import, but log the issue