# bot.py

import asyncio
import os
import signal
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, APPLICATION_ID
from core.commands import setup as setup_commands
from core.events import setup_events
from helpers import (
    BotLogger, ErrorHandler, AsyncHelpers, ValidationError,
    ErrorCategory, ErrorSeverity, handle_errors
)
from utils.utils import validate_utils_health
from integrations import validate_all_integrations


class BotInitializationError(Exception):
    """Exception raised when bot initialization fails."""

    def __init__(self, message: str, component: str, original_error: Optional[Exception] = None):
        self.component = component
        self.original_error = original_error
        self.timestamp = datetime.now(timezone.utc)
        super().__init__(f"Bot initialization failed in {component}: {message}")


class GracefulShutdownError(Exception):
    """Exception raised during graceful shutdown procedures."""

    def __init__(self, message: str, component: str):
        self.component = component
        super().__init__(f"Shutdown error in {component}: {message}")


class GALBot(commands.Bot):
    """
    Enhanced GAL Discord Bot with comprehensive error handling and monitoring.

    This bot class provides robust initialization, health monitoring, graceful
    shutdown capabilities, and integrated logging throughout all operations.
    """

    def __init__(self):
        """Initialize GAL Bot with comprehensive configuration and error handling."""
        try:
            # Configure Discord intents
            intents = self._configure_intents()

            # Parse application ID
            try:
                application_id = int(APPLICATION_ID) if APPLICATION_ID else None
            except (ValueError, TypeError) as e:
                raise BotInitializationError(
                    f"Invalid APPLICATION_ID format: {APPLICATION_ID}",
                    "application_id_parsing",
                    e
                )

            # Initialize bot with comprehensive settings
            super().__init__(
                command_prefix="!gal ",  # Legacy prefix (unused but required)
                intents=intents,
                application_id=application_id,
                help_command=None,  # We use slash commands exclusively
                case_insensitive=True,
                description="GAL Tournament Management Bot",
                chunk_guilds_at_startup=True,  # Load all guild members
                member_cache_flags=discord.MemberCacheFlags.all(),  # Cache all members
            )

            # Initialize bot state tracking - FIXED: Don't override discord.py's _ready
            # The parent class sets _ready as an asyncio.Event, so we use a different name
            self._bot_is_ready = False
            self._shutdown_requested = False
            self._background_tasks: List[asyncio.Task] = []
            self._startup_time = datetime.now(timezone.utc)
            self._error_counts: Dict[str, int] = {}

            # Initialize health monitoring
            self._health_status = {
                "bot_ready": False,
                "commands_synced": False,
                "sheets_connected": False,
                "database_connected": False,
                "last_health_check": None,
                "error_counts": self._error_counts
            }

            BotLogger.info("GAL Bot initialization completed successfully", "BOT_INIT")

        except Exception as e:
            BotLogger.error(f"Critical error during bot initialization: {e}", "BOT_INIT")
            raise BotInitializationError(f"Bot initialization failed: {e}", "bot_init", e)

    def _configure_intents(self) -> discord.Intents:
        """Configure Discord intents with comprehensive permissions for bot functionality."""
        try:
            intents = discord.Intents.default()

            # Required for member management and role operations
            intents.members = True
            intents.guilds = True

            # Required for message and reaction handling
            intents.messages = True
            intents.message_content = True
            intents.reactions = True

            # Required for scheduled event management
            intents.guild_scheduled_events = True

            # Required for voice state tracking (if needed)
            intents.voice_states = True

            # Required for moderation features
            intents.moderation = True

            BotLogger.debug("Discord intents configured successfully", "BOT_INIT")
            return intents

        except Exception as e:
            raise BotInitializationError(f"Intent configuration failed: {e}", "intents", e)

    async def setup_hook(self) -> None:
        """
        Comprehensive bot setup with rollback capabilities and health monitoring.

        This method handles all initialization steps required for the bot to function
        properly, including command registration, event handlers, and health monitoring.
        """
        completed_steps = []

        try:
            BotLogger.info("Starting comprehensive bot setup process...", "SETUP")

            # Step 1: Setup command tree
            BotLogger.info("Step 1: Preparing command tree...", "SETUP")
            self.tree.clear_commands(guild=None)
            completed_steps.append("tree_cleared")

            # Step 2: Setup command handlers
            BotLogger.info("Step 2: Setting up command handlers...", "SETUP")
            try:
                await setup_commands(self)
                BotLogger.success("Successfully set up command handlers", "SETUP")
                completed_steps.append("commands_setup")
            except Exception as e:
                BotLogger.error(f"Command setup failed: {e}", "SETUP")
                raise BotInitializationError("Failed to setup commands", "command_setup", e)

            # Step 3: Setup event handlers
            BotLogger.info("Step 3: Setting up event handlers...", "SETUP")
            try:
                setup_events(self)
                BotLogger.success("Successfully set up event handlers", "SETUP")
                completed_steps.append("events_setup")
            except Exception as e:
                BotLogger.error(f"Event setup failed: {e}", "SETUP")
                raise BotInitializationError("Failed to setup events", "event_setup", e)

            # Step 4: Initialize health monitoring
            BotLogger.info("Step 4: Starting health monitoring...", "SETUP")
            try:
                self._start_health_monitoring()
                BotLogger.success("Health monitoring initialized", "SETUP")
                completed_steps.append("health_monitoring")
            except Exception as e:
                BotLogger.warning(f"Health monitoring setup failed: {e}", "SETUP")
                # Non-critical failure - continue

            # Step 5: Sync commands globally
            BotLogger.info("Step 5: Syncing slash commands globally...", "SETUP")
            try:
                synced = await self.tree.sync()
                BotLogger.success(f"Synced {len(synced)} slash commands globally", "SETUP")
                self._health_status["commands_synced"] = True
                completed_steps.append("commands_synced")
            except Exception as e:
                BotLogger.error(f"Command sync failed: {e}", "SETUP")
                raise BotInitializationError("Failed to sync commands", "command_sync", e)

            BotLogger.success("Bot setup completed successfully!", "SETUP")

        except BotInitializationError:
            # Attempt rollback
            await self._rollback_setup(completed_steps)
            raise

        except Exception as e:
            BotLogger.error(f"Unexpected error during setup: {e}", "SETUP")
            await self._rollback_setup(completed_steps)
            raise BotInitializationError(f"Setup failed unexpectedly: {e}", "setup_hook", e)

    def _start_health_monitoring(self) -> None:
        """Initialize health monitoring background tasks."""
        try:
            # Create health check task
            health_task = asyncio.create_task(self._health_monitor_loop())
            self._background_tasks.append(health_task)

            BotLogger.debug("Health monitoring tasks started", "HEALTH_MONITOR")

        except Exception as e:
            BotLogger.error(f"Failed to start health monitoring: {e}", "HEALTH_MONITOR")
            raise

    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop."""
        while not self._shutdown_requested:
            try:
                # Update health status
                self._health_status.update({
                    "bot_ready": self._bot_is_ready,
                    "last_health_check": datetime.now(timezone.utc).isoformat(),
                    "guilds_connected": len(self.guilds),
                    "latency_ms": round(self.latency * 1000, 2)
                })

                # Sleep for health check interval (5 minutes)
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                BotLogger.info("Health monitor loop cancelled", "HEALTH_MONITOR")
                break
            except Exception as e:
                BotLogger.error(f"Health monitor error: {e}", "HEALTH_MONITOR")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _rollback_setup(self, completed_steps: List[str]) -> None:
        """Attempt to rollback completed setup steps on failure."""
        BotLogger.warning(f"Attempting to rollback setup steps: {completed_steps}", "SETUP")

        for step in reversed(completed_steps):
            try:
                if step == "commands_synced":
                    self.tree.clear_commands(guild=None)
                elif step == "events_setup":
                    # Clear event handlers (limited rollback capability)
                    pass
                elif step == "health_monitoring":
                    # Cancel health monitoring tasks
                    for task in self._background_tasks:
                        if not task.done():
                            task.cancel()
                    self._background_tasks.clear()

                BotLogger.debug(f"Rolled back: {step}", "SETUP")

            except Exception as e:
                BotLogger.error(f"Failed to rollback {step}: {e}", "SETUP")

    def run_with_error_handling(self) -> None:
        """Run the bot with comprehensive error handling and graceful shutdown."""

        def signal_handler(sig, frame):
            """Handle shutdown signals gracefully."""
            BotLogger.info(f"Received signal {sig} - initiating graceful shutdown", "SHUTDOWN")
            self._shutdown_requested = True
            # Create a new task to close the bot
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.close())
            except RuntimeError:
                # No event loop running, this will be handled by the finally block
                pass

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            BotLogger.info("Starting GAL Bot with error handling enabled", "STARTUP")
            self.run(DISCORD_TOKEN, log_handler=None)  # Use our custom logging

        except KeyboardInterrupt:
            BotLogger.info("Received keyboard interrupt", "SHUTDOWN")
        except Exception as e:
            BotLogger.error(f"Bot runtime error: {e}", "RUNTIME")
            raise
        finally:
            if not self._shutdown_requested:
                try:
                    asyncio.run(self._graceful_shutdown())
                except RuntimeError:
                    # Event loop might already be closed
                    BotLogger.info("Event loop already closed during cleanup", "SHUTDOWN")

    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown with comprehensive cleanup."""
        try:
            BotLogger.info("Starting graceful shutdown process", "SHUTDOWN")
            self._shutdown_requested = True

            # Cancel all background tasks
            BotLogger.info("Cancelling background tasks", "SHUTDOWN")
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            # Clean up helpers
            try:
                from helpers import cleanup_helpers
                await cleanup_helpers()
            except ImportError:
                BotLogger.debug("Helpers cleanup not available", "SHUTDOWN")

            # Calculate uptime for final log
            uptime = (datetime.now(timezone.utc) - self._startup_time).total_seconds()

            # Send shutdown log if possible
            if self.guilds and self._bot_is_ready:
                shutdown_info = {
                    "uptime_seconds": uptime,
                    "total_errors": sum(self._error_counts.values()),
                    "guilds_served": len(self.guilds)
                }

                for guild in self.guilds:
                    try:
                        await BotLogger.send_shutdown_log(guild, shutdown_info)
                        break  # Only send to first available guild
                    except Exception:
                        continue

            BotLogger.info(f"Graceful shutdown completed (uptime: {uptime:.1f}s)", "SHUTDOWN")

        except Exception as e:
            BotLogger.error(f"Error during graceful shutdown: {e}", "SHUTDOWN")

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        """Handle bot-level errors with comprehensive logging and context."""
        try:
            # Extract error information
            exc_type, exc_value, exc_traceback = sys.exc_info()

            if exc_value:
                # Update error counts
                error_key = f"event_{event_method}"
                self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

                # Create error context
                error_context = {
                    "event_method": event_method,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()) if kwargs else [],
                    "total_errors": sum(self._error_counts.values())
                }

                # Log the error with context
                BotLogger.error(
                    f"Unhandled error in event '{event_method}': {exc_value}",
                    "BOT_EVENT_ERROR"
                )
                BotLogger.error(
                    f"Event error traceback: {''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}",
                    "BOT_EVENT_ERROR"
                )

                # Use ErrorHandler if available
                if ErrorHandler:
                    await ErrorHandler.handle_interaction_error(
                        None, exc_value, f"bot_event_{event_method}",
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.DISCORD_API
                    )

        except Exception as e:
            BotLogger.error(f"Error in error handler: {e}", "BOT_ERROR_HANDLER")

    async def close(self) -> None:
        """Override close method to ensure proper cleanup."""
        try:
            # Perform our custom shutdown first
            await self._graceful_shutdown()

            # Then call parent close method
            await super().close()

        except Exception as e:
            BotLogger.error(f"Error during bot close: {e}", "SHUTDOWN")
            # Still try to call parent close even if our shutdown fails
            try:
                await super().close()
            except Exception as parent_error:
                BotLogger.error(f"Error in parent close: {parent_error}", "SHUTDOWN")


