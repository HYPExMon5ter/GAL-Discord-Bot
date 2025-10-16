"""
User data models.

Defines user-related entities and their relationships.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .base_model import BaseModel, utcnow


class UserRole(Enum):
    """User role enumeration."""
    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"
    TOURNAMENT_ORGANIZER = "tournament_organizer"
    STREAMER = "streamer"
    CASTER = "caster"


class UserStatus(Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SUSPENDED = "suspended"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


@dataclass
class UserStats(BaseModel):
    """User statistics and performance metrics."""
    
    user_id: str = ""
    tournaments_played: int = 0
    tournaments_won: int = 0
    matches_played: int = 0
    matches_won: int = 0
    win_rate: float = 0.0
    average_placement: float = 0.0
    earnings: float = 0.0
    ranking_points: float = 0.0
    current_rank: Optional[str] = None
    peak_rank: Optional[str] = None
    last_active: Optional[datetime] = field(default_factory=utcnow)
    custom_stats: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate user stats data."""
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.tournaments_played < 0:
            raise ValueError("Tournaments played cannot be negative")
        if self.tournaments_won < 0:
            raise ValueError("Tournaments won cannot be negative")
        if self.matches_played < 0:
            raise ValueError("Matches played cannot be negative")
        if self.matches_won < 0:
            raise ValueError("Matches won cannot be negative")
        if not 0 <= self.win_rate <= 1:
            raise ValueError("Win rate must be between 0 and 1")
        if self.earnings < 0:
            raise ValueError("Earnings cannot be negative")
    
    def update_win_rate(self) -> None:
        """Recalculate win rate based on matches played and won."""
        if self.matches_played > 0:
            self.win_rate = self.matches_won / self.matches_played
        else:
            self.win_rate = 0.0
        self.update_timestamp()
    
    def add_tournament_result(self, placement: int, winnings: float = 0.0) -> None:
        """
        Add a tournament result to the user's stats.
        
        Args:
            placement: Final placement in tournament
            winnings: Prize money won
        """
        self.tournaments_played += 1
        if placement == 1:
            self.tournaments_won += 1
        self.earnings += winnings
        
        # Update average placement
        total_placements = self.average_placement * (self.tournaments_played - 1) + placement
        self.average_placement = total_placements / self.tournaments_played
        
        self.update_timestamp()


@dataclass
class UserPreferences(BaseModel):
    """User preferences and settings."""
    
    user_id: str = ""
    timezone: str = "UTC"
    locale: str = "en-US"
    theme: str = "dark"  # dark, light, auto
    notifications_enabled: bool = True
    email_notifications: bool = False
    discord_notifications: bool = True
    tournament_reminders: bool = True
    result_notifications: bool = True
    privacy_level: str = "public"  # public, friends, private
    preferred_games: List[str] = field(default_factory=list)
    bio: Optional[str] = None
    social_links: Dict[str, str] = field(default_factory=dict)
    custom_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate user preferences data."""
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.privacy_level not in ["public", "friends", "private"]:
            raise ValueError("Invalid privacy level")
        if self.theme not in ["dark", "light", "auto"]:
            raise ValueError("Invalid theme preference")


@dataclass
class User(BaseModel):
    """Represents a Discord user in the system."""
    
    discord_id: str = ""
    username: str = ""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    roles: List[UserRole] = field(default_factory=list)
    status: UserStatus = UserStatus.ACTIVE
    joined_at: Optional[datetime] = field(default_factory=utcnow)
    last_seen: Optional[datetime] = field(default_factory=utcnow)
    is_verified: bool = False
    is_banned: bool = False
    ban_reason: Optional[str] = None
    ban_expires: Optional[datetime] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Embedded data
    stats: Optional[UserStats] = None
    preferences: Optional[UserPreferences] = None
    
    def validate(self) -> None:
        """Validate user data."""
        if not self.discord_id:
            raise ValueError("Discord ID is required")
        if not self.username:
            raise ValueError("Username is required")
        if self.is_banned and not self.ban_reason:
            raise ValueError("Ban reason is required when user is banned")
        if self.ban_expires and self.ban_expires <= utcnow():
            # Auto-expire ban
            self.is_banned = False
            self.ban_reason = None
            self.ban_expires = None
    
    def add_role(self, role: UserRole) -> None:
        """
        Add a role to the user.
        
        Args:
            role: Role to add
        """
        if role not in self.roles:
            self.roles.append(role)
            self.update_timestamp()
    
    def remove_role(self, role: UserRole) -> None:
        """
        Remove a role from the user.
        
        Args:
            role: Role to remove
        """
        if role in self.roles:
            self.roles.remove(role)
            self.update_timestamp()
    
    def has_role(self, role: UserRole) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role: Role to check
            
        Returns:
            True if user has the role
        """
        return role in self.roles
    
    def has_permission(self, required_role: UserRole) -> bool:
        """
        Check if user has permission based on role hierarchy.
        
        Args:
            required_role: Minimum required role
            
        Returns:
            True if user has sufficient permissions
        """
        role_hierarchy = {
            UserRole.MEMBER: 0,
            UserRole.STREAMER: 1,
            UserRole.CASTER: 1,
            UserRole.TOURNAMENT_ORGANIZER: 2,
            UserRole.MODERATOR: 3,
            UserRole.ADMIN: 4
        }
        
        user_level = max(role_hierarchy.get(role, 0) for role in self.roles)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def ban(self, reason: str, expires: Optional[datetime] = None) -> None:
        """
        Ban the user.
        
        Args:
            reason: Reason for ban
            expires: Optional ban expiration date
        """
        self.is_banned = True
        self.ban_reason = reason
        self.ban_expires = expires
        self.status = UserStatus.BANNED
        self.update_timestamp()
    
    def unban(self) -> None:
        """Unban the user."""
        self.is_banned = False
        self.ban_reason = None
        self.ban_expires = None
        self.status = UserStatus.ACTIVE
        self.update_timestamp()
    
    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = utcnow()
        self.update_timestamp()
    
    def is_active(self) -> bool:
        """Check if user is active (not banned or suspended)."""
        return self.status in [UserStatus.ACTIVE, UserStatus.VERIFIED] and not self.is_banned
