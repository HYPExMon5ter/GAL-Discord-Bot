"""
Event system for the Guardian Angel League Discord Bot.

Provides event-driven architecture for real-time updates and
data synchronization across all components.
"""

from .event_bus import EventBus, Event, EventHandler, EventSubscriber
from .event_types import (
    EventType, EventPriority, EventCategory,
    TournamentEvent, UserEvent, GuildEvent, ConfigurationEvent
)
from .handlers.tournament_events import TournamentEventHandler
from .handlers.user_events import UserEventHandler
from .handlers.guild_events import GuildEventHandler
from .handlers.configuration_events import ConfigurationEventHandler
from .subscribers.discord_subscribers import DiscordEventSubscriber
from .subscribers.dashboard_subscribers import DashboardEventSubscriber

__all__ = [
    'EventBus', 'Event', 'EventHandler', 'EventSubscriber',
    'EventType', 'EventPriority', 'EventCategory',
    'TournamentEvent', 'UserEvent', 'GuildEvent', 'ConfigurationEvent',
    'TournamentEventHandler', 'UserEventHandler', 'GuildEventHandler', 
    'ConfigurationEventHandler',
    'DiscordEventSubscriber', 'DashboardEventSubscriber'
]
