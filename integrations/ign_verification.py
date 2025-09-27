"""
IGN Verification Integration for existing Discord bot registration flow.
This module provides functions to integrate the live-graphics-dashboard verification
service into the existing registration process.
"""

import logging
import os
import sys
from typing import Tuple, Optional, Dict, Any

# Add the live-graphics-dashboard path to import the verification service
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'live-graphics-dashboard')
if dashboard_path not in sys.path:
    sys.path.append(dashboard_path)


async def verify_ign_for_registration(ign: str, region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
    """
    Verify IGN for registration flow with graceful fallback.

    Returns:
        (is_valid, message, riot_data)
        - is_valid: Whether the IGN is valid (True if verification unavailable)
        - message: User-friendly message explaining the result
        - riot_data: Dictionary with Riot API data if valid, None otherwise
    """
    try:
        # Try to import and use the verification service
        from services.ign_verification import verification_service

        if verification_service is None:
            # Service not initialized - allow registration with warning
            logging.warning("IGN verification service not available - allowing registration")
            return True, "⚠️ IGN verification temporarily unavailable - registration allowed", None

        # Use the verification service
        is_valid, message, riot_data = await verification_service.verify_ign(ign, region)

        # Add appropriate emoji to the message
        if is_valid and riot_data:
            return True, f"✅ {message}", riot_data
        elif is_valid and not riot_data:
            return True, f"⚠️ {message}", None
        else:
            return False, f"❌ {message}", None

    except ImportError:
        # Dashboard service not available - graceful fallback
        logging.info("Live graphics dashboard not available - IGN verification disabled")
        return True, "IGN verification not available - registration allowed", None
    except Exception as e:
        # Any other error - allow registration but log the issue
        logging.error(f"IGN verification error: {e}")
        return True, f"⚠️ IGN verification error - registration allowed", None


async def is_verification_available() -> bool:
    """Check if IGN verification service is available."""
    try:
        from services.ign_verification import verification_service
        return verification_service is not None
    except ImportError:
        return False
    except Exception as e:
        logging.error(f"Error checking verification availability: {e}")
        return False


def get_verification_embed_field(is_valid: bool, message: str) -> Dict[str, Any]:
    """
    Get embed field data for verification result.

    Returns:
        Dictionary with name, value, and inline for embed field
    """
    if "✅" in message:
        # Successful verification
        return {
            "name": "🔍 IGN Verification",
            "value": message,
            "inline": False
        }
    elif "⚠️" in message:
        # Warning (verification unavailable or timeout)
        return {
            "name": "🔍 IGN Verification",
            "value": message,
            "inline": False
        }
    elif "❌" in message:
        # Failed verification
        return {
            "name": "🔍 IGN Verification",
            "value": message,
            "inline": False
        }
    else:
        # Fallback
        return {
            "name": "🔍 IGN Verification",
            "value": f"{'✅' if is_valid else '❌'} {message}",
            "inline": False
        }


async def get_verification_stats() -> Dict[str, int]:
    """Get verification statistics if available."""
    try:
        from services.ign_verification import verification_service

        if verification_service is None:
            return {"total_cached": 0, "valid_cached": 0, "expired_cached": 0}

        return await verification_service.get_verification_stats()
    except ImportError:
        return {"total_cached": 0, "valid_cached": 0, "expired_cached": 0}
    except Exception as e:
        logging.error(f"Error getting verification stats: {e}")
        return {"total_cached": 0, "valid_cached": 0, "expired_cached": 0}