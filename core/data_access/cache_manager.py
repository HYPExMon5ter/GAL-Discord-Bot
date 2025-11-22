"""
Multi-level cache management system.

Provides intelligent caching with multiple levels, TTL management,
and automatic cache invalidation strategies.
"""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import hashlib
import pickle
from abc import ABC, abstractmethod

# Redis support removed - using in-memory caching only
REDIS_AVAILABLE = False


class CacheLevel(Enum):
    """Cache level enumeration."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


class CacheStrategy(Enum):
    """Cache invalidation strategy."""
    TTL = "ttl"  # Time-based expiration
    LRU = "lru"   # Least recently used
    LFU = "lfu"   # Least frequently used
    MANUAL = "manual"  # Manual invalidation only


def utcnow() -> datetime:
    """Return the current time in UTC with timezone information."""
    return datetime.now(UTC)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return utcnow() > self.expires_at
    
    def access(self) -> Any:
        """Record an access to the cache entry."""
        self.access_count += 1
        self.last_accessed = utcnow()
        return self.value


class MemoryCache:
    """In-memory cache implementation with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: timedelta = timedelta(minutes=5)):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live for entries
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("MemoryCache")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.access()
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[timedelta] = None,
                  tags: Optional[List[str]] = None) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (uses default if not provided)
            tags: Cache tags for group invalidation
        """
        async with self._lock:
            now = utcnow()
            expires_at = now + (ttl or self.default_ttl)
            
            # Calculate size (rough estimate)
            size_bytes = len(pickle.dumps(value))
            
            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or [],
                last_accessed=now
            )
            
            # Evict if necessary
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()
            
            self._cache[key] = entry
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcard)
            
        Returns:
            Number of keys deleted
        """
        async with self._lock:
            import fnmatch
            keys_to_delete = [
                key for key in self._cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            return len(keys_to_delete)
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """
        Delete entries with specified tags.
        
        Args:
            tags: List of tags to match
            
        Returns:
            Number of entries deleted
        """
        async with self._lock:
            keys_to_delete = []
            for key, entry in self._cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            return len(keys_to_delete)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired entries.
        
        Returns:
            Number of entries cleaned up
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            return {
                "entries": len(self._cache),
                "max_size": self.max_size,
                "total_size_bytes": total_size,
                "expired_entries": expired_count,
                "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
            }


class CacheManager:
    """
    Multi-level cache manager.
    
    Coordinates between different cache levels and provides
    intelligent caching strategies.
    """
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize cache manager.
        
        Args:
            config: Cache configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger("CacheManager")
        
        # Initialize cache levels
        self.memory_cache = MemoryCache(
            max_size=self.config.get("memory_max_size", 1000),
            default_ttl=timedelta(minutes=self.config.get("memory_ttl_minutes", 5))
        )
        
        # Redis support removed - using in-memory caching only
        
        # Cache strategies
        self.strategies: Dict[str, CacheStrategy] = {}
        self._setup_default_strategies()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _setup_default_strategies(self) -> None:
        """Setup default caching strategies for different data types."""
        self.strategies.update({
            "user": CacheStrategy.TTL,
            "tournament": CacheStrategy.TTL,
            "guild": CacheStrategy.TTL,
            "configuration": CacheStrategy.TTL,
            "temporary": CacheStrategy.LRU,
            "static": CacheStrategy.MANUAL
        })
    
    def set_strategy(self, data_type: str, strategy: CacheStrategy) -> None:
        """
        Set caching strategy for a data type.
        
        Args:
            data_type: Type of data
            strategy: Caching strategy
        """
        self.strategies[data_type] = strategy
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache (memory only).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        # Memory cache only
        return await self.memory_cache.get(key)
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[timedelta] = None,
                  tags: Optional[List[str]] = None,
                  data_type: Optional[str] = None) -> None:
        """
        Set a value in memory cache only.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live
            tags: Cache tags
            data_type: Type of data for strategy selection
        """
        # Set in memory cache only
        await self.memory_cache.set(key, value, ttl, tags)
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from memory cache only.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        return await self.memory_cache.delete(key)
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching a pattern from memory cache only.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            Total number of keys deleted
        """
        return await self.memory_cache.delete_pattern(pattern)
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """
        Delete entries with specified tags.
        
        Args:
            tags: List of tags to match
            
        Returns:
            Number of entries deleted
        """
        # Only memory cache supports tags currently
        return await self.memory_cache.delete_by_tags(tags)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        await self.memory_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            "timestamp": utcnow().isoformat(),
            "memory_cache": await self.memory_cache.get_stats(),
            "redis_cache": {"status": "removed", "reason": "Redis support removed - using memory-only caching"}
        }
        
        return stats
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        async def cleanup_expired():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean every 5 minutes
                    await self.memory_cache.cleanup_expired()
                except Exception as e:
                    self.logger.error(f"Cache cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_expired())
    
    async def shutdown(self) -> None:
        """Shutdown the cache manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Redis support removed - no disconnect needed
        
        self.logger.info("Cache manager shutdown complete")
