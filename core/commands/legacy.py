"""Legacy scaffolding for the GAL command group and shared error handling."""

from __future__ import annotations

import logging
from typing import Any, Dict

import discord
from discord import app_commands

from config import embed_from_cfg
from helpers import ErrorHandler

logger = logging.getLogger(__name__)


gal = app_commands.Group(
    name="gal",
    description="Group of GAL bot commands",
)


class CommandError(Exception):
    """Custom exception for command-related errors."""


@gal.error
async def gal_error_handler(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Global error handler for GAL commands."""
    try:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True,
            )
            return

        if isinstance(error, app_commands.CommandSignatureMismatch):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❓ Command Signature Error",
                    description="Please check the command syntax and try again.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        original = getattr(error, "original", None)
        await ErrorHandler.handle_interaction_error(
            interaction,
            original or error,
            context="Command",
        )
    except Exception as exc:
        logger.exception("Failed handling command error: %s", exc)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred while handling your request.",
                ephemeral=True,
            )


def validate_commands_setup() -> Dict[str, Any]:
    """Compatibility shim for legacy validation."""
    return {
        "valid": True,
        "issues": [],
        "total_commands": len(gal.commands),
    }


__all__ = ["gal", "CommandError", "validate_commands_setup"]
