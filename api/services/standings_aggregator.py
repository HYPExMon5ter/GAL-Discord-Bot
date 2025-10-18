"""
Standings aggregation pipeline.

Transforms Google Sheet snapshots and (optionally) Riot API data into a
normalized scoreboard payload that can be persisted via `StandingsService`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from api.schemas.scoreboard import (
    ScoreboardEntryCreate,
    ScoreboardSnapshot,
    ScoreboardSnapshotCreate,
)
from api.services.standings_service import StandingsService
from integrations.sheet_integration import build_event_snapshot

try:
    # Riot integration is optional; we guard imports for easier testing.
    from integrations.riot_api import RiotAPI, RiotAPIError
except Exception:  # pragma: no cover - optional dependency path
    RiotAPI = None  # type: ignore
    RiotAPIError = Exception  # type: ignore

log = logging.getLogger(__name__)

_POINT_MAP = {placement: points for placement, points in zip(range(1, 9), range(8, 0, -1))}


class StandingsAggregator:
    """Aggregate standings data into scoreboard snapshots."""

    def __init__(self, standings_service: StandingsService):
        self._standings_service = standings_service

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def refresh_scoreboard(
        self,
        *,
        guild_id: int,
        tournament_id: Optional[str] = None,
        tournament_name: Optional[str] = None,
        round_names: Optional[List[str]] = None,
        source: str = "riot_api",
        region: str = "na",
        replace_existing: bool = True,
        fetch_riot: bool = True,
        snapshot_override: Optional[Dict[str, Any]] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> ScoreboardSnapshot:
        """
        Build and persist a scoreboard snapshot.

        Args:
            guild_id: Discord guild identifier.
            tournament_id: Identifier for the tournament/event.
            tournament_name: Human-readable tournament name.
            round_names: Explicit round identifiers (e.g., ["round_1", ...]).
            source: Metadata string denoting data origin (riot_api/manual/etc.).
            region: Riot API region to query (when fetch_riot is enabled).
            replace_existing: Remove prior snapshots for same tournament/source.
            fetch_riot: Whether to augment standings with Riot match data.
            snapshot_override: Pre-built sheet snapshot (primarily for testing).
        """
        sheet_snapshot = snapshot_override or await build_event_snapshot(guild_id)
        players = self._extract_players(sheet_snapshot)

        if not players:
            log.warning("No players found in sheet snapshot for guild %s", guild_id)

        round_scores_from_riot = {}
        if fetch_riot:
            riot_scores = await self._fetch_riot_round_scores(players, region=region)
            if riot_scores:
                round_scores_from_riot = riot_scores
                if not round_names:
                    round_names = ["round_1"]

        final_round_names, entries_payload = self._build_entries(
            players,
            requested_rounds=round_names,
            riot_scores=round_scores_from_riot,
        )

        snapshot_extras = {
            "sheet_metadata": sheet_snapshot.get("metadata"),
            "mode": sheet_snapshot.get("mode"),
        }
        if extras:
            snapshot_extras.update(extras)

        snapshot_payload = ScoreboardSnapshotCreate(
            tournament_id=tournament_id,
            tournament_name=tournament_name,
            guild_id=str(guild_id),
            source=source,
            source_timestamp=datetime.now(UTC),
            round_names=final_round_names,
            extras=snapshot_extras,
            entries=entries_payload,
        )

        snapshot = self._standings_service.create_snapshot(
            snapshot_payload,
            replace_existing=replace_existing,
        )
        return snapshot

    # ------------------------------------------------------------------ #
    # Snapshot processing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_players(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize players from sheet snapshot."""
        standings = snapshot.get("standings") or []
        players: Dict[str, Dict[str, Any]] = {}

        def upsert_player(data: Dict[str, Any]) -> None:
            ign = (data.get("ign") or data.get("player_name") or "").strip()
            discord_tag = (data.get("discord_tag") or "").strip()
            key = discord_tag.lower() or ign.lower()
            if not key:
                return
            players[key] = {
                "key": key,
                "player_name": data.get("player_name") or ign or discord_tag,
                "discord_tag": discord_tag or None,
                "riot_id": ign or None,
                "player_id": data.get("sheet_row"),
                "points": data.get("points"),
                "round_scores": data.get("round_scores") or {},
                "extras": {
                    k: v
                    for k, v in data.items()
                    if k
                    not in {
                        "player_name",
                        "ign",
                        "discord_tag",
                        "points",
                        "round_scores",
                        "sheet_row",
                    }
                },
            }

        for entry in standings:
            upsert_player(entry)

        # Fallback to lobbies if standings were absent
        if not players:
            for lobby in snapshot.get("lobbies") or []:
                for participant in lobby.get("players") or []:
                    upsert_player(participant)

        return list(players.values())

    def _build_entries(
        self,
        players: List[Dict[str, Any]],
        *,
        requested_rounds: Optional[List[str]],
        riot_scores: Dict[str, Dict[str, int]],
    ) -> Tuple[List[str], List[ScoreboardEntryCreate]]:
        """Convert normalized player records into scoreboard entry payloads."""
        round_names: List[str] = []
        if requested_rounds:
            round_names = list(requested_rounds)
        else:
            collected = {
                round_name
                for player in players
                for round_name in player.get("round_scores", {}).keys()
            }
            if riot_scores:
                for scores in riot_scores.values():
                    collected.update(scores.keys())
            round_names = sorted(collected)

        entries_payload: List[ScoreboardEntryCreate] = []
        for player in players:
            base_scores = dict(player.get("round_scores") or {})
            if player["key"] in riot_scores:
                base_scores.update(riot_scores[player["key"]])

            normalized_scores = self._normalize_round_scores(base_scores, round_names)
            total_points = player.get("points")
            if total_points is None:
                total_points = sum(normalized_scores.values())

            entries_payload.append(
                ScoreboardEntryCreate(
                    player_name=player["player_name"],
                    player_id=player.get("player_id"),
                    discord_id=player.get("discord_tag"),
                    riot_id=player.get("riot_id"),
                    total_points=total_points or 0,
                    round_scores=normalized_scores,
                    extras=player.get("extras"),
                )
            )

        # Sort descending by total points, tie-breaking by player name
        entries_payload.sort(
            key=lambda entry: (-entry.total_points, entry.player_name.lower())
        )
        for idx, entry in enumerate(entries_payload, start=1):
            entry.standing_rank = idx

        return round_names, entries_payload

    @staticmethod
    def _normalize_round_scores(
        round_scores: Dict[str, int], round_names: List[str]
    ) -> Dict[str, int]:
        """Ensure every round has an explicit integer score (default 0)."""
        if not round_names:
            return {k: int(v) for k, v in round_scores.items()}
        normalized = {}
        for name in round_names:
            value = round_scores.get(name)
            normalized[name] = int(value) if value is not None else 0
        return normalized

    # ------------------------------------------------------------------ #
    # Riot API integration
    # ------------------------------------------------------------------ #
    async def _fetch_riot_round_scores(
        self,
        players: List[Dict[str, Any]],
        *,
        region: str,
    ) -> Dict[str, Dict[str, int]]:
        """Fetch latest match placements and convert to round scores."""
        if not RiotAPI:
            log.debug("Riot API client not available; skipping Riot fetch.")
            return {}

        if not os.getenv("RIOT_API_KEY"):
            log.debug("RIOT_API_KEY not set; skipping Riot fetch.")
            return {}

        async with RiotAPI() as riot:  # type: ignore[call-arg]
            tasks = [
                self._fetch_single_player_score(
                    riot, player_key=player["key"], riot_id=player.get("riot_id"), region=region
                )
                for player in players
                if player.get("riot_id")
            ]
            if not tasks:
                return {}

            results = await asyncio.gather(*tasks, return_exceptions=True)

        scores: Dict[str, Dict[str, int]] = {}
        for result in results:
            if isinstance(result, Exception):
                log.warning("Error fetching Riot data: %s", result)
                continue
            if not result:
                continue
            key, score = result
            scores[key] = score
        return scores

    async def _fetch_single_player_score(
        self,
        riot_client: RiotAPI,  # type: ignore[name-defined]
        *,
        player_key: str,
        riot_id: Optional[str],
        region: str,
    ) -> Optional[Tuple[str, Dict[str, int]]]:
        """Fetch latest placement for a single player."""
        if not riot_id:
            return None

        try:
            result = await riot_client.get_latest_placement(region, riot_id)
        except RiotAPIError as exc:  # type: ignore[name-defined]
            log.warning("Riot API error for %s: %s", riot_id, exc)
            return None
        except Exception as exc:  # pragma: no cover - network issues
            log.warning("Unexpected Riot API error for %s: %s", riot_id, exc)
            return None

        if not result.get("success"):
            return None

        placement = result.get("placement")
        if not isinstance(placement, int):
            return None

        points = _POINT_MAP.get(placement, 0)
        return player_key, {"round_1": points}


__all__ = ["StandingsAggregator"]
