# integrations/riot_api.py

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# Try to import HTTP client for API requests
try:
    import aiohttp

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# Configuration
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
API_AVAILABLE = bool(RIOT_API_KEY and HTTP_AVAILABLE)

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # requests per 2 minutes
RATE_LIMIT_WINDOW = 120  # seconds
request_times = []

# Region mapping
REGION_MAPPING = {
    "na": "na1",
    "euw": "euw1",
    "eune": "eun1",
    "kr": "kr",
    "br": "br1",
    "lan": "la1",
    "las": "las",
    "oce": "oc1",
    "ru": "ru",
    "tr": "tr1",
    "jp": "jp1"
}

# TFT API endpoints
TFT_ENDPOINTS = {
    "summoner_by_name": "https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-name/{summonerName}",
    "entries_by_summoner": "https://{region}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summonerId}",
    "matches_by_puuid": "https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids",
    "match_details": "https://{region}.api.riotgames.com/tft/match/v1/matches/{matchId}"
}


class RiotAPIError(Exception):
    """Exception raised for Riot API-related errors."""

    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


def _check_rate_limit() -> bool:
    """Check if we're within rate limits."""
    current_time = time.time()

    # Remove requests older than the window
    global request_times
    request_times = [req_time for req_time in request_times if current_time - req_time < RATE_LIMIT_WINDOW]

    # Check if we can make another request
    return len(request_times) < RATE_LIMIT_REQUESTS


def _record_request():
    """Record a request for rate limiting."""
    request_times.append(time.time())


async def _make_api_request(url: str, headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
    """Make an API request with rate limiting and error handling."""
    if not API_AVAILABLE:
        logging.warning("Riot API not available - missing API key or aiohttp")
        return None

    if not _check_rate_limit():
        logging.warning("Riot API rate limit exceeded - skipping request")
        return None

    try:
        default_headers = {"X-Riot-Token": RIOT_API_KEY}
        if headers:
            default_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=default_headers, timeout=10) as response:
                _record_request()

                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 404:
                    logging.info(f"Riot API: Resource not found (404) for URL: {url}")
                    return None
                elif response.status == 429:
                    logging.warning("Riot API: Rate limit exceeded (429)")
                    return None
                else:
                    error_text = await response.text()
                    logging.error(f"Riot API error {response.status}: {error_text}")
                    raise RiotAPIError(f"API request failed with status {response.status}", response.status)

    except asyncio.TimeoutError:
        logging.error("Riot API request timed out")
        return None
    except Exception as e:
        logging.error(f"Riot API request failed: {e}")
        return None


def _normalize_region(region: str) -> str:
    """Normalize region name to Riot API format."""
    if not region:
        return "na1"

    region = region.lower()
    return REGION_MAPPING.get(region, region)


async def get_summoner_by_name(summoner_name: str, region: str = "na1") -> Optional[Dict[str, Any]]:
    """
    Get summoner information by name.

    Args:
        summoner_name: The summoner's display name
        region: The region (e.g., 'na1', 'euw1')

    Returns:
        Dict with summoner info or None if not found
    """
    if not API_AVAILABLE:
        logging.info(f"Would lookup summoner '{summoner_name}' - Riot API not available")
        return None

    try:
        region = _normalize_region(region)
        url = TFT_ENDPOINTS["summoner_by_name"].format(
            region=region,
            summonerName=summoner_name.replace(" ", "%20")
        )

        summoner_data = await _make_api_request(url)

        if summoner_data:
            logging.info(f"Found summoner {summoner_name} in {region}")
            return summoner_data
        else:
            logging.info(f"Summoner {summoner_name} not found in {region}")
            return None

    except Exception as e:
        logging.error(f"Failed to get summoner {summoner_name}: {e}")
        return None


async def get_tft_rank(summoner_id: str, region: str = "na1") -> Optional[Dict[str, Any]]:
    """
    Get TFT rank information for a summoner.

    Args:
        summoner_id: The summoner's encrypted ID
        region: The region

    Returns:
        Dict with rank info or None if not found
    """
    if not API_AVAILABLE:
        logging.info(f"Would get TFT rank for {summoner_id} - Riot API not available")
        return None

    try:
        region = _normalize_region(region)
        url = TFT_ENDPOINTS["entries_by_summoner"].format(
            region=region,
            summonerId=summoner_id
        )

        rank_data = await _make_api_request(url)

        if rank_data and isinstance(rank_data, list) and len(rank_data) > 0:
            # Return the first (usually only) ranked entry
            return rank_data[0]
        else:
            logging.info(f"No TFT rank data found for summoner {summoner_id}")
            return None

    except Exception as e:
        logging.error(f"Failed to get TFT rank for {summoner_id}: {e}")
        return None


