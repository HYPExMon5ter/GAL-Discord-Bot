"""
Graphics models for templates and instances.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..storage.adapters.base import Base


class GraphicsTemplate(Base):
    """Model for graphics templates."""

    __tablename__ = "graphics_templates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(100), nullable=False, index=True)  # standings, player-card, match-result, etc.
    html_content = Column(Text, nullable=True)
    css_content = Column(Text, nullable=True)
    js_content = Column(Text, nullable=True)

    # For SQLite compatibility, store JSON as TEXT
    data_bindings = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    parent_template_id = Column(Integer, ForeignKey("graphics_templates.id"), nullable=True)

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    # Relationships
    event = relationship("Event", back_populates="graphics_templates")
    parent_template = relationship("GraphicsTemplate", remote_side=[id], backref="child_templates")
    instances = relationship("GraphicsInstance", back_populates="template", cascade="all, delete-orphan")
    state_history = relationship("GraphicsStateHistory", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GraphicsTemplate(id={self.id}, name='{self.name}', type='{self.type}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "type": self.type,
            "html_content": self.html_content,
            "css_content": self.css_content,
            "js_content": self.js_content,
            "data_bindings": json.loads(self.data_bindings) if self.data_bindings else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "parent_template_id": self.parent_template_id,
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        import json
        template = cls()
        for key, value in data.items():
            if key == "data_bindings" and isinstance(value, dict):
                value = json.dumps(value)
            elif key in ['created_at', 'archived_at'] and value:
                value = datetime.fromisoformat(value)
            setattr(template, key, value)
        return template

    def get_data_bindings(self):
        """Get data bindings as dictionary."""
        import json
        return json.loads(self.data_bindings) if self.data_bindings else {}

    def set_data_bindings(self, bindings_dict):
        """Set data bindings from dictionary."""
        import json
        self.data_bindings = json.dumps(bindings_dict)

    def is_archived(self) -> bool:
        """Check if template is archived."""
        return self.archived_at is not None

    def clone_from_parent(self, parent_template: 'GraphicsTemplate', new_name: str, new_event_id: int = None):
        """Clone template from parent template."""
        self.name = new_name
        self.type = parent_template.type
        self.html_content = parent_template.html_content
        self.css_content = parent_template.css_content
        self.js_content = parent_template.js_content
        self.data_bindings = parent_template.data_bindings
        self.parent_template_id = parent_template.id
        self.event_id = new_event_id


class GraphicsInstance(Base):
    """Model for live graphics instances."""

    __tablename__ = "graphics_instances"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("graphics_templates.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)

    # Store configuration as JSON text
    config = Column(Text, nullable=True)  # JSON string

    active = Column(Boolean, default=False, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # For SQLite sync tracking
    synced_to_postgres = Column(Boolean, default=False)

    # Relationships
    template = relationship("GraphicsTemplate", back_populates="instances")
    event = relationship("Event", back_populates="graphics_instances")

    def __repr__(self):
        return f"<GraphicsInstance(id={self.id}, name='{self.name}', active={self.active})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        return {
            "id": self.id,
            "template_id": self.template_id,
            "event_id": self.event_id,
            "name": self.name,
            "config": json.loads(self.config) if self.config else {},
            "active": self.active,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "synced_to_postgres": self.synced_to_postgres
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary."""
        import json
        instance = cls()
        for key, value in data.items():
            if key == "config" and isinstance(value, dict):
                value = json.dumps(value)
            elif key == 'last_updated' and value:
                value = datetime.fromisoformat(value)
            setattr(instance, key, value)
        return instance

    def get_config(self):
        """Get configuration as dictionary."""
        import json
        return json.loads(self.config) if self.config else {}

    def set_config(self, config_dict):
        """Set configuration from dictionary."""
        import json
        self.config = json.dumps(config_dict)

    def activate(self):
        """Mark instance as active."""
        self.active = True
        self.last_updated = datetime.utcnow()

    def deactivate(self):
        """Mark instance as inactive."""
        self.active = False
        self.last_updated = datetime.utcnow()