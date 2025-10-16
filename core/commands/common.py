"""Shared helpers for GAL bot command modules."""

from __future__ import annotations

import functools
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

import discord
from discord import app_commands

from helpers import ErrorHandler, Validators
from utils.logging_utils import SecureLogger
from utils.metrics import increment_counter, time_block

logger = SecureLogger(__name__)

T = TypeVar("T")
AsyncCommand = Callable[..., Awaitable[T]]


async def ensure_staff(interaction: discord.Interaction, context: str) -> bool:
    """Validate that the caller has staff permissions."""
    return await Validators.validate_and_respond(
        interaction,
        Validators.validate_staff_permission(interaction),
        context=context,
    )


def command_tracer(command_name: str) -> Callable[[AsyncCommand[T]], AsyncCommand[T]]:
    """Decorator that measures execution time and logs diagnostics."""

    def decorator(func: AsyncCommand[T]) -> AsyncCommand[T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Command '{command_name}' invoked")
            with time_block("command.duration", command=command_name):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    increment_counter(
                        "command.errors",
                        command=command_name,
                        error_type=exc.__class__.__name__,
                    )
                    logger.error(
                        f"Command '{command_name}' failed: {exc}",
                        exc_info=True,
                    )
                    raise
            logger.debug(f"Command '{command_name}' completed successfully")

        return wrapper

    return decorator


async def respond_with_message(
    interaction: discord.Interaction,
    *,
    embed: Optional[discord.Embed] = None,
    content: Optional[str] = None,
    ephemeral: bool = True,
) -> None:
    """Send a response or follow-up depending on interaction state."""
    kwargs: Dict[str, Any] = {"ephemeral": ephemeral}
    if embed:
        kwargs["embed"] = embed
    if content:
        kwargs["content"] = content

    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


async def handle_command_exception(
    interaction: discord.Interaction,
    error: Exception,
    context: str,
    user_message: Optional[str] = None,
) -> None:
    """Delegate to the central error handler with consistent context."""
    await ErrorHandler.handle_interaction_error(
        interaction,
        error,
        context=context,
        user_message=user_message,
    )


def localized_choice(
    name: str,
    value: str,
) -> app_commands.Choice[str]:
    """Shorthand to create a typed app command choice."""
    return app_commands.Choice(name=name, value=value)


__all__ = [
    "logger",
    "ensure_staff",
    "command_tracer",
    "respond_with_message",
    "handle_command_exception",
    "localized_choice",
]
