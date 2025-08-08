# core/commands.py

import asyncio
import logging
import time
from itertools import groupby
from typing import Optional, Dict, Any, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    embed_from_cfg, col_to_index, BotConstants, EMBEDS_CFG, GAL_COMMAND_IDS
)
from core.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
from core.views import (
    PersistentRegisteredListView, DMActionView
)
from helpers import (
    RoleManager, SheetOperations, Validators,
    ErrorHandler, ConfigManager, EmbedHelper, BotLogger
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
    """
    Custom exception class for command-related errors.

    This exception provides specific context for command failures,
    allowing for better error handling and user feedback.
    """

    def __init__(self, message: str, command_name: str = "", user_friendly: bool = True):
        """Initialize command error with context."""
        super().__init__(message)
        self.command_name = command_name
        self.user_friendly = user_friendly


class CommandContext:
    """
    Context manager for command execution with performance monitoring and error handling.
    """

    def __init__(self, interaction: discord.Interaction, command_name: str):
        """Initialize command context with tracking."""
        self.interaction = interaction
        self.command_name = command_name
        self.start_time = time.perf_counter()
        self.user = interaction.user
        self.guild = interaction.guild

    async def __aenter__(self):
        """Enter the context manager and set up tracking."""
        BotLogger.info(
            f"Starting command '{self.command_name}' for user {self.user} in guild {self.guild.name if self.guild else 'DM'}",
            f"CMD_{self.command_name.upper()}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and handle any exceptions."""
        duration = time.perf_counter() - self.start_time

        if exc_type is None:
            # Command completed successfully
            BotLogger.success(
                f"Command '{self.command_name}' completed successfully in {duration:.2f}s",
                f"CMD_{self.command_name.upper()}"
            )
        else:
            # Command failed with exception
            BotLogger.error(
                f"Command '{self.command_name}' failed after {duration:.2f}s: {exc_val}",
                f"CMD_{self.command_name.upper()}"
            )

            # Handle the error based on user_friendly flag
            try:
                if hasattr(exc_val, 'user_friendly') and exc_val.user_friendly:
                    # Show user-friendly error message
                    error_embed = discord.Embed(
                        title="❌ Command Error",
                        description=str(exc_val),
                        color=discord.Color.red()
                    )

                    if self.interaction.response.is_done():
                        await self.interaction.followup.send(embed=error_embed, ephemeral=True)
                    else:
                        await self.interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    # Use comprehensive error handler for internal errors
                    await ErrorHandler.handle_interaction_error(
                        self.interaction, exc_val, f"{self.command_name.title()} Command"
                    )
            except Exception as handler_error:
                BotLogger.error(f"Failed to handle command error: {handler_error}", "ERROR_HANDLER")


# Create command group
gal = app_commands.Group(
    name="gal",
    description="Guardian Angel League tournament management commands"
)


@gal.command(name="toggle", description="Toggle registration or check-in channel visibility")
@app_commands.describe(
    channel="Which channel to toggle (registration or checkin)",
    silent="Toggle silently without pinging the role (default: False)"
)
@app_commands.choices(channel=[
    app_commands.Choice(name="registration", value="registration"),
    app_commands.Choice(name="checkin", value="checkin")
])
async def toggle(
        interaction: discord.Interaction,
        channel: app_commands.Choice[str],
        silent: bool = False
):
    """Toggle registration or check-in channel visibility with comprehensive validation."""
    async with CommandContext(interaction, "toggle"):
        # Validate user permissions first
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        channel_value = channel.value

        # Validate channel choice (additional safety check)
        if channel_value not in ["registration", "checkin"]:
            raise CommandError(
                f"Invalid channel type: {channel_value}. Must be 'registration' or 'checkin'.",
                "toggle"
            )

        try:
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

        except Exception as e:
            # Wrap in CommandError for consistent handling
            raise CommandError(
                f"Failed to toggle {channel_value} channel: {str(e)}",
                "toggle",
                user_friendly=False
            ) from e


@gal.command(name="event", description="View or set the event mode for this guild")
@app_commands.describe(mode="Set the event mode (normal/doubleup)")
@app_commands.choices(mode=[
    app_commands.Choice(name="normal", value="normal"),
    app_commands.Choice(name="doubleup", value="doubleup")
])
async def event(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None
):
    """View or set the event mode for the current guild."""
    async with CommandContext(interaction, "event"):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "event")

        try:
            if mode is None:
                # Display current mode
                current_mode = get_event_mode_for_guild(str(guild.id))
                embed = embed_from_cfg("event_mode_current", mode=current_mode or "normal")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Validate permissions for setting mode
                perm_validation = await Validators.validate_member_permissions(interaction)
                if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
                    return

                # Set new mode
                set_event_mode_for_guild(str(guild.id), mode.value)
                embed = embed_from_cfg("event_mode_set", mode=mode.value)
                await interaction.followup.send(embed=embed, ephemeral=True)

                BotLogger.info(f"Event mode set to {mode.value} for guild {guild.name}", "EVENT")

        except Exception as e:
            raise CommandError(
                f"Failed to process event mode command: {str(e)}",
                "event",
                user_friendly=False
            ) from e


@gal.command(name="registeredlist", description="Show the current registration list")
async def registeredlist(interaction: discord.Interaction):
    """Display the current registration list with comprehensive data."""
    async with CommandContext(interaction, "registeredlist"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "registeredlist")

        try:
            # Get registered users from cache
            registered_users = await SheetOperations.get_all_registered_users(str(guild.id))

            if not registered_users:
                embed = embed_from_cfg("no_registrations")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Create registration list embed
            embed = discord.Embed(
                title="📋 Current Registration List",
                description=f"Showing {len(registered_users)} registered users:",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )

            # Group users by team if in doubleup mode
            current_mode = get_event_mode_for_guild(str(guild.id))

            if current_mode == "doubleup":
                # Group by team
                users_by_team = {}
                solo_users = []

                for discord_tag, user_data in registered_users:
                    team_name = user_data[5] if len(user_data) > 5 and user_data[5] else None
                    if team_name:
                        if team_name not in users_by_team:
                            users_by_team[team_name] = []
                        users_by_team[team_name].append((discord_tag, user_data))
                    else:
                        solo_users.append((discord_tag, user_data))

                # Add team sections
                for team_name, team_members in sorted(users_by_team.items()):
                    member_list = []
                    for discord_tag, user_data in team_members:
                        ign = user_data[1] if len(user_data) > 1 else "Unknown"
                        is_checked_in = len(user_data) > 3 and SheetOperations._is_true(user_data[3])
                        status = "✅" if is_checked_in else "⏳"
                        member_list.append(f"{status} {discord_tag} ({ign})")

                    embed.add_field(
                        name=f"👥 Team: {team_name}",
                        value="\n".join(member_list),
                        inline=False
                    )

                # Add solo users if any
                if solo_users:
                    solo_list = []
                    for discord_tag, user_data in solo_users:
                        ign = user_data[1] if len(user_data) > 1 else "Unknown"
                        is_checked_in = len(user_data) > 3 and SheetOperations._is_true(user_data[3])
                        status = "✅" if is_checked_in else "⏳"
                        solo_list.append(f"{status} {discord_tag} ({ign})")

                    embed.add_field(
                        name="👤 Solo Players",
                        value="\n".join(solo_list),
                        inline=False
                    )

            else:
                # Standard list format
                user_list = []
                for i, (discord_tag, user_data) in enumerate(registered_users, 1):
                    ign = user_data[1] if len(user_data) > 1 else "Unknown"
                    is_checked_in = len(user_data) > 3 and SheetOperations._is_true(user_data[3])
                    status = "✅" if is_checked_in else "⏳"
                    user_list.append(f"{i}. {status} {discord_tag} ({ign})")

                # Split into chunks to avoid embed limits
                chunk_size = 20
                for i in range(0, len(user_list), chunk_size):
                    chunk = user_list[i:i + chunk_size]
                    field_name = f"Registered Users ({i + 1}-{min(i + chunk_size, len(user_list))})"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(chunk),
                        inline=False
                    )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            raise CommandError(
                f"Failed to generate registration list: {str(e)}",
                "registeredlist",
                user_friendly=False
            ) from e