async def get_recent_matches(puuid: str, region: str = "na1", count: int = 5) -> List[str]:
    """
    Get recent match IDs for a player.

    Args:
        puuid: The player's PUUID
        region: The region
        count: Number of matches to retrieve (max 20)

    Returns:
        List of match IDs
    """
    if not API_AVAILABLE:
        logging.info(f"Would get recent matches for PUUID - Riot API not available")
        return []

    try:
        region = _normalize_region(region)
        # For match history, we need to use americas/asia/europe routing
        routing_region = _get_routing_region(region)

        url = TFT_ENDPOINTS["matches_by_puuid"].format(
            region=routing_region,
            puuid=puuid
        ) + f"?count={min(count, 20)}"

        match_ids = await _make_api_request(url)

        if match_ids and isinstance(match_ids, list):
            logging.info(f"Found {len(match_ids)} recent matches")
            return match_ids
        else:
            logging.info("No recent matches found")
            return []

    except Exception as e:
        logging.error(f"Failed to get recent matches: {e}")
        return []


async def get_match_details(match_id: str, region: str = "na1") -> Optional[Dict[str, Any]]:
    """
    Get detailed match information.

    Args:
        match_id: The match ID
        region: The region

    Returns:
        Dict with match details or None if not found
    """
    if not API_AVAILABLE:
        logging.info(f"Would get match details for {match_id} - Riot API not available")
        return None

    try:
        region = _normalize_region(region)
        routing_region = _get_routing_region(region)

        url = TFT_ENDPOINTS["match_details"].format(
            region=routing_region,
            matchId=match_id
        )

        match_data = await _make_api_request(url)

        if match_data:
            logging.debug(f"Retrieved match details for {match_id}")
            return match_data
        else:
            logging.info(f"Match details not found for {match_id}")
            return None

    except Exception as e:
        logging.error(f"Failed to get match details for {match_id}: {e}")
        return None


def _get_routing_region(region: str) -> str:
    """Convert platform region to routing region for match API."""
    americas = ["na1", "br1", "la1", "la2"]
    asia = ["kr", "jp1"]
    europe = ["euw1", "eun1", "tr1", "ru"]

    if region in americas:
        return "americas"
    elif region in asia:
        return "asia"
    elif region in europe:
        return "europe"
    else:
        return "americas"  # Default


async def get_latest_placement(summoner_name: str, region: str = "na1") -> Optional[Dict[str, Any]]:
    """
    Get the latest TFT placement for a summoner.

    Args:
        summoner_name: The summoner's display name
        region: The region

    Returns:
        Dict with placement info or None if not found
    """
    if not API_AVAILABLE:
        logging.info(f"Would get latest placement for {summoner_name} - Riot API not available")
        return None

    try:
        # Get summoner info
        summoner = await get_summoner_by_name(summoner_name, region)
        if not summoner:
            return None

        # Get recent matches
        match_ids = await get_recent_matches(summoner["puuid"], region, count=1)
        if not match_ids:
            logging.info(f"No recent matches found for {summoner_name}")
            return None

        # Get the latest match details
        match_details = await get_match_details(match_ids[0], region)
        if not match_details:
            return None

        # Find the player's placement in the match
        participants = match_details.get("info", {}).get("participants", [])
        for participant in participants:
            if participant.get("puuid") == summoner["puuid"]:
                placement_data = {
                    "summoner_name": summoner_name,
                    "placement": participant.get("placement", 0),
                    "match_id": match_ids[0],
                    "game_datetime": match_details.get("info", {}).get("game_datetime", 0),
                    "game_length": match_details.get("info", {}).get("game_length", 0),
                    "traits": participant.get("traits", []),
                    "units": participant.get("units", [])
                }

                logging.info(f"Found placement {placement_data['placement']} for {summoner_name}")
                return placement_data

        logging.warning(f"Could not find {summoner_name} in match {match_ids[0]}")
        return None

    except Exception as e:
        logging.error(f"Failed to get latest placement for {summoner_name}: {e}")
        return None


# Legacy function name for backward compatibility
async def tactics_tools_get_latest_placement(summoner_name: str, region: str = "na1") -> Optional[Dict[str, Any]]:
    """
    Legacy function name for getting latest TFT placement.

    Args:
        summoner_name: The summoner's display name
        region: The region

    Returns:
        Dict with placement info or None if not found
    """
    return await get_latest_placement(summoner_name, region)


