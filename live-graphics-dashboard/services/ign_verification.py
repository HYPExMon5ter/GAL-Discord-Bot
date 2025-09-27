"""
IGN Verification Service for validating Riot IDs during registration.
Integrates with the existing Discord bot registration flow.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

import aiohttp
from ..models.sessions import VerifiedIGN
from ..storage.adapters.base import DatabaseManager


class IGNVerificationError(Exception):
    """Custom exception for IGN verification errors."""
    pass


class IGNVerificationService:
    """Service for verifying IGNs against Riot API with caching and fallback."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.cache_duration_days = 30  # Cache verified IGNs for 30 days
        self.api_timeout = 10  # Timeout for API calls
        self.max_retries = 2

    async def verify_ign(self, ign: str, region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify an IGN against Riot API.

        Returns:
            (is_valid, message, riot_data)
            - is_valid: Whether the IGN is valid
            - message: User-friendly message explaining the result
            - riot_data: Dictionary with Riot API data if valid, None otherwise
        """
        try:
            # Check cache first
            cached_result = await self._check_cache(ign, region)
            if cached_result:
                return True, "IGN verified (cached)", cached_result

            # Try to verify with Riot API
            api_result = await self._verify_with_riot_api(ign, region)
            if api_result["success"]:
                # Cache the successful verification
                await self._cache_verification(ign, region, api_result["data"])
                return True, "IGN verified successfully", api_result["data"]
            else:
                # API returned an error (invalid IGN)
                return False, f"IGN verification failed: {api_result['error']}", None

        except aiohttp.ClientTimeout:
            # Timeout - allow registration but log the issue
            logging.warning(f"IGN verification timeout for {ign} in {region}")
            return True, "IGN verification timed out - registration allowed", None

        except aiohttp.ClientError as e:
            # Network error - allow registration but log the issue
            logging.warning(f"IGN verification network error for {ign} in {region}: {e}")
            return True, "IGN verification unavailable - registration allowed", None

        except Exception as e:
            # Other error - allow registration but log the issue
            logging.error(f"IGN verification error for {ign} in {region}: {e}")
            return True, "IGN verification error - registration allowed", None

    async def _check_cache(self, ign: str, region: str) -> Optional[Dict]:
        """Check if IGN verification is cached and still valid."""
        try:
            session = await self.db_manager.get_session()
            try:
                # Look for cached verification
                verified_ign = session.query(VerifiedIGN).filter(
                    VerifiedIGN.riot_id == ign,
                    VerifiedIGN.region == region.lower()
                ).first()

                if verified_ign and verified_ign.is_valid():
                    return {
                        "riot_id": verified_ign.riot_id,
                        "puuid": verified_ign.puuid,
                        "region": verified_ign.region
                    }
                elif verified_ign and verified_ign.is_expired():
                    # Remove expired entry
                    session.delete(verified_ign)
                    session.commit()

                return None
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error checking IGN cache: {e}")
            return None

    async def _verify_with_riot_api(self, ign: str, region: str) -> Dict[str, Any]:
        """Verify IGN with Riot API using existing RiotAPI class."""
        try:
            # Import the existing RiotAPI class
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from integrations.riot_api import RiotAPI

            # Parse IGN to extract game name and tag
            if '#' in ign:
                game_name, tag_line = ign.split('#', 1)
            else:
                game_name = ign
                # Default tag lines based on region
                region_tags = {
                    "na": "NA1", "br": "BR1", "lan": "LAN", "las": "LAS",
                    "euw": "EUW", "eune": "EUNE", "tr": "TR", "ru": "RU",
                    "kr": "KR", "jp": "JP1", "oce": "OCE"
                }
                tag_line = region_tags.get(region.lower(), "NA1")

            # Use existing RiotAPI for verification
            async with RiotAPI() as riot_api:
                try:
                    # Get account info
                    account_data = await riot_api.get_account_by_riot_id(region, game_name, tag_line)
                    puuid = account_data["puuid"]

                    # Get summoner info to confirm the account exists for TFT
                    summoner_data = await riot_api.get_summoner_by_puuid(region, puuid)

                    return {
                        "success": True,
                        "data": {
                            "riot_id": f"{account_data['gameName']}#{account_data['tagLine']}",
                            "puuid": puuid,
                            "region": region.upper(),
                            "summoner_level": summoner_data.get("summonerLevel", 0)
                        }
                    }

                except Exception as e:
                    error_msg = str(e)
                    if "not found" in error_msg.lower():
                        return {
                            "success": False,
                            "error": f"Riot ID '{ign}' not found. Please check your IGN and try again."
                        }
                    elif "forbidden" in error_msg.lower():
                        return {
                            "success": False,
                            "error": "Riot API access error. Please try again later."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Verification failed: {error_msg}"
                        }

        except ImportError:
            logging.error("Could not import RiotAPI class")
            raise IGNVerificationError("Riot API not available")
        except Exception as e:
            logging.error(f"Error in Riot API verification: {e}")
            raise IGNVerificationError(f"Verification error: {e}")

    async def _cache_verification(self, ign: str, region: str, riot_data: Dict):
        """Cache successful verification result."""
        try:
            session = await self.db_manager.get_session()
            try:
                # Check if already exists
                existing = session.query(VerifiedIGN).filter(
                    VerifiedIGN.riot_id == riot_data["riot_id"],
                    VerifiedIGN.region == region.lower()
                ).first()

                if existing:
                    # Update existing entry
                    existing.puuid = riot_data["puuid"]
                    existing.verified_at = datetime.utcnow()
                    existing.expires_at = datetime.utcnow() + timedelta(days=self.cache_duration_days)
                else:
                    # Create new entry
                    verified_ign = VerifiedIGN(
                        riot_id=riot_data["riot_id"],
                        puuid=riot_data["puuid"],
                        region=region.lower(),
                        verified_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=self.cache_duration_days)
                    )
                    session.add(verified_ign)

                session.commit()
                logging.info(f"Cached IGN verification for {riot_data['riot_id']} in {region}")

            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error caching IGN verification: {e}")

    async def cleanup_expired_cache(self):
        """Remove expired entries from the cache."""
        try:
            session = await self.db_manager.get_session()
            try:
                expired_count = session.query(VerifiedIGN).filter(
                    VerifiedIGN.expires_at < datetime.utcnow()
                ).delete()

                session.commit()
                if expired_count > 0:
                    logging.info(f"Cleaned up {expired_count} expired IGN cache entries")

            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error cleaning up expired cache: {e}")

    async def get_verification_stats(self) -> Dict[str, int]:
        """Get statistics about verification cache."""
        try:
            session = await self.db_manager.get_session()
            try:
                total = session.query(VerifiedIGN).count()
                valid = session.query(VerifiedIGN).filter(
                    VerifiedIGN.expires_at > datetime.utcnow()
                ).count()
                expired = total - valid

                return {
                    "total_cached": total,
                    "valid_cached": valid,
                    "expired_cached": expired
                }
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Error getting verification stats: {e}")
            return {"total_cached": 0, "valid_cached": 0, "expired_cached": 0}


# Global instance - will be initialized when dashboard starts
verification_service: Optional[IGNVerificationService] = None


async def initialize_verification_service(db_manager: DatabaseManager):
    """Initialize the global verification service."""
    global verification_service
    verification_service = IGNVerificationService(db_manager)
    logging.info("IGN verification service initialized")


async def verify_ign_for_registration(ign: str, region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
    """
    Verify IGN for registration flow.
    This function is called from the existing registration process.
    """
    if verification_service is None:
        # If service not initialized, allow registration (fallback behavior)
        logging.warning("IGN verification service not initialized - allowing registration")
        return True, "IGN verification not available - registration allowed", None

    return await verification_service.verify_ign(ign, region)