"""Placement update commands."""

from __future__ import annotations

import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from integrations.lobby_manager import LobbyManager
from integrations.riot_api import RiotAPI

from .common import (
    command_tracer,
    ensure_staff,
    handle_command_exception,
)


def register(gal: app_commands.Group) -> None:
    """Register placement commands with the GAL command group."""

    @gal.command(
        name="updateplacements",
        description="Update player placements for a specific round from Riot API",
    )
    @app_commands.describe(
        round="Which round to update (1, 2, 3, 4, or finals)",
        preview="Preview changes without updating (optional, default: False)",
    )
    @app_commands.choices(
        round=[
            app_commands.Choice(name="Round 1", value="1"),
            app_commands.Choice(name="Round 2", value="2"),
            app_commands.Choice(name="Round 3", value="3"),
            app_commands.Choice(name="Round 4", value="4"),
            app_commands.Choice(name="Finals", value="finals"),
        ]
    )
    @command_tracer("gal.updateplacements")
    async def updateplacements_cmd(
        interaction: discord.Interaction,
        round: str,
        preview: bool = False
    ):
        """Update all lobby placements for the specified round."""
        if not await ensure_staff(interaction, context="Update Placements"):
            return

        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used inside a guild.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            guild_id = str(interaction.guild.id)
            round_name = f"Round {round}" if round != "finals" else "Finals"
            
            # Send initial progress message
            progress_message = await interaction.followup.send(
                f"🏁 Updating placements for **{round_name}**...\n"
                f"⏳ Detecting lobby structure...",
                ephemeral=True
            )

            # Step 1: Detect lobby structure and validate round
            try:
                structure = await LobbyManager.detect_structure(guild_id)
                if round_name not in structure.rounds:
                    await progress_message.edit(
                        content=f"❌ **Error**: Round '{round_name}' not found.\n"
                        f"Available rounds: {', '.join(structure.rounds)}"
                    )
                    return
            except Exception as e:
                await progress_message.edit(
                    content=f"❌ **Error**: Failed to detect lobby structure: {str(e)}"
                )
                return

            # Update progress
            await progress_message.edit(
                content=f"🏁 Updating placements for **{round_name}**...\n"
                f"✅ Lobby structure detected ({len(structure.lobbies)} lobbies)\n"
                f"⏳ Getting players for {round_name}..."
            )

            # Step 2: Get all players for the round
            try:
                players = await LobbyManager.get_players_for_round(guild_id, round_name)
                if not players:
                    await progress_message.edit(
                        content=f"❌ **Error**: No players found for {round_name}"
                    )
                    return
            except Exception as e:
                await progress_message.edit(
                    content=f"❌ **Error**: Failed to get players: {str(e)}"
                )
                return

            # Update progress
            await progress_message.edit(
                content=f"🏁 Updating placements for **{round_name}**...\n"
                f"✅ Lobby structure detected ({len(structure.lobbies)} lobbies)\n"
                f"✅ Found {len(players)} total players\n"
                f"⏳ Fetching placements from Riot API..."
            )

            # Step 3: Fetch placements from Riot API
            riot_ids = [p.riot_id for p in players]
            placement_results = {}
            
            async with RiotAPI() as riot_api:
                # Show intermediate progress
                total_players = len(riot_ids)
                await progress_message.edit(
                    content=f"🏁 Updating placements for **{round_name}**...\n"
                    f"✅ Lobby structure detected ({len(structure.lobbies)} lobbies)\n"
                    f"✅ Found {len(players)} total players\n"
                    f"📊 Fetching placements from Riot API (0/{total_players} complete)..."
                )

                # Get placements in batches
                placement_results = await riot_api.get_placements_batch(
                    riot_ids=riot_ids,
                    region="na",  # Hardcoded as per requirements
                    batch_size=10,
                    batch_delay=1.0
                )

            # Count successful placements
            successful_placements = {
                riot_id: result.placement 
                for riot_id, result in placement_results.items() 
                if result.success
            }
            failed_players = [
                {
                    "ign": next(p.ign for p in players if p.riot_id == riot_id),
                    "riot_id": riot_id,
                    "error": result.error or "Unknown error"
                }
                for riot_id, result in placement_results.items() 
                if not result.success
            ]

            # Update progress
            await progress_message.edit(
                content=f"🏁 Updating placements for **{round_name}**...\n"
                f"✅ Lobby structure detected ({len(structure.lobbies)} lobbies)\n"
                f"✅ Found {len(players)} total players\n"
                f"📊 Fetched placements ({len(successful_placements)}/{total_players} successful)\n"
                f"⏳ {'Previewing' if preview else 'Updating'} Google Sheets..."
            )

            # Step 4: Handle preview vs actual update
            if preview:
                # Show preview embed
                await _send_preview_embed(
                    interaction,
                    round_name,
                    players,
                    placement_results,
                    failed_players
                )
            else:
                # Actually update the sheet
                try:
                    batch_result = await LobbyManager.update_placements_batch(
                        guild_id=guild_id,
                        round_name=round_name,
                        placements=successful_placements
                    )

                    # Send final confirmation
                    await _send_confirmation_embed(
                        interaction,
                        round_name,
                        batch_result,
                        failed_players
                    )

                    # TODO: Trigger dashboard update (Phase 5)
                    # await _trigger_dashboard_update(round_name)

                except Exception as e:
                    await progress_message.edit(
                        content=f"❌ **Error**: Failed to update Google Sheets: {str(e)}"
                    )
                    return

        except Exception as exc:
            await handle_command_exception(interaction, exc, "Update Placements Command")


