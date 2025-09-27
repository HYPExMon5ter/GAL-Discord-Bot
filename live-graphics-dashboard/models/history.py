"""
History models for undo/redo functionality and state tracking.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..storage.adapters.base import Base


class GraphicsStateHistory(Base):
    """Model for graphics state history (undo/redo)."""

    __tablename__ = "graphics_state_history"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("graphics_templates.id"), nullable=False, index=True)
    command_type = Column(String(100), nullable=False, index=True)  # create, update, delete, move, etc.

    # Store state as JSON text for SQLite compatibility
    state_before = Column(Text, nullable=True)  # JSON string
    state_after = Column(Text, nullable=True)   # JSON string

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Discord user ID

    # Additional command-specific data
    command_data = Column(Text, nullable=True)  # JSON string

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    # Relationships
    template = relationship("GraphicsTemplate", back_populates="state_history")

    def __repr__(self):
        return f"<GraphicsStateHistory(id={self.id}, command='{self.command_type}', user='{self.user_id}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        return {
            "id": self.id,
            "template_id": self.template_id,
            "command_type": self.command_type,
            "state_before": json.loads(self.state_before) if self.state_before else None,
            "state_after": json.loads(self.state_after) if self.state_after else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "command_data": json.loads(self.command_data) if self.command_data else {},
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        import json
        history = cls()
        for key, value in data.items():
            if key in ['state_before', 'state_after', 'command_data'] and isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif key == 'timestamp' and value:
                value = datetime.fromisoformat(value)
            setattr(history, key, value)
        return history

    def get_state_before(self):
        """Get state_before as dictionary."""
        import json
        return json.loads(self.state_before) if self.state_before else None

    def set_state_before(self, state_dict):
        """Set state_before from dictionary."""
        import json
        self.state_before = json.dumps(state_dict) if state_dict else None

    def get_state_after(self):
        """Get state_after as dictionary."""
        import json
        return json.loads(self.state_after) if self.state_after else None

    def set_state_after(self, state_dict):
        """Set state_after from dictionary."""
        import json
        self.state_after = json.dumps(state_dict) if state_dict else None

    def get_command_data(self):
        """Get command_data as dictionary."""
        import json
        return json.loads(self.command_data) if self.command_data else {}

    def set_command_data(self, data_dict):
        """Set command_data from dictionary."""
        import json
        self.command_data = json.dumps(data_dict) if data_dict else None

    def get_description(self):
        """Get human-readable description of the command."""
        descriptions = {
            "create": "Created new element",
            "update": "Updated element properties",
            "delete": "Deleted element",
            "move": "Moved element",
            "resize": "Resized element",
            "style": "Changed element style",
            "text": "Changed text content",
            "data": "Updated data binding",
            "template": "Modified template structure"
        }
        return descriptions.get(self.command_type, f"Executed {self.command_type}")

    def can_undo(self) -> bool:
        """Check if this command can be undone."""
        # Some commands might not be undoable
        return self.state_before is not None

    def can_redo(self) -> bool:
        """Check if this command can be redone."""
        return self.state_after is not None


class SyncQueue(Base):
    """Model for tracking synchronization between databases."""

    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    operation = Column(String(20), nullable=False, index=True)  # INSERT, UPDATE, DELETE

    # Store record data as JSON
    data = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    retry_count = Column(Integer, default=0)
    last_retry = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SyncQueue(id={self.id}, table='{self.table_name}', op='{self.operation}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        return {
            "id": self.id,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "operation": self.operation,
            "data": json.loads(self.data) if self.data else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "last_retry": self.last_retry.isoformat() if self.last_retry else None,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        import json
        sync_item = cls()
        for key, value in data.items():
            if key == "data" and isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif key in ['created_at', 'last_retry'] and value:
                value = datetime.fromisoformat(value)
            setattr(sync_item, key, value)
        return sync_item

    def get_data(self):
        """Get data as dictionary."""
        import json
        return json.loads(self.data) if self.data else None

    def set_data(self, data_dict):
        """Set data from dictionary."""
        import json
        self.data = json.dumps(data_dict) if data_dict else None

    def increment_retry(self, error_msg: str = None):
        """Increment retry count and update error message."""
        self.retry_count += 1
        self.last_retry = datetime.utcnow()
        if error_msg:
            self.error_message = error_msg

    def should_retry(self, max_retries: int = 5) -> bool:
        """Check if this item should be retried."""
        return self.retry_count < max_retries