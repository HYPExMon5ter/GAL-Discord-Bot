# integrations/live_graphics_api.py

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

import aiohttp
from aiohttp import ClientTimeout, ClientError

from config import get_live_graphics_settings


class LiveGraphicsAPIError(Exception):
    """Custom exception for live graphics API errors."""
    pass


class LiveGraphicsAPI:
    """
    Client for communicating with the FastAPI Live Graphics Dashboard.
    Handles authenticated REST API calls for syncing data and publishing graphics.
    """

    def __init__(self):
        self.settings = get_live_graphics_settings()
        self.base_url = self.settings["base_url"]
        self.token = self.settings["token"]
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = ClientTimeout(total=30, connect=10)
        
        if not self.base_url:
            raise LiveGraphicsAPIError("LIVE_GFX_BASE_URL not configured")
        if not self.token:
            raise LiveGraphicsAPIError("LIVE_GFX_TOKEN not configured")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout
            )
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated HTTP request to the live graphics API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            LiveGraphicsAPIError: If request fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        session = await self._get_session()
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with session.request(method, url, json=data, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 201:
                        return await response.json()
                    elif response.status == 401:
                        raise LiveGraphicsAPIError("Authentication failed - invalid token")
                    elif response.status == 403:
                        raise LiveGraphicsAPIError("Access forbidden - insufficient permissions")
                    elif response.status == 404:
                        raise LiveGraphicsAPIError(f"Endpoint not found: {endpoint}")
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logging.warning(f"Rate limited, waiting {delay}s before retry {attempt + 1}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise LiveGraphicsAPIError("Rate limit exceeded - max retries reached")
                    elif 500 <= response.status < 600:
                        # Server error - wait and retry
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logging.warning(f"Server error {response.status}, waiting {delay}s before retry {attempt + 1}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_text = await response.text()
                            raise LiveGraphicsAPIError(f"Server error {response.status}: {error_text}")
                    else:
                        error_text = await response.text()
                        raise LiveGraphicsAPIError(f"HTTP {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Request timeout, waiting {delay}s before retry {attempt + 1}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise LiveGraphicsAPIError("Request timeout - max retries reached")
            except ClientError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Network error, waiting {delay}s before retry {attempt + 1}: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise LiveGraphicsAPIError(f"Network error: {e}")

    async def upsert_standings(
        self, 
        event_id: int, 
        standings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upsert player standings for an event.
        
        Args:
            event_id: Event ID
            standings: List of standing data with rank, player info, points, etc.
            
        Returns:
            API response with updated standings
            
        Example standings format:
        [
            {
                "rank_position": 1,
                "discord_tag": "Player#1234",
                "ign": "PlayerName",
                "team": "TeamName",
                "points": 100,
                "wins": 5,
                "top4": 3,
                "average_placement": 2.1
            },
            ...
        ]
        """
        try:
            data = {
                "event_id": event_id,
                "standings": standings
            }
            
            logging.info(f"Upserting {len(standings)} standings for event {event_id}")
            response = await self._make_request("POST", "/api/standings/upsert", data)
            
            logging.info(f"Successfully upserted standings: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Failed to upsert standings for event {event_id}: {e}")
            raise LiveGraphicsAPIError(f"Failed to upsert standings: {e}")

    async def publish(
        self, 
        graphic_id: int, 
        template_data: Optional[Dict[str, Any]] = None,
        target_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish/update a graphic with current data.
        
        Args:
            graphic_id: Graphic instance ID
            template_data: Optional template data override
            target_urls: Optional list of URLs to publish to
            
        Returns:
            API response with publish status
            
        Example:
        await api.publish(
            graphic_id=1,
            template_data={"title": "Tournament Standings", "show_rank": True},
            target_urls=["obs://scene/standings", "file://output/standings.html"]
        )
        """
        try:
            data = {
                "graphic_id": graphic_id
            }
            
            if template_data:
                data["template_data"] = template_data
            if target_urls:
                data["target_urls"] = target_urls
            
            logging.info(f"Publishing graphic {graphic_id}")
            response = await self._make_request("POST", "/api/graphics/publish", data)
            
            logging.info(f"Successfully published graphic {graphic_id}: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Failed to publish graphic {graphic_id}: {e}")
            raise LiveGraphicsAPIError(f"Failed to publish graphic: {e}")

    async def create_graphic_instance(
        self,
        event_id: int,
        template_id: int,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new graphic instance.
        
        Args:
            event_id: Event ID
            template_id: Template ID to use
            name: Name for the graphic instance
            config: Configuration data for the graphic
            
        Returns:
            API response with created graphic instance
        """
        try:
            data = {
                "event_id": event_id,
                "template_id": template_id,
                "name": name
            }
            
            if config:
                data["config"] = config
            
            logging.info(f"Creating graphic instance '{name}' for event {event_id}")
            response = await self._make_request("POST", "/api/graphics/instances", data)
            
            logging.info(f"Successfully created graphic instance: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Failed to create graphic instance: {e}")
            raise LiveGraphicsAPIError(f"Failed to create graphic instance: {e}")

    async def update_graphic_instance(
        self,
        graphic_id: int,
        config: Dict[str, Any],
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing graphic instance.
        
        Args:
            graphic_id: Graphic instance ID
            config: New configuration data
            active: Optional active status override
            
        Returns:
            API response with updated graphic instance
        """
        try:
            data = {"config": config}
            if active is not None:
                data["active"] = active
            
            logging.info(f"Updating graphic instance {graphic_id}")
            response = await self._make_request("PUT", f"/api/graphics/instances/{graphic_id}", data)
            
            logging.info(f"Successfully updated graphic instance: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Failed to update graphic instance {graphic_id}: {e}")
            raise LiveGraphicsAPIError(f"Failed to update graphic instance: {e}")

    async def get_event_graphics(self, event_id: int) -> List[Dict[str, Any]]:
        """
        Get all graphic instances for an event.
        
        Args:
            event_id: Event ID
            
        Returns:
            List of graphic instances
        """
        try:
            logging.info(f"Fetching graphics for event {event_id}")
            response = await self._make_request("GET", f"/api/events/{event_id}/graphics")
            
            graphics = response.get("graphics", [])
            logging.info(f"Retrieved {len(graphics)} graphics for event {event_id}")
            return graphics
            
        except Exception as e:
            logging.error(f"Failed to get graphics for event {event_id}: {e}")
            raise LiveGraphicsAPIError(f"Failed to get event graphics: {e}")

    async def sync_event_snapshot(
        self, 
        event_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync a complete event snapshot to the dashboard.
        
        Args:
            event_snapshot: Complete event data with lobbies, standings, etc.
            
        Returns:
            API response with sync status
        """
        try:
            logging.info(f"Syncing event snapshot for event {event_snapshot.get('event_id')}")
            response = await self._make_request("POST", "/api/events/sync", event_snapshot)
            
            logging.info(f"Successfully synced event snapshot: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Failed to sync event snapshot: {e}")
            raise LiveGraphicsAPIError(f"Failed to sync event snapshot: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the live graphics API is healthy and accessible.
        
        Returns:
            Health check response
        """
        try:
            logging.info("Performing health check on live graphics API")
            response = await self._make_request("GET", "/api/health")
            
            logging.info(f"Live graphics API health check: {response}")
            return response
            
        except Exception as e:
            logging.error(f"Live graphics API health check failed: {e}")
            raise LiveGraphicsAPIError(f"Health check failed: {e}")


# Global instance for reuse
_api_instance: Optional[LiveGraphicsAPI] = None


def get_live_graphics_api() -> LiveGraphicsAPI:
    """
    Get a singleton instance of the LiveGraphicsAPI.
    
    Returns:
        LiveGraphicsAPI instance
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = LiveGraphicsAPI()
    return _api_instance


async def close_live_graphics_api():
    """Close the global LiveGraphicsAPI instance."""
    global _api_instance
    if _api_instance:
        await _api_instance.close()
        _api_instance = None
