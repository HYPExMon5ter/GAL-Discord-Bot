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

    async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
        """Get summoner information by PUUID (tries TFT, falls back to LoL)."""
        platform = self._get_platform_endpoint(region)
        
        # Try TFT API first (this should work now - the bug is fixed)
        tft_url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        try:
            logger.debug(f"🔍 Trying TFT API: {tft_url}")
            result = await self._make_request(tft_url)
            if result and result.get("id"):  # Fixed: API bug is resolved, just check for "id"
                logger.debug(f"✅ Got summoner data from TFT API for {puuid[:8]}... in {region}")
                return result
            else:
                logger.warning(f"⚠️ TFT API returned incomplete data for {puuid[:8]}... in {region}")
                logger.debug(f"TFT API response: {result}")
        except RiotAPIError as e:
            logger.warning(f"TFT Summoner API failed for {puuid[:8]}... in {region}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error with TFT Summoner API for {puuid[:8]}... in {region}: {e}")
        
        # Fallback to LoL endpoint (in case TFT player also has LoL account)
        lol_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        try:
            logger.info(f"🔍 Trying LoL API fallback: {lol_url}")
            result = await self._make_request(lol_url)
            if result and result.get("id"):  # Fixed: API bug is resolved, just check for "id"
                logger.info(f"✅ Got summoner data from LoL API fallback for {puuid[:8]}... in {region}")
                return result
            else:
                logger.error(f"❌ LoL API also returned incomplete data for {puuid[:8]}... in {region}")
                logger.error(f"LoL API response: {result}")
                raise RiotAPIError("Both TFT and LoL Summoner APIs returned incomplete data")
        except RiotAPIError as e:
            logger.error(f"❌ Both TFT and LoL Summoner APIs failed for {puuid[:8]}... in {region}: {e}")
            raise RiotAPIError(f"Summoner not found: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error with LoL Summoner API for {puuid[:8]}... in {region}: {e}")
            raise RiotAPIError(f"Unexpected error in summoner lookup: {e}")

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
        
        Uses proper 3-step flow (API bug is now fixed):
        1. Account API (get puuid)
        2. Summoner API (get summoner id) 
        3. League API (get rank entries)
        
        Args:
            ign_list: List of IGNs to check
            default_region: Default region to start with
            
        Returns:
            Dict with highest rank information or Iron IV if not found
        """
        logger.info(f"🎖️ Fetching highest rank for {len(ign_list)} IGNs")
        
        highest_rank = None
        highest_numeric = 0
        
        # Try multiple regions - prioritize tournament regions first
        regions_to_check = ["na", "euw", "kr", "br", "jp", "oce"]
        
        for ign in ign_list:
            for region in regions_to_check:
                try:
                    logger.debug(f"🔍 Checking {ign} in {region.upper()}")
                    
                    # Step 1: Get account (PUUID)
                    game_name, tag_line = self._parse_riot_id(ign, region)
                    account_data = await self.get_account_by_riot_id(region, game_name, tag_line)
                    
                    if not account_data or "puuid" not in account_data:
                        logger.debug(f"No account found for {ign} in {region}")
                        continue
                    
                    puuid = account_data["puuid"]
                    riot_id_display = f"{account_data['gameName']}#{account_data['tagLine']}"
                    
                    # Step 2: Get summoner (summoner ID) - API bug should be fixed now
                    try:
                        summoner_data = await self.get_summoner_by_puuid(region, puuid)
                        summoner_id = summoner_data.get("id")
                        
                        if not summoner_id:
                            logger.warning(f"⚠️ No summoner ID returned for {riot_id_display} in {region}")
                            continue
                        
                        # Step 3: Get league entries (RANK!)
                        league_entries = await self.get_league_entries(region, summoner_id)
                        
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
                                        "region": region.upper(),
                                        "ign": riot_id_display
                                    }
                                
                                logger.info(f"✅ Found rank for {riot_id_display}: {tier} {division} {lp} LP")
                                break  # Found TFT rank, no need to check other entries
                        
                        if not league_entries or not any(e.get("queueType") == "RANKED_TFT" for e in league_entries):
                            logger.debug(f"📊 {riot_id_display} in {region}: Unranked (no TFT games)")
                        
                    except RiotAPIError as e:
                        if "404" in str(e) or "not found" in str(e).lower():
                            logger.debug(f"Summoner not found: {ign} in {region}")
                        else:
                            logger.warning(f"Error getting rank for {ign} in {region}: {e}")
                        continue
                        
                except RiotAPIError as e:
                    if "404" in str(e):
                        logger.debug(f"Account not found: {ign} in {region}")
                    else:
                        logger.warning(f"API error for {ign} in {region}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error for {ign} in {region}: {e}")
                    continue
        
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
