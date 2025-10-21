"""
Legacy Adapter - Backward Compatibility Layer

This module provides a unified interface that maintains backward compatibility
with existing systems while gradually migrating to the new DAL architecture.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
import asyncio

from .sheets_repository import SheetsRepository
from .configuration_repository import ConfigurationRepository
from .persistence_repository import PersistenceRepository
from .cache_manager import CacheManager
from .connection_manager import ConnectionManager
from ..events.event_bus import EventBus


class LegacyAdapter:
    """
    Legacy adapter that provides backward compatibility while using the new DAL.
    
    This adapter acts as a facade that maintains the same interface as the legacy
    systems while internally using the new repository pattern and event system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.cache_manager = CacheManager()
        self.connection_manager = ConnectionManager()
        self.event_bus = EventBus()
        
        # Initialize repositories
        self.sheets_repo = SheetsRepository(self.cache_manager, self.event_bus)
        self.config_repo = ConfigurationRepository(self.cache_manager, self.event_bus)
        self.persistence_repo = PersistenceRepository(self.cache_manager, self.event_bus)
        
        # Legacy cache reference for sheets.py compatibility
        self.legacy_sheet_cache = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all components and repositories."""
        if self._initialized:
            return
            
        try:
            # Initialize repositories
            await self.sheets_repo.initialize()
            await self.config_repo.initialize()
            await self.persistence_repo.initialize()
            
            # Get legacy sheet cache reference
            self.legacy_sheet_cache = self.sheets_repo.get_legacy_cache()
            
            self._initialized = True
            self.logger.info("Legacy adapter initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize legacy adapter: {e}")
            raise
    
    # Sheets Integration Methods
    async def get_sheet_for_guild(self, guild_id: str, worksheet: str = "GAL Database"):
        """Get Google Sheet for guild."""
        await self.initialize()
        return await self.sheets_repo.get_sheet_for_guild(guild_id, worksheet)
    
    async def refresh_sheet_cache(self, guild_id: str = None) -> tuple[int, int]:
        """Refresh sheet cache."""
        await self.initialize()
        return await self.sheets_repo.refresh_sheet_cache(guild_id)
    
    async def find_or_register_user(
        self,
        discord_tag: str,
        ign: str,
        guild_id: str,
        team_name: str = None,
        alt_igns: str = None,
        pronouns: str = None
    ) -> int:
        """Find or register user."""
        await self.initialize()
        return await self.sheets_repo.find_or_register_user(
            discord_tag, ign, guild_id, team_name, alt_igns, pronouns
        )
    
    async def unregister_user(self, discord_tag: str, guild_id: str) -> bool:
        """Unregister user."""
        await self.initialize()
        return await self.sheets_repo.unregister_user(discord_tag, guild_id)
    
    async def mark_checked_in(self, discord_tag: str, guild_id: str) -> bool:
        """Mark user as checked in."""
        await self.initialize()
        return await self.sheets_repo.update_checkin_status(discord_tag, True, guild_id)
    
    async def unmark_checked_in(self, discord_tag: str, guild_id: str) -> bool:
        """Mark user as not checked in."""
        await self.initialize()
        return await self.sheets_repo.update_checkin_status(discord_tag, False, guild_id)
    
    async def reset_registration_data(self, guild_id: str) -> int:
        """Reset registration data."""
        await self.initialize()
        return await self.sheets_repo.reset_registration_data(guild_id)
    
    async def reset_checkin_data(self, guild_id: str) -> int:
        """Reset check-in data."""
        await self.initialize()
        return await self.sheets_repo.reset_checkin_data(guild_id)
    
    # Configuration Methods
    async def get_sheet_settings(self, mode: str) -> Dict[str, Any]:
        """Get sheet settings for mode."""
        await self.initialize()
        return await self.config_repo.get_sheet_settings(mode)
    
    async def get_embed_configuration(self, embed_key: str) -> Dict[str, Any]:
        """Get embed configuration."""
        await self.initialize()
        return await self.config_repo.get_embed_configuration(embed_key)
    
    async def get_role_configuration(self) -> Dict[str, Any]:
        """Get role configuration."""
        await self.initialize()
        return await self.config_repo.get_role_configuration()
    
    async def get_channel_configuration(self) -> Dict[str, str]:
        """Get channel configuration."""
        await self.initialize()
        return await self.config_repo.get_channel_configuration()
    
    async def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        await self.initialize()
        value = await self.config_repo.get_configuration(key)
        return value if value is not None else default
    
    # Persistence Methods
    async def get_guild_data(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """Get guild data."""
        await self.initialize()
        return await self.persistence_repo.get_guild_data(guild_id)
    
    async def update_guild_data(self, guild_id: Union[str, int], data: Dict[str, Any]) -> bool:
        """Update guild data."""
        await self.initialize()
        return await self.persistence_repo.update_guild_data(guild_id, data)
    
    async def set_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str,
        channel_id: int,
        message_id: int
    ) -> None:
        """Set persisted message."""
        await self.initialize()
        await self.persistence_repo.set_persisted_message(guild_id, key, channel_id, message_id)
    
    async def get_persisted_message(
        self,
        guild_id: Union[str, int],
        key: str
    ) -> tuple[Optional[int], Optional[int]]:
        """Get persisted message."""
        await self.initialize()
        return await self.persistence_repo.get_persisted_message(guild_id, key)
    
    async def get_event_mode(self, guild_id: Union[str, int]) -> str:
        """Get event mode."""
        await self.initialize()
        return await self.persistence_repo.get_event_mode(guild_id)
    
    async def set_event_mode(self, guild_id: Union[str, int], mode: str) -> None:
        """Set event mode."""
        await self.initialize()
        await self.persistence_repo.set_event_mode(guild_id, mode)
    
    async def get_schedule(self, guild_id: Union[str, int], key: str) -> Optional[str]:
        """Get schedule."""
        await self.initialize()
        return await self.persistence_repo.get_schedule(guild_id, key)
    
    async def set_schedule(self, guild_id: Union[str, int], key: str, dtstr: Optional[str]) -> None:
        """Set schedule."""
        await self.initialize()
        await self.persistence_repo.set_schedule(guild_id, key, dtstr)
    
    # Cache Management
    def get_legacy_sheet_cache(self) -> Dict:
        """Get legacy sheet cache for backward compatibility."""
        if self.legacy_sheet_cache:
            return self.legacy_sheet_cache
        return {"users": {}, "last_refresh": 0}
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        await self.initialize()
        
        # Get cache stats from cache manager
        cache_stats = await self.cache_manager.get_statistics()
        
        # Get repository-specific stats
        sheets_stats = {}
        try:
            guilds = await self.persistence_repo.get_all_guilds()
            for guild_id in guilds[:5]:  # Limit to first 5 guilds to avoid overwhelming
                sheets_stats[guild_id] = await self.sheets_repo.get_cache_stats(guild_id)
        except Exception as e:
            self.logger.warning(f"Failed to get sheets cache stats: {e}")
        
        return {
            "cache_manager": cache_stats,
            "sheets_repository": sheets_stats,
            "total_guilds": len(await self.persistence_repo.get_all_guilds()),
            "adapter_status": "initialized" if self._initialized else "not_initialized"
        }
    
    # Health Check Methods
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        await self.initialize()
        
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "issues": [],
            "timestamp": int(time.time())
        }
        
        # Check cache manager
        try:
            cache_health = await self.cache_manager.health_check()
            health_status["components"]["cache_manager"] = cache_health
            if cache_health["status"] != "healthy":
                health_status["overall_status"] = "degraded"
                health_status["issues"].append("Cache manager issues detected")
        except Exception as e:
            health_status["components"]["cache_manager"] = {"status": "error", "error": str(e)}
            health_status["overall_status"] = "unhealthy"
            health_status["issues"].append(f"Cache manager error: {e}")
        
        # Check connection manager
        try:
            conn_health = await self.connection_manager.health_check()
            health_status["components"]["connection_manager"] = conn_health
            if conn_health["status"] != "healthy":
                health_status["overall_status"] = "degraded"
                health_status["issues"].append("Connection manager issues detected")
        except Exception as e:
            health_status["components"]["connection_manager"] = {"status": "error", "error": str(e)}
            health_status["overall_status"] = "unhealthy"
            health_status["issues"].append(f"Connection manager error: {e}")
        
        # Check event bus
        try:
            event_health = await self.event_bus.health_check()
            health_status["components"]["event_bus"] = event_health
            if event_health["status"] != "healthy":
                health_status["overall_status"] = "degraded"
                health_status["issues"].append("Event bus issues detected")
        except Exception as e:
            health_status["components"]["event_bus"] = {"status": "error", "error": str(e)}
            health_status["overall_status"] = "unhealthy"
            health_status["issues"].append(f"Event bus error: {e}")
        
        # Check repositories
        for repo_name, repo in [("sheets", self.sheets_repo), 
                              ("configuration", self.config_repo),
                              ("persistence", self.persistence_repo)]:
            try:
                if hasattr(repo, 'health_check'):
                    repo_health = await repo.health_check()
                    health_status["components"][f"{repo_name}_repository"] = repo_health
                    if repo_health["status"] != "healthy":
                        health_status["overall_status"] = "degraded"
                        health_status["issues"].append(f"{repo_name.title()} repository issues detected")
                else:
                    health_status["components"][f"{repo_name}_repository"] = {"status": "unknown"}
            except Exception as e:
                health_status["components"][f"{repo_name}_repository"] = {"status": "error", "error": str(e)}
                health_status["overall_status"] = "degraded"
                health_status["issues"].append(f"{repo_name.title()} repository error: {e}")
        
        return health_status
    
    # Migration Status
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics."""
        await self.initialize()
        
        try:
            guild_stats = await self.persistence_repo.get_guild_statistics()
            cache_stats = await self.get_cache_statistics()
            
            return {
                "migration_phase": "phase_2_integration",
                "adapter_initialized": self._initialized,
                "repositories_initialized": all([
                    self.sheets_repo._initialized,
                    self.config_repo._initialized,
                    self.persistence_repo._initialized
                ]),
                "guild_statistics": guild_stats,
                "cache_statistics": cache_stats,
                "components": {
                    "cache_manager": "initialized",
                    "connection_manager": "initialized",
                    "event_bus": "initialized",
                    "sheets_repository": "initialized" if self.sheets_repo._initialized else "not_initialized",
                    "configuration_repository": "initialized" if self.config_repo._initialized else "not_initialized",
                    "persistence_repository": "initialized" if self.persistence_repo._initialized else "not_initialized"
                },
                "backward_compatibility": "active",
                "event_system": "active",
                "next_steps": [
                    "Complete Phase 2 integration testing",
                    "Migrate remaining bot commands to use new repositories",
                    "Implement full configuration management in Phase 3",
                    "Build API layer in Phase 3"
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {
                "migration_phase": "phase_2_integration",
                "status": "error",
                "error": str(e)
            }


# Global instance for backward compatibility
_legacy_adapter = None


async def get_legacy_adapter() -> LegacyAdapter:
    """Get or create the global legacy adapter instance."""
    global _legacy_adapter
    
    if _legacy_adapter is None:
        _legacy_adapter = LegacyAdapter()
        await _legacy_adapter.initialize()
    
    return _legacy_adapter


# Backward compatibility functions that maintain the same interface as legacy systems

async def initialize_legacy_systems():
    """Initialize all legacy systems through the adapter."""
    adapter = await get_legacy_adapter()
    return adapter


async def refresh_sheet_cache(guild_id: str = None) -> tuple[int, int]:
    """Backward compatibility function for sheet cache refresh."""
    adapter = await get_legacy_adapter()
    return await adapter.refresh_sheet_cache(guild_id)


async def find_or_register_user(
    discord_tag: str,
    ign: str,
    guild_id: str,
    team_name: str = None,
    alt_igns: str = None,
    pronouns: str = None
) -> int:
    """Backward compatibility function for user registration."""
    adapter = await get_legacy_adapter()
    return await adapter.find_or_register_user(
        discord_tag, ign, guild_id, team_name, alt_igns, pronouns
    )


async def get_event_mode_for_guild(guild_id: Union[str, int]) -> str:
    """Backward compatibility function for event mode."""
    adapter = await get_legacy_adapter()
    return await adapter.get_event_mode(guild_id)


async def set_event_mode_for_guild(guild_id: Union[str, int], mode: str) -> None:
    """Backward compatibility function for setting event mode."""
    adapter = await get_legacy_adapter()
    await adapter.set_event_mode(guild_id, mode)


async def get_guild_data(guild_id: Union[str, int]) -> Dict[str, Any]:
    """Backward compatibility function for guild data."""
    adapter = await get_legacy_adapter()
    return await adapter.get_guild_data(guild_id)


async def update_guild_data(guild_id: Union[str, int], data: Dict[str, Any]) -> None:
    """Backward compatibility function for updating guild data."""
    adapter = await get_legacy_adapter()
    await adapter.update_guild_data(guild_id, data)


async def set_persisted_msg(guild_id: Union[str, int], key: str, channel_id: int, msg_id: int) -> None:
    """Backward compatibility function for persisting messages."""
    adapter = await get_legacy_adapter()
    await adapter.set_persisted_message(guild_id, key, channel_id, msg_id)


async def get_persisted_msg(guild_id: Union[str, int], key: str) -> tuple[Optional[int], Optional[int]]:
    """Backward compatibility function for getting persisted messages."""
    adapter = await get_legacy_adapter()
    return await adapter.get_persisted_message(guild_id, key)
