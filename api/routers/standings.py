"""
Standings/scoreboard API endpoints.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from api.auth import TokenData
from api.dependencies import (
    get_active_user,
    get_standings_aggregator,
    get_standings_service,
    require_write_access,
)
from api.schemas.scoreboard import (
    ScoreboardRefreshRequest,
    ScoreboardSnapshot,
    ScoreboardSnapshotSummary,
)
from api.services.standings_aggregator import StandingsAggregator
from api.services.standings_service import StandingsService
from integrations.sheets import refresh_sheet_cache

router = APIRouter(prefix="/scoreboard", tags=["scoreboard"])


def _set_snapshot_headers(response: Response, snapshot: ScoreboardSnapshot) -> None:
    """Attach caching headers (ETag/Last-Modified) for clients."""
    if snapshot.updated_at:
        response.headers["ETag"] = f'W/"{snapshot.updated_at.timestamp()}"'
        response.headers["Last-Modified"] = snapshot.updated_at.isoformat()


@router.get(
    "/latest",
    response_model=ScoreboardSnapshot,
    summary="Get the latest scoreboard snapshot.",
)
async def get_latest_scoreboard(
    response: Response,
    tournament_id: Optional[str] = Query(None),
    guild_id: Optional[str] = Query(None),
    _user: TokenData = Depends(get_active_user),
    service: StandingsService = Depends(get_standings_service),
) -> ScoreboardSnapshot:
    snapshot = service.get_latest_snapshot(
        tournament_id=tournament_id,
        guild_id=guild_id,
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scoreboard snapshot found.",
        )
    schema = ScoreboardSnapshot.model_validate(snapshot)
    _set_snapshot_headers(response, schema)
    return schema


@router.get(
    "/snapshots",
    response_model=List[ScoreboardSnapshotSummary],
    summary="List recent scoreboard snapshots.",
)
async def list_scoreboard_snapshots(
    tournament_id: Optional[str] = Query(None),
    guild_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: TokenData = Depends(get_active_user),
    service: StandingsService = Depends(get_standings_service),
) -> List[ScoreboardSnapshotSummary]:
    return service.list_snapshots(
        tournament_id=tournament_id,
        guild_id=guild_id,
        limit=limit,
    )


@router.get(
    "/{snapshot_id}",
    response_model=ScoreboardSnapshot,
    summary="Get a scoreboard snapshot by id.",
)
async def get_scoreboard_snapshot(
    snapshot_id: int,
    response: Response,
    _user: TokenData = Depends(get_active_user),
    service: StandingsService = Depends(get_standings_service),
) -> ScoreboardSnapshot:
    snapshot = service.get_snapshot(snapshot_id)
    schema = ScoreboardSnapshot.model_validate(snapshot)
    _set_snapshot_headers(response, schema)
    return schema


@router.post(
    "/refresh",
    response_model=ScoreboardSnapshot,
    summary="Trigger a scoreboard refresh via the aggregation pipeline.",
)
async def refresh_scoreboard_snapshot(
    payload: ScoreboardRefreshRequest,
    response: Response,
    _user: TokenData = Depends(require_write_access),
    aggregator: StandingsAggregator = Depends(get_standings_aggregator),
) -> ScoreboardSnapshot:
    """
    Refresh scoreboard data for the specified guild/tournament.

    This endpoint is primarily used by automation/bot workflows.
    """
    guild_id = payload.guild_id
    if payload.sync_sheet:
        await refresh_sheet_cache(force=True)

    snapshot_model = await aggregator.refresh_scoreboard(
        guild_id=guild_id,
        tournament_id=payload.tournament_id or str(guild_id),
        tournament_name=payload.tournament_name,
        round_names=payload.round_names,
        fetch_riot=payload.fetch_riot,
        region=payload.region,
        replace_existing=payload.replace_existing,
        extras=payload.extras,
    )

    schema = ScoreboardSnapshot.model_validate(snapshot_model)
    _set_snapshot_headers(response, schema)
    return schema


__all__ = ["router"]
