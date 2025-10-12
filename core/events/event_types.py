"""
Event type definitions and base event classes.

Defines all event types that can be emitted and handled
by the event system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import uuid

from ..models.base_model import BaseModel


class EventType(Enum):
    """Event type enumeration."""
    
    # Tournament events
    TOURNAMENT_CREATED = "tournament_created"
    TOURNAMENT_UPDATED = "tournament_updated"
    TOURNAMENT_DELETED = "tournament_deleted"
    TOURNAMENT_STARTED = "tournament_started"
    TOURNAMENT_COMPLETED = "tournament_completed"
    TOURNAMENT_CANCELLED = "tournament_cancelled"
    REGISTRATION_OPENED = "registration_opened"
    REGISTRATION_CLOSED = "registration_closed"
    USER_REGISTERED = "user_registered"
    USER_WITHDRAWN = "user_withdrawn"
    MATCH_CREATED = "match_created"
    MATCH_UPDATED = "match_updated"
    MATCH_COMPLETED = "match_completed"
    
    # User events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    USER_ROLE_ADDED = "user_role_added"
    USER_ROLE_REMOVED = "user_role_removed"
    USER_JOINED_GUILD = "user_joined_guild"
    USER_LEFT_GUILD = "user_left_guild"
    
    # Guild events
    GUILD_CREATED = "guild_created"
    GUILD_UPDATED = "guild_updated"
    GUILD_DELETED = "guild_deleted"
    GUILD_CONFIGURATION_UPDATED = "guild_configuration_updated"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_ROLE_UPDATED = "member_role_updated"
    
    # Configuration events
    CONFIGURATION_UPDATED = "configuration_updated"
    CONFIGURATION_BACKUP_CREATED = "configuration_backup_created"
    CONFIGURATION_RESTORED = "configuration_restored"
    SYSTEM_SETTING_CHANGED = "system_setting_changed"
    
    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_SHUTDOWN = "system_shutdown"
    HEALTH_CHECK_COMPLETED = "health_check_completed"
    ERROR_OCCURRED = "error_occurred"
    BACKUP_COMPLETED = "backup_completed"
    
    # Integration events
    DISCORD_MESSAGE_SENT = "discord_message_sent"
    DISCORD_COMMAND_EXECUTED = "discord_command_executed"
    SHEET_DATA_UPDATED = "sheet_data_updated"
    CACHE_CLEARED = "cache_cleared"
    DATABASE_CONNECTED = "database_connected"
    DATABASE_DISCONNECTED = "database_disconnected"


class EventPriority(Enum):
    """Event priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventCategory(Enum):
    """Event category enumeration."""
    SYSTEM = "system"
    USER = "user"
    TOURNAMENT = "tournament"
    GUILD = "guild"
    CONFIGURATION = "configuration"
    INTEGRATION = "integration"
    ERROR = "error"


@dataclass
class Event:
    """
    Base event class.
    
    All events inherit from this class and provide
    consistent structure and metadata.
    """
    
    event_type: EventType
    data: Dict[str, Any]
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    category: EventCategory = EventCategory.SYSTEM
    user_id: Optional[str] = None
    guild_id: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Auto-detect category if not set
        if self.category == EventCategory.SYSTEM:
            self.category = self._detect_category()
    
    def _detect_category(self) -> EventCategory:
        """Auto-detect event category from event type."""
        type_str = self.event_type.value
        
        if "tournament" in type_str or "registration" in type_str or "match" in type_str:
            return EventCategory.TOURNAMENT
        elif "user" in type_str or "member" in type_str:
            return EventCategory.USER
        elif "guild" in type_str:
            return EventCategory.GUILD
        elif "configuration" in type_str or "system_setting" in type_str:
            return EventCategory.CONFIGURATION
        elif "discord" in type_str or "sheet" in type_str or "cache" in type_str or "database" in type_str:
            return EventCategory.INTEGRATION
        elif "error" in type_str:
            return EventCategory.ERROR
        else:
            return EventCategory.SYSTEM
    
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the event."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "category": self.category.value,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "correlation_id": self.correlation_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        # Convert timestamp back to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        
        # Convert enums
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])
        if isinstance(data.get("priority"), int):
            data["priority"] = EventPriority(data["priority"])
        if isinstance(data.get("category"), str):
            data["category"] = EventCategory(data["category"])
        
        return cls(**data)


