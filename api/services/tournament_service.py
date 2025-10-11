"""
Tournament business logic service
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from core.data_access.tournament_repository import TournamentRepository
from ..schemas.tournament import TournamentCreate, TournamentUpdate, TournamentList

class TournamentService:
    """
    Service class for tournament business logic
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
    
    async def get_tournaments(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> TournamentList:
        """
        Get list of tournaments with optional filtering
        """
        tournaments, total = await self.tournament_repo.get_all(
            skip=skip, 
            limit=limit, 
            status=status
        )
        
        return TournamentList(
            tournaments=tournaments,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit
        )
    
    async def get_tournament(self, tournament_id: int):
        """
        Get a specific tournament by ID
        """
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament with ID {tournament_id} not found")
        return tournament
    
    async def create_tournament(self, tournament_data: TournamentCreate):
        """
        Create a new tournament
        """
        return await self.tournament_repo.create(tournament_data.dict())
    
    async def update_tournament(
        self, 
        tournament_id: int, 
        tournament_data: TournamentUpdate
    ):
        """
        Update an existing tournament
        """
        # Check if tournament exists
        existing = await self.tournament_repo.get_by_id(tournament_id)
        if not existing:
            raise ValueError(f"Tournament with ID {tournament_id} not found")
        
        # Update tournament
        update_data = {k: v for k, v in tournament_data.dict().items() if v is not None}
        return await self.tournament_repo.update(tournament_id, update_data)
    
    async def delete_tournament(self, tournament_id: int):
        """
        Delete a tournament
        """
        # Check if tournament exists
        existing = await self.tournament_repo.get_by_id(tournament_id)
        if not existing:
            raise ValueError(f"Tournament with ID {tournament_id} not found")
        
        return await self.tournament_repo.delete(tournament_id)
    
    async def get_tournament_statistics(self, tournament_id: int):
        """
        Get statistics for a specific tournament
        """
        tournament = await self.get_tournament(tournament_id)
        return {
            "tournament_id": tournament.id,
            "name": tournament.name,
            "status": tournament.status,
            "max_participants": tournament.max_participants,
            "current_participants": tournament.current_participants,
            "participation_rate": (
                tournament.current_participants / tournament.max_participants * 100
                if tournament.max_participants > 0 else 0
            )
        }
