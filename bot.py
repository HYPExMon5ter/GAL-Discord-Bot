# bot.py

import asyncio
import logging
import signal
import sys

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, APPLICATION_ID
from core.commands import setup as setup_commands
from core.events import setup_events
from helpers.environment_helpers import EnvironmentHelper
from utils.logging_utils import mask_token


# Configure logging with better formatting
def setup_logging():
    """Configure logging with proper formatting and levels."""
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)

    # Fix Windows console encoding for Unicode support
    if sys.platform == "win32":
        try:
            # Set console to UTF-8 mode
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            else:
                # Fallback for older Python versions
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except Exception:
            # If encoding setup fails, continue with default encoding
            pass

    class ColoredFormatter(logging.Formatter):
        """Custom formatter with colors for different log levels."""

        COLORS = {
            logging.DEBUG: Style.DIM,
            logging.INFO: "",  # No color for info
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.RED + Style.BRIGHT,
        }

        def format(self, record):
            # Get the color for this log level
            color = self.COLORS.get(record.levelno, "")

            # Format the message
            formatted = super().format(record)

            # Only apply color to WARNING and above
            if record.levelno >= logging.WARNING:
                return f"{color}{formatted}{Style.RESET_ALL}"
            return formatted

    log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create colored formatter for console
    console_formatter = ColoredFormatter(log_format, date_format)

    # Create regular formatter for file
    file_formatter = logging.Formatter(log_format, date_format)

    # Remove all existing handlers first to prevent duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # File handler without colors
    file_handler = logging.FileHandler("gal_bot.log", encoding="utf-8", mode="a")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce discord.py logging noise
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    logging.info("Logging configured successfully")


