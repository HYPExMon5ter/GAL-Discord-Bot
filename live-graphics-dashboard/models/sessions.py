"""
Session models for tracking editing sessions and user activity.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from storage.adapters.base import Base


class EditingSession(Base):
    """Model for tracking editing sessions and undo/redo state."""

    __tablename__ = "editing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Discord user ID
    template_id = Column(Integer, ForeignKey("graphics_templates.id"), nullable=False, index=True)
    current_position = Column(Integer, default=0)  # Position in history stack
    max_history_depth = Column(Integer, default=50)  # Maximum undo history

    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Session flags
    is_active = Column(Boolean, default=True, index=True)

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    # Relationships
    template = relationship("GraphicsTemplate")

    def __repr__(self):
        return f"<EditingSession(id={self.id}, user='{self.user_id}', template={self.template_id})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "current_position": self.current_position,
            "max_history_depth": self.max_history_depth,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "is_active": self.is_active,
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        session = cls()
        for key, value in data.items():
            if key in ['created_at', 'last_activity'] and value:
                value = datetime.fromisoformat(value)
            setattr(session, key, value)
        return session

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return self.current_position > 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        # This would need to be checked against actual history records
        return False  # Placeholder - would be implemented with actual history logic

    def move_position_back(self) -> bool:
        """Move position back for undo operation."""
        if self.can_undo():
            self.current_position -= 1
            self.update_activity()
            return True
        return False

    def move_position_forward(self) -> bool:
        """Move position forward for redo operation."""
        # This would need history validation
        self.current_position += 1
        self.update_activity()
        return True

    def reset_position(self):
        """Reset position to current (clear redo history)."""
        # This would be called when new actions are performed
        self.update_activity()

    def is_expired(self, hours: int = 24) -> bool:
        """Check if session is expired."""
        if not self.last_activity:
            return True

        time_diff = datetime.utcnow() - self.last_activity
        return time_diff.total_seconds() > (hours * 3600)

    def deactivate(self):
        """Deactivate the session."""
        self.is_active = False
        self.last_activity = datetime.utcnow()


class VerifiedIGN(Base):
    """Model for IGN verification cache."""

    __tablename__ = "verified_igns"

    id = Column(Integer, primary_key=True, index=True)
    riot_id = Column(String(255), unique=True, nullable=False, index=True)
    puuid = Column(String(255), nullable=False, index=True)
    region = Column(String(10), nullable=False, index=True)
    verified_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    def __repr__(self):
        return f"<VerifiedIGN(riot_id='{self.riot_id}', region='{self.region}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "riot_id": self.riot_id,
            "puuid": self.puuid,
            "region": self.region,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        verified_ign = cls()
        for key, value in data.items():
            if key in ['verified_at', 'expires_at'] and value:
                value = datetime.fromisoformat(value)
            setattr(verified_ign, key, value)
        return verified_ign

    def is_expired(self) -> bool:
        """Check if verification is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if verification is still valid."""
        return not self.is_expired()

    def extend_expiry(self, days: int = 30):
        """Extend expiry date."""
        from datetime import timedelta
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        else:
            self.expires_at = max(self.expires_at, datetime.utcnow()) + timedelta(days=days)