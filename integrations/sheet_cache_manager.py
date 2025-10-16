"""Centralised cache management for Google Sheets data."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict


class SheetCacheManager:
    """Async-aware cache container with TTL tracking."""

    def __init__(self, ttl_seconds: int = 600) -> None:
        self._cache: Dict[str, Any] = {"users": {}, "last_refresh": 0.0}
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    @property
    def data(self) -> Dict[str, Any]:
        """Expose underlying cache dictionary (for backwards compatibility)."""
        return self._cache

    @property
    def lock(self) -> asyncio.Lock:
        """Expose shared async lock."""
        return self._lock

    def mark_refresh(self) -> None:
        """Record the completion of a cache refresh."""
        self._cache["last_refresh"] = time.time()

    def is_stale(self) -> bool:
        """Return True if cache exceeds TTL."""
        last_refresh = self._cache.get("last_refresh", 0.0)
        return (time.time() - last_refresh) >= self._ttl

    async def snapshot(self, key: str = "users") -> Dict[str, Any]:
        """Return a shallow copy of cached data for safe read access."""
        async with self._lock:
            return dict(self._cache.get(key, {}))

    def set_ttl(self, ttl_seconds: int) -> None:
        """Update TTL at runtime."""
        self._ttl = ttl_seconds


__all__ = ["SheetCacheManager"]
