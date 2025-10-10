"""
OBS Integration Module

This module provides async functions for OBS WebS connection management,
scene selection, source switching, and error handling for OBS studio automation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

try:
    import obsws_python as obs
except ImportError:
    obs = None

from config import get_config

logger = logging.getLogger(__name__)


class OBSIntegrationError(Exception):
    """Custom exception for OBS integration errors."""
    pass


class OBSManager:
    """Async OBS WebSocket connection manager."""
    
    def __init__(self, host: str = None, port: int = None, password: str = None):
        """
        Initialize OBS Manager.
        
        Args:
            host: OBS WebSocket host (default: localhost)
            port: OBS WebSocket port (default: 4455)
            password: OBS WebSocket password (default: from config)
        """
        if obs is None:
            raise OBSIntegrationError("obs-websocket-client not installed")
        
        config = get_config()
        self.host = host or getattr(config, 'OBS_HOST', 'localhost')
        self.port = port or getattr(config, 'OBS_PORT', 4455)
        self.password = password or getattr(config, 'OBS_PASSWORD', None)
        
        self._client: Optional[obs.ReqClient] = None
        self._is_connected = False
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        Establish connection to OBS WebSocket.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        async with self._lock:
            if self._is_connected:
                return True
            
            try:
                # Connect to OBS WebSocket
                self._client = obs.ReqClient(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    event_loop=asyncio.get_event_loop()
                )
                
                # Wait a moment for connection to establish
                await asyncio.sleep(0.1)
                
                # Test connection with get_version
                version = await self.get_version()
                if version:
                    self._is_connected = True
                    logger.info(f"Connected to OBS {version.get('obs_version', 'unknown')}")
                    return True
                
            except Exception as e:
                logger.error(f"Failed to connect to OBS: {e}")
                self._client = None
                self._is_connected = False
            
            return False
    
    async def disconnect(self):
        """Disconnect from OBS WebSocket."""
        async with self._lock:
            if self._client and self._is_connected:
                try:
                    # The obs-websocket-client doesn't have an explicit disconnect method
                    # We'll just mark as disconnected and let garbage collection handle it
                    self._is_connected = False
                    logger.info("Disconnected from OBS")
                except Exception as e:
                    logger.error(f"Error disconnecting from OBS: {e}")
                finally:
                    self._client = None
    
    @asynccontextmanager
    async def connection(self):
        """
        Context manager for OBS connection.
        
        Usage:
            async with obs_manager.connection():
                await obs_manager.switch_scene("Scene Name")
        """
        connected = await self.connect()
        if not connected:
            raise OBSIntegrationError("Failed to connect to OBS")
        
        try:
            yield self
        finally:
            await self.disconnect()
    
    async def ensure_connected(self) -> bool:
        """
        Ensure OBS connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self._is_connected or not self._client:
            return await self.connect()
        return True
    
    async def get_version(self) -> Optional[Dict[str, Any]]:
        """
        Get OBS version information.
        
        Returns:
            Dict containing version info or None if failed
        """
        if not await self.ensure_connected():
            return None
        
        try:
            response = self._client.get_version()
            return response.datain
        except Exception as e:
            logger.error(f"Failed to get OBS version: {e}")
            return None
    
    async def get_scene_list(self) -> List[str]:
        """
        Get list of available scenes.
        
        Returns:
            List of scene names
        """
        if not await self.ensure_connected():
            return []
        
        try:
            response = self._client.get_scene_list()
            scenes = response.datain.get('scenes', [])
            return [scene['sceneName'] for scene in scenes]
        except Exception as e:
            logger.error(f"Failed to get scene list: {e}")
            return []
    
    async def get_current_scene(self) -> Optional[str]:
        """
        Get currently active scene.
        
        Returns:
            Current scene name or None if failed
        """
        if not await self.ensure_connected():
            return None
        
        try:
            response = self._client.get_current_program_scene()
            return response.datain.get('currentProgramSceneName')
        except Exception as e:
            logger.error(f"Failed to get current scene: {e}")
            return None
    
    async def switch_scene(self, scene_name: str) -> bool:
        """
        Switch to specified scene.
        
        Args:
            scene_name: Name of scene to switch to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        try:
            self._client.set_current_program_scene(scene_name=scene_name)
            logger.info(f"Switched to scene: {scene_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to scene '{scene_name}': {e}")
            return False
    
    async def get_source_list(self) -> List[str]:
        """
        Get list of available sources.
        
        Returns:
            List of source names
        """
        if not await self.ensure_connected():
            return []
        
        try:
            response = self._client.get_input_list()
            sources = response.datain.get('inputs', [])
            return [source['inputName'] for source in sources]
        except Exception as e:
            logger.error(f"Failed to get source list: {e}")
            return []
    
    async def get_source_settings(self, source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get settings for a specific source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            Source settings dict or None if failed
        """
        if not await self.ensure_connected():
            return None
        
        try:
            response = self._client.get_input_settings(inputName=source_name)
            return response.datain
        except Exception as e:
            logger.error(f"Failed to get settings for source '{source_name}': {e}")
            return None
    
    async def set_source_settings(self, source_name: str, settings: Dict[str, Any]) -> bool:
        """
        Update settings for a specific source.
        
        Args:
            source_name: Name of the source
            settings: Dictionary of settings to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        try:
            self._client.set_input_settings(
                inputName=source_name,
                inputSettings=settings
            )
            logger.info(f"Updated settings for source: {source_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update settings for source '{source_name}': {e}")
            return False
    
    async def set_source_visibility(self, source_name: str, scene_name: str, visible: bool) -> bool:
        """
        Set visibility of a source in a specific scene.
        
        Args:
            source_name: Name of the source
            scene_name: Name of the scene
            visible: Whether source should be visible
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        try:
            # Get scene item reference
            scene_items = self._client.get_scene_item_list(sceneName=scene_name)
            scene_item = None
            
            for item in scene_items.datain.get('sceneItems', []):
                if item.get('sourceName') == source_name:
                    scene_item = item
                    break
            
            if not scene_item:
                logger.error(f"Source '{source_name}' not found in scene '{scene_name}'")
                return False
            
            # Set visibility
            self._client.set_scene_item_enabled(
                sceneName=scene_name,
                sceneItemId=scene_item['sceneItemId'],
                sceneItemEnabled=visible
            )
            
            logger.info(f"Set {source_name} visibility to {visible} in scene {scene_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set visibility for source '{source_name}': {e}")
            return False
    
    async def toggle_source(self, source_name: str, scene_name: str = None) -> bool:
        """
        Toggle visibility of a source.
        
        Args:
            source_name: Name of the source
            scene_name: Name of the scene (uses current scene if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        if scene_name is None:
            scene_name = await self.get_current_scene()
            if not scene_name:
                logger.error("Could not determine current scene")
                return False
        
        try:
            # Get current visibility
            scene_items = self._client.get_scene_item_list(sceneName=scene_name)
            scene_item = None
            
            for item in scene_items.datain.get('sceneItems', []):
                if item.get('sourceName') == source_name:
                    scene_item = item
                    break
            
            if not scene_item:
                logger.error(f"Source '{source_name}' not found in scene '{scene_name}'")
                return False
            
            # Toggle visibility
            current_visibility = scene_item.get('sceneItemEnabled', False)
            new_visibility = not current_visibility
            
            return await self.set_source_visibility(source_name, scene_name, new_visibility)
            
        except Exception as e:
            logger.error(f"Failed to toggle source '{source_name}': {e}")
            return False
    
    async def start_streaming(self) -> bool:
        """
        Start streaming.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        try:
            self._client.start_stream()
            logger.info("Started streaming")
            return True
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def stop_streaming(self) -> bool:
        """
        Stop streaming.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.ensure_connected():
            return False
        
        try:
            self._client.stop_stream()
            logger.info("Stopped streaming")
            return True
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}")
            return False
    
    async def get_stream_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current streaming status.
        
        Returns:
            Stream status dict or None if failed
        """
        if not await self.ensure_connected():
            return None
        
        try:
            response = self._client.get_stream_status()
            return response.datain
        except Exception as e:
            logger.error(f"Failed to get stream status: {e}")
            return None
    
    async def take_source_screenshot(self, source_name: str, save_to_path: str = None) -> Optional[str]:
        """
        Take a screenshot of a specific source.
        
        Args:
            source_name: Name of the source to screenshot
            save_to_path: Path to save screenshot (optional)
            
        Returns:
            Base64 encoded image data or None if failed
        """
        if not await self.ensure_connected():
            return None
        
        try:
            response = self._client.get_source_screenshot(
                sourceName=source_name,
                imageFormat="png",
                pictureFormat=save_to_path or None
            )
            return response.datain.get('imageData')
        except Exception as e:
            logger.error(f"Failed to take screenshot of source '{source_name}': {e}")
            return None


