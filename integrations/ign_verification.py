"""
IGN Verification Integration for existing Discord bot registration flow.
This module provides functions to integrate the live-graphics-dashboard verification
service into the existing registration process.
"""

import os
import sys
import asyncio
from typing import Dict, Optional, Tuple, Any

from utils.logging_utils import SecureLogger

logger = SecureLogger(__name__)

# Add the live-graphics-dashboard path to import the verification service
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'live-graphics-dashboard')
if dashboard_path not in sys.path:
    sys.path.append(dashboard_path)

# All regions for auto-detection
ALL_REGIONS = ["na", "euw", "eune", "kr", "br", "lan", "las", "oce", "jp", "tr", "ru"]


async def verify_ign_for_registration(ign: str, region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
    """
    Verify IGN for registration flow with multi-region detection and graceful fallback.

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
            # Service not initialized - use RiotAPI directly for multi-region support
            logger.info("IGN verification service not available - using RiotAPI with multi-region detection")
            return await _verify_ign_with_riot_api(ign, region)

        # Use the verification service first
        is_valid, message, riot_data = await verification_service.verify_ign(ign, region)

        # If not found in default region, try multi-region detection
        if not is_valid and ("not found" in message.lower() or "404" in message):
            logger.info(f"IGN {ign} not found in {region}, trying multi-region detection")
            return await _verify_ign_with_riot_api(ign, region)

        # Add appropriate emoji to the message
        if is_valid and riot_data:
            return True, f"✅ {message}", riot_data
        elif is_valid and not riot_data:
            return True, f"⚠️ {message}", None
        else:
            return False, f"❌ {message}", None

    except ImportError:
        # Dashboard service not available - use RiotAPI directly
        logger.info("Live graphics dashboard not available - using RiotAPI with multi-region detection")
        return await _verify_ign_with_riot_api(ign, region)
    except Exception as e:
        # Any other error - allow registration but log the issue
        logger.error(f"IGN verification error: {e}")
        return True, f"⚠️ IGN verification error - registration allowed", None


async def _verify_ign_with_riot_api(ign: str, default_region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
    """
    Verify IGN using RiotAPI with multi-region detection.
    
    This is a fallback when the dashboard verification service is not available
    or when we need multi-region support.
    """
    try:
        from integrations.riot_api import RiotAPI, RiotAPIError
        
        # Regions to try (default first, then others)
        regions_to_try = [default_region] + [r for r in ALL_REGIONS if r != default_region]
        
        for region in regions_to_try:
            try:
                logger.debug(f"Verifying {ign} in {region.upper()}")
                
                # Use RiotAPI context manager
                async with RiotAPI() as riot_client:
                    # Parse riot_id into game_name and tag_line
                    game_name, tag_line = riot_client._parse_riot_id(ign, region)
                    
                    # Try to get account info - this validates the IGN exists
                    account_data = await riot_client.get_account_by_riot_id(region, game_name, tag_line)
                    
                    # If we get here, the IGN is valid
                    found_ign = f"{account_data['gameName']}#{account_data['tagLine']}"
                    puuid = account_data['puuid']
                    
                    # Get basic summoner info for additional data
                    summoner_data = await riot_client.get_summoner_by_puuid(region, puuid)
                    
                    riot_data = {
                        "ign": found_ign,
                        "gameName": account_data['gameName'],
                        "tagLine": account_data['tagLine'],
                        "puuid": puuid,
                        "summonerId": summoner_data['id'],
                        "summonerLevel": summoner_data.get('summonerLevel', 0),
                        "region": region.upper(),
                        "accountId": account_data.get('accountId'),
                        "profileIconId": summoner_data.get('profileIconId', 0)
                    }
                    
                    logger.info(f"✅ Verified IGN {ign} as {found_ign} in {region.upper()}")
                    return True, f"✅ Verified in {region.upper()}", riot_data
                    
            except RiotAPIError as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    # Account not found in this region, try next
                    logger.debug(f"IGN {ign} not found in {region.upper()}")
                    continue
                else:
                    # Other API error (rate limit, etc.)
                    logger.warning(f"RiotAPI error verifying {ign} in {region.upper()}: {e}")
                    # Try next region for rate limit errors too
                    if "429" in str(e):
                        await asyncio.sleep(1)  # Brief pause for rate limit
                        continue
                    break
            except Exception as e:
                logger.error(f"Unexpected error verifying {ign} in {region.upper()}: {e}")
                continue
        
        # If we've tried all regions and didn't find the IGN
        return False, f"❌ IGN '{ign}' not found in any region", None
        
    except Exception as e:
        logger.error(f"Error in _verify_ign_with_riot_api: {e}")
        # Allow registration to continue even if verification fails
        return True, f"⚠️ IGN verification failed - registration allowed", None


async def is_verification_available() -> bool:
    """Check if IGN verification service is available."""
    try:
        from services.ign_verification import verification_service
        return verification_service is not None
    except ImportError:
        return False
    except Exception as e:
        logger.error(f"Error checking verification availability: {e}")
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
        logger.error(f"Error getting verification stats: {e}")
        return {"total_cached": 0, "valid_cached": 0, "expired_cached": 0}
