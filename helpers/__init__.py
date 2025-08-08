# helpers/__init__.py

import logging
import sys
from typing import Dict, Any, Optional

# Import core helpers with proper error handling and fallbacks
try:
    from .logging_helper import BotLogger, logger

    logging.info("✅ BotLogger imported successfully")
except ImportError as e:
    logging.critical(f"❌ Failed to import BotLogger: {e}")
    BotLogger = None
    logger = None

try:
    from .error_handler import (
        ErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext,
        handle_errors
    )

    if BotLogger:
        BotLogger.info("✅ ErrorHandler imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ ErrorHandler imported successfully")
except ImportError as e:
    logging.error(f"❌ Failed to import ErrorHandler: {e}")


    # Create minimal ErrorHandler fallback
    class ErrorCategory:
        DISCORD_API = "discord_api"
        USER_INPUT = "user_input"
        SHEETS = "sheets"
        PERMISSIONS = "permissions"
        CONFIGURATION = "configuration"


    class ErrorSeverity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


    class ErrorContext:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


    class ErrorHandler:
        @staticmethod
        async def handle_interaction_error(interaction, error, operation, severity=None, category=None):
            logging.error(f"Error in {operation}: {error}")


    def handle_errors(func):
        return func

# Create ValidationError fallback if not available
try:
    ValidationError = Exception  # Will be overridden if proper import works
except:
    pass

try:
    from .async_helpers import AsyncHelpers, performance_monitor

    if BotLogger:
        BotLogger.info("✅ AsyncHelpers imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ AsyncHelpers imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ AsyncHelpers not available: {e}")
    AsyncHelpers = None
    performance_monitor = None

try:
    from .config_manager import ConfigManager

    if BotLogger:
        BotLogger.info("✅ ConfigManager imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ ConfigManager imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ ConfigManager not available: {e}")
    ConfigManager = None

try:
    from .role_helpers import RoleManager

    if BotLogger:
        BotLogger.info("✅ RoleManager imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ RoleManager imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ RoleManager not available: {e}")
    RoleManager = None

try:
    from .channel_helpers import ChannelManager, open_channel_immediate, close_channel_immediate

    if BotLogger:
        BotLogger.info("✅ ChannelManager imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ ChannelManager imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ ChannelManager not available: {e}")
    ChannelManager = None
    open_channel_immediate = None
    close_channel_immediate = None

try:
    from .embed_helpers import EmbedHelper

    if BotLogger:
        BotLogger.info("✅ EmbedHelper imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ EmbedHelper imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ EmbedHelper not available: {e}")
    EmbedHelper = None

try:
    # Try multiple possible import paths for sheet operations
    try:
        from .sheet_operations import SheetOperations
    except ImportError:
        try:
            from .sheet_helpers import SheetOperations
        except ImportError:
            from helpers.sheet_helpers import SheetOperations

    if BotLogger:
        BotLogger.info("✅ SheetOperations imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ SheetOperations imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ SheetOperations not available: {e}")
    SheetOperations = None

try:
    # Try multiple possible import paths for validators
    try:
        from .validators import Validators, ValidationResult
    except ImportError:
        try:
            from .validation_helpers import Validators, ValidationError, ValidationResult
        except ImportError:
            from helpers.validation_helpers import Validators, ValidationError, ValidationResult

    if BotLogger:
        BotLogger.info("✅ Validators imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ Validators imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ Validators not available: {e}")
    Validators = None
    ValidationResult = None
    # ValidationError was already defined above as fallback

try:
    from .waitlist_helpers import WaitlistManager

    if BotLogger:
        BotLogger.info("✅ WaitlistManager imported successfully", "HELPERS_INIT")
    else:
        logging.info("✅ WaitlistManager imported successfully")
except ImportError as e:
    logging.warning(f"⚠️ WaitlistManager not available: {e}")
    WaitlistManager = None


