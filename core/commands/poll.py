"""Poll notification commands for mass DM functionality."""

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands

from core.commands.common import ensure_staff, command_tracer
from helpers.poll_helpers import PollNotifier, validate_discord_link
from helpers import ErrorHandler

logger = logging.getLogger(__name__)


def register(gal: app_commands.Group) -> None:
    """Register poll commands with the GAL command group."""
    
    @gal.command(
        name="poll",
        description="Send poll notification to all Angels"
    )
    @app_commands.describe(
        link="Link to the Discord poll message",
        custom_message="Optional custom message override"
    )
    @command_tracer("gal.poll")
    async def poll_notify(
        interaction: discord.Interaction,
        link: str,
        custom_message: Optional[str] = None
    ) -> None:
        """
        Send poll notification to all users with the Angels role.
        
        This command sends a customizable DM to all Angels with a link to a Discord poll.
        Progress is tracked and displayed in real-time.
        """
        if not await ensure_staff(interaction, context="Poll Command"):
            return
            
        try:
            # Defer response immediately since this will take time
            await interaction.response.defer(ephemeral=True)
            
            # Validate Discord link
            if not validate_discord_link(link):
                embed = discord.Embed(
                    title="❌ Invalid Link Format",
                    description="Please provide a valid Discord message link in the format:\n"
                               "`https://discord.com/channels/guild_id/channel_id/message_id`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create poll notifier
            notifier = PollNotifier(
                guild=interaction.guild,
                poll_link=link,
                custom_message=custom_message
            )
            
            # Create initial progress message
            progress_embed = discord.Embed(
                title="📨 Sending Poll Notifications",
                description="⏳ Preparing to send notifications to all Angels...",
                color=discord.Color.blue()
            )
            
            # Send initial progress message
            progress_message = await interaction.followup.send(embed=progress_embed, ephemeral=True)
            
            # Track elapsed time for final summary
            final_elapsed_time = 0
            
            # Progress callback function
            async def update_progress(embed, current, total, elapsed):
                nonlocal final_elapsed_time
                final_elapsed_time = elapsed  # Track the elapsed time
                try:
                    await progress_message.edit(embed=embed)
                except discord.NotFound:
                    logger.warning("Progress message was deleted")
                except discord.HTTPException as e:
                    logger.warning(f"Failed to update progress message: {e}")
            
            # Send DMs to all Angels
            success_count, failed_count, failed_users = await notifier.send_to_all_angels(update_progress)
            
            # Create final summary
            total_time = final_elapsed_time  # Use the tracked elapsed time
            summary_embed = notifier.create_summary_embed(total_time)
            
            # Send final summary
            await progress_message.edit(embed=summary_embed)
            
            # Log completion
            logger.info(f"Poll notification completed by {interaction.user}: "
                       f"{success_count} success, {failed_count} failed")
            
        except ValueError as e:
            # Handle configuration errors
            embed = discord.Embed(
                title="❌ Configuration Error",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.Forbidden:
            # Handle permission errors
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to send DMs to some users or access server information.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except asyncio.TimeoutError:
            # Handle timeout
            embed = discord.Embed(
                title="⏰ Operation Timed Out",
                description="The poll notification process took too long and was cancelled.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            # Handle other unexpected errors
            logger.error(f"Unexpected error in poll command: {e}")
            await ErrorHandler.handle_interaction_error(
                interaction,
                e,
                "Poll notification",
                "An unexpected error occurred while sending poll notifications."
            )

    @poll_notify.error
    async def poll_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Handle errors for the poll command."""
        if isinstance(error, app_commands.CheckFailure):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command. This command is restricted to staff members.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            
            if isinstance(original, discord.Forbidden):
                embed = discord.Embed(
                    title="❌ Permission Error",
                    description="I don't have permission to send DMs or access server information.",
                    color=discord.Color.red()
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Log the error and send generic error message
                logger.error(f"Poll command error: {original}")
                await ErrorHandler.handle_interaction_error(
                    interaction,
                    original,
                    "Poll notification",
                    "An error occurred while processing the poll command."
                )
        else:
            logger.error(f"Unhandled poll command error: {error}")
            embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)


__all__ = ["register"]
