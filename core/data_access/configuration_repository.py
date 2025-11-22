"""
Configuration Repository - Migration Adapter

This repository provides a unified interface for configuration management,
bridging the legacy config.py and persistence.py functionality with the new DAL architecture.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict

from .base_repository import BaseRepository
from .cache_manager import CacheManager
from .connection_manager import ConnectionManager
from ..events.event_bus import EventBus
from ..events.event_types import ConfigurationEvent
from ..models.configuration import Configuration, ConfigurationValue, ConfigurationHistory
from ..models.guild import Guild, GuildConfiguration


@dataclass
class LegacyConfig:
    """Legacy configuration structure for backward compatibility."""
    embeds: Dict[str, Any]
    sheet_configuration: Dict[str, Any]
    channels: Dict[str, str]
    roles: Dict[str, Any]
    onboard: Dict[str, Any] = None
    cache_refresh_seconds: int = 600
    current_mode: str = "normal"


class ConfigurationRepository:
    """
    Repository for configuration management with migration support.
    
    This repository acts as an adapter between the legacy config.py and persistence.py
    functionality and the new unified data access layer. It maintains backward compatibility
    while introducing event-driven updates and structured configuration models.
    """
    
    def __init__(self, cache_manager: CacheManager, event_bus: EventBus):
        self.logger = logging.getLogger(__name__)
        self.cache_manager = cache_manager
        self.event_bus = event_bus
        
        # Legacy config references
        self._legacy_config = None
        self._legacy_embeds = None
        self._legacy_sheet_config = None
        self._config_file_path = None
        
        # Legacy persistence references
        self._legacy_persisted = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the configuration repository with legacy data."""
        if self._initialized:
            return
            
        try:
            # Import legacy configuration
            import config
            from core import persistence
            
            # Store references to legacy config
            self._legacy_config = config._FULL_CFG
            self._legacy_embeds = config.EMBEDS_CFG
            self._legacy_sheet_config = config.SHEET_CONFIG
            self._config_file_path = os.path.join(os.path.dirname(config.__file__), "config.yaml")
            
            # Store reference to legacy persistence
            self._legacy_persisted = persistence.persisted
            
            # Load initial configuration into cache
            await self._load_legacy_configuration()
            
            self._initialized = True
            self.logger.info("Configuration repository initialized successfully")
            
        except ImportError as e:
            self.logger.error(f"Failed to import legacy configuration: {e}")
            raise
    
    async def _load_legacy_configuration(self):
        """Load legacy configuration into the new system."""
        if not self._legacy_config:
            return
            
        # Create unified configuration object
        unified_config = {
            "embeds": self._legacy_embeds or {},
            "sheet_configuration": self._legacy_sheet_config or {},
            "channels": self._legacy_config.get("channels", {}),
            "roles": self._legacy_config.get("roles", {}),
            "onboard": self._legacy_config.get("onboard", {}),
            "cache_refresh_seconds": self._legacy_config.get("cache_refresh_seconds", 600),
            "current_mode": self._legacy_config.get("current_mode", "normal"),
            "ping_user": self._legacy_config.get("ping_user", ""),
            "live_graphics": self._legacy_config.get("live_graphics", {})
        }
        
        # Cache the unified configuration
        from datetime import timedelta
        await self.cache_manager.set("unified_config", unified_config, ttl=timedelta(hours=1))
        
        self.logger.info("Legacy configuration loaded into unified system")
    
    async def get_configuration(self, key: str = None, guild_id: str = None) -> Any:
        """
        Get configuration value with fallback to legacy system.
        
        Args:
            key: Configuration key (optional, returns full config if None)
            guild_id: Guild identifier for guild-specific config
            
        Returns:
            Configuration value or full configuration
        """
        await self.initialize()
        
        # Try cache first
        if key:
            cache_key = f"config:{guild_id or 'global'}:{key}"
            cached_value = await self.cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
        
        # Fallback to legacy system
        if key and self._legacy_config:
            # Navigate nested keys with dot notation
            keys = key.split('.')
            value = self._legacy_config
            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return None
        
        # Return full configuration if no key specified
        if self._legacy_config:
            return self._legacy_config.copy()
        
        return None
    
    async def set_configuration(
        self,
        key: str,
        value: Any,
        guild_id: str = None,
        emit_event: bool = True
    ) -> bool:
        """
        Set configuration value with legacy persistence support.
        
        Args:
            key: Configuration key
            value: Configuration value
            guild_id: Guild identifier (optional)
            emit_event: Whether to emit configuration change event
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            # Update cache
            cache_key = f"config:{guild_id or 'global'}:{key}"
            from datetime import timedelta
            await self.cache_manager.set(cache_key, value, ttl=timedelta(hours=1))
            
            # For now, only update cache - legacy config file updates
            # would require file system access and careful YAML handling
            # This can be implemented in Phase 3 when we fully migrate
            
            # Emit configuration change event
            if emit_event:
                await self._emit_event(
                    ConfigurationEvent.CONFIGURATION_UPDATED,
                    {
                        "key": key,
                        "value": value,
                        "guild_id": guild_id,
                        "source": "repository"
                    }
                )
            
            self.logger.info(f"Configuration updated: {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration {key}: {e}")
            return False
    
    async def get_sheet_settings(self, mode: str, guild_id: str = None) -> Dict[str, Any]:
        """
        Get sheet configuration for specified mode.
        
        Args:
            mode: Tournament mode (normal, doubleup)
            guild_id: Guild identifier
            
        Returns:
            Sheet configuration dictionary
        """
        await self.initialize()
        
        # Try cache first
        cache_key = f"sheet_config:{guild_id or 'global'}:{mode}"
        cached_config = await self.cache_manager.get(cache_key)
        if cached_config:
            return cached_config
        
        # Fallback to legacy system
        if self._legacy_sheet_config and mode in self._legacy_sheet_config:
            config = self._legacy_sheet_config[mode].copy()
            
            # Cache the result
            await self.cache_manager.set(cache_key, config, ttl=timedelta(minutes=30))
            
            return config
        
        return {}
    
    async def get_embed_configuration(self, embed_key: str, guild_id: str = None) -> Dict[str, Any]:
        """
        Get embed configuration.
        
        Args:
            embed_key: Embed configuration key
            guild_id: Guild identifier
            
        Returns:
            Embed configuration dictionary
        """
        await self.initialize()
        
        return await self.get_configuration(f"embeds.{embed_key}", guild_id)
    
    async def get_role_configuration(self, guild_id: str = None) -> Dict[str, Any]:
        """
        Get role configuration.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Role configuration dictionary
        """
        await self.initialize()
        
        return await self.get_configuration("roles", guild_id)
    
    async def get_channel_configuration(self, guild_id: str = None) -> Dict[str, str]:
        """
        Get channel configuration.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Channel configuration dictionary
        """
        await self.initialize()
        
        return await self.get_configuration("channels", guild_id)
    
    async def get_guild_data(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get guild-specific data from legacy persistence.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Guild data dictionary
        """
        await self.initialize()
        
        # Try cache first
        cache_key = f"guild_data:{guild_id}"
        cached_data = await self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        # Fallback to legacy persistence
        if self._legacy_persisted:
            data = self._legacy_persisted.get(str(guild_id), {}).copy()
            
            # Cache the result
            await self.cache_manager.set(cache_key, data, ttl=timedelta(minutes=10))
            
            return data
        
        return {}
    
    async def update_guild_data(
        self,
        guild_id: Union[str, int],
        data: Dict[str, Any],
        emit_event: bool = True
    ) -> bool:
        """
        Update guild-specific data.
        
        Args:
            guild_id: Guild identifier
            data: Data to update
            emit_event: Whether to emit update event
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            # Update cache
            cache_key = f"guild_data:{guild_id}"
            await self.cache_manager.set(cache_key, data, ttl=timedelta(minutes=10))
            
            # For now, only update cache - legacy persistence updates
            # can be implemented in Phase 3 when we fully migrate
            
            # Emit guild data update event
            if emit_event:
                await self._emit_event(
                    ConfigurationEvent.GUILD_CONFIGURATION_UPDATED,
                    {
                        "guild_id": str(guild_id),
                        "updated_keys": list(data.keys()),
                        "source": "repository"
                    }
                )
            
            self.logger.info(f"Guild data updated for {guild_id}: {list(data.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update guild data for {guild_id}: {e}")
            return False
    
    async def get_event_mode(self, guild_id: Union[str, int]) -> str:
        """
        Get event mode for guild.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Event mode (normal, doubleup)
        """
        await self.initialize()
        
        guild_data = await self.get_guild_data(guild_id)
        return guild_data.get("event_mode", "normal")
    
    async def set_event_mode(
        self,
        guild_id: Union[str, int],
        mode: str,
        emit_event: bool = True
    ) -> bool:
        """
        Set event mode for guild.
        
        Args:
            guild_id: Guild identifier
            mode: Event mode (normal, doubleup)
            emit_event: Whether to emit event
            
        Returns:
            True if successful, False otherwise
        """
        if mode not in ["normal", "doubleup"]:
            raise ValueError(f"Invalid event mode: {mode}")
        
        guild_data = await self.get_guild_data(guild_id)
        guild_data["event_mode"] = mode
        
        success = await self.update_guild_data(guild_id, {"event_mode": mode}, emit_event)
        
        if success and emit_event:
            await self._emit_event(
                ConfigurationEvent.EVENT_MODE_CHANGED,
                {
                    "guild_id": str(guild_id),
                    "old_mode": await self.get_event_mode(guild_id),
                    "new_mode": mode
                }
            )
        
        return success
    
    async def get_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Get persisted message data.
        
        Args:
            guild_id: Guild identifier
            key: Message key
            
        Returns:
            Tuple of (channel_id, message_id) or (None, None)
        """
        await self.initialize()
        
        # Try cache first
        cache_key = f"persisted_msg:{guild_id}:{key}"
        cached_data = await self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data.get("channel_id"), cached_data.get("message_id")
        
        # Fallback to legacy persistence
        if self._legacy_persisted:
            guild_data = self._legacy_persisted.get(str(guild_id), {})
            value = guild_data.get(key)
            
            if isinstance(value, list) and len(value) == 2:
                result = value[0], value[1]
            elif isinstance(value, int):
                result = None, value  # Legacy support
            else:
                result = None, None
            
            # Cache the result
            await self.cache_manager.set(cache_key, {
                "channel_id": result[0],
                "message_id": result[1]
            }, ttl=timedelta(minutes=30))
            
            return result
        
        return None, None
    
    async def set_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str,
        channel_id: int,
        message_id: int,
        emit_event: bool = True
    ) -> bool:
        """
        Set persisted message data.
        
        Args:
            guild_id: Guild identifier
            key: Message key
            channel_id: Channel ID
            message_id: Message ID
            emit_event: Whether to emit event
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            # Update cache
            cache_key = f"persisted_msg:{guild_id}:{key}"
            await self.cache_manager.set(cache_key, {
                "channel_id": channel_id,
                "message_id": message_id
            }, ttl=timedelta(minutes=30))
            
            # For now, only update cache - legacy persistence updates
            # can be implemented in Phase 3 when we fully migrate
            
            # Emit message persistence event
            if emit_event:
                await self._emit_event(
                    ConfigurationEvent.MESSAGE_PERSISTED,
                    {
                        "guild_id": str(guild_id),
                        "key": key,
                        "channel_id": channel_id,
                        "message_id": message_id
                    }
                )
            
            self.logger.debug(f"Persisted message for guild {guild_id}, key {key}: {channel_id}/{message_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to persist message for guild {guild_id}, key {key}: {e}")
            return False
    
    async def validate_configuration(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation errors
        """
        await self.initialize()
        
        errors = []
        
        # Check required configuration sections
        required_sections = ["embeds", "sheet_configuration", "channels", "roles"]
        
        for section in required_sections:
            if not await self.get_configuration(section):
                errors.append(f"Missing required configuration section: {section}")
        
        # Check sheet configuration for both modes
        for mode in ["normal", "doubleup"]:
            sheet_config = await self.get_sheet_settings(mode)
            if not sheet_config:
                errors.append(f"Missing sheet configuration for mode: {mode}")
                continue
            
            # Check for sheet URLs
            if not (sheet_config.get("sheet_url_prod") or sheet_config.get("sheet_url_dev")):
                errors.append(f"Missing sheet URLs for {mode} mode")
        
        return errors
    
    async def get_environment_info(self) -> Dict[str, Any]:
        """
        Get environment information for configuration context.
        
        Returns:
            Environment information dictionary
        """
        # Support multiple common Railway production environment names
        production_names = ["production", "main", "prod"]
        railway_env = os.getenv("RAILWAY_ENVIRONMENT_NAME")
        
        return {
            "is_production": railway_env in production_names,
            "dev_guild_id": os.getenv("DEV_GUILD_ID"),
            "database_url": "configured" if os.getenv("DATABASE_URL") else "not configured",
            "discord_token": "configured" if os.getenv("DISCORD_TOKEN") else "not configured"
        }
    
    async def export_configuration(self, guild_id: str = None) -> Dict[str, Any]:
        """
        Export configuration for backup/migration.
        
        Args:
            guild_id: Guild identifier (optional, exports global if None)
            
        Returns:
            Configuration export dictionary
        """
        await self.initialize()
        
        export = {
            "timestamp": int(time.time()),
            "version": "1.0",
            "environment": await self.get_environment_info(),
            "configuration": {}
        }
        
        if guild_id:
            # Export guild-specific configuration
            export["guild_id"] = guild_id
            export["configuration"] = {
                "guild_data": await self.get_guild_data(guild_id),
                "event_mode": await self.get_event_mode(guild_id)
            }
        else:
            # Export global configuration
            export["configuration"] = {
                "embeds": await self.get_configuration("embeds"),
                "sheet_configuration": await self.get_configuration("sheet_configuration"),
                "channels": await self.get_configuration("channels"),
                "roles": await self.get_configuration("roles"),
                "onboard": await self.get_configuration("onboard"),
                "cache_refresh_seconds": await self.get_configuration("cache_refresh_seconds"),
                "current_mode": await self.get_configuration("current_mode")
            }
        
        return export
