# helpers/logging_helper.py

import asyncio
import logging
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass

import discord

from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER


@dataclass
class LogEntry:
    """Structured log entry for enhanced tracking and analysis."""
    message: str
    level: str
    context: str
    timestamp: datetime
    extra_data: Optional[Dict[str, Any]] = None
    suppressed: bool = False


class LogSuppressionManager:
    """Manages log message deduplication and suppression."""

    def __init__(self, max_similar: int = 3, time_window: int = 300):
        self.max_similar = max_similar
        self.time_window = time_window
        self.recent_messages = deque(maxlen=1000)
        self.suppressed_counts = defaultdict(int)

    def should_suppress(self, message: str, level: str) -> bool:
        """Determine if a message should be suppressed due to similarity."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.time_window)

        # Clean old messages
        while self.recent_messages and self.recent_messages[0].timestamp < cutoff:
            self.recent_messages.popleft()

        # Count similar messages
        similar_count = sum(
            1 for entry in self.recent_messages
            if entry.level == level and self._are_similar(entry.message, message)
        )

        if similar_count >= self.max_similar:
            message_key = self._get_message_key(message)
            self.suppressed_counts[message_key] += 1
            return True

        # Add message to recent tracking
        self.recent_messages.append(LogEntry(message, level, "", now))
        return False

    def _are_similar(self, msg1: str, msg2: str) -> bool:
        """Check if two messages are similar enough to suppress."""
        if len(msg1) < 10 or len(msg2) < 10:
            return msg1.lower() == msg2.lower()

        words1 = set(msg1.lower().split())
        words2 = set(msg2.lower().split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union > 0.7 if union > 0 else False

    def _get_message_key(self, message: str) -> str:
        """Generate a key for tracking message suppression."""
        return message[:50].lower().strip()

    async def report_suppressed_messages(self, guild: discord.Guild) -> None:
        """Report suppressed message counts to Discord channel."""
        if not self.suppressed_counts:
            return

        try:
            log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
            if not log_channel:
                return

            total_suppressed = sum(self.suppressed_counts.values())
            report_lines = [f"📊 **Suppressed {total_suppressed} duplicate log messages:**"]

            for message_key, count in sorted(self.suppressed_counts.items(), key=lambda x: x[1], reverse=True):
                if count > 1:
                    report_lines.append(f"  • `{message_key}...` ({count} times)")

            if len(report_lines) > 1:
                embed = discord.Embed(
                    title="🔇 Log Message Suppression Report",
                    description="\n".join(report_lines[:10]),
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="GAL Bot Logging System")
                await log_channel.send(embed=embed)

            self.suppressed_counts.clear()

        except Exception as e:
            logging.error(f"Failed to report suppressed messages: {e}")


class BotLogger:
    """Centralized logging system with Discord integration and performance monitoring."""

    # Class-level tracking
    _error_counts = defaultdict(int)
    _operation_stats = defaultdict(lambda: {"count": 0, "total_time": 0.0, "errors": 0})
    _last_error_report = datetime.now(timezone.utc)
    _suppression_manager = LogSuppressionManager()

    @staticmethod
    def configure_logging():
        """Configure comprehensive logging for the entire application."""
        try:
            log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
            date_format = "%Y-%m-%d %H:%M:%S"

            class ContextFormatter(logging.Formatter):
                """Enhanced formatter with exception context."""

                def format(self, record):
                    if not hasattr(record, 'thread_name'):
                        record.thread_name = 'MainThread'

                    formatted = super().format(record)

                    if record.exc_info:
                        formatted += f"\nException: {record.exc_info[1]}"

                    return formatted

            formatter = ContextFormatter(log_format, date_format)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)

            # File handler with fallback
            try:
                file_handler = logging.FileHandler("gal_bot.log", encoding="utf-8", mode="a")
                file_handler.setFormatter(formatter)
                file_handler.setLevel(logging.DEBUG)
            except (OSError, PermissionError) as e:
                logging.warning(f"Could not create log file, using console only: {e}")
                file_handler = None

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            root_logger.handlers.clear()
            root_logger.addHandler(console_handler)

            if file_handler:
                root_logger.addHandler(file_handler)

            # Reduce discord.py noise
            logging.getLogger("discord").setLevel(logging.WARNING)
            logging.getLogger("discord.http").setLevel(logging.WARNING)
            logging.getLogger("discord.gateway").setLevel(logging.WARNING)

            BotLogger.info("Logging system configured successfully", "LOGGING_INIT")

        except Exception as e:
            logging.critical(f"Failed to configure logging: {e}")
            sys.exit(1)

    @staticmethod
    async def log_to_channel(
            guild: discord.Guild,
            message: str,
            level: str = "INFO",
            context: Optional[Dict[str, Any]] = None,
            ping_on_error: bool = True
    ) -> bool:
        """Send structured log message to Discord channel."""
        try:
            log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
            if not log_channel:
                return False

            # Check suppression
            if BotLogger._suppression_manager.should_suppress(message, level):
                return True  # Suppressed but "successful"

            embed = BotLogger._create_log_embed(message, level, context)

            # Ping on errors if configured
            content = None
            if level in ["ERROR", "CRITICAL"] and ping_on_error and PING_USER:
                content = f"<@{PING_USER}>"

            await log_channel.send(content=content, embed=embed)
            return True

        except Exception as e:
            logging.error(f"Failed to send log to Discord: {e}")
            return False

    @staticmethod
    def _create_log_embed(message: str, level: str, context: Optional[Dict[str, Any]] = None) -> discord.Embed:
        """Create standardized log embed."""
        level_config = {
            "DEBUG": {"color": discord.Color.light_grey(), "emoji": "🔍"},
            "INFO": {"color": discord.Color.blue(), "emoji": "ℹ️"},
            "SUCCESS": {"color": discord.Color.green(), "emoji": "✅"},
            "WARNING": {"color": discord.Color.orange(), "emoji": "⚠️"},
            "ERROR": {"color": discord.Color.red(), "emoji": "❌"},
            "CRITICAL": {"color": discord.Color.dark_red(), "emoji": "🚨"}
        }

        config = level_config.get(level, level_config["INFO"])

        embed = discord.Embed(
            title=f"{config['emoji']} {level}",
            description=message[:2000],
            color=config["color"],
            timestamp=datetime.now(timezone.utc)
        )

        if context:
            context_items = list(context.items())[:5]
            for key, value in context_items:
                value_str = str(value)[:1000] if value is not None else "None"
                embed.add_field(
                    name=key.replace("_", " ").title(),
                    value=f"```{value_str}```",
                    inline=True
                )

        embed.set_footer(text="GAL Bot Logging System")
        return embed

    @staticmethod
    def debug(message: str, context: str = "", extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug information with optional context and extra data."""
        try:
            formatted_message = f"[{context}] {message}" if context else message

            if extra_data:
                formatted_message += f" | Data: {extra_data}"

            logging.debug(formatted_message)

        except Exception as e:
            logging.error(f"Error in debug logging: {e}")

    @staticmethod
    def info(message: str, context: str = "", extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log informational messages with optional context and extra data."""
        try:
            formatted_message = f"[{context}] {message}" if context else message

            console_message = formatted_message
            if extra_data:
                console_message += f" | Data: {extra_data}"

            logging.info(console_message)

        except Exception as e:
            logging.error(f"Error in info logging: {e}")

    @staticmethod
    def warning(message: str, context: str = "", extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log warning messages with optional context and extra data."""
        try:
            formatted_message = f"[{context}] {message}" if context else message

            console_message = formatted_message
            if extra_data:
                console_message += f" | Data: {extra_data}"

            logging.warning(console_message)
            BotLogger._error_counts[f"warning_{context}"] += 1

        except Exception as e:
            logging.error(f"Error in warning logging: {e}")

    @staticmethod
    def error(message: str, context: str = "", extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log error messages with optional context and extra data."""
        try:
            formatted_message = f"[{context}] {message}" if context else message

            console_message = formatted_message
            if extra_data:
                console_message += f" | Data: {extra_data}"

            logging.error(console_message)
            BotLogger._error_counts[f"error_{context}"] += 1

            asyncio.create_task(BotLogger._check_error_threshold())

        except Exception as e:
            logging.critical(f"Critical error in error logging system: {e}")

    @staticmethod
    def success(message: str, context: str = "", extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log success messages for important operations."""
        try:
            formatted_message = f"[{context}] {message}" if context else message

            console_message = formatted_message
            if extra_data:
                console_message += f" | Data: {extra_data}"

            logging.info(f"SUCCESS: {console_message}")

        except Exception as e:
            logging.error(f"Error in success logging: {e}")

    @staticmethod
    async def log_operation(
            guild: Optional[discord.Guild],
            operation: str,
            user: str,
            details: str = "",
            success: bool = True,
            duration_seconds: Optional[float] = None,
            extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log bot operations with structured data and performance tracking."""
        try:
            # Update operation statistics
            BotLogger._operation_stats[operation]["count"] += 1
            if duration_seconds:
                BotLogger._operation_stats[operation]["total_time"] += duration_seconds
            if not success:
                BotLogger._operation_stats[operation]["errors"] += 1

            # Format log message
            status = "SUCCESS" if success else "FAILED"
            base_message = f"{operation} {status} for {user}"

            if details:
                base_message += f" - {details}"

            if duration_seconds:
                base_message += f" ({duration_seconds:.2f}s)"

            # Log locally
            level_func = BotLogger.success if success else BotLogger.error
            level_func(base_message, "OPERATION", extra_data)

            # Log to Discord if guild provided
            if guild:
                log_level = "SUCCESS" if success else "ERROR"
                context = {"operation": operation, "user": user, "duration": duration_seconds}
                if extra_data:
                    context.update(extra_data)

                await BotLogger.log_to_channel(guild, base_message, log_level, context)

        except Exception as e:
            logging.error(f"Error logging operation: {e}")

    @staticmethod
    async def _check_error_threshold():
        """Check if error threshold is reached and report if necessary."""
        try:
            now = datetime.now(timezone.utc)
            time_since_last_report = (now - BotLogger._last_error_report).total_seconds()

            # Report every hour or if error count is high
            total_errors = sum(count for key, count in BotLogger._error_counts.items() if "error_" in key)

            if time_since_last_report > 3600 or total_errors > 50:
                BotLogger._last_error_report = now
                # This would typically trigger a health report

        except Exception as e:
            logging.error(f"Error checking error threshold: {e}")

    @staticmethod
    async def send_startup_log(guild: discord.Guild, bot_info: Dict[str, Any]) -> None:
        """Send comprehensive bot startup log to Discord."""
        try:
            startup_message = "🚀 **GAL Bot Started Successfully**\n\n"

            if "bot_name" in bot_info:
                startup_message += f"**Bot:** {bot_info['bot_name']}\n"
            if "bot_id" in bot_info:
                startup_message += f"**Bot ID:** {bot_info['bot_id']}\n"
            if "guild_count" in bot_info:
                startup_message += f"**Guilds:** {bot_info['guild_count']}\n"
            if "startup_duration" in bot_info:
                startup_message += f"**Startup Time:** {bot_info['startup_duration']:.2f}s\n"

            startup_message += "\n**System Status:**\n"
            for key, value in bot_info.items():
                if key.startswith("system_") or key.endswith("_status"):
                    clean_key = key.replace("system_", "").replace("_status", "").replace("_", " ").title()
                    status_emoji = "✅" if value else "❌"
                    startup_message += f"{status_emoji} {clean_key}\n"

            await BotLogger.log_to_channel(guild, startup_message, "SUCCESS", bot_info)

        except Exception as e:
            logging.error(f"Failed to send startup log: {e}")

    @staticmethod
    async def send_shutdown_log(guild: discord.Guild, shutdown_info: Dict[str, Any]) -> None:
        """Send bot shutdown log to Discord."""
        try:
            shutdown_message = "👋 **GAL Bot Shutting Down**\n\n"

            if "uptime_seconds" in shutdown_info:
                uptime_hours = shutdown_info["uptime_seconds"] / 3600
                shutdown_message += f"**Uptime:** {uptime_hours:.1f} hours\n"

            if "operations_completed" in shutdown_info:
                shutdown_message += f"**Operations Completed:** {shutdown_info['operations_completed']}\n"

            if "total_errors" in shutdown_info:
                shutdown_message += f"**Total Errors:** {shutdown_info['total_errors']}\n"

            await BotLogger.log_to_channel(guild, shutdown_message, "INFO", shutdown_info)

        except Exception as e:
            logging.error(f"Failed to send shutdown log: {e}")

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get comprehensive logging and performance statistics."""
        return {
            "error_counts": dict(BotLogger._error_counts),
            "operation_stats": dict(BotLogger._operation_stats),
            "last_error_report": BotLogger._last_error_report.isoformat(),
            "suppression_stats": {
                "recent_messages_count": len(BotLogger._suppression_manager.recent_messages),
                "suppressed_counts": dict(BotLogger._suppression_manager.suppressed_counts)
            }
        }

    @staticmethod
    def reset_stats():
        """Reset all logging statistics."""
        try:
            BotLogger._error_counts.clear()
            BotLogger._operation_stats.clear()
            BotLogger._last_error_report = datetime.now(timezone.utc)
            BotLogger._suppression_manager.suppressed_counts.clear()
            logging.info("Reset logging statistics")
        except Exception as e:
            logging.error(f"Error resetting logging statistics: {e}")


# Global logger instance for backward compatibility
logger = BotLogger()

# Export all important classes and functions
__all__ = [
    'BotLogger',
    'logger',
    'LogEntry',
    'LogSuppressionManager'
]