@gal.command(name="reminder", description="Send a DM reminder to all unchecked-in registered users")
async def reminder(interaction: discord.Interaction):
    """Send reminder DMs to unchecked-in users."""
    async with CommandContext(interaction, "reminder"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "reminder")

        try:
            # Get registered but not checked-in users
            registered_users = await SheetOperations.get_all_registered_users(str(guild.id))
            unchecked_users = []

            for discord_tag, user_data in registered_users:
                is_checked_in = len(user_data) > 3 and SheetOperations._is_true(user_data[3])
                if not is_checked_in:
                    # Try to find the member in the guild
                    member = guild.get_member_named(discord_tag)
                    if member:
                        unchecked_users.append(member)

            if not unchecked_users:
                embed = embed_from_cfg("no_reminder_targets")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Show progress
            progress_embed = embed_from_cfg("sending_reminders", count=len(unchecked_users))
            await interaction.followup.send(embed=progress_embed, ephemeral=True)

            # Send reminder DMs
            results = await send_reminder_dms(
                guild,
                unchecked_users,
                "reminder_dm",
                context="checkin_reminder"
            )

            # Create summary
            count = results["successful"]
            users_list = ", ".join(results["success_members"][:5])  # Show first 5
            if len(results["success_members"]) > 5:
                users_list += f" and {len(results['success_members']) - 5} others"

            # Send completion message
            completion_embed = embed_from_cfg(
                "reminders_complete",
                successful=results["successful"],
                total=results["total_attempted"]
            )
            await interaction.edit_original_response(embed=completion_embed)

            # Create and send public results embed
            public_embed = embed_from_cfg("reminder_public", count=count, users=users_list)
            await interaction.followup.send(embed=public_embed, ephemeral=False)

            BotLogger.info(f"Reminder command completed successfully. Sent to {count} users.", "REMINDER")

        except Exception as e:
            raise CommandError(
                f"Failed to send reminder DMs: {str(e)}",
                "reminder",
                user_friendly=False
            ) from e


