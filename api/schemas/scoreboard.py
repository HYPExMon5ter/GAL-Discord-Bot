"""
Pydantic models for scoreboard/standings data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ScoreboardEntryBase(BaseModel):
    """Shared fields for scoreboard entries."""

    player_name: str = Field(..., description="Display name for the player.")
    player_id: Optional[str] = Field(
        default=None, description="Internal identifier (e.g., sheet row id or DB pk)."
    )
    discord_id: Optional[str] = Field(default=None, description="Discord user id.")
    riot_id: Optional[str] = Field(default=None, description="Canonical Riot player id.")
    standing_rank: Optional[int] = Field(
        default=None, description="Rank/placement within the scoreboard snapshot."
    )
    total_points: int = Field(..., description="Total tournament points accumulated.")
    round_scores: Dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of round identifier -> score for that round.",
    )
    extras: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional extra data (team, notes, etc.)."
    )


class ScoreboardEntryCreate(ScoreboardEntryBase):
    """Payload for creating scoreboard entries."""

    pass


class ScoreboardEntry(ScoreboardEntryBase):
    """Response model for a persisted scoreboard entry."""

    id: int
    snapshot_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScoreboardSnapshotBase(BaseModel):
    """Shared fields for scoreboard snapshots."""

    tournament_id: Optional[str] = Field(
        default=None, description="Tournament identifier associated with this snapshot."
    )
    tournament_name: Optional[str] = Field(
        default=None, description="Human readable tournament/event name."
    )
    guild_id: Optional[str] = Field(
        default=None, description="Discord guild associated with the snapshot."
    )
    source: Optional[str] = Field(
        default="manual", description="Origin of the data (manual, riot_api, etc.)."
    )
    source_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the source data (e.g., when the sheet was read).",
    )
    round_names: List[str] = Field(
        default_factory=list, description="Ordered list of round identifiers."
    )
    extras: Optional[Dict[str, Any]] = Field(
        default=None, description="Arbitrary metadata (scoring config, notes, etc.)."
    )


class ScoreboardSnapshotCreate(ScoreboardSnapshotBase):
    """Payload for creating a scoreboard snapshot."""

    entries: List[ScoreboardEntryCreate] = Field(
        ..., description="Entries included in the snapshot."
    )


class ScoreboardSnapshot(ScoreboardSnapshotBase):
    """Response model for a persisted scoreboard snapshot."""

    id: int
    created_at: datetime
    updated_at: datetime
    entries: List[ScoreboardEntry] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ScoreboardSnapshotSummary(ScoreboardSnapshotBase):
    """Lightweight view without entry payloads."""

    id: int
    created_at: datetime
    updated_at: datetime
    entry_count: int = Field(default=0)
    model_config = ConfigDict(from_attributes=True)


class ScoreboardRefreshRequest(BaseModel):
    """Request payload for triggering a scoreboard refresh via API."""

    guild_id: int = Field(..., description="Discord guild identifier.")
    tournament_id: Optional[str] = Field(
        default=None, description="Tournament identifier (defaults to guild)."
    )
    tournament_name: Optional[str] = Field(
        default=None, description="Friendly tournament name."
    )
    region: str = Field(default="na", description="Riot API region for fetches.")
    fetch_riot: bool = Field(
        default=True, description="Whether to pull latest placements from Riot API."
    )
    round_names: Optional[List[str]] = Field(
        default=None, description="Explicit round identifiers (optional)."
    )
    replace_existing: bool = Field(
        default=True,
        description="Replace previous snapshot for same tournament/source.",
    )
    sync_sheet: bool = Field(
        default=True,
        description="Refresh Google Sheet cache before aggregation.",
    )
    extras: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata to embed in snapshot."
    )
