"""GAL command package entry point."""

from __future__ import annotations

from typing import Any, Dict, List

from discord.ext import commands

from .common import logger
from . import configuration, legacy, onboarding, placement, poll, registration, utility
from .legacy import CommandError

gal = legacy.gal


async def setup(bot: commands.Bot) -> None:
    """Register the GAL command group with the bot."""
    try:
        existing: List[str] = [cmd.name for cmd in bot.tree.get_commands()]
        if "gal" in existing:
            logger.warning("GAL command group already registered; skipping setup")
            return

        for command_name in (
            "toggle",
            "event",
            "registeredlist",
            "reminder",
            "cache",
            "config",
        ):
            try:
                gal.remove_command(command_name)
            except KeyError:
                continue

        # Legacy module already registered its commands via decorators.
        registration.register(gal)
        configuration.register(gal)
        onboarding.register(gal)
        placement.register(gal)
        poll.register(gal)
        utility.register(gal)

        bot.tree.add_command(gal)
        logger.info("GAL command group registered successfully")
    except Exception as exc:
        logger.error(f"Failed to setup GAL commands: {exc}", exc_info=True)
        raise


def validate_commands_setup() -> Dict[str, Any]:
    """Validate configuration for GAL commands."""
    return legacy.validate_commands_setup()


try:
    validation = legacy.validate_commands_setup()
    if validation["valid"]:
        logger.info(
            f"Commands setup validated: {validation['total_commands']} commands configured"
        )
    else:
        logger.warning(f"Command setup issues: {validation['issues']}")
except Exception as exc:
    logger.error(f"Failed to validate commands setup: {exc}", exc_info=True)


__all__ = ["gal", "setup", "CommandError"]
