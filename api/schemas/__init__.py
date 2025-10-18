"""
Pydantic schemas for API models
"""

from .auth import Token, TokenData, LoginRequest
from .tournament import Tournament, TournamentCreate, TournamentUpdate
from .user import User, UserCreate, UserUpdate
from .configuration import Configuration, ConfigurationUpdate
from .scoreboard import (
    ScoreboardEntry,
    ScoreboardEntryCreate,
    ScoreboardSnapshot,
    ScoreboardSnapshotCreate,
    ScoreboardSnapshotSummary,
)

__all__ = [
    "Token", "TokenData", "LoginRequest",
    "Tournament", "TournamentCreate", "TournamentUpdate", 
    "User", "UserCreate", "UserUpdate",
    "Configuration", "ConfigurationUpdate",
    "ScoreboardEntry", "ScoreboardEntryCreate",
    "ScoreboardSnapshot", "ScoreboardSnapshotCreate", "ScoreboardSnapshotSummary",
]
