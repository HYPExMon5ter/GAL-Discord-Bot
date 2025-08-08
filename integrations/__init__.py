# integrations/__init__.py

import logging
from typing import Dict, Any

# Import integrations with error handling
try:
    from .sheets import (
        refresh_sheet_cache, get_sheet_for_guild, health_check as sheets_health_check
    )

    sheets_available = True
except ImportError as e:
    logging.error(f"Google Sheets integration not available: {e}")
    sheets_available = False


    # Create stub functions
    async def refresh_sheet_cache(*args, **kwargs):
        pass


    def get_sheet_for_guild(*args, **kwargs):
        return None


    async def sheets_health_check():
        return {"status": False, "error": "Sheets integration not available"}

try:
    from .riot_api import get_latest_placement, validate_riot_connection

    riot_available = True
except ImportError as e:
    logging.warning(f"Riot API integration not available: {e}")
    riot_available = False


    # Create stub functions
    async def get_latest_placement(*args, **kwargs):
        return None


    async def validate_riot_connection():
        return {"status": False, "error": "Riot API not available"}

try:
    from .database import get_database_connection, validate_database_connection

    database_available = True
except ImportError as e:
    logging.warning(f"Database integration not available: {e}")
    database_available = False


    # Create stub functions
    def get_database_connection(*args, **kwargs):
        return None


    async def validate_database_connection():
        return {"status": False, "error": "Database integration not available"}


async def validate_all_integrations() -> Dict[str, Any]:
    """
    Validate all available integrations and return comprehensive health status.

    This function checks the health of all integration systems including
    Google Sheets, Riot API, and database connections.

    Returns:
        Dict with status, warnings, errors, and detailed integration info
    """
    try:
        validation_result = {
            "status": True,
            "warnings": [],
            "critical_errors": [],
            "integrations": {},
            "overall_health": "unknown"
        }

        # Validate Google Sheets integration
        if sheets_available:
            try:
                sheets_health = await sheets_health_check()
                validation_result["integrations"]["sheets"] = sheets_health

                if not sheets_health.get("status", False):
                    validation_result["critical_errors"].append("Google Sheets not available")
                    validation_result["status"] = False

            except Exception as e:
                validation_result["integrations"]["sheets"] = {"status": False, "error": str(e)}
                validation_result["critical_errors"].append(f"Google Sheets validation failed: {e}")
                validation_result["status"] = False
        else:
            validation_result["integrations"]["sheets"] = {"status": False, "error": "Module not imported"}
            validation_result["critical_errors"].append("Google Sheets integration not available")
            validation_result["status"] = False

        # Validate Riot API integration (optional)
        if riot_available:
            try:
                riot_health = await validate_riot_connection()
                validation_result["integrations"]["riot_api"] = riot_health

                if not riot_health.get("status", False):
                    validation_result["warnings"].append("Riot API not available")

            except Exception as e:
                validation_result["integrations"]["riot_api"] = {"status": False, "error": str(e)}
                validation_result["warnings"].append(f"Riot API validation failed: {e}")
        else:
            validation_result["integrations"]["riot_api"] = {"status": False, "error": "Module not imported"}
            validation_result["warnings"].append("Riot API integration not available")

        # Validate Database integration (optional)
        if database_available:
            try:
                database_health = await validate_database_connection()
                validation_result["integrations"]["database"] = database_health

                if not database_health.get("status", False):
                    validation_result["warnings"].append("Database not available")

            except Exception as e:
                validation_result["integrations"]["database"] = {"status": False, "error": str(e)}
                validation_result["warnings"].append(f"Database validation failed: {e}")
        else:
            validation_result["integrations"]["database"] = {"status": False, "error": "Module not imported"}
            validation_result["warnings"].append("Database integration not available")

        # Determine overall health
        if validation_result["critical_errors"]:
            validation_result["overall_health"] = "critical"
        elif validation_result["warnings"]:
            validation_result["overall_health"] = "degraded"
        else:
            validation_result["overall_health"] = "healthy"

        # Log summary
        if validation_result["status"]:
            logging.info(f"Integration validation passed with {len(validation_result['warnings'])} warnings")
        else:
            logging.error(f"Integration validation failed: {validation_result['critical_errors']}")

        return validation_result

    except Exception as e:
        logging.error(f"Integration validation failed with error: {e}")
        return {
            "status": False,
            "warnings": [],
            "critical_errors": [f"Validation system error: {e}"],
            "integrations": {},
            "overall_health": "error"
        }


def get_integration_status() -> Dict[str, bool]:
    """
    Get simple availability status for all integrations.

    Returns:
        Dict mapping integration names to availability status
    """
    return {
        "sheets": sheets_available,
        "riot_api": riot_available,
        "database": database_available
    }


def log_integration_status():
    """Log the status of all integrations for diagnostics."""
    status = get_integration_status()

    available = [name for name, available in status.items() if available]
    unavailable = [name for name, available in status.items() if not available]

    if available:
        logging.info(f"Available integrations: {', '.join(available)}")
    if unavailable:
        logging.warning(f"Unavailable integrations: {', '.join(unavailable)}")

    if not available:
        logging.critical("No integrations available - bot functionality will be limited")
    elif "sheets" not in available:
        logging.error("Critical integration failure: Google Sheets not available")


# Log integration status on import
log_integration_status()

# Export available functions
__all__ = [
    # Sheets integration
    'refresh_sheet_cache', 'get_sheet_for_guild', 'sheets_health_check',

    # Riot API integration
    'get_latest_placement', 'validate_riot_connection',

    # Database integration
    'get_database_connection', 'validate_database_connection',

    # Validation functions
    'validate_all_integrations', 'get_integration_status', 'log_integration_status',

    # Status flags
    'sheets_available', 'riot_available', 'database_available'
]