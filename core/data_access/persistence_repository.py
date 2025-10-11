"""
Persistence Repository - Migration Adapter

This repository provides a unified interface for data persistence,
bridging the legacy persistence.py functionality with the new DAL architecture.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from .base_repository import BaseRepository
from .cache_manager import CacheManager
from .connection_manager import ConnectionManager
from ..events.event_bus import EventBus
from ..events.event_types import ConfigurationEvent


@dataclass
class PersistedMessage:
    """Persisted message data structure."""
    channel_id: Optional[int]
    message_id: int
    guild_id: str
    key: str


@dataclass
class GuildSchedule:
    """Guild schedule data structure."""
    guild_id: str
    key: str
    scheduled_time: Optional[str]


class PersistenceRepository(BaseRepository):
    """
    Repository for data persistence with migration support.
    
    This repository acts as an adapter between the legacy persistence.py
    functionality and the new unified data access layer. It maintains backward compatibility
    while introducing event-driven updates and structured data models.
    """
    
    def __init__(self, cache_manager: CacheManager, event_bus: EventBus):
        super().__init__("persistence", cache_manager, event_bus)
        self.logger = logging.getLogger(__name__)
        
        # Legacy persistence references
        self._legacy_persisted = None
        self._legacy_persistence_module = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the persistence repository with legacy data."""
        if self._initialized:
            return
            
        try:
            # Import legacy persistence
            from core import persistence
            
            # Store references to legacy persistence
            self._legacy_persisted = persistence.persisted
            self._legacy_persistence_module = persistence
            
            # Load initial data into cache
            await self._load_legacy_persistence()
            
            self._initialized = True
            self.logger.info("Persistence repository initialized successfully")
            
        except ImportError as e:
            self.logger.error(f"Failed to import legacy persistence: {e}")
            raise
    
    async def _load_legacy_persistence(self):
        """Load legacy persistence data into the new system."""
        if not self._legacy_persisted:
            return
            
        # Cache all guild data for quick access
        for guild_id, guild_data in self._legacy_persisted.items():
            if guild_id != "default":  # Skip default key
                cache_key = f"guild_data:{guild_id}"
                await self.cache_manager.set(cache_key, guild_data.copy(), ttl=600)  # 10 minutes
        
        self.logger.info(f"Loaded persistence data for {len(self._legacy_persisted)} guilds")
    
    async def get_guild_data(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get guild-specific data.
        
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
            await self.cache_manager.set(cache_key, data, ttl=600)  # 10 minutes
            
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
            gid = str(guild_id)
            
            # Update cache
            cache_key = f"guild_data:{gid}"
            await self.cache_manager.set(cache_key, data, ttl=600)
            
            # Update legacy persistence
            if self._legacy_persisted:
                self._legacy_persisted[gid] = data
                # Use legacy save method
                self._legacy_persistence_module.save_persisted(self._legacy_persisted)
            
            # Emit guild data update event
            if emit_event:
                await self._emit_event(
                    ConfigurationEvent.GUILD_CONFIGURATION_UPDATED,
                    {
                        "guild_id": gid,
                        "updated_keys": list(data.keys()),
                        "source": "persistence_repository"
                    }
                )
            
            self.logger.debug(f"Guild data updated for {gid}: {list(data.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update guild data for {guild_id}: {e}")
            return False
    
    async def set_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str,
        channel_id: int,
        message_id: int,
        emit_event: bool = True
    ) -> bool:
        """
        Store message data for the given guild/key.
        
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
            gid = str(guild_id)
            
            # Get current guild data
            guild_data = await self.get_guild_data(gid)
            
            # Update message data
            guild_data[key] = [channel_id, message_id]
            
            # Update cache and legacy persistence
            success = await self.update_guild_data(gid, {key: [channel_id, message_id]}, False)
            
            if success and emit_event:
                await self._emit_event(
                    ConfigurationEvent.MESSAGE_PERSISTED,
                    {
                        "guild_id": gid,
                        "key": key,
                        "channel_id": channel_id,
                        "message_id": message_id,
                        "source": "persistence_repository"
                    }
                )
            
            self.logger.debug(f"Persisted message for guild {gid}, key {key}: {channel_id}/{message_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to persist message for guild {guild_id}, key {key}: {e}")
            return False
    
    async def get_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Return (channel_id, message_id) tuple, or (None, None) if missing.
        Supports legacy format where only message_id was stored.
        
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
        guild_data = await self.get_guild_data(guild_id)
        value = guild_data.get(key)
        
        if isinstance(value, list) and len(value) == 2:
            result = value[0], value[1]
        elif isinstance(value, int):
            # Legacy support
            result = None, value
        else:
            result = None, None
        
        # Cache the result
        if result[0] is not None or result[1] is not None:
            await self.cache_manager.set(cache_key, {
                "channel_id": result[0],
                "message_id": result[1]
            }, ttl=1800)  # 30 minutes
        
        return result
    
    async def clear_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str,
        emit_event: bool = True
    ) -> bool:
        """
        Clear persisted message data.
        
        Args:
            guild_id: Guild identifier
            key: Message key
            emit_event: Whether to emit event
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            gid = str(guild_id)
            
            # Get current guild data
            guild_data = await self.get_guild_data(gid)
            
            # Remove message data if it exists
            if key in guild_data:
                del guild_data[key]
                
                # Update cache and legacy persistence
                success = await self.update_guild_data(gid, guild_data, False)
                
                if success and emit_event:
                    await self._emit_event(
                        ConfigurationEvent.MESSAGE_CLEARED,
                        {
                            "guild_id": gid,
                            "key": key,
                            "source": "persistence_repository"
                        }
                    )
                
                # Clear cache
                cache_key = f"persisted_msg:{gid}:{key}"
                await self.cache_manager.delete(cache_key)
                
                self.logger.debug(f"Cleared persisted message for guild {gid}, key {key}")
                return success
            
            return True  # Nothing to clear is still success
            
        except Exception as e:
            self.logger.error(f"Failed to clear persisted message for guild {guild_id}, key {key}: {e}")
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
        
        try:
            old_mode = await self.get_event_mode(guild_id)
            
            # Update guild data
            success = await self.update_guild_data(guild_id, {"event_mode": mode}, False)
            
            if success:
                # Use legacy method for consistency
                if self._legacy_persistence_module:
                    self._legacy_persistence_module.set_event_mode_for_guild(guild_id, mode)
                
                if emit_event:
                    await self._emit_event(
                        ConfigurationEvent.EVENT_MODE_CHANGED,
                        {
                            "guild_id": str(guild_id),
                            "old_mode": old_mode,
                            "new_mode": mode,
                            "source": "persistence_repository"
                        }
                    )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to set event mode for guild {guild_id}: {e}")
            return False
    
    async def get_schedule(self, guild_id: Union[str, int], key: str) -> Optional[str]:
        """
        Get scheduled time for a specific key.
        
        Args:
            guild_id: Guild identifier
            key: Schedule key
            
        Returns:
            Scheduled time string or None
        """
        await self.initialize()
        
        # Try cache first
        cache_key = f"schedule:{guild_id}:{key}"
        cached_time = await self.cache_manager.get(cache_key)
        if cached_time is not None:
            return cached_time
        
        # Fallback to legacy persistence
        guild_data = await self.get_guild_data(guild_id)
        schedule_key = f"{key}_schedule"
        scheduled_time = guild_data.get(schedule_key)
        
        # Cache the result
        if scheduled_time:
            await self.cache_manager.set(cache_key, scheduled_time, ttl=3600)  # 1 hour
        
        return scheduled_time
    
    async def set_schedule(
        self,
        guild_id: Union[str, int],
        key: str,
        dtstr: Optional[str],
        emit_event: bool = True
    ) -> bool:
        """
        Set scheduled time for a specific key.
        
        Args:
            guild_id: Guild identifier
            key: Schedule key
            dtstr: Scheduled time string (None to clear)
            emit_event: Whether to emit event
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            gid = str(guild_id)
            schedule_key = f"{key}_schedule"
            
            # Get current guild data
            guild_data = await self.get_guild_data(gid)
            
            if dtstr is None:
                # Clear schedule
                if schedule_key in guild_data:
                    del guild_data[schedule_key]
                    
                    # Update cache and legacy persistence
                    success = await self.update_guild_data(gid, guild_data, False)
                    
                    if success:
                        # Use legacy method for consistency
                        if self._legacy_persistence_module:
                            self._legacy_persistence_module.set_schedule(gid, key, None)
                        
                        # Clear cache
                        cache_key = f"schedule:{gid}:{key}"
                        await self.cache_manager.delete(cache_key)
                        
                        if emit_event:
                            await self._emit_event(
                                ConfigurationEvent.SCHEDULE_CLEARED,
                                {
                                    "guild_id": gid,
                                    "key": key,
                                    "source": "persistence_repository"
                                }
                            )
                        
                        self.logger.debug(f"Cleared schedule for guild {gid}, key {key}")
                    return success
            else:
                # Set schedule
                guild_data[schedule_key] = dtstr
                
                # Update cache and legacy persistence
                success = await self.update_guild_data(gid, {schedule_key: dtstr}, False)
                
                if success:
                    # Use legacy method for consistency
                    if self._legacy_persistence_module:
                        self._legacy_persistence_module.set_schedule(gid, key, dtstr)
                    
                    # Update cache
                    cache_key = f"schedule:{gid}:{key}"
                    await self.cache_manager.set(cache_key, dtstr, ttl=3600)  # 1 hour
                    
                    if emit_event:
                        await self._emit_event(
                            ConfigurationEvent.SCHEDULE_SET,
                            {
                                "guild_id": gid,
                                "key": key,
                                "scheduled_time": dtstr,
                                "source": "persistence_repository"
                            }
                        )
                    
                    self.logger.debug(f"Set schedule for guild {gid}, key {key}: {dtstr}")
                
                return success
            
        except Exception as e:
            self.logger.error(f"Failed to set schedule for guild {guild_id}, key {key}: {e}")
            return False
    
    async def get_all_guilds(self) -> List[str]:
        """
        Get list of all guild IDs with persisted data.
        
        Returns:
            List of guild IDs
        """
        await self.initialize()
        
        if self._legacy_persisted:
            return [gid for gid in self._legacy_persisted.keys() if gid != "default"]
        
        return []
    
    async def get_guild_statistics(self) -> Dict[str, int]:
        """
        Get statistics about persisted data.
        
        Returns:
            Statistics dictionary
        """
        await self.initialize()
        
        stats = {
            "total_guilds": 0,
            "guilds_with_registration": 0,
            "guilds_with_checkin": 0,
            "guilds_with_schedules": 0,
            "total_persisted_messages": 0
        }
        
        if self._legacy_persisted:
            for guild_id, guild_data in self._legacy_persisted.items():
                if guild_id == "default":
                    continue
                    
                stats["total_guilds"] += 1
                
                if "registration" in guild_data:
                    stats["guilds_with_registration"] += 1
                
                if "checkin" in guild_data:
                    stats["guilds_with_checkin"] += 1
                
                if any(key.endswith("_schedule") for key in guild_data.keys()):
                    stats["guilds_with_schedules"] += 1
                
                # Count persisted messages (exclude schedules and event_mode)
                message_keys = [key for key in guild_data.keys() 
                              if not key.endswith("_schedule") and key != "event_mode"]
                stats["total_persisted_messages"] += len(message_keys)
        
        return stats
    
    async def cleanup_old_data(self, days: int = 30) -> int:
        """
        Clean up old persisted data (only works with database).
        
        Args:
            days: Number of days to keep data
            
        Returns:
            Number of entries cleaned up
        """
        await self.initialize()
        
        if self._legacy_persistence_module:
            try:
                # Use legacy cleanup method
                old_stats = await self.get_guild_statistics()
                self._legacy_persistence_module.cleanup_old_data(days)
                new_stats = await self.get_guild_statistics()
                
                cleaned = old_stats["total_guilds"] - new_stats["total_guilds"]
                
                if cleaned > 0:
                    await self._emit_event(
                        ConfigurationEvent.DATA_CLEANED_UP,
                        {
                            "days": days,
                            "entries_cleaned": cleaned,
                            "source": "persistence_repository"
                        }
                    )
                
                return cleaned
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup old data: {e}")
        
        return 0
    
    async def export_guild_data(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """
        Export guild data for backup/migration.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Guild data export
        """
        await self.initialize()
        
        guild_data = await self.get_guild_data(guild_id)
        
        return {
            "guild_id": str(guild_id),
            "timestamp": int(time.time()),
            "version": "1.0",
            "data": guild_data.copy(),
            "statistics": {
                "message_count": len([k for k in guild_data.keys() 
                                    if not k.endswith("_schedule") and k != "event_mode"]),
                "schedule_count": len([k for k in guild_data.keys() if k.endswith("_schedule")]),
                "has_event_mode": "event_mode" in guild_data
            }
        }
