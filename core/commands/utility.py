"""Utility, help, and information commands."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from config import EMBEDS_CFG, GAL_COMMAND_IDS
from helpers import ConfigManager

from .common import (
    command_tracer,
    ensure_staff,
    handle_command_exception,
)


def register(gal: app_commands.Group) -> None:
    """Register utility commands with the GAL command group."""

    @gal.command(
        name="test",
        description="Test the Discord component layout.",
    )
    @command_tracer("gal.test")
    async def test_cmd(interaction: discord.Interaction):
        """Render interactive test components for staff review."""
        if not await ensure_staff(interaction, context="Test Command"):
            return

        try:
            # Test UI components have been removed during project cleanup
            await interaction.response.send_message(
                "Test UI components have been removed during project cleanup.\n"
                "Use the main tournament commands for UI functionality.",
                ephemeral=True
            )
        except Exception as exc:
            await handle_command_exception(interaction, exc, "Test Command")

  

    @gal.command(
        name="help",
        description="Shows this help message.",
    )
    @command_tracer("gal.help")
    async def help_cmd(interaction: discord.Interaction):
        """Display interactive help including slash command mentions."""
        try:
            cfg = EMBEDS_CFG.get("help", {})
            help_embed = discord.Embed(
                title=cfg.get("title", "GAL Bot Help"),
                description=cfg.get(
                    "description",
                    "Here are all the available commands:",
                ),
                color=discord.Color.blurple(),
            )

            cmd_descs = ConfigManager.get_command_help()
            for cmd_name, cmd_id in GAL_COMMAND_IDS.items():
                desc = cmd_descs.get(cmd_name, "No description available.")
                clickable = f"</gal {cmd_name}:{cmd_id}>"
                help_embed.add_field(
                    name=clickable,
                    value=desc,
                    inline=False,
                )

            help_embed.set_footer(
                text="All commands are restricted to staff members.",
            )

            await interaction.response.send_message(
                embed=help_embed,
                ephemeral=True,
            )
        except Exception as exc:
            await handle_command_exception(interaction, exc, "Help Command")


__all__ = ["register"]