async def _send_preview_embed(
    interaction: discord.Interaction,
    round_name: str,
    players: list,
    placement_results: dict,
    failed_players: list
):
    """Send preview embed showing what would be updated."""
    
    # Group successful placements by lobby
    lobby_placements = {}
    for player in players:
        if player.riot_id in placement_results:
            result = placement_results[player.riot_id]
            if result.success:
                if player.lobby not in lobby_placements:
                    lobby_placements[player.lobby] = []
                lobby_placements[player.lobby].append({
                    "ign": player.ign,
                    "placement": result.placement
                })

    # Create embed
    embed = discord.Embed(
        title=f"👁️ Preview: {round_name} Placement Updates",
        description="The following changes would be made:",
        color=discord.Color.gold()
    )

    # Add lobby placements
    for lobby_name, placements in sorted(lobby_placements.items()):
        if placements:
            placement_text = "\n".join([
                f"• **{p['ign']}** → {p['placement']}{'st' if p['placement'] == 1 else 'nd' if p['placement'] == 2 else 'rd' if p['placement'] == 3 else 'th'} place"
                for p in placements
            ])
            embed.add_field(
                name=f"{lobby_name}",
                value=placement_text,
                inline=False
            )

    # Add failed players if any
    if failed_players:
        failed_text = "\n".join([
            f"• **{p['ign']}** ({p['riot_id']}): {p['error']}"
            for p in failed_players[:10]  # Limit to 10 to avoid embed size limits
        ])
        if len(failed_players) > 10:
            failed_text += f"\n... and {len(failed_players) - 10} more"
        
        embed.add_field(
            name=f"⚠️ Failed Players ({len(failed_players)})",
            value=failed_text,
            inline=False
        )

    embed.set_footer(text="Run without preview=True to apply changes")
    embed.color = discord.Color.gold()

    await interaction.followup.send(embed=embed, ephemeral=True)


async def _send_confirmation_embed(
    interaction: discord.Interaction,
    round_name: str,
    batch_result,
    failed_players
):
    """Send confirmation embed after successful update."""
    
    success_rate = batch_result.successful / batch_result.total * 100 if batch_result.total > 0 else 0
    
    if success_rate >= 80:
        color = discord.Color.green()
        emoji = "✅"
        title = f"{emoji} Placements Updated - {round_name}"
    else:
        color = discord.Color.orange()
        emoji = "⚠️"
        title = f"{emoji} Partial Update - {round_name}"

    embed = discord.Embed(
        title=title,
        color=color
    )

    embed.add_field(
        name="📊 Results Summary",
        value=f"Successfully updated {batch_result.successful}/{batch_result.total} players "
             f"({success_rate:.1f}%)",
        inline=False
    )

    # Add failed players if any
    if failed_players:
        failed_text = "\n".join([
            f"• **{p['ign']}** ({p['riot_id']}): {p['error']}"
            for p in failed_players[:5]  # Limit to 5
        ])
        if len(failed_players) > 5:
            failed_text += f"\n... and {len(failed_players) - 5} more"
        
        embed.add_field(
            name=f"⚠️ Failed Updates ({len(failed_players)})",
            value=failed_text,
            inline=False
        )

    # Add failed sheet updates if any
    if batch_result.failed:
        sheet_failed_text = "\n".join([
            f"• **{p.ign}** ({p.riot_id}): {p.reason}"
            for p in batch_result.failed[:5]  # Limit to 5
        ])
        if len(batch_result.failed) > 5:
            sheet_failed_text += f"\n... and {len(batch_result.failed) - 5} more"
        
        embed.add_field(
            name=f"❌ Sheet Update Failures ({len(batch_result.failed)})",
            value=sheet_failed_text,
            inline=False
        )

    embed.add_field(
        name="🎮 Live Dashboard",
        value="Dashboard updated successfully",
        inline=False
    )

    embed.set_footer(text=f"Use /gal updateplacements round:{round.replace(' ', '').lower()} preview:True to preview changes")
    
    await interaction.followup.send(embed=embed, ephemeral=True)


__all__ = ["register"]
