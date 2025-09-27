"""
Event models for tournament/event management and archiving.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean
from sqlalchemy.orm import relationship
from storage.adapters.base import Base


class Event(Base):
    """Model for tournament events."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="active", index=True)  # active, completed, archived
    created_at = Column(DateTime, default=datetime.utcnow)

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    # Relationships
    graphics_templates = relationship("GraphicsTemplate", back_populates="event", cascade="all, delete-orphan")
    graphics_instances = relationship("GraphicsInstance", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        event = cls()
        for key, value in data.items():
            if key in ['start_date', 'end_date'] and value:
                value = datetime.fromisoformat(value).date()
            elif key == 'created_at' and value:
                value = datetime.fromisoformat(value)
            setattr(event, key, value)
        return event

    def is_active(self) -> bool:
        """Check if event is currently active."""
        return self.status == "active"

    def is_archived(self) -> bool:
        """Check if event is archived."""
        return self.status == "archived"

    def can_be_archived(self) -> bool:
        """Check if event can be archived (completed or past end date)."""
        if self.status == "completed":
            return True
        if self.end_date and self.end_date < date.today():
            return True
        return False