async def startup_checks() -> bool:
    """
    Comprehensive startup health checks with detailed diagnostics.

    Validates that all critical systems are operational before bot startup.
    Returns True if all checks pass, False if critical issues are detected.
    """
    try:
        BotLogger.info("🏥 Running comprehensive startup health checks", "STARTUP_CHECKS")
        BotLogger.info("=" * 50, "STARTUP_CHECKS")

        health = {
            "overall_status": True,
            "warnings": [],
            "errors": []
        }

        # Environment validation
        BotLogger.info("🔧 Checking environment configuration...", "STARTUP_CHECKS")
        env_check = _check_environment_variables()
        if not env_check["status"]:
            health["overall_status"] = False
            health["errors"].extend(env_check["errors"])

        # Helper system validation - FIXED: More lenient
        BotLogger.info("🔨 Validating helper system integration...", "STARTUP_CHECKS")
        try:
            from helpers import validate_helpers_health
            helper_health = await validate_helpers_health()
            if not helper_health.get("status", False):
                health["warnings"].extend(helper_health.get("warnings", []))
                # FIXED: Don't fail startup for helper issues, just warn
                critical_errors = helper_health.get("critical_errors", [])
                if critical_errors:
                    # Only fail if BotLogger is missing
                    if any("BotLogger" in error for error in critical_errors):
                        health["overall_status"] = False
                        health["errors"].extend(critical_errors)
                    else:
                        health["warnings"].extend(critical_errors)
        except ImportError as e:
            health["warnings"].append(f"Helper validation not available: {e}")

        # Utils system validation
        BotLogger.info("🛠️ Checking utils system health...", "STARTUP_CHECKS")
        try:
            utils_health = await validate_utils_health()
            if not utils_health.get("status", True):
                health["warnings"].extend(utils_health.get("warnings", []))
        except Exception as e:
            health["warnings"].append(f"Utils validation failed: {e}")

        # Integration system validation - FIXED: Much more lenient
        BotLogger.info("🔗 Validating integration systems...", "STARTUP_CHECKS")
        try:
            integration_health = await validate_all_integrations()
            if not integration_health.get("status", True):
                health["warnings"].extend(integration_health.get("warnings", []))
                # FIXED: Sheets unavailable is just a warning, not critical error
                critical_errors = integration_health.get("critical_errors", [])
                for error in critical_errors:
                    if "Google Sheets" in error:
                        health["warnings"].append(f"Non-critical: {error}")
                    else:
                        health["errors"].append(error)
                        health["overall_status"] = False
        except Exception as e:
            health["warnings"].append(f"Integration validation failed: {e}")

        # Discord connectivity test
        BotLogger.info("🌐 Testing Discord API connectivity...", "STARTUP_CHECKS")
        discord_health = await _test_discord_connection()
        if not discord_health["status"]:
            health["overall_status"] = False
            health["errors"].extend(discord_health["errors"])

        # Log results
        BotLogger.info("=" * 50, "STARTUP_CHECKS")

        # Log errors if any
        if health["errors"]:
            BotLogger.error("❌ Critical errors detected:", "STARTUP_CHECKS")
            for i, error in enumerate(health["errors"], 1):
                BotLogger.error(f"  {i}. {error}", "STARTUP_CHECKS")

        # Log warnings if any
        if health["warnings"]:
            BotLogger.warning("⚠️ Warnings:", "STARTUP_CHECKS")
            for i, warning in enumerate(health["warnings"], 1):
                BotLogger.warning(f"  {i}. {warning}", "STARTUP_CHECKS")

        BotLogger.info("=" * 50, "STARTUP_CHECKS")

        # Determine if startup should proceed - FIXED: More lenient
        if health["overall_status"]:
            BotLogger.success("✅ All critical systems are healthy - proceeding with startup", "STARTUP_CHECKS")
            if health["warnings"]:
                BotLogger.info("ℹ️ Bot will start with limited functionality due to warnings above", "STARTUP_CHECKS")
            return True
        else:
            BotLogger.error("❌ Critical issues detected - startup aborted", "STARTUP_CHECKS")
            BotLogger.error("💡 Fix the critical errors above and restart the bot", "STARTUP_CHECKS")
            return False

    except Exception as e:
        BotLogger.error(f"💥 Startup checks failed with unexpected error: {e}", "STARTUP_CHECKS")
        return False


