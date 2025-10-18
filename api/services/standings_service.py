"""
Service layer for tournament standings / scoreboard snapshots.

Responsible for persisting computed scoreboard data so the dashboard
and other consumers can retrieve a consistent, audit-friendly view
without re-processing Google Sheet or Riot API data in request scope.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.models import ScoreboardEntry, ScoreboardSnapshot as ScoreboardSnapshotModel
from api.schemas.scoreboard import (
    ScoreboardEntryCreate,
    ScoreboardSnapshotCreate,
    ScoreboardSnapshotSummary,
)
from api.services.errors import NotFoundError


class StandingsService:
    """Service responsible for scoreboard snapshot persistence and retrieval."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _normalize_round_names(round_names: Iterable[str]) -> List[str]:
        return [name for name in round_names if name]

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #
    def create_snapshot(
        self,
        payload: ScoreboardSnapshotCreate,
        *,
        replace_existing: bool = False,
    ) -> ScoreboardSnapshotModel:
        """
        Persist a new scoreboard snapshot.

        Args:
            payload: Scoreboard data produced by the aggregation pipeline.
            replace_existing: When True, delete any existing snapshot matching
                the tournament_id and source before inserting the new payload.
        """
        if replace_existing and payload.tournament_id:
            self._delete_existing_snapshot(
                tournament_id=payload.tournament_id,
                source=payload.source,
            )

        snapshot = ScoreboardSnapshotModel(
            tournament_id=payload.tournament_id,
            tournament_name=payload.tournament_name,
            guild_id=payload.guild_id,
            source=payload.source,
            source_timestamp=payload.source_timestamp,
            round_names=self._normalize_round_names(payload.round_names),
            extras=payload.extras,
            created_at=self._utcnow(),
            updated_at=self._utcnow(),
        )

        self.db.add(snapshot)
        self.db.flush()  # Assign snapshot.id before creating entries

        entries: List[ScoreboardEntry] = []
        for index, entry in enumerate(payload.entries, start=1):
            entries.append(self._build_entry(snapshot.id, entry, index))

        snapshot.entries = entries
        self.db.add_all(entries)
        snapshot.updated_at = self._utcnow()
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def delete_snapshot(self, snapshot_id: int) -> None:
        """Remove a snapshot and all associated entries."""
        snapshot = (
            self.db.query(ScoreboardSnapshotModel)
            .filter(ScoreboardSnapshotModel.id == snapshot_id)
            .one_or_none()
        )
        if not snapshot:
            raise NotFoundError("Scoreboard snapshot not found.")

        self.db.delete(snapshot)
        self.db.commit()

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def get_snapshot(self, snapshot_id: int) -> ScoreboardSnapshotModel:
        """Fetch a scoreboard snapshot by id."""
        snapshot = (
            self.db.query(ScoreboardSnapshotModel)
            .filter(ScoreboardSnapshotModel.id == snapshot_id)
            .one_or_none()
        )
        if not snapshot:
            raise NotFoundError("Scoreboard snapshot not found.")
        return snapshot  # noqa: RET504 - explicit return for clarity

    def get_latest_snapshot(
        self,
        *,
        tournament_id: Optional[str] = None,
        guild_id: Optional[str] = None,
    ) -> Optional[ScoreboardSnapshotModel]:
        """
        Retrieve the most recent snapshot, optionally scoped by tournament or guild.
        """
        query = self.db.query(ScoreboardSnapshotModel)
        if tournament_id:
            query = query.filter(ScoreboardSnapshotModel.tournament_id == tournament_id)
        if guild_id:
            query = query.filter(ScoreboardSnapshotModel.guild_id == guild_id)

        return query.order_by(desc(ScoreboardSnapshotModel.created_at)).first()

    def list_snapshots(
        self,
        *,
        tournament_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ScoreboardSnapshotSummary]:
        """
        List snapshot metadata for auditing/history views.
        """
        query = self.db.query(ScoreboardSnapshotModel)
        if tournament_id:
            query = query.filter(ScoreboardSnapshotModel.tournament_id == tournament_id)
        if guild_id:
            query = query.filter(ScoreboardSnapshotModel.guild_id == guild_id)

        snapshots = (
            query.order_by(desc(ScoreboardSnapshotModel.created_at))
            .limit(limit)
            .all()
        )
        return [
            ScoreboardSnapshotSummary(
                id=s.id,
                tournament_id=s.tournament_id,
                tournament_name=s.tournament_name,
                guild_id=s.guild_id,
                source=s.source,
                source_timestamp=s.source_timestamp,
                round_names=s.round_names or [],
                extras=s.extras,
                created_at=s.created_at,
                updated_at=s.updated_at,
                entry_count=len(s.entries or []),
            )
            for s in snapshots
        ]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _delete_existing_snapshot(
        self,
        *,
        tournament_id: str,
        source: Optional[str],
    ) -> None:
        """
        Delete existing snapshots for the same tournament/source combination.
        """
        query = self.db.query(ScoreboardSnapshotModel).filter(
            ScoreboardSnapshotModel.tournament_id == tournament_id
        )
        if source:
            query = query.filter(ScoreboardSnapshotModel.source == source)

        existing = query.all()
        for snapshot in existing:
            self.db.delete(snapshot)
        if existing:
            self.db.flush()

    def _build_entry(
        self,
        snapshot_id: int,
        entry: ScoreboardEntryCreate,
        default_rank: int,
    ) -> ScoreboardEntry:
        """Convert a Pydantic entry payload into a SQLAlchemy model."""
        return ScoreboardEntry(
            snapshot_id=snapshot_id,
            player_id=entry.player_id,
            player_name=entry.player_name,
            discord_id=entry.discord_id,
            riot_id=entry.riot_id,
            standing_rank=entry.standing_rank or default_rank,
            total_points=entry.total_points,
            round_scores=entry.round_scores or {},
            extras=entry.extras,
            created_at=self._utcnow(),
        )


__all__ = ["StandingsService"]
