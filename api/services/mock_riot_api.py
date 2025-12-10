"""Mock Riot API service for testing without live API calls."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from integrations.riot_api import RiotAPI, PlacementResult


class MockRiotAPI:
    """
    Deterministic mock Riot API for testing.
    Returns predictable data without making actual HTTP requests.
    """

    # Predefined player data for consistent testing
    PLAYER_DATABASE = {
        # Basic players
        "Alice#NA1": {
            "puuid": "alice-puuid-123",
            "gameName": "Alice",
            "tagLine": "NA1",
            "summonerId": "alice-summoner-456",
            "summonerLevel": 150,
            "placements": [1, 3, 2, 4, 1],  # Recent placements
            "rank": {"tier": "DIAMOND", "rank": "I", "lp": 75}
        },
        "Bob#NA1": {
            "puuid": "bob-puuid-789",
            "gameName": "Bob",
            "tagLine": "NA1",
            "summonerId": "bob-summoner-012",
            "summonerLevel": 85,
            "placements": [5, 6, 4, 7, 5],
            "rank": {"tier": "GOLD", "rank": "II", "lp": 50}
        },
        "Charlie#EUW": {
            "puuid": "charlie-puuid-345",
            "gameName": "Charlie",
            "tagLine": "EUW",
            "summonerId": "charlie-summoner-678",
            "summonerLevel": 200,
            "placements": [2, 1, 3, 2, 1],
            "rank": {"tier": "MASTER", "rank": "I", "lp": 350}
        },
        "Diana#KR": {
            "puuid": "diana-puuid-901",
            "gameName": "Diana",
            "tagLine": "KR",
            "summonerId": "diana-summoner-234",
            "summonerLevel": 300,
            "placements": [8, 7, 8, 6, 8],
            "rank": {"tier": "SILVER", "rank": "III", "lp": 25}
        },
        # Edge case players
        "NoGames#NA1": {
            "puuid": "nogames-puuid-567",
            "gameName": "NoGames",
            "tagLine": "NA1",
            "summonerId": "nogames-summoner-890",
            "summonerLevel": 10,
            "placements": [],  # No recent games
            "rank": {"tier": "UNRANKED", "rank": "IV", "lp": 0}
        },
        "Invalid#NA1": None,  # Will return 404
        "ServerError#NA1": "server_error",  # Will simulate server error
    }

    def __init__(self, delay: float = 0.1):
        """
        Initialize mock API.
        
        Args:
            delay: Simulated API delay in seconds
        """
        self.delay = delay
        self.call_count = 0
        self.last_call_region = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    async def _simulate_delay(self):
        """Simulate API delay."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)

    def _get_player_data(self, riot_id: str) -> Optional[Dict]:
        """Get predefined player data or return None for unknown players."""
        return self.PLAYER_DATABASE.get(riot_id)

    async def get_latest_placement(self, region: str, riot_id: str) -> Dict:
        """
        Mock implementation of get_latest_placement.
        Returns deterministic data based on predefined player database.
        """
        self.call_count += 1
        self.last_call_region = region

        await self._simulate_delay()

        player_data = self._get_player_data(riot_id)

        # Handle unknown player
        if player_data is None:
            return {
                "success": False,
                "error": "Summoner not found",
                "riot_id": riot_id,
                "region": region.upper()
            }

        # Handle server error case
        if player_data == "server_error":
            return {
                "success": False,
                "error": "Internal server error",
                "riot_id": riot_id,
                "region": region.upper()
            }

        # Handle player with no games
        if not player_data["placements"]:
            return {
                "success": False,
                "error": "No recent matches found",
                "riot_id": f"{player_data['gameName']}#{player_data['tagLine']}",
                "region": region.upper()
            }

        # Return latest placement
        latest_placement = player_data["placements"][0]

        return {
            "success": True,
            "riot_id": f"{player_data['gameName']}#{player_data['tagLine']}",
            "game_name": player_data["gameName"],
            "tag_line": player_data["tagLine"],
            "region": region.upper(),
            "placement": latest_placement,
            "total_players": 8,  # Standard TFT lobby size
            "game_datetime": datetime.now().timestamp() * 1000,
            "game_length": 1800,  # 30 minutes
            "game_version": "13.24.406.5487",
            "match_id": f"{region.upper()}_{latest_placement}_{player_data['puuid'][:8]}",
            "level": player_data["summonerLevel"]
        }

    async def get_placements_batch(
        self,
        riot_ids: List[str],
        region: str = "na",
        batch_delay: float = 1.0,
        batch_size: int = 10
    ) -> Dict[str, PlacementResult]:
        """
        Mock implementation of get_placements_batch.
        Processes all IDs but simulates batching behavior.
        """
        results = {}
        
        # Simulate batch processing
        for i in range(0, len(riot_ids), batch_size):
            batch = riot_ids[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self._get_single_placement_safe(riot_id, region)
                for riot_id in batch
            ]
            
            batch_results = await asyncio.gather(*tasks)
            
            for j, result in enumerate(batch_results):
                riot_id = batch[j]
                results[riot_id] = result
            
            # Add delay between batches
            if i + batch_size < len(riot_ids):
                await asyncio.sleep(batch_delay)
        
        return results

    async def _get_single_placement_safe(self, riot_id: str, region: str) -> PlacementResult:
        """
        Safe wrapper for single placement fetch.
        """
        try:
            result = await self.get_latest_placement(region, riot_id)
            
            if result["success"]:
                return PlacementResult(
                    riot_id=result["riot_id"],
                    placement=result["placement"],
                    game_datetime=datetime.now(),
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
            return PlacementResult(
                riot_id=riot_id,
                placement=0,
                game_datetime=datetime.now(),
                success=False,
                error=str(e)
            )

    async def get_highest_rank_across_accounts(
        self,
        ign_list: List[str],
        default_region: str = "na"
    ) -> Dict[str, any]:
        """
        Mock implementation that returns highest rank from IGN list.
        """
        highest_rank = None
        highest_numeric = 0
        
        from integrations.riot_api import get_rank_numeric_value, format_rank_display
        
        for ign in ign_list:
            player_data = self._get_player_data(ign)
            if not player_data or player_data in [None, "server_error"]:
                continue
                
            rank_data = player_data["rank"]
            numeric_value = get_rank_numeric_value(
                rank_data["tier"],
                rank_data["rank"],
                rank_data["lp"]
            )
            
            if numeric_value > highest_numeric:
                highest_numeric = numeric_value
                highest_rank = {
                    "tier": rank_data["tier"],
                    "division": rank_data["rank"],
                    "lp": rank_data["lp"],
                    "wins": 50,  # Mock data
                    "losses": 30,
                    "region": ign.split('#')[-1].upper() if '#' in ign else default_region.upper(),
                    "ign": ign
                }
        
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
            return {
                "highest_rank": "Iron IV",
                "tier": "IRON",
                "division": "IV",
                "lp": 0,
                "found_ign": ign_list[0] if ign_list else "Unknown",
                "region": "N/A",
                "success": False
            }

    def get_call_stats(self) -> Dict[str, any]:
        """Get statistics about API calls made."""
        return {
            "call_count": self.call_count,
            "last_call_region": self.last_call_region,
            "known_players": len([p for p in self.PLAYER_DATABASE.values() if p not in [None, "server_error"]])
        }

    def reset_stats(self):
        """Reset call statistics."""
        self.call_count = 0
        self.last_call_region = None

    def add_player(self, riot_id: str, player_data: Dict):
        """
        Add a new player to the mock database.
        
        Args:
            riot_id: Player's Riot ID (e.g., "NewPlayer#NA1")
            player_data: Dict with player information
        """
        self.PLAYER_DATABASE[riot_id] = player_data
