"""
Guardian Angel League Discord Bot - Core Architecture

This module provides the unified data flow architecture foundation
including data models, data access layer, event system, and utilities.

Example usage:

```python
# Initialize the new architecture
from core.data_access import CacheManager, ConnectionManager
from core.events import EventBus, get_event_bus
from core.models import Tournament, User

# Setup components
cache_manager = CacheManager(config={"redis_enabled": True})
connection_manager = ConnectionManager()
event_bus = get_event_bus()

# Register database connections
connection_manager.register_connection(
    "main", 
    ConnectionConfig(url="postgresql://localhost/gal_bot")
)

# Subscribe to events
from core.events.handlers import TournamentEventHandler
event_bus.subscribe(TournamentEventHandler())

# Create a tournament
tournament = Tournament(
    name="Summer Championship 2025",
    tournament_type=TournamentType.SINGLES,
    max_participants=64
)

# Emit event
from core.events import create_tournament_event, EventType
event = create_tournament_event(
    EventType.TOURNAMENT_CREATED,
    tournament.id,
    tournament.to_dict(),
    "system"
)
await event_bus.emit(event)
```

The new architecture provides:
- Unified data access through repository pattern
- Event-driven real-time updates
- Multi-level caching for performance
- Comprehensive data modeling
- Database connection management
"""

# Core components
from . import models
from . import data_access
from . import events

# Public API
__all__ = [
    'models',
    'data_access', 
    'events'
]

__version__ = "1.0.0"