# FIXED: Comprehensive health validation function
async def validate_helpers_health() -> Dict[str, Any]:
    """
    Validate the health and availability of all helper modules.

    This function checks which helper modules are available and working properly,
    providing detailed diagnostics for troubleshooting.

    Returns:
        Dict containing health status, warnings, and availability info
    """
    health_status = {
        "status": True,
        "critical_errors": [],
        "warnings": [],
        "modules_available": {},
        "module_versions": {},
        "performance_stats": {}
    }

    # Check core modules (critical for basic operation)
    critical_modules = {
        "BotLogger": BotLogger,
        "ErrorHandler": ErrorHandler
    }

    for module_name, module_obj in critical_modules.items():
        available = module_obj is not None
        health_status["modules_available"][module_name] = available

        # FIXED: Don't fail startup for missing ErrorHandler - provide fallback
        if not available and module_name == "ErrorHandler":
            health_status["warnings"].append(f"Using fallback {module_name} implementation")
        elif not available and module_name == "BotLogger":
            health_status["critical_errors"].append(f"Critical module {module_name} not available")
            health_status["status"] = False

    # Check optional modules (warnings only if missing)
    optional_modules = {
        "AsyncHelpers": AsyncHelpers,
        "ConfigManager": ConfigManager,
        "RoleManager": RoleManager,
        "ChannelManager": ChannelManager,
        "EmbedHelper": EmbedHelper,
        "SheetOperations": SheetOperations,
        "Validators": Validators,
        "WaitlistManager": WaitlistManager
    }

    for module_name, module_obj in optional_modules.items():
        available = module_obj is not None
        health_status["modules_available"][module_name] = available

        if not available:
            health_status["warnings"].append(f"Optional module {module_name} not available")

    # Test core functionality
    if BotLogger:
        try:
            # Test logging functionality
            BotLogger.debug("Testing BotLogger functionality", "HEALTH_CHECK")
            health_status["logging_test"] = "passed"
        except Exception as e:
            health_status["warnings"].append(f"BotLogger test failed: {e}")
            health_status["logging_test"] = "failed"

    if ErrorHandler:
        try:
            # Test error handler availability
            health_status["error_handler_test"] = "available"
        except Exception as e:
            health_status["warnings"].append(f"ErrorHandler test failed: {e}")
            health_status["error_handler_test"] = "failed"

    # Get performance statistics if available
    if performance_monitor:
        try:
            health_status["performance_stats"] = performance_monitor.get_stats()
        except Exception as e:
            health_status["warnings"].append(f"Performance stats unavailable: {e}")

    # Get logging statistics if available
    if BotLogger:
        try:
            health_status["logging_stats"] = BotLogger.get_stats()
        except Exception as e:
            health_status["warnings"].append(f"Logging stats unavailable: {e}")

    # Summary
    total_modules = len(critical_modules) + len(optional_modules)
    available_modules = sum(health_status["modules_available"].values())
    health_status["module_availability_ratio"] = f"{available_modules}/{total_modules}"

    # FIXED: More lenient health assessment - don't fail for fallback ErrorHandler
    critical_missing = [name for name, obj in critical_modules.items()
                        if obj is None and name != "ErrorHandler"]

    if critical_missing:
        health_status["overall_health"] = "critical"
        health_status["status"] = False
    elif health_status["warnings"]:
        health_status["overall_health"] = "degraded"
    else:
        health_status["overall_health"] = "healthy"

    if BotLogger:
        BotLogger.info(f"Helpers health check complete: {health_status['overall_health']}", "HEALTH_CHECK")
    else:
        logging.info(f"Helpers health check complete: {health_status['overall_health']}")

    return health_status


async def cleanup_helpers():
    """
    Cleanup helper modules and resources.

    This function is called during bot shutdown to properly clean up
    any resources held by helper modules.
    """
    try:
        if BotLogger:
            BotLogger.info("Starting helpers cleanup", "CLEANUP")
        else:
            logging.info("Starting helpers cleanup")

        # Cleanup performance monitor
        if performance_monitor:
            try:
                if hasattr(performance_monitor, 'cleanup'):
                    performance_monitor.cleanup()
                if BotLogger:
                    BotLogger.debug("Performance monitor cleaned up", "CLEANUP")
            except Exception as e:
                if BotLogger:
                    BotLogger.warning(f"Performance monitor cleanup error: {e}", "CLEANUP")
                else:
                    logging.warning(f"Performance monitor cleanup error: {e}")

        # Cleanup logging system
        if BotLogger:
            try:
                if hasattr(BotLogger, 'reset_stats'):
                    BotLogger.reset_stats()
                BotLogger.debug("Logging system reset", "CLEANUP")
            except Exception as e:
                logging.warning(f"Logging cleanup error: {e}")

        # Cleanup other modules as needed
        cleanup_tasks = []

        if AsyncHelpers and hasattr(AsyncHelpers, 'cleanup'):
            try:
                cleanup_tasks.append(AsyncHelpers.cleanup())
            except Exception as e:
                if BotLogger:
                    BotLogger.warning(f"AsyncHelpers cleanup error: {e}", "CLEANUP")

        # Wait for cleanup tasks
        if cleanup_tasks:
            import asyncio
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        if BotLogger:
            BotLogger.info("Helpers cleanup completed", "CLEANUP")
        else:
            logging.info("Helpers cleanup completed")

    except Exception as e:
        logging.error(f"Error during helpers cleanup: {e}")


