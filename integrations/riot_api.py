# integrations/riot_api.py

import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

import aiohttp

from utils.logging_utils import SecureLogger


logger = SecureLogger(__name__)


# Rank to numeric value for comparison (higher = better rank)
RANK_VALUES = {
    "CHALLENGER": 28,
    "GRANDMASTER": 27,
    "MASTER": 26,
    "DIAMOND": 25,  # Diamond I
    "PLATINUM": 21,  # Platinum I
    "GOLD": 17,      # Gold I
    "SILVER": 13,    # Silver I
    "BRONZE": 9,     # Bronze I
    "IRON": 5,       # Iron I
    "UNRANKED": 0
}

# Division offsets within each tier
DIVISION_OFFSETS = {
    "I": 0,
    "II": -1,
    "III": -2,
    "IV": -3
}


def get_rank_numeric_value(tier: str, division: str = "I", lp: int = 0) -> int:
    """
    Convert rank to numeric value for comparison.
    
    Args:
        tier: The rank tier (e.g., "DIAMOND", "PLATINUM")
        division: The division within the tier ("I", "II", "III", "IV")
        lp: League points (0-100)
        
    Returns:
        Numeric value where higher = better rank
    """
    tier_upper = tier.upper()
    tier_base = RANK_VALUES.get(tier_upper, 0)
    
    # Apply division offset
    division_offset = DIVISION_OFFSETS.get(division.upper(), 0)
    
    # Add LP contribution (100 LP = +0.25 in rank value)
    lp_contribution = lp / 400.0
    
    return tier_base + division_offset + lp_contribution


def parse_rank_string(rank_string: str) -> Tuple[str, str, int]:
    """
    Parse rank string into tier, division, and LP.
    
    Args:
        rank_string: String like "Diamond II 45 LP" or "DIAMOND II"
        
    Returns:
        Tuple of (tier, division, lp)
    """
    if not rank_string or rank_string.upper() == "UNRANKED":
        return "UNRANKED", "I", 0
    
    # Handle special cases
    if "MASTER" in rank_string.upper() or "GRANDMASTER" in rank_string.upper() or "CHALLENGER" in rank_string.upper():
        # For master+, division isn't applicable, extract LP if present
        lp_match = re.search(r'(\d+)\s*LP', rank_string, re.IGNORECASE)
        lp = int(lp_match.group(1)) if lp_match else 0
        
        if "CHALLENGER" in rank_string.upper():
            return "CHALLENGER", "I", lp
        elif "GRANDMASTER" in rank_string.upper():
            return "GRANDMASTER", "I", lp
        elif "MASTER" in rank_string.upper():
            return "MASTER", "I", lp
    
    # Parse regular ranks: "Diamond II 45 LP"
    # Remove LP and get tier/division
    clean_rank = re.sub(r'\d+\s*LP', '', rank_string).strip()
    
    # Extract tier and division
    parts = clean_rank.upper().split()
    if len(parts) >= 2:
        tier = parts[0]
        division = parts[1]
    elif len(parts) == 1:
        tier = parts[0]
        division = "I"
    else:
        return "UNRANKED", "I", 0
    
    # Extract LP if present
    lp_match = re.search(r'(\d+)\s*LP', rank_string, re.IGNORECASE)
    lp = int(lp_match.group(1)) if lp_match else 0
    
    return tier, division, lp


def format_rank_display(tier: str, division: str = "I", lp: int = 0) -> str:
    """
    Format rank components into display string.
    
    Args:
        tier: The rank tier
        division: The division within the tier
        lp: League points
        
    Returns:
        Formatted rank string
    """
    if tier.upper() == "UNRANKED":
        return "Unranked"
    
    # For master+, division is typically not shown
    if tier.upper() in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
        if lp > 0:
            return f"{tier.title()} {lp} LP"
        else:
            return tier.title()
    
    # Regular ranks show tier and division
    if lp > 0:
        return f"{tier.title()} {division} {lp} LP"
    else:
        return f"{tier.title()} {division}"


