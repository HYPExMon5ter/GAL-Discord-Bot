"""
Google Sheets Repository - Migration Adapter

This repository provides a unified interface for Google Sheets operations,
bridging the legacy sheets.py functionality with the new DAL architecture.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .base_repository import BaseRepository
from .cache_manager import CacheManager
from .connection_manager import ConnectionManager
from ..events.event_bus import EventBus
from ..events.event_types import TournamentEvent, UserEvent
from ..models.tournament import Tournament, TournamentRegistration
from ..models.user import User


@dataclass
class SheetUser:
    """Legacy sheet user data structure."""
    discord_tag: str
    ign: str
    registered: bool
    checked_in: bool
    team: str = ""
    alt_ign: str = ""
    pronouns: str = ""
    row: int = 0


class SheetsRepository(BaseRepository):
    """
    Repository for Google Sheets operations with migration support.
    
    This repository acts as an adapter between the legacy sheets.py functionality
    and the new unified data access layer. It maintains backward compatibility
    while introducing event-driven updates and caching.
    """
    
    def __init__(self, cache_manager: CacheManager, event_bus: EventBus):
        super().__init__("sheets", cache_manager, event_bus)
        self.logger = logging.getLogger(__name__)
        
        # Legacy sheet cache for backward compatibility
        self._legacy_cache = {"users": {}, "last_refresh": 0}
        self._cache_lock = None  # Will be set asynchronously
        
        # Sheet integration helpers (legacy compatibility)
        self._sheet_integration = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the sheets repository with async components."""
        if self._initialized:
            return
            
        import asyncio
        self._cache_lock = asyncio.Lock()
        
        # Import legacy components
        try:
            from integrations.sheet_integration import SheetIntegrationHelper
            self._sheet_integration = SheetIntegrationHelper
            self._initialized = True
            self.logger.info("Sheets repository initialized successfully")
        except ImportError as e:
            self.logger.error(f"Failed to import sheet integration: {e}")
            raise
    
    async def get_sheet_for_guild(self, guild_id: str, worksheet: str = "GAL Database"):
        """
        Get Google Sheet for guild using legacy method.
        
        Args:
            guild_id: Guild identifier
            worksheet: Worksheet name (default: "GAL Database")
            
        Returns:
            Google Sheet worksheet object
        """
        from integrations.sheets import get_sheet_for_guild
        return await get_sheet_for_guild(guild_id, worksheet)
    
    async def refresh_sheet_cache(self, guild_id: str = None) -> Tuple[int, int]:
        """
        Refresh the sheet cache with event-driven updates.
        
        This method maintains backward compatibility with the legacy cache_refresh
        while adding event broadcasting for real-time updates.
        
        Args:
            guild_id: Guild identifier (optional)
            
        Returns:
            Tuple of (total_changes, total_users)
        """
        await self.initialize()
        
        if not self._cache_lock:
            raise RuntimeError("Repository not properly initialized")
            
        async with self._cache_lock:
            try:
                # Use legacy refresh logic but capture events
                from integrations.sheets import refresh_sheet_cache
                
                # Store current cache state for diff calculation
                old_cache = dict(self._legacy_cache["users"])
                
                # Perform legacy refresh
                total_changes, total_users = await refresh_sheet_cache(force=True)
                
                # Get new cache state
                new_cache = dict(self._legacy_cache["users"])
                
                # Calculate and broadcast changes as events
                await self._broadcast_cache_changes(old_cache, new_cache, guild_id)
                
                # Update unified cache
                await self._update_unified_cache(new_cache, guild_id)
                
                self.logger.info(f"Sheet cache refreshed: {total_changes} changes, {total_users} users")
                return total_changes, total_users
                
            except Exception as e:
                self.logger.error(f"Failed to refresh sheet cache: {e}")
                raise
    
    async def _broadcast_cache_changes(self, old_cache: Dict, new_cache: Dict, guild_id: str):
        """Broadcast cache changes as events."""
        added = set(new_cache) - set(old_cache)
        removed = set(old_cache) - set(new_cache)
        changed = {tag for tag in set(new_cache) & set(old_cache) 
                  if new_cache[tag] != old_cache[tag]}
        
        # Broadcast user registration events
        for discord_tag in added:
            user_data = new_cache[discord_tag]
            if user_data[2]:  # registered field
                await self._emit_event(
                    UserEvent.USER_REGISTERED,
                    {
                        "discord_tag": discord_tag,
                        "ign": user_data[1],
                        "guild_id": guild_id,
                        "team": user_data[4] if len(user_data) > 4 else "",
                        "alt_ign": user_data[5] if len(user_data) > 5 else "",
                        "pronouns": user_data[6] if len(user_data) > 6 else ""
                    }
                )
        
        # Broadcast user unregistration events
        for discord_tag in removed:
            old_data = old_cache[discord_tag]
            if old_data[2]:  # was registered
                await self._emit_event(
                    UserEvent.USER_UNREGISTERED,
                    {
                        "discord_tag": discord_tag,
                        "guild_id": guild_id,
                        "reason": "removed_from_sheet"
                    }
                )
        
        # Broadcast check-in events
        for discord_tag in changed:
            old_data = old_cache[discord_tag]
            new_data = new_cache[discord_tag]
            
            old_checked_in = str(old_data[3]).upper() == "TRUE" if len(old_data) > 3 else False
            new_checked_in = str(new_data[3]).upper() == "TRUE" if len(new_data) > 3 else False
            
            if old_checked_in != new_checked_in:
                event_type = (UserEvent.USER_CHECKED_IN if new_checked_in 
                            else UserEvent.USER_CHECKED_OUT)
                await self._emit_event(
                    event_type,
                    {
                        "discord_tag": discord_tag,
                        "ign": new_data[1],
                        "guild_id": guild_id
                    }
                )
    
    async def _update_unified_cache(self, sheet_cache: Dict, guild_id: str):
        """Update the unified cache with sheet data."""
        for discord_tag, user_data in sheet_cache.items():
            cache_key = f"sheet_user:{guild_id}:{discord_tag}"
            
            user_info = {
                "discord_tag": discord_tag,
                "ign": user_data[1],
                "registered": str(user_data[2]).upper() == "TRUE" if len(user_data) > 2 else False,
                "checked_in": str(user_data[3]).upper() == "TRUE" if len(user_data) > 3 else False,
                "team": user_data[4] if len(user_data) > 4 else "",
                "alt_ign": user_data[5] if len(user_data) > 5 else "",
                "pronouns": user_data[6] if len(user_data) > 6 else "",
                "row": user_data[0] if len(user_data) > 0 else 0
            }
            
            await self.cache_manager.set(cache_key, user_info, ttl=300)  # 5 minutes
    
    async def find_or_register_user(
        self,
        discord_tag: str,
        ign: str,
        guild_id: str,
        team_name: str = None,
        alt_igns: str = None,
        pronouns: str = None
    ) -> int:
        """
        Find existing user or register new user.
        
        This method provides a bridge between the legacy sheets functionality
        and the new repository pattern.
        
        Args:
            discord_tag: Discord user tag
            ign: In-game name
            guild_id: Guild identifier
            team_name: Team name (for doubleup mode)
            alt_igns: Alternate IGNs
            pronouns: User pronouns
            
        Returns:
            Row number where user was registered/updated
        """
        await self.initialize()
        
        try:
            from integrations.sheets import find_or_register_user
            
            # Use legacy method
            row = await find_or_register_user(
                discord_tag, ign, guild_id, team_name, alt_igns, pronouns
            )
            
            # Emit registration event
            await self._emit_event(
                UserEvent.USER_REGISTERED,
                {
                    "discord_tag": discord_tag,
                    "ign": ign,
                    "guild_id": guild_id,
                    "team": team_name,
                    "alt_ign": alt_igns,
                    "pronouns": pronouns,
                    "row": row
                }
            )
            
            # Update cache
            await self.refresh_sheet_cache(guild_id)
            
            return row
            
        except Exception as e:
            self.logger.error(f"Failed to find or register user {discord_tag}: {e}")
            raise
    
    async def unregister_user(self, discord_tag: str, guild_id: str) -> bool:
        """
        Unregister user from sheet.
        
        Args:
            discord_tag: Discord user tag
            guild_id: Guild identifier
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            from integrations.sheets import unregister_user
            
            # Use legacy method
            success = await unregister_user(discord_tag, guild_id)
            
            if success:
                # Emit unregistration event
                await self._emit_event(
                    UserEvent.USER_UNREGISTERED,
                    {
                        "discord_tag": discord_tag,
                        "guild_id": guild_id,
                        "reason": "manual_unregistration"
                    }
                )
                
                # Update cache
                await self.refresh_sheet_cache(guild_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to unregister user {discord_tag}: {e}")
            raise
    
    async def update_checkin_status(
        self,
        discord_tag: str,
        checked_in: bool,
        guild_id: str
    ) -> bool:
        """
        Update user check-in status.
        
        Args:
            discord_tag: Discord user tag
            checked_in: Check-in status
            guild_id: Guild identifier
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            from integrations.sheets import (
                mark_checked_in_async if checked_in else unmark_checked_in_async
            )
            
            # Use legacy method
            success = await (mark_checked_in_async if checked_in else unmark_checked_in_async)(
                discord_tag, guild_id
            )
            
            if success:
                # Emit check-in event
                event_type = (UserEvent.USER_CHECKED_IN if checked_in 
                            else UserEvent.USER_CHECKED_OUT)
                await self._emit_event(
                    event_type,
                    {
                        "discord_tag": discord_tag,
                        "guild_id": guild_id
                    }
                )
                
                # Update cache
                await self.refresh_sheet_cache(guild_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update check-in status for {discord_tag}: {e}")
            raise
    
    async def get_registered_users(self, guild_id: str) -> List[SheetUser]:
        """
        Get all registered users from cache.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            List of SheetUser objects
        """
        await self.initialize()
        
        if not self._cache_lock:
            return []
            
        async with self._cache_lock:
            users = []
            for discord_tag, user_data in self._legacy_cache["users"].items():
                if user_data[2]:  # registered field
                    users.append(SheetUser(
                        discord_tag=discord_tag,
                        ign=user_data[1],
                        registered=True,
                        checked_in=str(user_data[3]).upper() == "TRUE" if len(user_data) > 3 else False,
                        team=user_data[4] if len(user_data) > 4 else "",
                        alt_ign=user_data[5] if len(user_data) > 5 else "",
                        pronouns=user_data[6] if len(user_data) > 6 else "",
                        row=user_data[0] if len(user_data) > 0 else 0
                    ))
            
            return users
    
    async def get_checked_in_users(self, guild_id: str) -> List[SheetUser]:
        """
        Get all checked-in users from cache.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            List of SheetUser objects
        """
        await self.initialize()
        
        if not self._cache_lock:
            return []
            
        async with self._cache_lock:
            users = []
            for discord_tag, user_data in self._legacy_cache["users"].items():
                if (user_data[2] and  # registered
                    str(user_data[3]).upper() == "TRUE"):  # checked in
                    users.append(SheetUser(
                        discord_tag=discord_tag,
                        ign=user_data[1],
                        registered=True,
                        checked_in=True,
                        team=user_data[4] if len(user_data) > 4 else "",
                        alt_ign=user_data[5] if len(user_data) > 5 else "",
                        pronouns=user_data[6] if len(user_data) > 6 else "",
                        row=user_data[0] if len(user_data) > 0 else 0
                    ))
            
            return users
    
    async def reset_registration_data(self, guild_id: str) -> int:
        """
        Reset all registration data for guild.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Number of rows cleared
        """
        await self.initialize()
        
        try:
            from integrations.sheets import reset_registered_roles_and_sheet
            import discord
            
            # Mock guild object for legacy method
            guild = type('Guild', (), {'id': int(guild_id)})()
            
            # Use legacy method
            cleared_rows = await reset_registered_roles_and_sheet(guild, None)
            
            # Emit reset event
            await self._emit_event(
                TournamentEvent.TOURNAMENT_RESET,
                {
                    "guild_id": guild_id,
                    "reset_type": "registration",
                    "rows_cleared": cleared_rows
                }
            )
            
            # Update cache
            await self.refresh_sheet_cache(guild_id)
            
            return cleared_rows
            
        except Exception as e:
            self.logger.error(f"Failed to reset registration data for guild {guild_id}: {e}")
            raise
    
    async def reset_checkin_data(self, guild_id: str) -> int:
        """
        Reset all check-in data for guild.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Number of rows cleared
        """
        await self.initialize()
        
        try:
            from integrations.sheets import reset_checked_in_roles_and_sheet
            import discord
            
            # Mock guild object for legacy method
            guild = type('Guild', (), {'id': int(guild_id)})()
            
            # Use legacy method
            cleared_rows = await reset_checked_in_roles_and_sheet(guild, None)
            
            # Emit reset event
            await self._emit_event(
                TournamentEvent.TOURNAMENT_RESET,
                {
                    "guild_id": guild_id,
                    "reset_type": "checkin",
                    "rows_cleared": cleared_rows
                }
            )
            
            # Update cache
            await self.refresh_sheet_cache(guild_id)
            
            return cleared_rows
            
        except Exception as e:
            self.logger.error(f"Failed to reset check-in data for guild {guild_id}: {e}")
            raise
    
    def get_legacy_cache(self) -> Dict:
        """
        Get legacy cache for backward compatibility.
        
        Returns:
            Legacy cache dictionary
        """
        return self._legacy_cache
    
    async def get_cache_stats(self, guild_id: str) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Args:
            guild_id: Guild identifier
            
        Returns:
            Cache statistics
        """
        await self.initialize()
        
        if not self._cache_lock:
            return {}
            
        async with self._cache_lock:
            total_users = len(self._legacy_cache["users"])
            registered_users = sum(1 for data in self._legacy_cache["users"].values() 
                                 if data[2])  # registered field
            checked_in_users = sum(1 for data in self._legacy_cache["users"].values() 
                                 if data[2] and str(data[3]).upper() == "TRUE")  # registered and checked in
            
            last_refresh = self._legacy_cache.get("last_refresh", 0)
            time_since_refresh = time.time() - last_refresh if last_refresh > 0 else 0
            
            return {
                "guild_id": guild_id,
                "total_users": total_users,
                "registered_users": registered_users,
                "checked_in_users": checked_in_users,
                "last_refresh": last_refresh,
                "time_since_refresh_seconds": time_since_refresh,
                "cache_status": "fresh" if time_since_refresh < 300 else "stale"
            }