async def validate_riot_connection() -> Dict[str, Any]:
    """
    Validate Riot API connection and configuration.

    Returns:
        Dict with validation status and details
    """
    validation = {
        "status": False,
        "available": API_AVAILABLE,
        "api_key_configured": bool(RIOT_API_KEY),
        "http_client_available": HTTP_AVAILABLE,
        "rate_limit_status": "ok",
        "errors": [],
        "warnings": []
    }

    try:
        if not RIOT_API_KEY:
            validation["errors"].append("RIOT_API_KEY environment variable not set")

        if not HTTP_AVAILABLE:
            validation["errors"].append("aiohttp package not installed")

        if not API_AVAILABLE:
            validation["warnings"].append("Riot API integration disabled")
            return validation

        # Check rate limit status
        if not _check_rate_limit():
            validation["rate_limit_status"] = "exceeded"
            validation["warnings"].append("Rate limit currently exceeded")

        # Test API connectivity with a simple request
        try:
            # Make a test request to check connectivity
            test_url = "https://na1.api.riotgames.com/tft/summoner/v1/summoners/by-name/test"
            response = await _make_api_request(test_url)

            # We expect this to fail (404), but if we get a response, API is working
            validation["api_connectivity"] = True
            validation["status"] = True

        except Exception as e:
            validation["errors"].append(f"API connectivity test failed: {e}")
            validation["api_connectivity"] = False

        # Overall status
        validation["status"] = len(validation["errors"]) == 0

    except Exception as e:
        validation["errors"].append(f"Validation failed: {e}")

    return validation


async def get_multiple_placements(summoner_names: List[str], region: str = "na1") -> Dict[
    str, Optional[Dict[str, Any]]]:
    """
    Get latest placements for multiple summoners efficiently.

    Args:
        summoner_names: List of summoner names
        region: The region

    Returns:
        Dict mapping summoner names to their placement data
    """
    if not API_AVAILABLE:
        logging.info(f"Would get placements for {len(summoner_names)} summoners - Riot API not available")
        return {name: None for name in summoner_names}

    results = {}

    # Process in batches to respect rate limits
    batch_size = 10  # Adjust based on rate limits

    for i in range(0, len(summoner_names), batch_size):
        batch = summoner_names[i:i + batch_size]

        # Create tasks for concurrent processing
        tasks = []
        for summoner_name in batch:
            task = asyncio.create_task(
                get_latest_placement(summoner_name, region),
                name=f"placement_{summoner_name}"
            )
            tasks.append((summoner_name, task))

        # Wait for batch completion
        for summoner_name, task in tasks:
            try:
                placement_data = await task
                results[summoner_name] = placement_data
            except Exception as e:
                logging.error(f"Failed to get placement for {summoner_name}: {e}")
                results[summoner_name] = None

        # Small delay between batches to be nice to the API
        if i + batch_size < len(summoner_names):
            await asyncio.sleep(1)

    successful = sum(1 for result in results.values() if result is not None)
    logging.info(f"Retrieved placements for {successful}/{len(summoner_names)} summoners")

    return results


# Health check and status functions
def get_api_status() -> Dict[str, Any]:
    """Get current API status and configuration."""
    return {
        "api_available": API_AVAILABLE,
        "api_key_configured": bool(RIOT_API_KEY),
        "http_client_available": HTTP_AVAILABLE,
        "rate_limit_remaining": max(0, RATE_LIMIT_REQUESTS - len(request_times)),
        "rate_limit_window_seconds": RATE_LIMIT_WINDOW,
        "recent_requests": len(request_times),
        "supported_regions": list(REGION_MAPPING.keys())
    }


def clear_rate_limit_history():
    """Clear rate limit history (for testing or admin purposes)."""
    global request_times
    request_times.clear()
    logging.info("Cleared Riot API rate limit history")


# Initialize and log status
if API_AVAILABLE:
    logging.info("✅ Riot API integration available")
    logging.info(f"📊 Rate limit: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds")
else:
    if not RIOT_API_KEY:
        logging.warning("⚠️ Riot API disabled - RIOT_API_KEY not configured")
    if not HTTP_AVAILABLE:
        logging.warning("⚠️ Riot API disabled - aiohttp package not installed")
    logging.info("💡 To enable Riot API: set RIOT_API_KEY and install aiohttp")

# Export all functions
__all__ = [
    # Main API functions
    'get_summoner_by_name',
    'get_tft_rank',
    'get_recent_matches',
    'get_match_details',
    'get_latest_placement',
    'get_multiple_placements',

    # Legacy function names
    'tactics_tools_get_latest_placement',

    # Validation and status
    'validate_riot_connection',
    'get_api_status',
    'clear_rate_limit_history',

    # Constants and configuration
    'API_AVAILABLE',
    'REGION_MAPPING',

    # Exception class
    'RiotAPIError'
]