class GALBot(commands.Bot):
    """Enhanced GAL Discord Bot with comprehensive error handling and monitoring."""

    def __init__(self):
        """Initialize the bot with proper configuration."""
        # Use Discord.py v2 modernized intents constructor
        intents = discord.Intents(
            guilds=True,
            members=True,
            messages=True,
            message_content=True,
            guild_scheduled_events=True
        )

        # Validate required environment variables
        if not APPLICATION_ID:
            raise ValueError("APPLICATION_ID environment variable is required")

        try:
            application_id = int(APPLICATION_ID)
        except ValueError:
            raise ValueError("APPLICATION_ID must be a valid integer")

        super().__init__(
            command_prefix="!gal",  # Prefix for legacy commands (unused but required)
            intents=intents,
            application_id=application_id,
            help_command=None,  # Disable default help command
            case_insensitive=True
        )

        # Bot state tracking
        self._ready = False
        self._shutdown_requested = False
        self._commands_synced = False  # Track if commands have been synced
        self._sync_lock = asyncio.Lock()  # Prevent concurrent syncing

        logging.info(f"GAL Bot initialized with application ID: {application_id}")

    async def setup_hook(self):
        """Setup hook called when the bot is starting up."""
        try:
            logging.info("Starting bot setup...")

            # Log pre-setup command state
            pre_setup_commands = [cmd.name for cmd in self.tree.get_commands()]
            logging.info(f"Commands in tree before setup: {pre_setup_commands}")

            # Setup commands - this adds them to the tree but doesn't sync
            await setup_commands(self)

            # Log post-setup command state
            post_setup_commands = [cmd.name for cmd in self.tree.get_commands()]
            logging.info(f"Commands in tree after setup: {post_setup_commands}")

            # Use lock to prevent concurrent syncing
            async with self._sync_lock:
                # Determine environment and sync strategy
                is_production, dev_guild_id = EnvironmentHelper.get_environment_info()

                logging.info("Preparing to sync commands...")

                if is_production:
                    # Production mode: sync globally ONLY
                    logging.info("Production mode detected, syncing globally...")

                    # Clear any guild-specific commands that might exist
                    if dev_guild_id:
                        try:
                            dev_guild = discord.Object(id=int(dev_guild_id))
                            # Clear guild commands without syncing
                            self.tree.clear_commands(guild=dev_guild)
                            # Sync the clear to remove them
                            await self.tree.sync(guild=dev_guild)
                            logging.info(f"Cleared guild commands from {dev_guild_id}")
                        except Exception as e:
                            logging.warning(f"Could not clear dev guild commands: {e}")

                    # Single global sync
                    logging.info("Starting global command sync...")
                    synced = await self.tree.sync()
                    logging.info(f"Production mode: Synced {len(synced)} commands globally")

                    # List the synced commands
                    for cmd in synced:
                        logging.info(f"  - Synced command: {cmd.name} (ID: {cmd.id})")

                    self._commands_synced = True

                else:
                    # Development mode: Only sync to guild
                    if dev_guild_id:
                        try:
                            dev_guild = discord.Object(id=int(dev_guild_id))

                            # Clear only guild commands (don't sync the clear)
                            self.tree.clear_commands(guild=dev_guild)

                            # Copy global commands to guild for testing
                            self.tree.copy_global_to(guild=dev_guild)

                            # Single sync to the specific guild
                            logging.info(f"Starting guild command sync to {dev_guild_id}...")
                            synced = await self.tree.sync(guild=dev_guild)
                            logging.info(f"Development mode: Synced {len(synced)} commands to guild {dev_guild_id}")

                            # List the synced commands
                            for cmd in synced:
                                logging.info(f"  - Synced command: {cmd.name} (ID: {cmd.id})")

                            self._commands_synced = True

                        except ValueError as e:
                            logging.error(f"Invalid DEV_GUILD_ID: {dev_guild_id}")
                            raise
                        except Exception as e:
                            logging.error(f"Failed to sync commands to dev guild: {e}")
                            raise
                    else:
                        logging.warning("Development mode but no DEV_GUILD_ID set - commands not synced")

            # Setup event handlers
            setup_events(self)

            # Initialize onboard system
            await self._setup_onboard_system()

            # Start dashboard services
            await self._setup_dashboard_services()

            logging.info("Bot setup completed successfully")

        except Exception as e:
            logging.error(f"Failed to setup bot: {e}")
            raise

    async def verify_commands(self):
        """Verify that commands are properly synced and accessible."""
        try:
            # Reduced wait time since we're more efficient now
            await asyncio.sleep(1)

            is_production, dev_guild_id = EnvironmentHelper.get_environment_info()

            if dev_guild_id and not is_production:
                # Check guild commands
                guild = self.get_guild(int(dev_guild_id))
                if guild:
                    # Use tree.fetch_commands for faster retrieval with timeout
                    try:
                        commands = await asyncio.wait_for(self.tree.fetch_commands(guild=guild), timeout=10.0)
                        logging.info(f"Verified {len(commands)} commands in guild {guild.name}")
                    except asyncio.TimeoutError:
                        logging.error("Guild command fetch timed out - skipping verification")
                        return

                    # Check for duplicates
                    command_names = {}
                    duplicates = []
                    for cmd in commands:
                        if cmd.name in command_names:
                            duplicates.append((cmd.name, cmd.id, command_names[cmd.name]))
                        else:
                            command_names[cmd.name] = cmd.id

                    if duplicates:
                        logging.warning(f"Found {len(duplicates)} duplicate commands")
                        for name, id1, id2 in duplicates:
                            logging.warning(f"  - Duplicate: {name} (IDs: {id1}, {id2})")

                        # Attempt to clean up duplicates
                        await self.cleanup_duplicate_commands(guild)
            else:
                # Check global commands
                try:
                    commands = await asyncio.wait_for(self.tree.fetch_commands(), timeout=10.0)
                    logging.info(f"Verified {len(commands)} global commands")
                except asyncio.TimeoutError:
                    logging.error("Global command fetch timed out - skipping verification")
                    return

                # Check for duplicates
                command_names = {}
                duplicates = []
                for cmd in commands:
                    if cmd.name in command_names:
                        duplicates.append((cmd.name, cmd.id, command_names[cmd.name]))
                    else:
                        command_names[cmd.name] = cmd.id

                if duplicates:
                    logging.warning(f"Found {len(duplicates)} duplicate global commands")
                    for name, id1, id2 in duplicates:
                        logging.warning(f"  - Duplicate: {name} (IDs: {id1}, {id2})")

                    # Attempt to clean up duplicates
                    await self.cleanup_duplicate_commands(None)

        except Exception as e:
            logging.error(f"Failed to verify commands: {e}")

    async def cleanup_duplicate_commands(self, guild=None):
        """Remove duplicate commands more efficiently."""
        try:
            if guild:
                commands = await self.tree.fetch_commands(guild=guild)
                target = f"guild {guild.name}"
            else:
                commands = await self.tree.fetch_commands()
                target = "global"

            # Group commands by name
            command_dict = {}
            for cmd in commands:
                if cmd.name not in command_dict:
                    command_dict[cmd.name] = []
                command_dict[cmd.name].append(cmd)

            # Delete duplicates in parallel for speed
            delete_tasks = []
            for name, cmd_list in command_dict.items():
                if len(cmd_list) > 1:
                    logging.info(f"Found {len(cmd_list)} instances of command '{name}' in {target}")

                    # Sort by ID (newer commands have higher IDs)
                    cmd_list.sort(key=lambda x: x.id, reverse=True)

                    # Create delete tasks for all but the newest
                    for cmd in cmd_list[1:]:
                        logging.info(f"Scheduling deletion of duplicate '{name}' (ID: {cmd.id})")
                        delete_tasks.append(cmd.delete())

            # Execute all deletions in parallel
            if delete_tasks:
                logging.info(f"Deleting {len(delete_tasks)} duplicate commands...")
                await asyncio.gather(*delete_tasks, return_exceptions=True)
                logging.info(f"Duplicate cleanup completed for {target}")
            else:
                logging.debug(f"No duplicates found in {target}")

        except Exception as e:
            logging.error(f"Failed to cleanup duplicates: {e}")

    async def on_ready(self):
        """Called when the bot has finished logging in and setting up."""
        if self._ready:
            logging.info(f"Bot reconnected as {self.user}")

            # Re-sync commands on reconnect if needed
            async with self._sync_lock:
                if not self._commands_synced:
                    logging.info("Re-syncing commands after reconnect...")
                    is_production, dev_guild_id = EnvironmentHelper.get_environment_info()

                    if dev_guild_id and not is_production:
                        try:
                            dev_guild = discord.Object(id=int(dev_guild_id))
                            synced = await self.tree.sync(guild=dev_guild)
                            logging.info(f"Re-synced {len(synced)} commands to guild {dev_guild_id}")
                            self._commands_synced = True
                        except Exception as e:
                            logging.error(f"Failed to re-sync commands: {e}")
                    else:
                        try:
                            synced = await self.tree.sync()
                            logging.info(f"Re-synced {len(synced)} commands globally")
                            self._commands_synced = True
                        except Exception as e:
                            logging.error(f"Failed to re-sync commands: {e}")
            return

        self._ready = True
        logging.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logging.info(f"Connected to {len(self.guilds)} guilds")

        # Log guild information
        for guild in self.guilds:
            logging.info(f"  - {guild.name} ({guild.id}) - {guild.member_count} members")

        # Log environment info
        env_type = EnvironmentHelper.get_environment_type()
        logging.info(f"Running in {env_type} mode")

        # Verify commands are accessible
        await self.verify_commands()

        # Initialize column mappings for all guilds
        await self.initialize_column_mappings()

    async def initialize_column_mappings(self):
        """Initialize column mappings for all guilds the bot is in."""
        logging.info("Initializing column mappings for all guilds...")
        
        for guild in self.guilds:
            try:
                from integrations.sheet_detector import ensure_column_mappings_initialized
                success = await ensure_column_mappings_initialized(str(guild.id))
                if success:
                    logging.info(f"✅ Column mappings initialized for guild {guild.name} ({guild.id})")
                else:
                    logging.error(f"❌ Failed to initialize column mappings for guild {guild.name} ({guild.id})")
            except Exception as e:
                logging.error(f"❌ Error initializing column mappings for guild {guild.name} ({guild.id}): {e}")
        
        logging.info("Column mapping initialization completed")

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord."""
        logging.warning("Bot disconnected from Discord")
        self._commands_synced = False  # Reset sync status on disconnect

    async def on_resumed(self):
        """Called when the bot resumes a session."""
        logging.info("Bot session resumed")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logging.info(f"Joined new guild: {guild.name} ({guild.id}) - {guild.member_count} members")

        # Initialize guild-specific data if needed
        try:
            from integrations.sheets import refresh_sheet_cache
            await refresh_sheet_cache(bot=self, force=True)
        except Exception as e:
            logging.error(f"Failed to initialize data for new guild {guild.id}: {e}")

        # Note: Channel setup is handled in the main on_ready event in events.py

    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot is removed from a guild."""
        logging.info(f"Removed from guild: {guild.name} ({guild.id})")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors from prefix commands (though we don't use them)."""
        logging.error(f"Command error in {ctx.command}: {error}")

    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle general bot errors."""
        logging.error(f"Error in event {event_method}", exc_info=True)

    async def _setup_onboard_system(self):
        """Setup onboard system during bot initialization."""
        try:
            # Note: Persistent view registration now happens in on_ready event
            # when guilds are actually available
            logging.info("Onboard system setup deferred to on_ready event")
        except Exception as e:
            logging.error(f"Failed to setup onboard system: {e}")

    async def _setup_dashboard_services(self):
        """Setup and start dashboard services during bot initialization."""
        import os
        
        # Check if dashboard should be enabled
        enable_dashboard = os.getenv("ENABLE_DASHBOARD", "false").lower() == "true"
        
        if not enable_dashboard:
            logging.info("Dashboard services disabled - set ENABLE_DASHBOARD=true to enable")
            return
            
        try:
            # Import here to avoid circular imports
            from services.dashboard_manager import start_dashboard_services
            
            logging.info("Starting dashboard services...")
            success = await start_dashboard_services()
            
            if success:
                logging.info("✅ Dashboard services started successfully")
            else:
                logging.warning("⚠️ Dashboard services failed to start - continuing without dashboard")
                
        except Exception as e:
            logging.error(f"Failed to setup dashboard services: {e}")
            logging.warning("Continuing without dashboard services")


    async def close(self):
        """Cleanup when the bot is shutting down."""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        logging.info("Bot shutdown initiated...")

        try:
            # Stop dashboard services with timeout
            try:
                from services.dashboard_manager import stop_dashboard_services
                # Add timeout to ensure dashboard services stop properly
                await asyncio.wait_for(stop_dashboard_services(), timeout=15.0)
                logging.info("Stopped dashboard services")
            except asyncio.TimeoutError:
                logging.warning("Dashboard services cleanup timed out - forcing termination")
                # Force cleanup by importing the manager directly
                from services.dashboard_manager import get_dashboard_manager
                manager = get_dashboard_manager()
                await manager._cleanup_services_by_ports()
            except Exception as e:
                logging.error(f"Error stopping dashboard services: {e}")

            # Stop event bus
            try:
                # Access event bus from bot instance
                if hasattr(self, 'event_bus') and self.event_bus:
                    await self.event_bus.stop()
                    logging.info("Stopped event bus")
                else:
                    # Fallback: import directly from event_bus module
                    from core.events.event_bus import get_event_bus
                    event_bus = get_event_bus()
                    await event_bus.stop()
                    logging.info("Stopped event bus")
            except Exception as e:
                logging.error(f"Error stopping event bus: {e}")

            # Close any additional resources here
            logging.info("All resources cleaned up successfully")

            # Clean up any database connections
            try:
                from core.persistence import connection_pool
                if connection_pool:
                    connection_pool.closeall()
                    logging.info("Closed database connection pool")
            except Exception as e:
                logging.error(f"Error closing database connections: {e}")

            # Clean up waitlist storage service
            try:
                from helpers.waitlist_helpers import WaitlistManager
                # No connection pool to close - storage service handles cleanup
                logging.info("Waitlist storage service cleanup completed")
            except Exception as e:
                logging.error(f"Error during waitlist cleanup: {e}")

            # Close the bot connection
            await super().close()
            logging.info("Bot shutdown completed successfully")

        except Exception as e:
            logging.error(f"Error during bot shutdown: {e}")

    def run_with_error_handling(self):
        """Run the bot with comprehensive error handling."""

        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully."""
            logging.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.close())

        # Register signal handlers for graceful shutdown
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

        try:
            self.run(DISCORD_TOKEN, log_handler=None)  # We handle logging ourselves
        except discord.LoginFailure:
            logging.error("Failed to login - check your Discord token configuration")
            if DISCORD_TOKEN:
                logging.debug(f"Token format validation failed. Token preview: {mask_token(DISCORD_TOKEN)}")
            else:
                logging.error("DISCORD_TOKEN environment variable is not set")
            sys.exit(1)
        except discord.ConnectionClosed:
            logging.error("Connection to Discord was closed")
            sys.exit(1)
        except KeyboardInterrupt:
            logging.info("Bot shutdown requested via keyboard interrupt")
        except Exception as e:
            logging.error(f"Unexpected error running bot: {e}", exc_info=True)
            sys.exit(1)