# Global OBS manager instance
_obs_manager: Optional[OBSManager] = None


def get_obs_manager() -> OBSManager:
    """
    Get global OBS manager instance.
    
    Returns:
        OBSManager instance
    """
    global _obs_manager
    if _obs_manager is None:
        _obs_manager = OBSManager()
    return _obs_manager


async def test_obs_connection() -> Dict[str, Any]:
    """
    Test OBS connection and return status information.
    
    Returns:
        Dict containing connection status and OBS info
    """
    manager = get_obs_manager()
    
    result = {
        'connected': False,
        'version': None,
        'scenes': [],
        'sources': [],
        'error': None
    }
    
    try:
        connected = await manager.connect()
        result['connected'] = connected
        
        if connected:
            # Get version info
            version_info = await manager.get_version()
            result['version'] = version_info
            
            # Get scenes
            scenes = await manager.get_scene_list()
            result['scenes'] = scenes
            
            # Get sources
            sources = await manager.get_source_list()
            result['sources'] = sources
            
            # Get current scene
            current_scene = await manager.get_current_scene()
            result['current_scene'] = current_scene
            
            # Get stream status
            stream_status = await manager.get_stream_status()
            result['stream_status'] = stream_status
        
        await manager.disconnect()
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"OBS connection test failed: {e}")
    
    return result


# Convenience functions
async def switch_to_scene(scene_name: str) -> bool:
    """
    Switch to specified OBS scene.
    
    Args:
        scene_name: Name of scene to switch to
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = get_obs_manager()
    async with manager.connection():
        return await manager.switch_scene(scene_name)


async def toggle_source_visibility(source_name: str, scene_name: str = None) -> bool:
    """
    Toggle visibility of an OBS source.
    
    Args:
        source_name: Name of the source
        scene_name: Name of the scene (uses current scene if None)
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = get_obs_manager()
    async with manager.connection():
        return await manager.toggle_source(source_name, scene_name)


async def set_source_visibility(source_name: str, visible: bool, scene_name: str) -> bool:
    """
    Set visibility of an OBS source.
    
    Args:
        source_name: Name of the source
        visible: Whether source should be visible
        scene_name: Name of the scene
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = get_obs_manager()
    async with manager.connection():
        return await manager.set_source_visibility(source_name, scene_name, visible)


async def update_browser_source(source_name: str, url: str, scene_name: str = None) -> bool:
    """
    Update URL of a browser source.
    
    Args:
        source_name: Name of the browser source
        url: New URL to set
        scene_name: Name of the scene (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = get_obs_manager()
    async with manager.connection():
        settings = {'url': url}
        return await manager.set_source_settings(source_name, settings)
