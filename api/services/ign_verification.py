"""
IGN Verification Service for Riot Games API integration.
Provides IGN validation and verification for League of Legends accounts.
"""

import asyncio
import logging
import re
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
import aiohttp
import redis.asyncio as redis
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IGNVerificationResult:
    """Result of IGN verification."""
    is_valid: bool
    message: str
    riot_data: Optional[Dict[str, Any]] = None
    summoner_id: Optional[str] = None
    account_id: Optional[str] = None
    puuid: Optional[str] = None
    rank: Optional[str] = None
    level: Optional[int] = None


@dataclass
class VerificationCache:
    """Cached verification result."""
    ign: str
    region: str
    result: IGNVerificationResult
    cached_at: datetime
    expires_at: datetime


class IGNVerificationService:
    """
    Service for verifying League of Legends IGNs using Riot Games API.
    Includes caching, rate limiting, and graceful error handling.
    """

    def __init__(self, riot_api_key: str, redis_url: str = "redis://localhost:6379"):
        """
        Initialize IGN verification service.
        
        Args:
            riot_api_key: Riot Games API key
            redis_url: Redis connection URL for caching
        """
        self.riot_api_key = riot_api_key
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = timedelta(hours=1)  # Cache results for 1 hour
        self.rate_limit_per_minute = 100
        self.rate_limit_per_second = 20
        
        # Riot API endpoints
        self.base_url = "https://{region}.api.riotgames.com"
        self.regions = ["na1", "euw1", "kr", "jp1", "br1", "las", "lan", "oce", "ru", "tr"]
        
        # Request tracking for rate limiting
        self.request_times: List[datetime] = []

    async def initialize(self) -> bool:
        """
        Initialize the service (Redis connection, etc.).
        
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("IGN verification service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize IGN verification service: {e}")
            # Continue without Redis (in-memory fallback)
            self.redis_client = None
            logger.warning("IGN verification service continuing without Redis cache")
            return True

    async def verify_ign(self, ign: str, region: str = "na") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify an IGN using Riot Games API.
        
        Args:
            ign: In-game name to verify (format: "Name#Tag")
            region: Riot server region (default: "na")
            
        Returns:
            Tuple of (is_valid, message, riot_data)
        """
        if not ign or not self.riot_api_key:
            return False, "IGN verification service not available", None

        try:
            # Clean and parse IGN
            ign_clean = self._clean_ign(ign)
            if not ign_clean:
                return False, "Invalid IGN format", None

            name, _, tag = ign_clean.partition("#")
            if not name or not tag:
                return False, "IGN must be in format: Name#Tag", None

            # Check cache first
            cached_result = await self._get_cached_result(ign_clean, region)
            if cached_result:
                logger.info(f"Using cached verification result for {ign_clean}")
                return cached_result.is_valid, cached_result.message, cached_result.riot_data

            # Apply rate limiting
            if not await self._check_rate_limit():
                return False, "Rate limit exceeded - please try again later", None

            # Verify via Riot API
            result = await self._verify_via_riot_api(name.strip(), tag.strip(), region)
            
            # Cache the result
            await self._cache_result(ign_clean, region, result)
            
            return result.is_valid, result.message, result.riot_data

        except Exception as e:
            logger.error(f"Error verifying IGN {ign}: {e}")
            return False, f"Verification error: {str(e)}", None

    def _clean_ign(self, ign: str) -> str:
        """
        Clean and normalize IGN format.
        
        Args:
            ign: Raw IGN string
            
        Returns:
            Cleaned IGN string
        """
        if not ign:
            return ""
            
        # Remove extra whitespace and special characters
        ign = re.sub(r'[\u2066-\u2069]', '', ign)  # Remove Unicode control chars
        ign = ign.strip()
        
        # Ensure proper format
        if "#" not in ign:
            return ""
            
        return ign

    async def _get_cached_result(self, ign: str, region: str) -> Optional[VerificationCache]:
        """
        Get cached verification result.
        
        Args:
            ign: IGN to lookup
            region: Region for the lookup
            
        Returns:
            Cached result if available and not expired, None otherwise
        """
        if not self.redis_client:
            return None

        try:
            cache_key = f"ign_verification:{ign.lower()}:{region}"
            cached_data = await self.redis_client.hgetall(cache_key)
            
            if not cached_data:
                return None

            # Check if cache is expired
            expires_at = datetime.fromisoformat(cached_data.get('expires_at', ''))
            if datetime.now() > expires_at:
                await self.redis_client.delete(cache_key)
                return None

            # Reconstruct result
            result = IGNVerificationResult(
                is_valid=cached_data.get('is_valid') == 'true',
                message=cached_data.get('message', ''),
                riot_data=eval(cached_data.get('riot_data', '{}')) if cached_data.get('riot_data') else None,
                summoner_id=cached_data.get('summoner_id'),
                account_id=cached_data.get('account_id'),
                puuid=cached_data.get('puuid'),
                rank=cached_data.get('rank'),
                level=int(cached_data.get('level', 0)) if cached_data.get('level') else None
            )

            return VerificationCache(
                ign=ign,
                region=region,
                result=result,
                cached_at=datetime.fromisoformat(cached_data.get('cached_at')),
                expires_at=expires_at
            )

        except Exception as e:
            logger.error(f"Error getting cached result for {ign}: {e}")
            return None

    async def _cache_result(self, ign: str, region: str, result: IGNVerificationResult) -> None:
        """
        Cache verification result.
        
        Args:
            ign: IGN that was verified
            region: Region for the verification
            result: Verification result to cache
        """
        if not self.redis_client:
            return

        try:
            cache_key = f"ign_verification:{ign.lower()}:{region}"
            expires_at = datetime.now() + self.cache_ttl

            cache_data = {
                'is_valid': str(result.is_valid).lower(),
                'message': result.message,
                'riot_data': str(result.riot_data) if result.riot_data else '',
                'summoner_id': result.summoner_id or '',
                'account_id': result.account_id or '',
                'puuid': result.puuid or '',
                'rank': result.rank or '',
                'level': str(result.level) if result.level else '',
                'cached_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }

            await self.redis_client.hset(cache_key, mapping=cache_data)
            await self.redis_client.expireat(cache_key, int(expires_at.timestamp()))

        except Exception as e:
            logger.error(f"Error caching result for {ign}: {e}")

    async def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.
        
        Returns:
            True if we can make a request, False otherwise
        """
        now = datetime.now()
        
        # Clean old requests (older than 1 minute)
        self.request_times = [req_time for req_time in self.request_times 
                            if now - req_time < timedelta(minutes=1)]
        
        # Check per-minute limit
        if len(self.request_times) >= self.rate_limit_per_minute:
            return False
        
        # Check per-second limit
        recent_requests = [req_time for req_time in self.request_times 
                         if now - req_time < timedelta(seconds=1)]
        if len(recent_requests) >= self.rate_limit_per_second:
            return False
        
        # Record this request
        self.request_times.append(now)
        return True

    async def _verify_via_riot_api(self, name: str, tag: str, region: str) -> IGNVerificationResult:
        """
        Verify IGN via Riot Games API.
        
        Args:
            name: Summoner name
            tag: Tagline (after #)
            region: Riot server region
            
        Returns:
            Verification result
        """
        # Convert region code
        region_code = self._get_region_code(region)
        if not region_code:
            return IGNVerificationResult(
                is_valid=False,
                message=f"Unsupported region: {region}",
                riot_data=None
            )

        headers = {
            "X-Riot-Token": self.riot_api_key,
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                # Step 1: Get account by Riot ID
                account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
                
                async with session.get(account_url, headers=headers) as response:
                    if response.status == 404:
                        return IGNVerificationResult(
                            is_valid=False,
                            message=f"IGN '{name}#{tag}' not found on Riot servers",
                            riot_data=None
                        )
                    elif response.status == 429:
                        return IGNVerificationResult(
                            is_valid=False,
                            message="Rate limit exceeded - please try again later",
                            riot_data=None
                        )
                    elif response.status != 200:
                        error_text = await response.text()
                        return IGNVerificationResult(
                            is_valid=False,
                            message=f"Riot API error: {response.status} - {error_text}",
                            riot_data=None
                        )

                    account_data = await response.json()
                    puuid = account_data.get('puuid')
                    game_name = account_data.get('gameName')
                    tag_line = account_data.get('tagLine')

                    if not puuid:
                        return IGNVerificationResult(
                            is_valid=False,
                            message="Invalid account data received from Riot API",
                            riot_data=None
                        )

                # Step 2: Get summoner information
                summoner_url = f"https://{region_code}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
                
                async with session.get(summoner_url, headers=headers) as response:
                    if response.status != 200:
                        return IGNVerificationResult(
                            is_valid=True,  # Account exists even if summoner lookup fails
                            message=f"✅ Account '{game_name}#{tag_line}' verified (summoner data unavailable)",
                            riot_data=account_data
                        )

                    summoner_data = await response.json()
                    summoner_id = summoner_data.get('id')
                    account_id = summoner_data.get('accountId')
                    summoner_level = summoner_data.get('summonerLevel')

                # Step 3: Get rank information (optional, for enhanced verification)
                rank_info = None
                try:
                    if summoner_id:
                        rank_url = f"https://{region_code}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
                        
                        async with session.get(rank_url, headers=headers) as response:
                            if response.status == 200:
                                rank_data = await response.json()
                                # Find ranked data (Solo/Duo)
                                ranked_entry = next((entry for entry in rank_data 
                                                  if entry.get('queueType') == 'RANKED_SOLO_5x5'), None)
                                if ranked_entry:
                                    tier = ranked_entry.get('tier', 'UNRANKED')
                                    rank = ranked_entry.get('rank', '')
                                    lp = ranked_entry.get('leaguePoints', 0)
                                    rank_info = f"{tier} {rank} ({lp} LP)" if rank else f"{tier}"
                                else:
                                    rank_info = "UNRANKED"
                except Exception as e:
                    logger.debug(f"Could not fetch rank data: {e}")
                    rank_info = "Unknown"

                # Create comprehensive result
                riot_data = {
                    'puuid': puuid,
                    'gameName': game_name,
                    'tagLine': tag_line,
                    'summonerId': summoner_id,
                    'accountId': account_id,
                    'summonerLevel': summoner_level,
                    'region': region_code,
                    'verifiedAt': datetime.now().isoformat()
                }

                # Success message
                if rank_info and rank_info != "Unknown":
                    message = f"✅ IGN '{game_name}#{tag_line}' verified - Level {summoner_level}, {rank_info}"
                else:
                    message = f"✅ IGN '{game_name}#{tag_line}' verified - Level {summoner_level}"

                return IGNVerificationResult(
                    is_valid=True,
                    message=message,
                    riot_data=riot_data,
                    summoner_id=summoner_id,
                    account_id=account_id,
                    puuid=puuid,
                    rank=rank_info,
                    level=summoner_level
                )

            except asyncio.TimeoutError:
                return IGNVerificationResult(
                    is_valid=False,
                    message="Verification request timed out - please try again",
                    riot_data=None
                )
            except aiohttp.ClientError as e:
                return IGNVerificationResult(
                    is_valid=False,
                    message=f"Network error during verification: {str(e)}",
                    riot_data=None
                )

    def _get_region_code(self, region: str) -> Optional[str]:
        """
        Convert region code to Riot API region format.
        
        Args:
            region: Region code (e.g., "na", "euw")
            
        Returns:
            Riot API region code or None if unsupported
        """
        region_mapping = {
            'na': 'na1',
            'lan': 'la1',
            'las': 'la2',
            'br': 'br1',
            'euw': 'euw1',
            'eune': 'eun1',
            'tr': 'tr1',
            'ru': 'ru',
            'kr': 'kr',
            'jp': 'jp1',
            'oce': 'oc1'
        }
        
        return region_mapping.get(region.lower())

    async def get_verification_stats(self) -> Dict[str, int]:
        """
        Get verification statistics.
        
        Returns:
            Dictionary with verification statistics
        """
        try:
            if not self.redis_client:
                return {
                    "total_cached": 0,
                    "valid_cached": 0, 
                    "expired_cached": 0,
                    "recent_verifications": 0
                }

            # Count cached results
            cache_keys = await self.redis_client.keys("ign_verification:*")
            total_cached = len(cache_keys)
            
            valid_cached = 0
            recent_verifications = 0
            now = datetime.now()
            
            for key in cache_keys[:100]:  # Limit to avoid too many Redis calls
                try:
                    cached_data = await self.redis_client.hgetall(key)
                    if cached_data.get('is_valid') == 'true':
                        valid_cached += 1
                        
                    cached_at = datetime.fromisoformat(cached_data.get('cached_at', ''))
                    if now - cached_at < timedelta(hours=24):
                        recent_verifications += 1
                except Exception:
                    continue

            return {
                "total_cached": total_cached,
                "valid_cached": valid_cached,
                "expired_cached": 0,  # We clean expired entries automatically
                "recent_verifications": recent_verifications
            }

        except Exception as e:
            logger.error(f"Error getting verification stats: {e}")
            return {
                "total_cached": 0,
                "valid_cached": 0,
                "expired_cached": 0,
                "recent_verifications": 0
            }

    async def cleanup(self) -> None:
        """
        Cleanup resources when service is shutting down.
        """
        if self.redis_client:
            await self.redis_client.close()
            logger.info("IGN verification service cleanup completed")


# Global service instance
_verification_service: Optional[IGNVerificationService] = None


async def get_verification_service() -> Optional[IGNVerificationService]:
    """
    Get the global IGN verification service instance.
    
    Returns:
        IGN verification service instance or None if not initialized
    """
    global _verification_service
    return _verification_service


async def initialize_verification_service(riot_api_key: str, redis_url: str = "redis://localhost:6379") -> bool:
    """
    Initialize the global IGN verification service.
    
    Args:
        riot_api_key: Riot Games API key
        redis_url: Redis connection URL
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _verification_service
    
    if not riot_api_key:
        logger.warning("Riot API key not provided - IGN verification disabled")
        return False
    
    try:
        _verification_service = IGNVerificationService(riot_api_key, redis_url)
        success = await _verification_service.initialize()
        
        if success:
            logger.info("✅ IGN verification service initialized")
        else:
            logger.warning("⚠️ IGN verification service initialization failed")
            _verification_service = None
            
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize IGN verification service: {e}")
        _verification_service = None
        return False
