"""
Tournament API endpoints.

Routers delegate to the TournamentService while shared dependencies supply
authentication and database-backed services.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import TokenData
from api.dependencies import (
    get_active_user,
    get_tournament_service,
    require_write_access,
)
from api.services.tournament_service import TournamentService
from api.utils.service_runner import execute_service
from ..schemas.tournament import (
    Tournament,
    TournamentCreate,
    TournamentList,
    TournamentUpdate,
)

router = APIRouter()


@router.get("/", response_model=TournamentList)
async def get_tournaments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    _user: TokenData = Depends(get_active_user),
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentList:
    return await execute_service(service.get_tournaments, skip=skip, limit=limit, status=status)


@router.get("/{tournament_id}", response_model=Tournament)
async def get_tournament(
    tournament_id: int,
    _user: TokenData = Depends(get_active_user),
    service: TournamentService = Depends(get_tournament_service),
) -> Tournament:
    return await execute_service(service.get_tournament, tournament_id)


@router.post("/", response_model=Tournament)
async def create_tournament(
    tournament_data: TournamentCreate,
    _user: TokenData = Depends(require_write_access),
    service: TournamentService = Depends(get_tournament_service),
) -> Tournament:
    return await execute_service(service.create_tournament, tournament_data)


@router.put("/{tournament_id}", response_model=Tournament)
async def update_tournament(
    tournament_id: int,
    tournament_data: TournamentUpdate,
    _user: TokenData = Depends(require_write_access),
    service: TournamentService = Depends(get_tournament_service),
) -> Tournament:
    return await execute_service(service.update_tournament, tournament_id, tournament_data)


@router.delete("/{tournament_id}")
async def delete_tournament(
    tournament_id: int,
    _user: TokenData = Depends(require_write_access),
    service: TournamentService = Depends(get_tournament_service),
) -> dict:
    await execute_service(service.delete_tournament, tournament_id)
    return {"message": f"Tournament {tournament_id} deleted successfully"}


@router.get("/{tournament_id}/statistics")
async def get_tournament_statistics(
    tournament_id: int,
    _user: TokenData = Depends(get_active_user),
    service: TournamentService = Depends(get_tournament_service),
) -> dict:
    return await execute_service(service.get_tournament_statistics, tournament_id)
