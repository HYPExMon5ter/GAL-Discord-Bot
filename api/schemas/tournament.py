"""
Tournament schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class Tournament(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    max_participants: int
    current_participants: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TournamentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_participants: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    max_participants: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class TournamentList(BaseModel):
    tournaments: List[Tournament]
    total: int
    page: int
    per_page: int