async def health_check():
    """Perform a health check of bot components."""
    health_status = {
        "config_valid": True,
        "database_connected": False,
        "sheets_available": False,
        "dashboard_available": False,
        "ign_verification_available": False,
        "errors": []
    }

    try:
        # Check configuration
        from config import validate_configuration
        validate_configuration()
    except Exception as e:
        health_status["config_valid"] = False
        health_status["errors"].append(f"Config validation failed: {e}")

    try:
        # Check database connectivity
        from core.persistence import connection_pool
        if connection_pool:
            health_status["database_connected"] = True
    except Exception as e:
        health_status["errors"].append(f"Database check failed: {e}")

    try:
        # Check sheets integration
        from integrations.sheets import client
        if client:
            health_status["sheets_available"] = True
    except Exception as e:
        health_status["errors"].append(f"Sheets check failed: {e}")

    try:
        # Check dashboard dependencies
        import aiohttp
        import asyncio
        
        # Check if Node.js is available (for frontend)
        import subprocess
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            health_status["dashboard_available"] = True
        else:
            health_status["errors"].append("Node.js not available for dashboard frontend")
            
        # Check if ports are available
        import socket
        def check_port(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) != 0
        
        if check_port(8000) and check_port(3000):
            logging.info("Dashboard ports 8000 and 3000 are available")
        else:
            health_status["errors"].append("Dashboard ports may be in use")
            
    except Exception as e:
        health_status["errors"].append(f"Dashboard dependency check failed: {e}")

    try:
        # Check IGN verification dependencies
        import os
        if os.getenv("RIOT_API_KEY"):
            health_status["ign_verification_available"] = True
        else:
            health_status["errors"].append("RIOT_API_KEY not set - IGN verification will be disabled")
    except Exception as e:
        health_status["errors"].append(f"IGN verification check failed: {e}")

    return health_status