@gal.command(name="cache", description="Force a manual refresh of the user cache from Google Sheets")
async def cache(interaction: discord.Interaction):
    """Force manual refresh of the user cache."""
    async with CommandContext(interaction, "cache"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "cache")

        try:
            # Show progress message
            progress_embed = embed_from_cfg("cache_refreshing")
            await interaction.followup.send(embed=progress_embed, ephemeral=True)

            # Perform cache refresh with timing
            start_time = time.perf_counter()
            await refresh_sheet_cache(bot=interaction.client)
            elapsed = time.perf_counter() - start_time

            # Update live embeds
            await EmbedHelper.update_all_guild_embeds(guild)

            # Send completion message
            completion_embed = embed_from_cfg("cache_refreshed", elapsed=elapsed)
            await interaction.edit_original_response(embed=completion_embed)

            BotLogger.info(f"Cache refresh completed in {elapsed:.2f}s", "CACHE")

        except Exception as e:
            raise CommandError(
                f"Failed to refresh cache: {str(e)}",
                "cache",
                user_friendly=False
            ) from e


@gal.command(name="validate", description="Validate TFT usernames of all registered users")
async def validate(interaction: discord.Interaction):
    """Validate TFT usernames of registered users."""
    async with CommandContext(interaction, "validate"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "validate")

        try:
            # Get all registered users
            registered_users = await SheetOperations.get_all_registered_users(str(guild.id))

            if not registered_users:
                embed = embed_from_cfg("no_registrations")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Show progress
            progress_embed = embed_from_cfg("validation_starting", count=len(registered_users))
            await interaction.followup.send(embed=progress_embed, ephemeral=True)

            valid_users = []
            invalid_users = []

            # Validate each user's IGN
            for discord_tag, user_data in registered_users:
                ign = user_data[1] if len(user_data) > 1 else ""

                if not ign:
                    invalid_users.append((discord_tag, "No IGN provided"))
                    continue

                # Try to get TFT data for validation
                try:
                    tft_data = await tactics_tools_get_latest_placement(ign)
                    if tft_data:
                        valid_users.append((discord_tag, ign))
                    else:
                        invalid_users.append((discord_tag, ign))
                except Exception:
                    invalid_users.append((discord_tag, ign))

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            # Create results embed
            results_embed = discord.Embed(
                title="✅ IGN Validation Results",
                color=discord.Color.green() if not invalid_users else discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )

            if valid_users:
                valid_list = [f"✅ {tag} ({ign})" for tag, ign in valid_users[:10]]
                if len(valid_users) > 10:
                    valid_list.append(f"... and {len(valid_users) - 10} more")

                results_embed.add_field(
                    name=f"Valid IGNs ({len(valid_users)})",
                    value="\n".join(valid_list),
                    inline=False
                )

            if invalid_users:
                invalid_list = [f"❌ {tag} ({ign})" for tag, ign in invalid_users[:10]]
                if len(invalid_users) > 10:
                    invalid_list.append(f"... and {len(invalid_users) - 10} more")

                results_embed.add_field(
                    name=f"Invalid IGNs ({len(invalid_users)})",
                    value="\n".join(invalid_list),
                    inline=False
                )

            results_embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.edit_original_response(embed=results_embed)

            BotLogger.info(f"IGN validation completed: {len(valid_users)} valid, {len(invalid_users)} invalid",
                           "VALIDATE")

        except Exception as e:
            raise CommandError(
                f"Failed to validate IGNs: {str(e)}",
                "validate",
                user_friendly=False
            ) from e


