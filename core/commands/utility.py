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
            from core.test_components import TestComponents

            view = TestComponents()
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as exc:
            await handle_command_exception(interaction, exc, "Test Command")

    @gal.command(
        name="placement",
        description="Get the latest TFT placement for a player.",
    )
    @app_commands.describe(
        riot_id="Riot ID (format: GameName#TAG or GameName)",
        region="Riot region (defaults to NA)",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="North America (NA)", value="na"),
            app_commands.Choice(name="Europe West (EUW)", value="euw"),
            app_commands.Choice(name="Europe Nordic & East (EUNE)", value="eune"),
            app_commands.Choice(name="Korea (KR)", value="kr"),
            app_commands.Choice(name="Japan (JP)", value="jp"),
            app_commands.Choice(name="Oceania (OCE)", value="oce"),
            app_commands.Choice(name="Brazil (BR)", value="br"),
            app_commands.Choice(name="Latin America North (LAN)", value="lan"),
            app_commands.Choice(name="Latin America South (LAS)", value="las"),
            app_commands.Choice(name="Russia (RU)", value="ru"),
            app_commands.Choice(name="Turkey (TR)", value="tr"),
        ]
    )
    @command_tracer("gal.placement")
    async def placement_cmd(
        interaction: discord.Interaction,
        riot_id: str,
        region: Optional[app_commands.Choice[str]] = None,
    ):
        """Fetch the latest TFT placement using the Riot API."""
        try:
            await interaction.response.defer()
            from integrations.riot_api import RiotAPI

            region_value = region.value if region else "na"

            async with RiotAPI() as riot_api:
                result = await riot_api.get_latest_placement(region_value, riot_id)

            if result["success"]:
                placement_emojis = {
                    1: "🥇",
                    2: "🥈",
                    3: "🥉",
                    4: "4️⃣",
                    5: "5️⃣",
                    6: "6️⃣",
                    7: "7️⃣",
                    8: "8️⃣",
                }
                placement_emoji = placement_emojis.get(
                    result["placement"], f"{result['placement']}️⃣"
                )

                embed = discord.Embed(
                    title="🎯 TFT Latest Placement",
                    color=discord.Color.gold()
                    if result["placement"] <= 4
                    else discord.Color.blue(),
                )
                embed.add_field(
                    name="🏆 Placement",
                    value=f"{placement_emoji} **{result['placement']}** of {result['total_players']}",
                    inline=False,
                )
                embed.add_field(
                    name="👤 Player",
                    value=f"**{result['riot_id']}** (Level {result['level']})",
                    inline=True,
                )
                embed.add_field(
                    name="📅 Game Date",
                    value=result["game_datetime"].strftime("%Y-%m-%d %H:%M UTC"),
                    inline=True,
                )
                embed.add_field(
                    name="📈 Average Placement",
                    value=f"{result['average_placement']:.2f}",
                    inline=True,
                )

                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Placement Not Found",
                        description=result["message"],
                        color=discord.Color.red(),
                    )
                )

        except Exception as exc:
            await handle_command_exception(interaction, exc, "Placement Command")

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