@dataclass
class PlacementResult:
    """Result of fetching placement for a single player."""
    riot_id: str
    placement: int
    game_datetime: datetime
    success: bool
    error: Optional[str] = None


class RiotAPIError(Exception):
    """Custom exception for Riot API-related errors."""
    pass


class RateLimitError(RiotAPIError):
    """Exception for rate limit errors."""
    pass


class RiotAPI:
    """Riot Games API integration for TFT data."""

    # Regional routing for TFT Match API
    REGIONAL_ENDPOINTS = {
        "na": "americas",
        "euw": "europe",
        "eune": "europe",
        "kr": "asia",
        "jp": "asia",
        "oce": "americas",
        "br": "americas",
        "lan": "americas",
        "las": "americas",
        "ru": "europe",
        "tr": "europe"
    }

    # Platform endpoints for Summoner API
    PLATFORM_ENDPOINTS = {
        "na": "na1",
        "euw": "euw1",
        "eune": "eun1",
        "kr": "kr",
        "jp": "jp1",
        "oce": "oc1",
        "br": "br1",
        "lan": "la1",
        "las": "la2",
        "ru": "ru",
        "tr": "tr1"
    }

    # Maps platform routing (e.g., "na1") to regional routing (e.g., "americas")
    PLATFORM_TO_REGION = {
        # AMERICAS
        "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas", "oc1": "americas",
        # EUROPE
        "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
        # ASIA
        "kr": "asia", "jp1": "asia",
        # SEA (TFT-specific)
        "sg2": "sea", "ph2": "sea", "vn2": "sea", "th2": "sea", "tw2": "sea"
    }

    # Maps regional to list of platforms to try (in priority order)
    REGIONAL_TO_PLATFORMS = {
        "americas": ["na1", "br1", "la1", "la2", "oc1"],
        "europe": ["euw1", "eun1", "tr1", "ru"],
        "asia": ["kr", "jp1"],
        "sea": ["sg2", "ph2", "vn2", "th2", "tw2"]
    }

    def __init__(self):
        self.api_key = os.getenv("RIOT_API_KEY")
        if not self.api_key:
            raise ValueError("RIOT_API_KEY environment variable is required")

        self.session = None
        self._semaphore = asyncio.Semaphore(int(os.getenv("RIOT_API_MAX_CONCURRENCY", "4")))
        self._rate_limit_wait = int(os.getenv("RIOT_API_RETRY_WAIT", "60"))

    logger = SecureLogger(__name__)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"X-Riot-Token": self.api_key}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _get_platform_endpoint(self, region: str) -> str:
        """Get platform endpoint for summoner API calls."""
        region_lower = region.lower()
        if region_lower not in self.PLATFORM_ENDPOINTS:
            raise RiotAPIError(f"Unsupported region: {region}. Supported regions: {list(self.PLATFORM_ENDPOINTS.keys())}")
        return self.PLATFORM_ENDPOINTS[region_lower]

    def _get_regional_endpoint(self, region: str) -> str:
        """Get regional endpoint for match API calls."""
        region_lower = region.lower()
        if region_lower not in self.REGIONAL_ENDPOINTS:
            raise RiotAPIError(f"Unsupported region: {region}. Supported regions: {list(self.REGIONAL_ENDPOINTS.keys())}")
        return self.REGIONAL_ENDPOINTS[region_lower]

    async def _make_request(self, url: str, *, retries: int = 3) -> Dict[str, Any]:
        """Make HTTP request with retry and rate limit handling."""
        if not self.session:
            raise RiotAPIError("Session not initialized. Use async context manager.")

        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                async with self._semaphore:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            return await response.json()

                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", self._rate_limit_wait))
                            logger.warning(
                                "Riot API rate limited request",
                                extra={"retry_after": retry_after, "attempt": attempt, "url": url},
                            )
                            if attempt >= retries:
                                raise RateLimitError(f"Rate limited. Retry after {retry_after} seconds")
                            await asyncio.sleep(retry_after)
                            continue

                        if response.status == 404:
                            raise RiotAPIError("Summoner not found")
                        if response.status == 403:
                            raise RiotAPIError("Forbidden - Invalid API key or expired token")

                        error_text = await response.text()
                        raise RiotAPIError(
                            f"API request failed with status {response.status}: {error_text}"
                        )

            except aiohttp.ClientError as e:
                if attempt >= retries:
                    raise RiotAPIError(f"Network error: {str(e)}") from e
                backoff = min(2 ** attempt, self._rate_limit_wait)
                logger.warning(
                    "Network error from Riot API, retrying",
                    extra={"attempt": attempt, "retries": retries, "backoff": backoff, "url": url},
                )
                await asyncio.sleep(backoff)
                continue

        raise RiotAPIError(f"All retries exhausted for Riot API request: {url}")

    async def get_account_by_riot_id(self, region: str, game_name: str, tag_line: str) -> Dict[str, Any]:
        """Get account information by Riot ID (game name + tag line)."""
        regional = self._get_regional_endpoint(region)
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return await self._make_request(url)

    async def get_active_tft_platform(self, regional: str, puuid: str) -> Optional[str]:
        """
        Get the active TFT platform/shard for a player.
        This tells us which platform server the player is actively playing on.
        
        Args:
            regional: Regional endpoint (e.g., "americas", "europe", "asia", "sea")
            puuid: Player's PUUID
            
        Returns:
            Platform code (e.g., "na1", "kr", "euw1") or None if not found
        """
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/active-shards/by-game/tft/by-puuid/{puuid}"
        try:
            data = await self._make_request(url)
            platform = data.get("activeShard")  # e.g., "na1"
            if platform:
                logger.debug(f"✅ Found active TFT platform {platform} for {puuid[:8]}... in {regional}")
            return platform
        except RiotAPIError as e:
            if "404" in str(e):
                # This is normal - player might not have played TFT on this regional
                logger.debug(f"No active TFT shard for {puuid[:8]}... in {regional}")
            else:
                logger.debug(f"Active shard API error for {puuid[:8]}... in {regional}: {e}")
            return None

    async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
        """Get summoner information by PUUID (tries TFT, falls back to LoL)."""
        platform = self._get_platform_endpoint(region)
        
        # Try TFT API first
        tft_url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        try:
            logger.debug(f"🔍 Trying TFT API: {tft_url}")
            result = await self._make_request(tft_url)
            if result and result.get("id"):  # Has summoner ID - normal case
                logger.debug(f"✅ Got summoner data from TFT API for {puuid[:8]}... in {region}")
                return result
            else:
                # This is the API bug - account exists but no summoner entry
                logger.info(f"⚠️ Account {puuid[:8]}... exists but has no TFT summoner entry in {region}")
                if result:
                    result["_no_summoner_entry"] = True  # Flag for fallback detection
                    return result
                else:
                    logger.debug(f"TFT API returned null/empty for {puuid[:8]}... in {region}")
        except RiotAPIError as e:
            logger.debug(f"TFT Summoner API returned error for {puuid[:8]}... in {region}: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error with TFT Summoner API for {puuid[:8]}... in {region}: {e}")
        
        # Fallback to LoL endpoint (in case TFT player also has LoL account)
        lol_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        try:
            logger.info(f"🔍 Trying LoL API fallback: {lol_url}")
            result = await self._make_request(lol_url)
            if result and result.get("id"):  # Has summoner ID - normal case
                logger.info(f"✅ Got summoner data from LoL API fallback for {puuid[:8]}... in {region}")
                return result
            else:
                # This is the API bug - account exists but no summoner entry
                logger.info(f"⚠️ Account {puuid[:8]}... exists but has no LoL summoner entry in {region}")
                if result:
                    result["_no_summoner_entry"] = True  # Flag for fallback detection
                    return result
                else:
                    logger.debug(f"LoL API returned null/empty for {puuid[:8]}... in {region}")
        except RiotAPIError as e:
            logger.debug(f"LoL Summoner API returned error for {puuid[:8]}... in {region}: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error with LoL Summoner API for {puuid[:8]}... in {region}: {e}")
        
        # No summoner entry found in either TFT or LoL for this region
        raise RiotAPIError(f"No summoner entry found for {puuid[:8]}... in {region}")

    async def get_league_entries(self, region: str, summoner_id: str) -> List[Dict[str, Any]]:
        """Get TFT league (rank) entries for a summoner."""
        platform = self._get_platform_endpoint(region)
        url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner_id}"
        return await self._make_request(url)

    async def get_match_history(self, region: str, puuid: str, count: int = 20) -> List[str]:
        """Get match history for a player."""
        regional = self._get_regional_endpoint(region)
        url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
        return await self._make_request(url)

    async def _fallback_search_league_entries(
        self,
        region: str,
        game_name: str,  # Exact name from Account API
        puuid: str       # For verification
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback method to find rank when Summoner API doesn't return ID.
        Only called when primary flow fails due to missing 'id' field.
        
        Args:
            region: Region to search
            game_name: Exact game name from Account API (case-sensitive)
            puuid: PUUID for verification
            
        Returns:
            Rank data or None
        """
        platform = self._get_platform_endpoint(region)
        
        logger.info(f"🔄 Using fallback tier search for {game_name} in {region} (Summoner ID missing)")
        
        # Search order: Most common tiers first, skip apex tiers (they timeout)
        tier_search_order = [
            # Most common (60% of players)
            ("GOLD", "I"), ("GOLD", "II"), ("GOLD", "III"), ("GOLD", "IV"),
            ("PLATINUM", "I"), ("PLATINUM", "II"), ("PLATINUM", "III"), ("PLATINUM", "IV"),
            
            # High tiers
            ("DIAMOND", "I"), ("DIAMOND", "II"), ("DIAMOND", "III"), ("DIAMOND", "IV"),
            
            # Lower tiers
            ("SILVER", "I"), ("SILVER", "II"), ("SILVER", "III"), ("SILVER", "IV"),
            ("BRONZE", "I"), ("BRONZE", "II"), ("BRONZE", "III"), ("BRONZE", "IV"),
            ("IRON", "I"), ("IRON", "II"), ("IRON", "III"), ("IRON", "IV"),
            
            # Skip Master/GM/Challenger - they cause 504 timeouts
        ]
        
        game_name_lower = game_name.lower().replace(" ", "").replace("_", "")
        
        for tier, division in tier_search_order:
            try:
                url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/{tier}/{division}"
                entries = await self._make_request(url)
                
                if not isinstance(entries, list):
                    continue
                
                # Search for matching summoner
                for entry in entries:
                    entry_name = entry.get("summonerName", "").lower().replace(" ", "").replace("_", "")
                    
                    # Exact match on cleaned names
                    if entry_name == game_name_lower:
                        logger.info(f"✅ Found {game_name} in {tier} {division} via fallback search")
                        return {
                            "tier": tier,
                            "rank": division,
                            "leaguePoints": entry.get("leaguePoints", 0),
                            "wins": entry.get("wins", 0),
                            "losses": entry.get("losses", 0),
                            "queueType": "RANKED_TFT"
                        }
                
                # Rate limit protection
                await asyncio.sleep(0.05)
                
            except RiotAPIError as e:
                if "404" not in str(e):
                    logger.debug(f"Error searching {tier} {division}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Unexpected error in {tier} {division}: {e}")
                continue
        
        logger.info(f"⚠️ No rank found for {game_name} in {region} via fallback search")
        return None

    async def get_match_details(self, region: str, match_id: str) -> Dict[str, Any]:
        """Get detailed match information."""
        regional = self._get_regional_endpoint(region)
        url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        return await self._make_request(url)

    def _parse_riot_id(self, riot_id: str, region: str = "na") -> tuple[str, str]:
        """Parse Riot ID into game name and tag line."""
        if '#' in riot_id:
            game_name, tag_line = riot_id.split('#', 1)
        else:
            # If no # provided, assume it's just the game name and default tag based on region
            game_name = riot_id
            # Default tag lines based on region
            region_tags = {
                "na": "NA1", "br": "BR1", "lan": "LAN", "las": "LAS",
                "euw": "EUW", "eune": "EUNE", "tr": "TR", "ru": "RU",
                "kr": "KR", "jp": "JP1", "oce": "OCE"
            }
            tag_line = region_tags.get(region.lower(), "NA1")
        return game_name.strip(), tag_line.strip()

    async def get_latest_placement(self, region: str, riot_id: str) -> Dict[str, Any]:
        """Get the latest TFT placement for a player using Riot ID."""
        try:
            # Parse Riot ID into game name and tag line
            game_name, tag_line = self._parse_riot_id(riot_id, region)

            # Get account info using Riot ID
            account_data = await self.get_account_by_riot_id(region, game_name, tag_line)
            puuid = account_data["puuid"]

            # Get summoner info using PUUID
            summoner_data = await self.get_summoner_by_puuid(region, puuid)

            # Get recent match history (just the latest match)
            match_ids = await self.get_match_history(region, puuid, count=1)

            if not match_ids:
                return {
                    "success": False,
                    "error": "No recent matches found",
                    "riot_id": riot_id,
                    "region": region.upper()
                }

            # Get match details
            match_details = await self.get_match_details(region, match_ids[0])

            # Find the player's data in participants
            player_data = None
            for participant in match_details["info"]["participants"]:
                if participant["puuid"] == puuid:
                    player_data = participant
                    break

            if not player_data:
                return {
                    "success": False,
                    "error": "Player data not found in match",
                    "riot_id": riot_id,
                    "region": region.upper()
                }

            # Extract placement and other useful info
            return {
                "success": True,
                "riot_id": f"{account_data['gameName']}#{account_data['tagLine']}",
                "game_name": account_data["gameName"],
                "tag_line": account_data["tagLine"],
                "region": region.upper(),
                "placement": player_data["placement"],
                "total_players": len(match_details["info"]["participants"]),
                "game_datetime": match_details["info"]["game_datetime"],
                "game_length": match_details["info"]["game_length"],
                "game_version": match_details["info"]["game_version"],
                "match_id": match_ids[0],
                "level": summoner_data["summonerLevel"]
            }

        except RiotAPIError as e:
            return {
                "success": False,
                "error": str(e),
                "riot_id": riot_id,
                "region": region.upper()
            }
        except Exception as e:
            logger.error(f"Unexpected error in get_latest_placement: {e}")
            return {
                "success": False,
                "error": "An unexpected error occurred",
                "riot_id": riot_id,
                "region": region.upper()
            }

    async def get_placements_batch(
        self,
        riot_ids: List[str],
        region: str = "na",
        batch_delay: float = 1.0,
        batch_size: int = 10
    ) -> Dict[str, PlacementResult]:
        """
        Fetch placements for multiple players with rate limiting.
        
        Args:
            riot_ids: List of Riot IDs to fetch placements for
            region: Riot API region (default: "na")
            batch_delay: Delay between batches in seconds
            batch_size: Number of players to process in each batch
            
        Returns:
            Dictionary mapping riot_id to PlacementResult
        """
        results = {}
        total_players = len(riot_ids)
        
        logger.info(f"Starting batch placement fetch for {total_players} players in region {region.upper()}")
        
        # Process in batches to respect rate limits
        for i in range(0, len(riot_ids), batch_size):
            batch = riot_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(riot_ids) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} players")
            
            # Create tasks for concurrent requests within the batch
            tasks = []
            for riot_id in batch:
                task = self._get_single_placement_safe(riot_id, region)
                tasks.append(task)
            
            # Wait for all tasks in this batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results from this batch
            for j, result in enumerate(batch_results):
                riot_id = batch[j]
                
                if isinstance(result, Exception):
                    # Handle exceptions
                    logger.warning(f"Exception fetching placement for {riot_id}: {result}")
                    results[riot_id] = PlacementResult(
                        riot_id=riot_id,
                        placement=0,
                        game_datetime=datetime.now(),
                        success=False,
                        error=str(result)
                    )
                else:
                    results[riot_id] = result
            
            # Log batch progress
            successful = sum(1 for r in results.values() if r.success)
            logger.info(f"Batch {batch_num}/{total_batches} complete: {successful}/{len(batch)} successful")
            
            # Add delay between batches (except for the last batch)
            if i + batch_size < len(riot_ids):
                await asyncio.sleep(batch_delay)
        
        # Log final results
        successful = sum(1 for r in results.values() if r.success)
        logger.info(f"Batch placement fetch complete: {successful}/{total_players} successful overall")
        
        return results

    async def get_highest_rank_across_accounts(
        self, 
        ign_list: List[str], 
        default_region: str = "na"
    ) -> Dict[str, Any]:
        """
        Get highest rank across multiple IGNs and regions.
        
        Uses proper 4-step flow with active shard detection:
        1. Account API (get puuid) - try all regionals to find account
        2. Active Shard API (get exact platform where they play TFT)
        3. Summoner API (get summoner id using active platform)
        4. League API (get rank entries using active platform)
        
        Args:
            ign_list: List of IGNs to check
            default_region: Default region to start with (not used with new flow)
            
        Returns:
            Dict with highest rank information or Iron IV if not found
        """
        logger.info(f"🎖️ Fetching highest rank for {len(ign_list)} IGNs using 4-step flow")
        
        highest_rank = None
        highest_numeric = 0
        
        # Regionals to try for finding accounts
        regionals_to_check = ["americas", "europe", "asia", "sea"]
        
        for ign in ign_list:
            account_puuid = None
            account_game_name = None
            account_tag_line = None
            riot_id_display = None
            
            # Step 1: Get PUUID (account is global, use americas regional)
            try:
                # Parse Riot ID (use default region for parsing only)
                game_name, tag_line = self._parse_riot_id(ign, default_region)
                
                logger.debug(f"🔍 Step 1: Getting PUUID for {ign}")
                
                # Account API is global - use any regional (americas is fine)
                url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
                account_data = await self._make_request(url)
                
                if account_data and "puuid" in account_data:
                    account_puuid = account_data["puuid"]
                    account_game_name = account_data["gameName"]
                    account_tag_line = account_data["tagLine"]
                    
                    riot_id_display = f"{account_game_name}#{account_tag_line}"
                    logger.info(f"✅ Step 1: Found account {riot_id_display} with PUUID {account_puuid[:8]}...")
                else:
                    logger.warning(f"❌ Account data invalid for {ign}")
                    continue
                    
            except RiotAPIError as e:
                if "404" in str(e):
                    logger.warning(f"❌ Account not found: {ign}")
                else:
                    logger.warning(f"❌ API error for {ign}: {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error for {ign}: {e}")
                continue
            
            # Step 2: Try Active Shard on ALL regionals
            active_platforms = []
            all_regionals = ["americas", "europe", "asia", "sea"]
            
            try:
                logger.debug(f"🔍 Step 2: Checking active TFT shards for {account_puuid[:8]}...")
                
                for regional in all_regionals:
                    platform = await self.get_active_tft_platform(regional, account_puuid)
                    if platform:
                        logger.info(f"✅ Found active shard {platform} in {regional}")
                        active_platforms.append(platform)
                
                if active_platforms:
                    platforms_to_check = active_platforms
                    logger.info(f"✅ Step 2: Found {len(active_platforms)} active platform(s): {active_platforms}")
                else:
                    logger.info(f"ℹ️ Step 2: No active TFT shards - will try ALL platforms")
                    # Fallback: Try ALL platforms from ALL regionals
                    platforms_to_check = (
                        self.REGIONAL_TO_PLATFORMS["americas"] +
                        self.REGIONAL_TO_PLATFORMS["europe"] +
                        self.REGIONAL_TO_PLATFORMS["asia"] +
                        self.REGIONAL_TO_PLATFORMS["sea"]
                    )
                    
            except Exception as e:
                logger.warning(f"❌ Step 2 error: {e}")
                # Fallback to trying ALL platforms
                platforms_to_check = (
                    self.REGIONAL_TO_PLATFORMS["americas"] +
                    self.REGIONAL_TO_PLATFORMS["europe"] +
                    self.REGIONAL_TO_PLATFORMS["asia"] +
                    self.REGIONAL_TO_PLATFORMS["sea"]
                )
            
            if not platforms_to_check:
                logger.warning(f"❌ No platforms to check for {riot_id_display}")
                continue
            
            # Steps 3 & 4: Try each platform until we find rank data
            rank_found = False
            for platform in platforms_to_check:
                # Map platform to region name
                region_name = None
                for region, plat in self.PLATFORM_ENDPOINTS.items():
                    if plat == platform:
                        region_name = region
                        break
                
                if not region_name:
                    logger.debug(f"Could not map platform {platform} to region, skipping")
                    continue
                
                # Try to get summoner and rank data on this platform
                try:
                    logger.debug(f"🔍 Step 3: Trying platform {platform} for {riot_id_display}")
                    
                    # Step 3: Get summoner data using this platform
                    summoner_data = await self.get_summoner_by_puuid(region_name, account_puuid)
                    summoner_id = summoner_data.get("id")
                    
                    if not summoner_id:
                        # Check if this is the known API bug (account exists but no summoner entry)
                        if summoner_data and summoner_data.get("_no_summoner_entry"):
                            # API bug detected - use fallback search on this platform
                            logger.info(f"⚠️ Summoner API bug detected for {riot_id_display} on {platform} - using fallback search")
                            
                            # Use exact game_name from Account API
                            fallback_rank = await self._fallback_search_league_entries(
                                region=region_name,
                                game_name=account_game_name,  # Exact name from API
                                puuid=account_puuid
                            )
                            
                            if fallback_rank:
                                tier = fallback_rank["tier"]
                                division = fallback_rank["rank"]
                                lp = fallback_rank["leaguePoints"]
                                wins = fallback_rank.get("wins", 0)
                                losses = fallback_rank.get("losses", 0)
                                
                                # Skip unplayed accounts
                                if wins == 0 and losses == 0:
                                    logger.debug(f"{riot_id_display}: Has rank entry but 0 games on {platform}")
                                else:
                                    # Compare with highest rank
                                    numeric_value = get_rank_numeric_value(tier, division, lp)
                                    
                                    if numeric_value > highest_numeric:
                                        highest_numeric = numeric_value
                                        highest_rank = {
                                            "tier": tier,
                                            "division": division,
                                            "lp": lp,
                                            "wins": wins,
                                            "losses": losses,
                                            "region": platform.upper(),
                                            "ign": riot_id_display
                                        }
                                    
                                    logger.info(f"✅ Found rank via fallback: {riot_id_display}: {tier} {division} {lp} LP on {platform}")
                                    rank_found = True
                            else:
                                logger.debug(f"No rank found for {riot_id_display} on {platform} via fallback")
                        else:
                            logger.debug(f"No summoner ID found for {riot_id_display} on {platform}")
                        
                        # Continue to next platform
                        continue
                    
                    # Step 4: Get league entries using this platform
                    logger.debug(f"🔍 Step 4: Getting league entries for {riot_id_display} on {platform}")
                    league_entries = await self.get_league_entries(region_name, summoner_id)
                    
                    # Find TFT ranked entry
                    for entry in league_entries:
                        if entry.get("queueType") == "RANKED_TFT":
                            tier = entry.get("tier", "UNRANKED")
                            division = entry.get("rank", "IV")
                            lp = entry.get("leaguePoints", 0)
                            wins = entry.get("wins", 0)
                            losses = entry.get("losses", 0)
                            
                            # Skip new/unplayed accounts
                            if wins == 0 and losses == 0:
                                continue
                            
                            # Compare ranks to find highest
                            numeric_value = get_rank_numeric_value(tier, division, lp)
                            
                            if numeric_value > highest_numeric:
                                highest_numeric = numeric_value
                                highest_rank = {
                                    "tier": tier,
                                    "division": division,
                                    "lp": lp,
                                    "wins": wins,
                                    "losses": losses,
                                    "region": platform.upper(),
                                    "ign": riot_id_display
                                }
                            
                            logger.info(f"✅ Step 4: Found rank for {riot_id_display}: {tier} {division} {lp} LP on {platform}")
                            rank_found = True
                            break  # Found TFT rank, no need to check other entries
                    
                    if rank_found:
                        break  # Stop trying other platforms if we found rank
                    
                    if not league_entries or not any(e.get("queueType") == "RANKED_TFT" for e in league_entries):
                        logger.debug(f"📊 {riot_id_display} on {platform}: Unranked (no TFT ranked games)")
                        
                except RiotAPIError as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        logger.debug(f"No summoner/rank for {riot_id_display} on {platform}, trying next...")
                        continue  # Try next platform
                    else:
                        logger.warning(f"Error on {platform}: {e}")
                        continue
                except Exception as e:
                    logger.debug(f"Unexpected error on {platform}: {e}")
                    continue
            
            if not rank_found:
                logger.info(f"📊 {riot_id_display}: No rank found on any platform in {found_regional}")
                
                # End of platform loop
        
        # Return highest rank found or default to Iron IV
        if highest_rank:
            return {
                "highest_rank": format_rank_display(
                    highest_rank["tier"], 
                    highest_rank["division"], 
                    highest_rank["lp"]
                              ),
                "tier": highest_rank["tier"],
                "division": highest_rank["division"],
                "lp": highest_rank["lp"],
                "found_ign": highest_rank["ign"],
                "region": highest_rank["region"],
                "success": True
            }
        else:
            logger.info(f"No ranks found for {ign_list}, defaulting to Iron IV")
            return {
                "highest_rank": "Iron IV",
                "tier": "IRON",
                "division": "IV",
                "lp": 0,
                "found_ign": ign_list[0] if ign_list else "Unknown",
                "region": "N/A",
                "success": False
            }

    async def _get_single_placement_safe(self, riot_id: str, region: str) -> PlacementResult:
        """
        Safely get placement for a single player, wrapped to handle all exceptions.
        
        Args:
            riot_id: Riot ID of the player
            region: Riot API region
            
        Returns:
            PlacementResult with success/failure information
        """
        try:
            result = await self.get_latest_placement(region, riot_id)
            
            if result["success"]:
                return PlacementResult(
                    riot_id=result["riot_id"],
                    placement=result["placement"],
                    game_datetime=result["game_datetime"],
                    success=True
                )
            else:
                return PlacementResult(
                    riot_id=riot_id,
                    placement=0,
                    game_datetime=datetime.now(),
                    success=False,
                    error=result.get("error", "Unknown error")
                )
                
        except Exception as e:
            logger.error(f"Unexpected error fetching placement for {riot_id}: {e}")
            return PlacementResult(
                riot_id=riot_id,
                placement=0,
                game_datetime=datetime.now(),
                success=False,
                error=str(e)
            )


def validate_region(region: str) -> bool:
    """Validate if a region is supported."""
    return region.lower() in RiotAPI.PLATFORM_ENDPOINTS