def validate_package_integrity() -> bool:
    """
    Validate the integrity and functionality of all helper modules.

    This is a synchronous version for use during startup validation.

    Returns:
        True if critical modules are available, False otherwise
    """
    try:
        # FIXED: Only require BotLogger as truly critical
        critical_available = BotLogger is not None

        if critical_available:
            if BotLogger:
                BotLogger.info("Helpers package validation successful", "HELPERS_INIT")
            else:
                logging.info("Helpers package validation successful")
            return True
        else:
            logging.error("Critical helpers modules not available")
            return False

    except Exception as e:
        logging.error(f"Helpers package validation failed: {e}")
        return False


# Package health check on import - FIXED: More lenient
try:
    if validate_package_integrity():
        if BotLogger:
            BotLogger.success("✅ Critical helpers loaded successfully", "HELPERS_INIT")
        else:
            logging.info("✅ Critical helpers loaded successfully")
    else:
        logging.warning("⚠️ Some helper modules unavailable, using fallbacks")
        # Don't exit - allow bot to start with fallbacks
except Exception as e:
    logging.error(f"Helpers package health check error: {e}")
    logging.warning("Continuing with available modules...")

# Package metadata
__version__ = "2.1.0"
__author__ = "GAL Bot Development Team"


def get_package_info() -> dict:
    """
    Get comprehensive information about the helpers package.

    This function provides version, import status, and health information
    about the helpers package. Useful for debugging and system monitoring.
    """
    try:
        # Available modules check
        modules = {
            "BotLogger": {"available": BotLogger is not None, "version": "2.1.0"},
            "ErrorHandler": {"available": ErrorHandler is not None, "version": "2.1.0"},
            "AsyncHelpers": {"available": AsyncHelpers is not None, "version": "2.1.0"},
            "ConfigManager": {"available": ConfigManager is not None, "version": "2.1.0"},
            "RoleManager": {"available": RoleManager is not None, "version": "2.1.0"},
            "ChannelManager": {"available": ChannelManager is not None, "version": "2.1.0"},
            "EmbedHelper": {"available": EmbedHelper is not None, "version": "2.1.0"},
            "SheetOperations": {"available": SheetOperations is not None, "version": "2.1.0"},
            "Validators": {"available": Validators is not None, "version": "2.1.0"},
            "WaitlistManager": {"available": WaitlistManager is not None, "version": "2.1.0"}
        }

        # Import errors check
        import_errors = []
        for module_name, module_info in modules.items():
            if not module_info["available"]:
                import_errors.append(f"{module_name} not available")

        # Performance stats
        performance_stats = {}
        try:
            if performance_monitor and hasattr(performance_monitor, 'get_stats'):
                performance_stats = performance_monitor.get_stats()
        except:
            performance_stats = {"error": "Performance monitor not available"}

        # Logging stats
        logging_stats = {}
        try:
            if BotLogger and hasattr(BotLogger, 'get_stats'):
                logging_stats = BotLogger.get_stats()
        except:
            logging_stats = {"error": "Logging stats not available"}

        return {
            "package_version": __version__,
            "package_author": __author__,
            "modules": modules,
            "import_errors": import_errors,
            "performance_stats": performance_stats,
            "logging_stats": logging_stats,
            "health_status": "healthy" if not import_errors else "degraded"
        }

    except Exception as e:
        return {
            "error": f"Failed to generate package info: {e}",
            "package_version": __version__,
            "health_status": "error"
        }


# Export all available helpers - ensure all expected names are available
__all__ = [
    # Core logging and error handling
    'BotLogger', 'logger', 'ErrorHandler', 'ErrorCategory',
    'ErrorSeverity', 'ErrorContext', 'handle_errors',

    # Utility helpers
    'AsyncHelpers', 'ConfigManager',

    # Discord-specific helpers
    'RoleManager', 'ChannelManager', 'EmbedHelper',
    'open_channel_immediate', 'close_channel_immediate',

    # Integration helpers
    'SheetOperations', 'Validators', 'ValidationResult', 'WaitlistManager',

    # Monitoring and performance
    'performance_monitor',

    # Package management functions
    'validate_helpers_health', 'cleanup_helpers', 'validate_package_integrity',
    'get_package_info',

    # Package metadata
    '__version__', '__author__'
]

# Make sure ValidationError is available
if 'ValidationError' not in globals():
    ValidationError = Exception