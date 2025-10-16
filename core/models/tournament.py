"""
Tournament data models.

Defines tournament-related entities and their relationships.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .base_model import BaseModel, utcnow


class TournamentType(Enum):
    """Tournament type enumeration."""
    SINGLES = "singles"
    DOUBLES = "doubles"
    TEAM = "team"
    CUSTOM = "custom"


class TournamentStatus(Enum):
    """Tournament status enumeration."""
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class RegistrationStatus(Enum):
    """Registration status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAITLIST = "waitlist"
    WITHDRAWN = "withdrawn"


@dataclass
class TournamentRegistration(BaseModel):
    """Represents a user's registration for a tournament."""
    
    tournament_id: str = ""
    user_id: str = ""
    status: RegistrationStatus = RegistrationStatus.PENDING
    registration_date: datetime = field(default_factory=utcnow)
    partner_id: Optional[str] = None  # For doubles tournaments
    team_name: Optional[str] = None  # For team tournaments
    seed: Optional[int] = None
    notes: Optional[str] = None
    payment_status: str = "unpaid"
    waiver_signed: bool = False
    
    def validate(self) -> None:
        """Validate tournament registration data."""
        if not self.tournament_id:
            raise ValueError("Tournament ID is required")
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.seed is not None and self.seed < 1:
            raise ValueError("Seed must be positive")


@dataclass
class Tournament(BaseModel):
    """Represents a tournament."""
    
    name: str = ""
    description: Optional[str] = None
    tournament_type: TournamentType = TournamentType.SINGLES
    status: TournamentStatus = TournamentStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    max_participants: Optional[int] = None
    current_participants: int = 0
    entry_fee: float = 0.0
    prize_pool: float = 0.0
    format: str = "standard"  # e.g., "single_elimination", "round_robin", etc.
    rules: Optional[str] = None
    location: Optional[str] = None
    organizer_id: Optional[str] = None
    discord_channel_id: Optional[str] = None
    discord_role_id: Optional[str] = None
    sheet_id: Optional[str] = None  # Google Sheets integration
    image_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate tournament data."""
        if not self.name:
            raise ValueError("Tournament name is required")
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        if self.registration_start and self.registration_end and self.registration_start >= self.registration_end:
            raise ValueError("Registration start must be before registration end")
        if self.max_participants is not None and self.max_participants < 1:
            raise ValueError("Max participants must be positive")
        if self.entry_fee < 0:
            raise ValueError("Entry fee cannot be negative")
        if self.current_participants < 0:
            raise ValueError("Current participants cannot be negative")
    
    def is_registration_open(self) -> bool:
        """Check if registration is currently open."""
        if self.status != TournamentStatus.REGISTRATION_OPEN:
            return False
        
        now = utcnow()
        
        if self.registration_start and now < self.registration_start:
            return False
        
        if self.registration_end and now > self.registration_end:
            return False
        
        if self.max_participants and self.current_participants >= self.max_participants:
            return False
        
        return True
    
    def can_register(self, user_id: str) -> tuple[bool, str]:
        """
        Check if a user can register for this tournament.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (can_register, reason)
        """
        if not self.is_registration_open():
            return False, "Registration is not open"
        
        if self.max_participants and self.current_participants >= self.max_participants:
            return False, "Tournament is full"
        
        # Additional checks would go here (e.g., user eligibility, etc.)
        
        return True, "Registration allowed"
    
    def update_participant_count(self, delta: int) -> None:
        """
        Update the participant count.
        
        Args:
            delta: Change in participant count (positive or negative)
        """
        new_count = self.current_participants + delta
        if new_count < 0:
            raise ValueError("Cannot have negative participants")
        self.current_participants = new_count
        self.update_timestamp()


@dataclass
class TournamentMatch(BaseModel):
    """Represents a match within a tournament."""
    
    tournament_id: str = ""
    round_number: int = 1
    match_number: int = 1
    player1_id: Optional[str] = None
    player2_id: Optional[str] = None
    player1_score: Optional[int] = None
    player2_score: Optional[int] = None
    winner_id: Optional[str] = None
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    scheduled_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    discord_channel_id: Optional[str] = None
    notes: Optional[str] = None
    
    def validate(self) -> None:
        """Validate match data."""
        if not self.tournament_id:
            raise ValueError("Tournament ID is required")
        if self.round_number < 1:
            raise ValueError("Round number must be positive")
        if self.match_number < 1:
            raise ValueError("Match number must be positive")
        if self.scheduled_time and self.completed_time and self.scheduled_time >= self.completed_time:
            raise ValueError("Scheduled time must be before completed time")
    
    def is_complete(self) -> bool:
        """Check if the match is complete."""
        return self.status == "completed" and self.winner_id is not None
    
    def set_winner(self, winner_id: str, player1_score: int, player2_score: int) -> None:
        """
        Set the match winner and scores.
        
        Args:
            winner_id: ID of the winning player
            player1_score: Score for player 1
            player2_score: Score for player 2
        """
        if winner_id not in [self.player1_id, self.player2_id]:
            raise ValueError("Winner must be one of the players")
        
        self.winner_id = winner_id
        self.player1_score = player1_score
        self.player2_score = player2_score
        self.status = "completed"
        self.completed_time = utcnow()
        self.update_timestamp()