def _check_environment_variables() -> Dict[str, Any]:
    """Check required environment variables."""
    required_vars = ["DISCORD_TOKEN", "APPLICATION_ID"]
    optional_vars = ["DEV_GUILD_ID", "DATABASE_URL", "LOG_CHANNEL_NAME"]

    result = {"status": True, "errors": [], "found": {}, "missing": []}

    for var in required_vars:
        value = os.getenv(var)
        if value:
            result["found"][var] = "✅ Set"
        else:
            result["status"] = False
            result["errors"].append(f"Required environment variable {var} is not set")
            result["missing"].append(var)

    for var in optional_vars:
        value = os.getenv(var)
        result["found"][var] = "✅ Set" if value else "⚠️ Not set (optional)"

    return result


async def _test_discord_connection() -> Dict[str, Any]:
    """Test basic Discord API connectivity."""
    try:
        # Simple HTTP client test to Discord API
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v10/gateway") as response:
                if response.status == 200:
                    return {"status": True}
                else:
                    return {
                        "status": False,
                        "errors": [f"Discord API returned status {response.status}"]
                    }
    except Exception as e:
        return {
            "status": False,
            "errors": [f"Discord connectivity test failed: {e}"]
        }


def main():
    """
    Main entry point for the GAL Discord Bot.

    Provides comprehensive error handling and initialization with detailed
    diagnostics for deployment and operational issues.
    """
    bot_instance = None

    try:
        # Step 1: Initialize logging system
        print("GAL Discord Bot - Initializing...")
        BotLogger.configure_logging()

        BotLogger.info("🎭 GAL (Guardian Angel League) Discord Bot", "MAIN")
        BotLogger.info("=" * 60, "MAIN")
        BotLogger.info("Starting comprehensive initialization sequence...", "MAIN")
        BotLogger.info("=" * 60, "MAIN")

        # Step 2: Validate environment
        BotLogger.info("Step 1: Validating environment...", "MAIN")
        if not DISCORD_TOKEN:
            raise BotInitializationError(
                "DISCORD_TOKEN environment variable is required but not set",
                "environment"
            )

        if not APPLICATION_ID:
            raise BotInitializationError(
                "APPLICATION_ID environment variable is required but not set",
                "environment"
            )

        BotLogger.success("✅ Environment validation passed", "MAIN")

        # Step 3: Run startup checks
        BotLogger.info("Step 2: Running startup health checks...", "MAIN")
        startup_success = asyncio.run(startup_checks())

        if not startup_success:
            BotLogger.error("Startup checks failed - exiting", "MAIN")
            sys.exit(1)

        BotLogger.success("✅ Startup health checks passed", "MAIN")

        # Step 4: Create and run bot
        BotLogger.info("Step 3: Creating bot instance...", "MAIN")
        bot_instance = GALBot()

        BotLogger.info("Step 4: Starting bot...", "MAIN")
        bot_instance.run_with_error_handling()

    except BotInitializationError as e:
        BotLogger.error(f"🚨 Bot initialization failed: {e}", "MAIN")
        BotLogger.error(f"Failed component: {e.component}", "MAIN")
        if e.original_error:
            BotLogger.error(f"Original error: {e.original_error}", "MAIN")
        sys.exit(1)

    except KeyboardInterrupt:
        BotLogger.info("⌨️ Received keyboard interrupt - initiating shutdown", "MAIN")

    except Exception as e:
        BotLogger.error(f"💥 Fatal error during bot operation: {e}", "MAIN")
        BotLogger.error(f"Fatal error traceback: {traceback.format_exc()}", "MAIN")
        sys.exit(1)

    finally:
        try:
            # Final cleanup
            if bot_instance and not bot_instance._shutdown_requested:
                BotLogger.info("🧹 Performing final cleanup...", "MAIN")
                try:
                    asyncio.run(bot_instance.close())
                except RuntimeError:
                    # Event loop might already be closed
                    BotLogger.info("Event loop already closed during final cleanup", "MAIN")
        except Exception as cleanup_error:
            BotLogger.error(f"Error during final cleanup: {cleanup_error}", "MAIN")
        finally:
            BotLogger.info("🏁 GAL Bot has exited", "MAIN")
            BotLogger.info("=" * 60, "MAIN")


# Entry point protection
if __name__ == "__main__":
    main()