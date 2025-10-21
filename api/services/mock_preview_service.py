"""
Utility service for generating mock scoreboard data used in canvas previews.

The simplified editor needs lightweight placeholder data when no live
scoreboard feed is connected. This service produces deterministic sample data
and caches the result briefly to avoid regenerating identical payloads on every
request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Any, Dict, List


@dataclass
class _CacheEntry:
    payload: Dict[str, Any]
    timestamp: datetime


class MockPreviewService:
    """Generate and cache mock scoreboard payloads for preview purposes."""

    def __init__(self, *, cache_ttl: timedelta = timedelta(minutes=2), seed: int = 1729) -> None:
        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._seed = seed

    def get_players(self, count: int = 12) -> Dict[str, Any]:
        """Return cached mock players or generate a fresh payload."""
        count = max(1, min(48, count))
        cache_key = f"players:{count}"
        now = datetime.now(UTC)

        cached = self._cache.get(cache_key)
        if cached and now - cached.timestamp < self._cache_ttl:
            return cached.payload

        payload = self._generate_players(count, now)
        self._cache[cache_key] = _CacheEntry(payload=payload, timestamp=now)
        return payload

    def _generate_players(self, count: int, generated_at: datetime) -> Dict[str, Any]:
        rng = Random(self._seed + count)
        first_names = [
            "Alex", "Jordan", "Riley", "Morgan", "Taylor", "Quinn", "Sky", "Hayden",
            "Reese", "Casey", "Rowan", "Emerson", "Blake", "Sage", "Phoenix",
        ]
        team_names = [
            "Aurora", "Vanguard", "Eclipse", "Falcons", "Quantum", "Summit",
            "Frontier", "Nebula", "Pulse", "Catalyst", "Nexus", "Orbit",
        ]

        players: List[Dict[str, Any]] = []
        base_score = rng.randint(120, 220)

        for index in range(count):
            name = f"{rng.choice(first_names)} {chr(65 + (index % 26))}."
            placement = index + 1
            score_delta = rng.randint(0, 14)
            score = max(0, base_score - placement * score_delta)
            team = rng.choice(team_names)

            extras = {
                "team": team,
                "accentColor": f"#{rng.randint(0x20, 0xE0):02x}{rng.randint(0x20, 0xE0):02x}{rng.randint(0x20, 0xE0):02x}",
            }

            players.append(
                {
                    "name": name,
                    "placement": placement,
                    "score": score,
                    "extras": extras,
                }
            )

        return {
            "players": players,
            "generated_at": generated_at,
        }


__all__ = ["MockPreviewService"]