async def startup_checks():
    """Perform startup checks before running the bot."""
    logging.info("Performing startup checks...")

    health = await health_check()

    if not health["config_valid"]:
        logging.error("Configuration validation failed - cannot start bot")
        return False

    if not health["sheets_available"]:
        logging.warning("Google Sheets integration not available")

    if not health["database_connected"]:
        logging.warning("Database not connected - using file fallback")

    if not health["dashboard_available"]:
        logging.warning("Dashboard dependencies not fully available - dashboard may not start")

    if not health["ign_verification_available"]:
        logging.info("IGN verification will be disabled (no RIOT_API_KEY)")

    if health["errors"]:
        logging.warning(f"Startup warnings: {health['errors']}")
        # Log specific warnings for better debugging
        for error in health["errors"]:
            logging.warning(f"  - {error}")

    logging.info("Startup checks completed")
    return True


def main():
    """Main entry point for the bot."""
    # Setup logging first
    setup_logging()

    logging.info("=" * 60)
    logging.info("GAL Discord Bot Starting Up")
    logging.info("=" * 60)

    # Log environment
    EnvironmentHelper.log_environment_info()

    # Validate environment
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN environment variable is required")
        sys.exit(1)

    if not EnvironmentHelper.validate_environment():
        logging.error("Environment validation failed")
        sys.exit(1)

    try:
        # Run startup checks
        if not asyncio.run(startup_checks()):
            logging.error("Startup checks failed - exiting")
            sys.exit(1)

        # Create and run bot
        bot = GALBot()
        logging.info("Starting bot...")
        bot.run_with_error_handling()

    except Exception as e:
        logging.error(f"Fatal error during startup: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("Bot has exited")


if __name__ == "__main__":
    main()
