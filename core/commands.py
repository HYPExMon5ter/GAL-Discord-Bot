# core/commands.py

import logging
import time
from itertools import groupby
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    embed_from_cfg, col_to_index, BotConstants
)
from core.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
from core.views import (
    PersistentRegisteredListView, DMActionView
)
# Import all helpers
from helpers import (
    RoleManager, SheetOperations, Validators,
    ErrorHandler, ConfigManager, EmbedHelper
)
from integrations.riot_api import tactics_tools_get_latest_placement
from integrations.sheets import (
    sheet_cache, cache_lock, refresh_sheet_cache, ordinal_suffix,
    retry_until_successful, get_sheet_for_guild
)
from utils.utils import (
    toggle_persisted_channel, send_reminder_dms,
)


class CommandError(Exception):
    """Custom exception for command-related errors."""
    pass


# Create command group with better error handling
gal = app_commands.Group(
    name="gal",
    description="Group of GAL bot commands"
)


@gal.command(name="toggle", description="Toggles the registration or check-in channel.")
@app_commands.describe(
    channel="Which channel to toggle (registration or checkin)",
    silent="Toggle silently without pinging the role (default: False)"
)
@app_commands.choices(channel=[
    app_commands.Choice(name="registration", value="registration"),
    app_commands.Choice(name="checkin", value="checkin")
])
async def toggle(interaction: discord.Interaction, channel: app_commands.Choice[str], silent: bool = False):
    """Toggle registration or check-in channel visibility."""
    # Use validator for permission check
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        channel_value = channel.value

        if channel_value == "registration":
            await toggle_persisted_channel(
                interaction,
                persist_key="registration",
                channel_name=BotConstants.REGISTRATION_CHANNEL,
                role_name=BotConstants.ANGEL_ROLE,
                ping_role=not silent,  # Invert silent flag
            )
        elif channel_value == "checkin":
            await toggle_persisted_channel(
                interaction,
                persist_key="checkin",
                channel_name=BotConstants.CHECK_IN_CHANNEL,
                role_name=BotConstants.REGISTERED_ROLE,
                ping_role=not silent,  # Invert silent flag
            )
        else:
            # This shouldn't happen with choices, but just in case
            await interaction.response.send_message(
                "Invalid channel type! Use `registration` or `checkin`.",
                ephemeral=True
            )

    except Exception as e:
        await ErrorHandler.handle_interaction_error(
            interaction, e, "Toggle Command"
        )


