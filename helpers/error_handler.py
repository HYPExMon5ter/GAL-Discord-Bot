# helpers/error_handler.py

import asyncio
import functools
import traceback
import hashlib
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Set, Callable, Tuple, Awaitable, Union
from enum import Enum

import discord

from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER
from .logging_helper import BotLogger


class ErrorSeverity(Enum):
    """Error severity levels for categorization and handling."""
    LOW = "low"  # Minor issues, no user impact
    MEDIUM = "medium"  # Some functionality affected
    HIGH = "high"  # Major functionality broken
    CRITICAL = "critical"  # System-wide failure


class ErrorCategory(Enum):
    """Error categories for targeted handling and analysis."""
    DISCORD_API = "discord_api"
    PERMISSIONS = "permissions"
    CHANNEL_MANAGEMENT = "channel_management"
    VALIDATION = "validation"
    DATABASE = "database"
    SHEETS = "sheets"
    CONFIGURATION = "configuration"
    USER_INPUT = "user_input"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorContext:
    """Comprehensive error context container for detailed error information."""

    def __init__(
            self,
            error: Exception,
            operation: str,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            category: ErrorCategory = ErrorCategory.UNKNOWN,
            user_id: Optional[int] = None,
            guild_id: Optional[int] = None,
            channel_id: Optional[int] = None,
            command_name: Optional[str] = None,
            additional_context: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.operation = operation
        self.severity = severity
        self.category = category
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.command_name = command_name
        self.additional_context = additional_context or {}
        self.timestamp = datetime.now(timezone.utc)
        self.error_id = self._generate_error_id()

    def _generate_error_id(self) -> str:
        """Generate a unique error ID for tracking and correlation."""
        context_str = f"{self.operation}_{type(self.error).__name__}_{self.timestamp.isoformat()}"
        return hashlib.md5(context_str.encode()).hexdigest()[:8]


class ErrorRateLimiter:
    """Rate limiting system to prevent error spam and notification flooding."""

    def __init__(self):
        self.error_counts = defaultdict(lambda: deque(maxlen=100))
        self.cooldown_periods = {
            ErrorSeverity.LOW: 300,  # 5 minutes
            ErrorSeverity.MEDIUM: 180,  # 3 minutes
            ErrorSeverity.HIGH: 60,  # 1 minute
            ErrorSeverity.CRITICAL: 30  # 30 seconds
        }

    async def should_report_error(self, error_context: ErrorContext) -> bool:
        """Determine if an error should be reported based on rate limiting."""
        now = datetime.now(timezone.utc)
        error_key = f"{error_context.category.value}_{type(error_context.error).__name__}"

        # Clean old entries
        cutoff = now - timedelta(seconds=self.cooldown_periods[error_context.severity])
        error_times = self.error_counts[error_key]

        while error_times and error_times[0] < cutoff:
            error_times.popleft()

        # Check if we should report
        should_report = len(error_times) == 0 or error_context.severity == ErrorSeverity.CRITICAL

        # Add this error occurrence
        error_times.append(now)

        return should_report


class ErrorHandler:
    """Centralized error handling system with comprehensive context and recovery."""

    # Class-level error tracking
    _error_statistics = defaultdict(int)
    _error_patterns = defaultdict(list)
    _rate_limiter = ErrorRateLimiter()
    _recovery_handlers: Dict[ErrorCategory, List[Callable]] = defaultdict(list)

    @classmethod
    def register_recovery_handler(cls, category: ErrorCategory, handler: Callable):
        """Register a recovery handler for specific error categories."""
        cls._recovery_handlers[category].append(handler)
        BotLogger.info(f"Registered recovery handler for {category.value}: {handler.__name__}", "ERROR_HANDLER")

    @staticmethod
    async def handle_interaction_error(
            interaction: discord.Interaction,
            error: Exception,
            context: str = "Command",
            user_message: Optional[str] = None,
            log_full_trace: bool = True,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            category: ErrorCategory = None
    ) -> None:
        """Enhanced interaction error handler with comprehensive context and intelligent categorization."""

        # Create comprehensive error context
        error_context = ErrorContext(
            error=error,
            operation=context,
            severity=severity,
            category=category or ErrorHandler._categorize_error(error),
            user_id=interaction.user.id if interaction.user else None,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if hasattr(interaction, 'channel') and interaction.channel else None,
            command_name=getattr(interaction.command, 'name', None) if hasattr(interaction, 'command') else None,
            additional_context={
                "interaction_type": type(interaction).__name__,
                "bot_permissions": ErrorHandler._get_bot_permissions(interaction),
                "user_permissions": ErrorHandler._get_user_permissions(interaction)
            }
        )

        # Update error statistics
        ErrorHandler._update_error_statistics(error_context)

        # Check rate limiting
        should_report = await ErrorHandler._rate_limiter.should_report_error(error_context)

        # Log error with structured data
        await ErrorHandler._log_error_structured(error_context, log_full_trace, should_report)

        # Attempt automatic recovery
        await ErrorHandler._attempt_recovery(error_context)

        # Send user feedback if reporting is not rate limited
        if should_report:
            await ErrorHandler._send_user_feedback(interaction, error_context, user_message)

        # Report to monitoring systems
        await ErrorHandler._report_to_monitoring(error_context)

    @staticmethod
    def _categorize_error(error: Exception) -> ErrorCategory:
        """Automatically categorize errors based on type and content."""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Discord API errors
        if isinstance(error, (discord.HTTPException, discord.DiscordException)):
            if "rate limit" in error_message or "429" in error_message:
                return ErrorCategory.RATE_LIMIT
            return ErrorCategory.DISCORD_API

        # Permission errors
        if isinstance(error, (discord.Forbidden, discord.NotFound)):
            return ErrorCategory.PERMISSIONS

        # Network and timeout errors
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return ErrorCategory.TIMEOUT
        if "network" in error_message or "connection" in error_message:
            return ErrorCategory.NETWORK

        # Database errors
        if any(db_term in error_message for db_term in ["database", "sql", "postgres", "connection pool"]):
            return ErrorCategory.DATABASE

        # Sheets errors
        if any(sheet_term in error_message for sheet_term in ["sheet", "gspread", "google", "quota"]):
            return ErrorCategory.SHEETS

        # Configuration errors
        if any(config_term in error_message for config_term in ["config", "setting", "environment"]):
            return ErrorCategory.CONFIGURATION

        # Validation errors
        if any(val_term in error_type.lower() for val_term in ["validation", "value", "type"]):
            return ErrorCategory.VALIDATION

        return ErrorCategory.UNKNOWN

    @staticmethod
    def _get_bot_permissions(interaction: discord.Interaction) -> Optional[Dict[str, bool]]:
        """Get bot permissions for context."""
        try:
            if (interaction.guild and hasattr(interaction, 'channel') and interaction.channel and
                    interaction.guild.me):
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                return {
                    "send_messages": permissions.send_messages,
                    "embed_links": permissions.embed_links,
                    "manage_roles": permissions.manage_roles,
                    "administrator": permissions.administrator
                }
        except Exception:
            pass
        return None

    @staticmethod
    def _get_user_permissions(interaction: discord.Interaction) -> Optional[Dict[str, bool]]:
        """Get user permissions for context."""
        try:
            if (interaction.guild and interaction.user and
                    hasattr(interaction, 'channel') and interaction.channel):
                if hasattr(interaction.user, 'guild_permissions'):
                    permissions = interaction.channel.permissions_for(interaction.user)
                    return {
                        "administrator": permissions.administrator,
                        "manage_guild": permissions.manage_guild,
                        "manage_messages": permissions.manage_messages,
                        "manage_roles": permissions.manage_roles
                    }
        except Exception:
            pass
        return None

    @staticmethod
    def _update_error_statistics(error_context: ErrorContext) -> None:
        """Update error statistics for monitoring and analysis."""
        try:
            # Update global statistics
            ErrorHandler._error_statistics["total"] += 1
            ErrorHandler._error_statistics[f"category_{error_context.category.value}"] += 1
            ErrorHandler._error_statistics[f"severity_{error_context.severity.value}"] += 1
            ErrorHandler._error_statistics[f"type_{type(error_context.error).__name__}"] += 1

            # Track error patterns
            pattern_key = f"{error_context.category.value}_{type(error_context.error).__name__}"
            ErrorHandler._error_patterns[pattern_key].append(error_context.timestamp)

            # Keep only recent patterns (last 24 hours)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            ErrorHandler._error_patterns[pattern_key] = [
                ts for ts in ErrorHandler._error_patterns[pattern_key] if ts > cutoff
            ]

        except Exception as e:
            BotLogger.error(f"Error updating error statistics: {e}", "ERROR_HANDLER")

    @staticmethod
    async def _log_error_structured(error_context: ErrorContext, log_full_trace: bool, should_report: bool) -> None:
        """Log error with comprehensive structured information."""
        try:
            # Build comprehensive log message
            log_parts = [
                f"[{error_context.operation.upper()}-ERROR] ID: {error_context.error_id}",
                f"Category: {error_context.category.value}",
                f"Severity: {error_context.severity.value}",
                f"Type: {type(error_context.error).__name__}",
                f"Message: {str(error_context.error)}"
            ]

            if error_context.guild_id:
                log_parts.append(f"Guild: {error_context.guild_id}")
            if error_context.user_id:
                log_parts.append(f"User: {error_context.user_id}")
            if error_context.command_name:
                log_parts.append(f"Command: {error_context.command_name}")

            if not should_report:
                log_parts.append("(Rate Limited)")

            if log_full_trace:
                log_parts.append(f"Traceback:\n{traceback.format_exc()}")

            log_message = "\n".join(log_parts)

            # Log with appropriate level based on severity
            if error_context.severity == ErrorSeverity.CRITICAL:
                BotLogger.error(log_message, "ERROR_HANDLER")
            elif error_context.severity == ErrorSeverity.HIGH:
                BotLogger.error(log_message, "ERROR_HANDLER")
            elif error_context.severity == ErrorSeverity.MEDIUM:
                BotLogger.warning(log_message, "ERROR_HANDLER")
            else:
                BotLogger.info(log_message, "ERROR_HANDLER")

        except Exception as e:
            # Fallback logging if structured logging fails
            BotLogger.error(f"Error in structured logging: {e}", "ERROR_HANDLER")
            BotLogger.error(f"Original error: {error_context.error}", "ERROR_HANDLER")

    @staticmethod
    async def _attempt_recovery(error_context: ErrorContext) -> None:
        """Attempt automatic recovery for known error types."""
        try:
            recovery_handlers = ErrorHandler._recovery_handlers.get(error_context.category, [])

            for handler in recovery_handlers:
                try:
                    await handler(error_context)
                    BotLogger.info(f"Recovery handler {handler.__name__} executed successfully", "ERROR_HANDLER")
                except Exception as e:
                    BotLogger.error(f"Recovery handler {handler.__name__} failed: {e}", "ERROR_HANDLER")

        except Exception as e:
            BotLogger.error(f"Error during recovery attempt: {e}", "ERROR_HANDLER")

    @staticmethod
    async def _send_user_feedback(
            interaction: discord.Interaction,
            error_context: ErrorContext,
            user_message: Optional[str] = None
    ) -> None:
        """Send appropriate user feedback based on error context."""
        try:
            # Determine user message based on error category and severity
            if user_message:
                message = user_message
            else:
                message = ErrorHandler._generate_user_message(error_context)

            # Create error embed
            embed = discord.Embed(
                title="⚠️ Something went wrong",
                description=message,
                color=ErrorHandler._get_severity_color(error_context.severity),
                timestamp=error_context.timestamp
            )

            if error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                embed.add_field(
                    name="Error ID",
                    value=f"`{error_context.error_id}`",
                    inline=False
                )

            embed.set_footer(text="If this problem persists, please contact support")

            # Send response
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            BotLogger.error(f"Error sending user feedback: {e}", "ERROR_HANDLER")

    @staticmethod
    def _generate_user_message(error_context: ErrorContext) -> str:
        """Generate appropriate user-facing error message."""
        category_messages = {
            ErrorCategory.DISCORD_API: "Discord is experiencing issues. Please try again in a moment.",
            ErrorCategory.PERMISSIONS: "I don't have the necessary permissions to complete this action.",
            ErrorCategory.VALIDATION: "There was an issue with the provided information. Please check your input.",
            ErrorCategory.DATABASE: "Database is temporarily unavailable. Please try again later.",
            ErrorCategory.SHEETS: "Google Sheets integration is experiencing issues. Please try again later.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please wait a moment before trying again.",
            ErrorCategory.TIMEOUT: "The operation timed out. Please try again.",
            ErrorCategory.NETWORK: "Network connection issue. Please try again in a moment."
        }

        base_message = category_messages.get(
            error_context.category,
            "An unexpected error occurred. Please try again later."
        )

        if error_context.severity == ErrorSeverity.CRITICAL:
            return f"🚨 Critical error: {base_message} Support has been notified."
        elif error_context.severity == ErrorSeverity.HIGH:
            return f"❌ {base_message} If this continues, please contact support."
        else:
            return base_message

    @staticmethod
    def _get_severity_color(severity: ErrorSeverity) -> discord.Color:
        """Get Discord color for error severity."""
        severity_colors = {
            ErrorSeverity.LOW: discord.Color.yellow(),
            ErrorSeverity.MEDIUM: discord.Color.orange(),
            ErrorSeverity.HIGH: discord.Color.red(),
            ErrorSeverity.CRITICAL: discord.Color.dark_red()
        }
        return severity_colors.get(severity, discord.Color.orange())

    @staticmethod
    async def _report_to_monitoring(error_context: ErrorContext) -> None:
        """Report error to monitoring systems if configured."""
        try:
            # This would integrate with external monitoring services
            # For now, we'll just log to Discord if it's a critical error

            if error_context.severity == ErrorSeverity.CRITICAL and error_context.guild_id:
                # Try to get guild for Discord reporting
                pass  # Implementation would depend on available bot instance

        except Exception as e:
            BotLogger.error(f"Error reporting to monitoring: {e}", "ERROR_HANDLER")

    @staticmethod
    def wrap_callback(operation_name: str):
        """
        Decorator for wrapping Discord UI callbacks with error handling.

        This is a convenience wrapper around create_operation_wrapper specifically
        designed for Discord interaction callbacks in views and buttons.
        """

        def decorator(func):
            async def wrapper(self, interaction):
                try:
                    await func(self, interaction)
                except Exception as e:
                    await ErrorHandler.handle_interaction_error(
                        interaction, e, operation_name,
                        severity=ErrorSeverity.MEDIUM,
                        category=ErrorCategory.USER_INPUT
                    )

            return wrapper

        return decorator

    @staticmethod
    def create_operation_wrapper(
            operation_name: str,
            category: ErrorCategory = ErrorCategory.UNKNOWN,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            fallback_return: Any = None,
            log_success: bool = False,
            integration_service: str = None
    ):
        """Create a standardized decorator for consistent error handling across the project."""

        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.perf_counter()
                    try:
                        result = await func(*args, **kwargs)

                        if log_success:
                            duration = time.perf_counter() - start_time
                            BotLogger.success(
                                f"{operation_name} completed successfully in {duration:.2f}s",
                                integration_service or "OPERATION"
                            )

                        return result

                    except Exception as e:
                        duration = time.perf_counter() - start_time

                        # Create error context
                        error_context = ErrorContext(
                            error=e,
                            operation=operation_name,
                            severity=severity,
                            category=category,
                            additional_context={
                                "duration": duration,
                                "function": func.__name__,
                                "integration_service": integration_service
                            }
                        )

                        # Log error
                        await ErrorHandler._log_error_structured(error_context, True, True)

                        # Attempt recovery
                        await ErrorHandler._attempt_recovery(error_context)

                        return fallback_return

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.perf_counter()
                    try:
                        result = func(*args, **kwargs)

                        if log_success:
                            duration = time.perf_counter() - start_time
                            BotLogger.success(
                                f"{operation_name} completed successfully in {duration:.2f}s",
                                integration_service or "OPERATION"
                            )

                        return result

                    except Exception as e:
                        duration = time.perf_counter() - start_time

                        # Create error context
                        error_context = ErrorContext(
                            error=e,
                            operation=operation_name,
                            severity=severity,
                            category=category,
                            additional_context={
                                "duration": duration,
                                "function": func.__name__,
                                "integration_service": integration_service
                            }
                        )

                        # Log error (create task for async logging)
                        asyncio.create_task(ErrorHandler._log_error_structured(error_context, True, True))

                        return fallback_return

                return sync_wrapper

        return decorator

    @staticmethod
    def get_error_statistics() -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        return {
            "statistics": dict(ErrorHandler._error_statistics),
            "patterns": {
                pattern: len(timestamps)
                for pattern, timestamps in ErrorHandler._error_patterns.items()
            },
            "recovery_handlers": {
                category.value: len(handlers)
                for category, handlers in ErrorHandler._recovery_handlers.items()
            }
        }

    @staticmethod
    def reset_statistics():
        """Reset all error statistics."""
        ErrorHandler._error_statistics.clear()
        ErrorHandler._error_patterns.clear()
        BotLogger.info("Reset error handler statistics", "ERROR_HANDLER")


# Convenience decorator for common error handling
def handle_errors(
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        fallback_return: Any = None,
        log_success: bool = False
):
    """Convenience decorator for adding error handling to functions."""

    def decorator(func):
        operation_name = f"{func.__module__}.{func.__name__}"
        return ErrorHandler.create_operation_wrapper(
            operation_name, category, severity, fallback_return, log_success
        )(func)

    return decorator


# Export all important classes and functions
__all__ = [
    'ErrorHandler',
    'ErrorContext',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorRateLimiter',
    'handle_errors'
]