@dataclass
class TournamentEvent(Event):
    """Tournament-specific event."""
    
    tournament_id: str = ""
    tournament_name: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if "tournament_id" not in self.data:
            self.data["tournament_id"] = self.tournament_id
        if self.tournament_name and "tournament_name" not in self.data:
            self.data["tournament_name"] = self.tournament_name
        super().__post_init__()


@dataclass
class UserEvent(Event):
    """User-specific event."""
    
    user_id: str = ""
    username: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        self.user_id = user_id  # Ensure user_id is set
        if "user_id" not in self.data:
            self.data["user_id"] = self.user_id
        if self.username and "username" not in self.data:
            self.data["username"] = self.username
        super().__post_init__()


@dataclass
class GuildEvent(Event):
    """Guild-specific event."""
    
    guild_id: str = ""
    guild_name: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        self.guild_id = guild_id  # Ensure guild_id is set
        if "guild_id" not in self.data:
            self.data["guild_id"] = self.guild_id
        if self.guild_name and "guild_name" not in self.data:
            self.data["guild_name"] = self.guild_name
        super().__post_init__()


@dataclass
class ConfigurationEvent(Event):
    """Configuration-specific event."""
    
    configuration_key: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if "configuration_key" not in self.data:
            self.data["configuration_key"] = self.configuration_key
        if self.old_value is not None and "old_value" not in self.data:
            self.data["old_value"] = self.old_value
        if self.new_value is not None and "new_value" not in self.data:
            self.data["new_value"] = self.new_value
        super().__post_init__()


# Event factory functions for convenience
def create_tournament_event(event_type: EventType, 
                           tournament_id: str,
                           data: Dict[str, Any],
                           source: str,
                           **kwargs) -> TournamentEvent:
    """
    Create a tournament event.
    
    Args:
        event_type: Type of event
        tournament_id: Tournament ID
        data: Event data
        source: Event source
        **kwargs: Additional event parameters
        
    Returns:
        Tournament event instance
    """
    return TournamentEvent(
        event_type=event_type,
        data=data,
        source=source,
        tournament_id=tournament_id,
        **kwargs
    )


def create_user_event(event_type: EventType,
                     user_id: str,
                     data: Dict[str, Any],
                     source: str,
                     **kwargs) -> UserEvent:
    """
    Create a user event.
    
    Args:
        event_type: Type of event
        user_id: User ID
        data: Event data
        source: Event source
        **kwargs: Additional event parameters
        
    Returns:
        User event instance
    """
    return UserEvent(
        event_type=event_type,
        data=data,
        source=source,
        user_id=user_id,
        **kwargs
    )


def create_guild_event(event_type: EventType,
                      guild_id: str,
                      data: Dict[str, Any],
                      source: str,
                      **kwargs) -> GuildEvent:
    """
    Create a guild event.
    
    Args:
        event_type: Type of event
        guild_id: Guild ID
        data: Event data
        source: Event source
        **kwargs: Additional event parameters
        
    Returns:
        Guild event instance
    """
    return GuildEvent(
        event_type=event_type,
        data=data,
        source=source,
        guild_id=guild_id,
        **kwargs
    )


def create_configuration_event(event_type: EventType,
                             configuration_key: str,
                             data: Dict[str, Any],
                             source: str,
                             **kwargs) -> ConfigurationEvent:
    """
    Create a configuration event.
    
    Args:
        event_type: Type of event
        configuration_key: Configuration key
        data: Event data
        source: Event source
        **kwargs: Additional event parameters
        
    Returns:
        Configuration event instance
    """
    return ConfigurationEvent(
        event_type=event_type,
        data=data,
        source=source,
        configuration_key=configuration_key,
        **kwargs
    )