@gal.command(name="event", description="View or set the event mode for this guild (normal/doubleup).")
@app_commands.describe(mode="Set the event mode (normal/doubleup)")
@app_commands.choices(mode=[
    app_commands.Choice(name="normal", value="normal"),
    app_commands.Choice(name="doubleup", value="doubleup")
])
async def event(interaction: discord.Interaction, mode: Optional[app_commands.Choice[str]] = None):
    """View or set event mode."""
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        guild_id = str(guild.id)

        current_mode = get_event_mode_for_guild(guild_id)

        # If no mode is provided, show current mode
        if mode is None:
            embed = embed_from_cfg(
                "event_mode_current",
                mode=current_mode.capitalize()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Only staff can change mode
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        mode_value = mode.value
        set_event_mode_for_guild(guild_id, mode_value)

        await interaction.followup.send(
            embed=embed_from_cfg(
                "event_mode_set",
                mode=mode_value.capitalize()
            ),
            ephemeral=True
        )

        # Update embeds/views after mode change
        await refresh_sheet_cache(bot=interaction.client)
        await EmbedHelper.update_all_guild_embeds(guild)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Event Command")


@gal.command(name="registeredlist", description="Show all registered users and who is checked in.")
async def registeredlist(interaction: discord.Interaction):
    """Display registered users list."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=False)
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)

        # Get all registered users
        users = await SheetOperations.get_all_registered_users(guild_id)

        if mode == "normal":
            lines = []
            async with cache_lock:
                for discord_tag, ign, _ in users:
                    user_data = sheet_cache["users"].get(discord_tag)
                    if user_data:
                        checked_in_flag = user_data[3]
                        status = "✅" if SheetOperations.is_true(checked_in_flag) else "❌"
                        lines.append(f"`{discord_tag}` (`{ign}`) — {status}")

            count = len(lines)
            embed = discord.Embed(
                title=f"Registered Players: {count}",
                description="No registered users found." if not lines else "\n".join(lines),
                color=discord.Color.blurple()
            )

        elif mode == "doubleup":
            # Get teams summary
            teams_summary = await SheetOperations.get_teams_summary(guild_id)

            lines = []
            async with cache_lock:
                for team_name in sorted(teams_summary.keys(), key=str.lower):
                    team_members = []
                    for discord_tag in teams_summary[team_name]:
                        user_data = sheet_cache["users"].get(discord_tag)
                        if user_data:
                            ign = user_data[1]
                            checked_in = user_data[3]
                            status = "✅" if SheetOperations.is_true(checked_in) else "❌"
                            team_members.append((discord_tag, ign, status))

                    if team_members:
                        for tag, ign, status in team_members:
                            lines.append(f"{team_name} | `{tag}` (`{ign}`) — {status}")
                        lines.append("")  # Blank line between teams

            # Remove trailing blank line
            if lines and lines[-1] == "":
                lines.pop()

            embed = discord.Embed(
                title=f"Registered Players: {len(users)} | Teams: {len(teams_summary)}",
                description="No registered users found." if not lines else "\n".join(lines),
                color=discord.Color.blurple()
            )

        await interaction.followup.send(
            embed=embed,
            ephemeral=False,
            view=PersistentRegisteredListView(interaction.guild)
        )

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Registered List Command")


@gal.command(name="reminder", description="DM all registered users who are not checked in.")
async def reminder(interaction: discord.Interaction):
    """Send reminder DMs to unchecked users."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=False)

        dm_embed = embed_from_cfg("reminder_dm")
        guild = interaction.guild

        # Use existing helper
        dmmed = await send_reminder_dms(
            client=interaction.client,
            guild=guild,
            dm_embed=dm_embed,
            view_cls=DMActionView
        )

        # Summarize results
        count = len(dmmed)
        users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd."
        public_embed = embed_from_cfg("reminder_public", count=count, users=users_list)

        await interaction.followup.send(embed=public_embed, ephemeral=False)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Reminder Command")


@gal.command(name="cache", description="Forces a manual refresh of the user cache from the Google Sheet.")
async def cache(interaction: discord.Interaction):
    """Refresh sheet cache manually."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        start_time = time.perf_counter()

        # Refresh cache
        updated_users, total_users = await refresh_sheet_cache(bot=interaction.client)
        elapsed = time.perf_counter() - start_time

        # Update all embeds
        embed_results = await EmbedHelper.update_all_guild_embeds(interaction.guild)

        embed = embed_from_cfg(
            "cache",
            updated=updated_users,
            count=total_users,
            elapsed=elapsed
        )

        # Add embed update info if available
        if embed_results:
            successful_updates = sum(1 for success in embed_results.values() if success)
            embed.add_field(
                name="Embed Updates",
                value=f"{successful_updates}/{len(embed_results)} embeds updated",
                inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Cache Command")


@gal.command(
    name="validate",
    description="Validate checked-in IGNs by verifying they have recent TFT placements."
)
async def validate(interaction: discord.Interaction):
    """Validate IGNs of checked-in users."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild.id)

        valid, invalid = [], []

        # Get all checked-in users
        checked_in_users = await SheetOperations.get_all_checked_in_users(guild_id)

        for discord_tag, user_row in checked_in_users:
            ign = user_row[1]

            try:
                placement = await tactics_tools_get_latest_placement(ign, guild_id)
            except Exception as e:
                await ErrorHandler.log_warning(
                    interaction.guild,
                    f"Error validating IGN `{ign}` for {discord_tag}: {e}",
                    "Validate Command"
                )
                invalid.append(f"`{discord_tag}` — `{ign}`: **Error**")
                continue

            # Valid if we got an integer placement
            if isinstance(placement, int):
                valid.append(f"`{discord_tag}` — `{ign}`")
            else:
                invalid.append(f"`{discord_tag}` — `{ign}`: **IGN not found or no recent matches**")

        # Build result embed
        if not (valid or invalid):
            description = "No checked-in users to validate."
            color = discord.Color.light_grey()
        else:
            parts = []
            if valid:
                parts.append("**✅ Valid (played recently):**")
                parts.extend(valid)
            if invalid:
                parts.append("\n**❌ Invalid or no recent matches:**")
                parts.extend(invalid)
            description = "\n".join(parts)

            # Set color based on results
            if valid and not invalid:
                color = discord.Color.green()
            elif valid and invalid:
                color = discord.Color.orange()
            else:
                color = discord.Color.red()

        embed = discord.Embed(
            title="IGN Validation Results",
            description=description,
            color=color
        )

        # Add summary footer
        if valid or invalid:
            embed.set_footer(text=f"✅ {len(valid)} valid • ❌ {len(invalid)} invalid")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Validate Command")


@gal.command(
    name="placements",
    description="Show latest TFT placements for checked-in players."
)
@app_commands.describe(
    round="(Optional) Double-up round number (1–4)."
)
@app_commands.choices(round=[
    app_commands.Choice(name="Round 1", value=1),
    app_commands.Choice(name="Round 2", value=2),
    app_commands.Choice(name="Round 3", value=3),
    app_commands.Choice(name="Round 4", value=4)
])
async def placements(
        interaction: discord.Interaction,
        round: Optional[app_commands.Choice[int]] = None
):
    """Show TFT placements for checked-in players."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        gid = str(guild.id)
        mode = get_event_mode_for_guild(gid)

        round_num = round.value if round else None

        # DOUBLE-UP MODE
        if mode == "doubleup":
            # If a round was given, update that column in the "Lobbies" tab
            if round_num in (1, 2, 3, 4):
                await _update_doubleup_placements(guild, round_num)

            # Build the embed
            checked_in_users = await SheetOperations.get_all_checked_in_users(gid)

            players = []
            for tag, tpl in checked_in_users:
                team = tpl[4] if len(tpl) > 4 else "No Team"
                ign = tpl[1]

                try:
                    placement = await tactics_tools_get_latest_placement(ign, gid)
                except Exception as e:
                    logging.warning(f"Error getting placement for {ign}: {e}")
                    placement = "Error"

                players.append({
                    "team": team,
                    "discord_tag": tag,
                    "ign": ign,
                    "placement": placement
                })

            # Sort & group by team
            players.sort(key=lambda p: (p["team"].lower(), p["discord_tag"].lower()))

            embed = discord.Embed(
                title="🗺️ Double-Up Placements",
                color=discord.Color.blue()
            )

            if round_num:
                embed.title += f" (Round {round_num} Updated)"

            for team, group in groupby(players, key=lambda p: p["team"]):
                lines = []
                for p in group:
                    pl = p["placement"]
                    if isinstance(pl, int):
                        suffix = ordinal_suffix(pl)
                        pl_str = f"{pl}{suffix}"
                    else:
                        pl_str = "N/A"
                    lines.append(f"`{p['discord_tag']}` (`{p['ign']}`): **{pl_str}**")

                embed.add_field(name=team, value="\n".join(lines), inline=False)

            return await interaction.followup.send(embed=embed, ephemeral=True)

        # NORMAL MODE
        checked_in_users = await SheetOperations.get_all_checked_in_users(gid)
        lines = []

        for discord_tag, tpl in checked_in_users:
            ign = tpl[1]
            try:
                placement = await tactics_tools_get_latest_placement(ign, gid)
            except Exception as e:
                logging.warning(f"Error getting placement for {ign}: {e}")
                lines.append(f"`{discord_tag}` — `{ign}`: **Error**")
                continue

            if isinstance(placement, int):
                suffix = ordinal_suffix(placement)
                lines.append(f"`{discord_tag}` — `{ign}`: **{placement}{suffix} place**")
            else:
                lines.append(f"`{discord_tag}` — `{ign}`: **No recent matches**")

        desc = "\n".join(lines) or "No checked-in players to show placements for."
        embed = discord.Embed(
            title="📈 Checked-In Players Latest TFT Placements",
            description=desc,
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Placements Command")


async def _update_doubleup_placements(guild: discord.Guild, round: int):
    """Helper to update double-up placements in the Lobbies sheet."""
    try:
        gid = str(guild.id)
        lobby_sheet = get_sheet_for_guild(gid, "Lobbies")

        # Map rounds → (IGN col, Placement col)
        cols = {
            1: ("C", "D"),
            2: ("G", "H"),
            3: ("K", "L"),
            4: ("O", "P"),
        }

        if round not in cols:
            return

        ign_col_letter, place_col_letter = cols[round]
        ign_idx = col_to_index(ign_col_letter)

        # Fetch all IGN values once
        igns = await retry_until_successful(lobby_sheet.col_values, ign_idx)

        # For each IGN cell (skip header at row 1–2), scrape and write placement
        updates_made = 0
        for row_num, ign in enumerate(igns, start=1):
            if row_num <= 2:  # Skip headers
                continue
            ign = ign.strip()
            if not ign:
                continue

            try:
                placement = await tactics_tools_get_latest_placement(ign, gid)
                val = str(placement) if isinstance(placement, int) else ""

                if val:  # Only update if we have a valid placement
                    await SheetOperations.update_cell(
                        gid,
                        place_col_letter,
                        row_num,
                        val,
                        "Lobbies"
                    )
                    updates_made += 1

            except Exception as e:
                logging.warning(f"Error updating placement for {ign} in round {round}: {e}")
                continue

        logging.info(f"Updated {updates_made} placements for round {round}")

    except Exception as e:
        logging.error(f"Failed to update double-up placements for round {round}: {e}")


@gal.command(name="reload", description="Reloads config, updates live embeds, and refreshes rich presence.")
async def reload_cmd(interaction: discord.Interaction):
    """Reload configuration and update all components."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=True)

        # Use ConfigManager for comprehensive reloading
        results = await ConfigManager.reload_and_update_all(interaction.client)

        if results["config_reload"]:
            # Success embed
            embed = discord.Embed(
                title="✅ Configuration Reloaded",
                description="All embeds, live views, and rich presence have been updated!",
                color=discord.Color.green()
            )

            # Add details about what was updated
            if results["embeds_updated"]:
                guild_results = results["embeds_updated"].get(interaction.guild.name, {})
                if guild_results:
                    successful = sum(1 for success in guild_results.values() if success)
                    total = len(guild_results)
                    embed.add_field(
                        name="Embeds Updated",
                        value=f"✅ {successful}/{total} embeds updated successfully",
                        inline=False
                    )

            if results["presence_update"]:
                embed.add_field(
                    name="Rich Presence",
                    value="✅ Updated successfully",
                    inline=True
                )
        else:
            embed = discord.Embed(
                title="❌ Configuration Reload Failed",
                description="Failed to reload config.yaml. Check console for errors.",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Reload Command")


@gal.command(name="help", description="Shows this help message.")
async def help_cmd(interaction: discord.Interaction):
    """Display help information."""
    try:
        from config import EMBEDS_CFG, GAL_COMMAND_IDS

        cfg = EMBEDS_CFG.get("help", {})
        help_embed = discord.Embed(
            title=cfg.get("title", "GAL Bot Help"),
            description=cfg.get("description", "Here are all the available commands:"),
            color=discord.Color.blurple()
        )

        cmd_descs = ConfigManager.get_command_help()
        for cmd_name, cmd_id in GAL_COMMAND_IDS.items():
            desc = cmd_descs.get(cmd_name, "No description available")
            clickable = f"</gal {cmd_name}:{cmd_id}>"
            help_embed.add_field(
                name=clickable,
                value=desc,
                inline=False
            )

        # Add footer with additional info
        help_embed.set_footer(
            text="All commands are restricted to staff members."
        )

        await interaction.response.send_message(embed=help_embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Help Command")


# Error handlers for the command group
@toggle.error
@event.error
@registeredlist.error
@reminder.error
@cache.error
@validate.error
@placements.error
@reload_cmd.error
@help_cmd.error
async def command_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for all GAL commands."""
    try:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
        else:
            # Let the ErrorHandler deal with other errors
            await ErrorHandler.handle_command_error(interaction, error)

    except Exception as handler_error:
        logging.error(f"Error in command error handler: {handler_error}")
        # Fallback error message
        try:
            fallback_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=fallback_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=fallback_embed, ephemeral=True)
        except:
            pass  # Give up if we can't even send a fallback


# Setup function for the commands module
async def setup(bot: commands.Bot):
    """Setup function to add the command group to the bot."""
    try:
        bot.tree.add_command(gal)
        logging.info("GAL command group added to bot tree")
    except Exception as e:
        logging.error(f"Failed to setup GAL commands: {e}")
        raise


# Health check function
def validate_commands_setup() -> Dict[str, Any]:
    """Validate that commands are properly configured."""
    issues = []

    # Check that all commands have descriptions
    for command in gal.commands:
        if not command.description:
            issues.append(f"Command '{command.name}' missing description")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_commands": len(gal.commands)
    }


# Validate setup
try:
    validation = validate_commands_setup()
    if validation["valid"]:
        logging.info(f"Commands setup validated: {validation['total_commands']} commands configured")
    else:
        logging.warning(f"Command setup issues: {validation['issues']}")
except Exception as e:
    logging.error(f"Failed to validate commands setup: {e}")

# Export the command group
__all__ = ['gal', 'setup', 'CommandError']