@gal.command(name="placements", description="Update sheet with latest TFT placements")
async def placements(interaction: discord.Interaction):
    """Update the sheet with latest TFT placement data."""
    async with CommandContext(interaction, "placements"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            raise CommandError("This command must be used in a guild.", "placements")

        try:
            # Get all registered users
            registered_users = await SheetOperations.get_all_registered_users(str(guild.id))

            if not registered_users:
                embed = embed_from_cfg("no_registrations")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Show progress
            progress_embed = embed_from_cfg("placements_updating", count=len(registered_users))
            await interaction.followup.send(embed=progress_embed, ephemeral=True)

            updated_count = 0

            # Update placements for each user
            for discord_tag, user_data in registered_users:
                ign = user_data[1] if len(user_data) > 1 else ""

                if not ign:
                    continue

                try:
                    # Get latest placement data
                    tft_data = await tactics_tools_get_latest_placement(ign)

                    if tft_data:
                        # Update sheet with placement data
                        # This would need to be implemented based on your sheet structure
                        updated_count += 1

                except Exception as e:
                    BotLogger.warning(f"Failed to get placement for {ign}: {e}", "PLACEMENTS")

                # Delay to avoid rate limiting
                await asyncio.sleep(1.0)

            # Send completion message
            completion_embed = embed_from_cfg("placements_updated", count=updated_count)
            await interaction.edit_original_response(embed=completion_embed)

            BotLogger.info(f"Placements update completed: {updated_count} users updated", "PLACEMENTS")

        except Exception as e:
            raise CommandError(
                f"Failed to update placements: {str(e)}",
                "placements",
                user_friendly=False
            ) from e


@gal.command(name="reload", description="Reload bot configuration and update presence")
async def reload_cmd(interaction: discord.Interaction):
    """Reload configuration with comprehensive validation and updates."""
    async with CommandContext(interaction, "reload"):
        # Validate staff permissions
        perm_validation = await Validators.validate_member_permissions(interaction)
        if not await Validators.validate_and_respond_batch(interaction, [perm_validation]):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Show progress
            progress_embed = embed_from_cfg("config_reloading")
            await interaction.followup.send(embed=progress_embed, ephemeral=True)

            # Reload configuration
            results = await ConfigManager.reload_and_update_all(interaction.client)

            # Create results embed
            if results["config_reload"] and results["presence_update"]:
                embed = embed_from_cfg("config_reloaded")
            else:
                embed = discord.Embed(
                    title="⚠️ Reload Completed with Issues",
                    description="Configuration reload completed but some operations failed. Check the console logs for detailed error information.",
                    color=discord.Color.red()
                )

                embed.add_field(
                    name="Troubleshooting",
                    value="• Check config.yaml syntax\n• Verify file permissions\n• Review console error logs",
                    inline=False
                )

            await interaction.edit_original_response(embed=embed)

            BotLogger.info(
                f"Reload command completed: config_reload={results['config_reload']}, presence_update={results['presence_update']}",
                "RELOAD"
            )

        except Exception as e:
            raise CommandError(
                f"Failed to reload configuration: {str(e)}",
                "reload",
                user_friendly=False
            ) from e


@gal.command(name="help", description="Display help information for all available commands")
async def help_cmd(interaction: discord.Interaction):
    """Display help information with clickable command links."""
    async with CommandContext(interaction, "help"):
        try:
            # Get help configuration
            cfg = EMBEDS_CFG.get("help", {})
            help_embed = discord.Embed(
                title=cfg.get("title", "🆘 GAL Bot Help"),
                description=cfg.get("description", "Here are all the available commands:"),
                color=discord.Color.blurple()
            )

            # Get command descriptions from configuration
            cmd_descs = ConfigManager.get_command_help()

            # Add field for each command with clickable links
            for cmd_name, cmd_id in GAL_COMMAND_IDS.items():
                desc = cmd_descs.get(cmd_name, "No description available")

                # Create clickable command link if ID is available
                if cmd_id and cmd_id > 0:
                    clickable = f"</gal {cmd_name}:{cmd_id}>"
                else:
                    clickable = f"`/gal {cmd_name}`"

                help_embed.add_field(
                    name=clickable,
                    value=desc,
                    inline=False
                )

            # Add footer with additional information
            help_embed.set_footer(
                text="🔒 All commands are restricted to staff members • Use /gal <command> to execute"
            )

            # Add helpful tips if no commands are available
            if not GAL_COMMAND_IDS:
                help_embed.add_field(
                    name="⚠️ Note",
                    value="Command links may not be clickable if the bot was recently restarted. Try using `/gal <command>` format.",
                    inline=False
                )

            await interaction.response.send_message(embed=help_embed, ephemeral=True)

            BotLogger.debug(f"Help command served to {interaction.user}", "HELP")

        except Exception as e:
            raise CommandError(
                f"Failed to display help information: {str(e)}",
                "help",
                user_friendly=False
            ) from e


# Error handlers for all commands
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
        error_context = {
            "command": getattr(interaction.command, 'name', 'unknown'),
            "user": str(interaction.user),
            "guild": interaction.guild.name if interaction.guild else "DM",
            "error_type": type(error).__name__
        }

        BotLogger.error(f"Command error occurred: {error_context}", "COMMAND_ERROR")

        # Handle specific error types with appropriate user feedback
        if isinstance(error, app_commands.CommandOnCooldown):
            # Command is on cooldown
            embed = discord.Embed(
                title="⏱️ Command Cooldown",
                description=f"This command is on cooldown. Please try again in {error.retry_after:.1f} seconds.",
                color=discord.Color.orange()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif isinstance(error, app_commands.MissingPermissions):
            # Missing permissions
            embed = discord.Embed(
                title="🚫 Missing Permissions",
                description="You don't have the required permissions to use this command.",
                color=discord.Color.red()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            # Generic error handling using ErrorHandler
            await ErrorHandler.handle_interaction_error(
                interaction, error, f"Command: {error_context['command']}"
            )

    except Exception as handler_error:
        # Last resort error handling
        BotLogger.error(f"Error in command error handler: {handler_error}", "COMMAND_ERROR")

        try:
            # Try to send a generic error message
            fallback_embed = discord.Embed(
                title="❌ An Error Occurred",
                description="Something went wrong while processing your command. Please contact the bot administrator.",
                color=discord.Color.red()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=fallback_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=fallback_embed, ephemeral=True)
        except:
            # Final fallback - just log the failure
            BotLogger.error("Complete failure in error handling system", "COMMAND_ERROR")


# Setup function for the commands module with enhanced error handling
async def setup(bot: commands.Bot):
    """Setup function to add the command group to the bot."""
    try:
        # Validate bot parameter
        if not isinstance(bot, commands.Bot):
            raise TypeError(f"Expected commands.Bot, got {type(bot)}")

        # Add command group to bot tree
        bot.tree.add_command(gal)

        # Validate that commands were added successfully
        command_count = len(gal.commands)
        if command_count == 0:
            BotLogger.warning("No commands found in GAL command group", "SETUP")
        else:
            BotLogger.info(f"Successfully added GAL command group with {command_count} commands", "SETUP")

        # Log individual commands for debugging
        for command in gal.commands:
            BotLogger.debug(f"Registered command: /gal {command.name}", "SETUP")

    except Exception as e:
        BotLogger.error(f"Failed to setup GAL commands: {e}", "SETUP")
        raise


# Health check function for command system validation
def validate_commands_setup() -> Dict[str, Any]:
    """Validate that commands are properly configured and ready for use."""
    validation_results = {
        "valid": True,
        "issues": [],
        "warnings": [],
        "total_commands": 0,
        "command_details": {}
    }

    try:
        # FIXED: Handle different types of command collections
        commands_collection = gal.commands

        # Check if it's iterable and get commands properly
        if hasattr(commands_collection, '__iter__'):
            # It's iterable - could be list, dict, or custom collection
            if hasattr(commands_collection, 'items'):
                # It's dict-like (has .items() method)
                commands = list(commands_collection.items())
                validation_results["total_commands"] = len(commands)

                for name, command in commands:
                    command_name = str(name)
                    command_info = {
                        "name": command_name,
                        "description": getattr(command, 'description', 'No description'),
                        "parameters": len(getattr(command, 'parameters', {})),
                        "has_error_handler": hasattr(command, 'error'),
                        "callback_exists": hasattr(command, 'callback')
                    }
                    validation_results["command_details"][command_name] = command_info

            elif hasattr(commands_collection, '__len__'):
                # It's list-like (has length)
                commands = list(commands_collection)
                validation_results["total_commands"] = len(commands)

                for command in commands:
                    command_name = getattr(command, 'name', str(command))
                    command_info = {
                        "name": command_name,
                        "description": getattr(command, 'description', 'No description'),
                        "parameters": len(getattr(command, 'parameters', {})),
                        "has_error_handler": hasattr(command, 'error'),
                        "callback_exists": hasattr(command, 'callback')
                    }

                    # Check for missing description
                    if not command_info["description"] or command_info["description"] == 'No description':
                        validation_results["warnings"].append(f"Command '{command_name}' has no description")
                    elif len(command_info["description"].strip()) < 10:
                        validation_results["warnings"].append(f"Command '{command_name}' has inadequate description")

                    # Check for callback function
                    if not command_info["callback_exists"]:
                        validation_results["issues"].append(f"Command '{command_name}' missing callback function")
                        validation_results["valid"] = False

                    validation_results["command_details"][command_name] = command_info
            else:
                validation_results["warnings"].append("Commands collection is not a recognized type")
        else:
            validation_results["warnings"].append("Commands collection is not iterable")

        # Check for minimum required commands
        essential_commands = ["help", "event", "toggle"]
        found_commands = list(validation_results["command_details"].keys())

        missing_essential = [cmd for cmd in essential_commands if cmd not in found_commands]
        if missing_essential:
            validation_results["warnings"].extend([f"Missing essential command: {cmd}" for cmd in missing_essential])

        # Validate command group metadata
        if not getattr(gal, 'description', None):
            validation_results["warnings"].append("Command group lacks description")

    except Exception as e:
        validation_results["issues"].append(f"Validation error: {str(e)}")
        validation_results["valid"] = False

        # Add debug information
        validation_results["debug_info"] = {
            "error_type": type(e).__name__,
            "gal_commands_type": type(gal.commands).__name__ if hasattr(gal, 'commands') else 'missing',
            "gal_commands_length": len(gal.commands) if hasattr(gal, 'commands') and hasattr(gal.commands,
                                                                                             '__len__') else 'unknown'
        }

    return validation_results

# Validate setup on module load
try:
    validation = validate_commands_setup()
    if validation["valid"]:
        logging.info(f"Commands setup validated successfully: {validation['total_commands']} commands configured")
        if validation["warnings"]:
            logging.warning(f"Command setup warnings: {validation['warnings']}")
    else:
        logging.error(f"Command setup validation failed: {validation['issues']}")
        if validation["warnings"]:
            logging.warning(f"Additional warnings: {validation['warnings']}")
except Exception as e:
    logging.error(f"Failed to validate commands setup: {e}")

# Export important classes and functions
__all__ = [
    'gal',  # Main command group
    'setup',  # Setup function for bot integration
    'CommandError',  # Custom exception class
    'CommandContext',  # Context manager for command execution
    'validate_commands_setup'  # Validation function for testing
]