# integrations/riot_api.py

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any

import aiohttp
import discord


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

    async def _make_request(self, url: str) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        if not self.session:
            raise RiotAPIError("Session not initialized. Use async context manager.")

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited
                    retry_after = response.headers.get('Retry-After', '60')
                    raise RateLimitError(f"Rate limited. Retry after {retry_after} seconds")
                elif response.status == 404:
                    raise RiotAPIError("Summoner not found")
                elif response.status == 403:
                    raise RiotAPIError("Forbidden - Invalid API key or expired token")
                else:
                    error_text = await response.text()
                    raise RiotAPIError(f"API request failed with status {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise RiotAPIError(f"Network error: {str(e)}")

    async def get_account_by_riot_id(self, region: str, game_name: str, tag_line: str) -> Dict[str, Any]:
        """Get account information by Riot ID (game name + tag line)."""
        regional = self._get_regional_endpoint(region)
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return await self._make_request(url)

    async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
        """Get summoner information by PUUID."""
        platform = self._get_platform_endpoint(region)
        url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
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
            logging.error(f"Unexpected error in get_latest_placement: {e}")
            return {
                "success": False,
                "error": "An unexpected error occurred",
                "riot_id": riot_id,
                "region": region.upper()
            }


def validate_region(region: str) -> bool:
    """Validate if a region is supported."""
    return region.lower() in RiotAPI.PLATFORM_ENDPOINTS