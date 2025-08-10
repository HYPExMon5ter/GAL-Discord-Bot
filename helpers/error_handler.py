# helpers/error_handler.py

import traceback
from datetime import datetime, timezone
from typing import Optional

import discord

from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER


class ErrorHandler:
    """Centralized error handling for the bot."""
    @staticmethod
    async def handle_interaction_error(
            interaction: discord.Interaction,
            error: Exception,
            context: str = "Command",
            user_message: Optional[str] = None,
            log_full_trace: bool = True
    ) -> None:
        """
        Handle errors from Discord interactions with logging and user feedback.
        """
        # Prepare error details
        error_id = f"{context}_{datetime.now().timestamp():.0f}"
        guild = interaction.guild
        user = interaction.user

        # Build detailed error message for logging
        log_parts = [
            f"[{context.upper()}-ERROR] ID: {error_id}",
            f"Guild: {guild.name if guild else 'DM'} ({guild.id if guild else 'N/A'})",
            f"User: {user} (ID: {user.id})",
            f"Error: {type(error).__name__}: {str(error)}"
        ]

        if hasattr(interaction, 'command'):
            log_parts.append(f"Command: {interaction.command.name}")

        if log_full_trace:
            log_parts.append(f"Traceback:\n{traceback.format_exc()}")

        log_message = "\n".join(log_parts)

        # Log to console
        print(log_message)

        # Log to Discord channel if available
        if guild:
            await ErrorHandler._log_to_channel(guild, log_message, error_id)

        # Send user feedback
        if not user_message:
            user_message = (
                "An error occurred while processing your request. "
                f"Error ID: `{error_id}`\n"
                "This has been logged and will be investigated."
            )

        error_embed = discord.Embed(
            title="❌ Error",
            description=user_message,
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except:
            # If we can't send to the user, just log it
            print(f"[ERROR-HANDLER] Could not send error message to user {user}")

    @staticmethod
    async def _log_to_channel(
            guild: discord.Guild,
            message: str,
            error_id: str
    ) -> None:
        """Log error to designated log channel."""
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if not log_channel:
            return

        # Split message if too long
        if len(message) > 3900:
            message = message[:3900] + "...\n[Truncated]"

        embed = discord.Embed(
            title=f"🚨 Error Report: {error_id}",
            description=f"```\n{message}\n```",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="GAL Bot Error Handler")

        try:
            await log_channel.send(
                content=PING_USER,
                embed=embed
            )
        except Exception as e:
            print(f"[ERROR-HANDLER] Failed to log to channel: {e}")

    @staticmethod
    def wrap_callback(context: str):
        """
        Decorator to wrap interaction callbacks with error handling.
        """

        def decorator(func):
            async def wrapper(self, interaction: discord.Interaction):
                try:
                    return await func(self, interaction)
                except Exception as e:
                    await ErrorHandler.handle_interaction_error(
                        interaction, e, context
                    )

            return wrapper

        return decorator

    @staticmethod
    async def handle_command_error(
            interaction: discord.Interaction,
            error: Exception
    ) -> None:
        """
        Specialized handler for command errors with common error type handling.
        """
        # Check for common Discord.py errors
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
        elif isinstance(error, discord.Forbidden):
            await ErrorHandler.handle_interaction_error(
                interaction, error, "Permission",
                "I don't have the required permissions to perform this action."
            )
        elif isinstance(error, discord.HTTPException):
            await ErrorHandler.handle_interaction_error(
                interaction, error, "HTTP",
                "A Discord API error occurred. Please try again later."
            )
        else:
            # Generic error handling
            await ErrorHandler.handle_interaction_error(
                interaction, error, "Command"
            )

    @staticmethod
    async def log_warning(
            guild: discord.Guild,
            message: str,
            context: str = "Warning"
    ) -> None:
        """Log a warning message to the log channel."""
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"⚠️ {context}",
            description=message,
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="GAL Bot")

        try:
            await log_channel.send(embed=embed)
        except:
            print(f"[WARNING] {context}: {message}")

    @staticmethod
    async def log_info(
            guild: discord.Guild,
            message: str,
            context: str = "Info"
    ) -> None:
        """Log an info message to the log channel."""
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"ℹ️ {context}",
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="GAL Bot")

        try:
            await log_channel.send(embed=embed)
        except:
            print(f"[INFO] {context}: {message}")