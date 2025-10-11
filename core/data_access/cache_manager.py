"""
Multi-level cache management system.

Provides intelligent caching with multiple levels, TTL management,
and automatic cache invalidation strategies.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import hashlib
import pickle
from abc import ABC, abstractmethod

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
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
        return datetime.utcnow() > self.expires_at
    
    def access(self) -> Any:
        """Record an access to the cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
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
            now = datetime.utcnow()
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


class RedisCache:
    """Redis-based cache implementation."""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 default_ttl: timedelta = timedelta(minutes=5),
                 key_prefix: str = "gal_cache:"):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live
            key_prefix: Prefix for all cache keys
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache")
        
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client: Optional[redis.Redis] = None
        self.logger = logging.getLogger("RedisCache")
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._client = redis.from_url(self.redis_url)
            await self._client.ping()
            self.logger.info("Connected to Redis cache")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
    
    def _make_key(self, key: str) -> str:
        """Create a namespaced key."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self._client:
            await self.connect()
        
        try:
            redis_key = self._make_key(key)
            data = await self._client.get(redis_key)
            
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[timedelta] = None,
                  tags: Optional[List[str]] = None) -> None:
        """
        Set a value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live
            tags: Cache tags (stored as metadata)
        """
        if not self._client:
            await self.connect()
        
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)
            cache_ttl = ttl or self.default_ttl
            
            # Store the data
            await self._client.setex(redis_key, cache_ttl, data)
            
            # Store tags if provided
            if tags:
                tags_key = f"{redis_key}:tags"
                await self._client.setex(tags_key, cache_ttl, pickle.dumps(tags))
                
        except Exception as e:
            self.logger.error(f"Redis set error for key {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        if not self._client:
            await self.connect()
        
        try:
            redis_key = self._make_key(key)
            tags_key = f"{redis_key}:tags"
            
            # Delete both data and tags
            await self._client.delete(redis_key, tags_key)
            return True
        except Exception as e:
            self.logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching a pattern.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            Number of keys deleted
        """
        if not self._client:
            await self.connect()
        
        try:
            redis_pattern = self._make_key(pattern)
            keys = await self._client.keys(redis_pattern)
            
            if keys:
                # Also delete tag keys
                tag_keys = [f"{key.decode()}:tags" for key in keys]
                all_keys = keys + tag_keys
                return await self._client.delete(*all_keys)
            
            return 0
        except Exception as e:
            self.logger.error(f"Redis delete pattern error for pattern {pattern}: {e}")
            return 0
    
    async def clear(self) -> None:
        """Clear all cache entries with this prefix."""
        if not self._client:
            await self.connect()
        
        try:
            pattern = self._make_key("*")
            keys = await self._client.keys(pattern)
            
            if keys:
                await self._client.delete(*keys)
                
        except Exception as e:
            self.logger.error(f"Redis clear error: {e}")


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
        
        self.redis_cache = None
        if self.config.get("redis_enabled", False) and REDIS_AVAILABLE:
            try:
                self.redis_cache = RedisCache(
                    redis_url=self.config.get("redis_url", "redis://localhost:6379"),
                    default_ttl=timedelta(minutes=self.config.get("redis_ttl_minutes", 15)),
                    key_prefix=self.config.get("redis_key_prefix", "gal_cache:")
                )
            except Exception as e:
                self.logger.warning(f"Redis cache initialization failed: {e}")
        
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
        Get a value from cache (tries memory first, then Redis).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try Redis cache
        if self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                # Populate memory cache
                await self.memory_cache.set(key, value)
                return value
        
        return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[timedelta] = None,
                  tags: Optional[List[str]] = None,
                  data_type: Optional[str] = None) -> None:
        """
        Set a value in all available cache levels.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live
            tags: Cache tags
            data_type: Type of data for strategy selection
        """
        # Set in memory cache
        await self.memory_cache.set(key, value, ttl, tags)
        
        # Set in Redis cache if available
        if self.redis_cache:
            await self.redis_cache.set(key, value, ttl, tags)
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from all cache levels.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted from any level
        """
        memory_deleted = await self.memory_cache.delete(key)
        redis_deleted = False
        
        if self.redis_cache:
            redis_deleted = await self.redis_cache.delete(key)
        
        return memory_deleted or redis_deleted
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching a pattern from all cache levels.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            Total number of keys deleted
        """
        memory_deleted = await self.memory_cache.delete_pattern(pattern)
        redis_deleted = 0
        
        if self.redis_cache:
            redis_deleted = await self.redis_cache.delete_pattern(pattern)
        
        return memory_deleted + redis_deleted
    
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
        
        if self.redis_cache:
            await self.redis_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "memory_cache": await self.memory_cache.get_stats(),
            "redis_cache": None
        }
        
        if self.redis_cache:
            try:
                # Basic Redis stats
                info = await self.redis_cache._client.info()
                stats["redis_cache"] = {
                    "connected": True,
                    "memory_used": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed")
                }
            except Exception as e:
                stats["redis_cache"] = {"connected": False, "error": str(e)}
        else:
            stats["redis_cache"] = {"connected": False, "reason": "Redis not available"}
        
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
        
        if self.redis_cache:
            await self.redis_cache.disconnect()
        
        self.logger.info("Cache manager shutdown complete")
