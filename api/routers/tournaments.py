"""
Tournament API endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_database_session
from ..auth import get_current_authenticated_user, TokenData
from ..services.tournament_service import TournamentService
from ..schemas.tournament import (
    Tournament, 
    TournamentCreate, 
    TournamentUpdate, 
    TournamentList
)


router = APIRouter()

@router.get("/", response_model=TournamentList)
async def get_tournaments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get list of tournaments with pagination and optional status filtering
    """
    try:
        service = TournamentService(db)
        return await service.get_tournaments(skip=skip, limit=limit, status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tournament_id}", response_model=Tournament)
async def get_tournament(
    tournament_id: int,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific tournament by ID
    """
    try:
        service = TournamentService(db)
        return await service.get_tournament(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Tournament)
async def create_tournament(
    tournament_data: TournamentCreate,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new tournament
    """
    try:
        service = TournamentService(db)
        return await service.create_tournament(tournament_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{tournament_id}", response_model=Tournament)
async def update_tournament(
    tournament_id: int,
    tournament_data: TournamentUpdate,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update an existing tournament
    """
    try:
        service = TournamentService(db)
        return await service.update_tournament(tournament_id, tournament_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{tournament_id}")
async def delete_tournament(
    tournament_id: int,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a tournament
    """
    try:
        service = TournamentService(db)
        await service.delete_tournament(tournament_id)
        return {"message": f"Tournament {tournament_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tournament_id}/statistics")
async def get_tournament_statistics(
    tournament_id: int,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get statistics for a specific tournament
    """
    try:
        service = TournamentService(db)
        return await service.get_tournament_statistics(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
