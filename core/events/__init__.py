"""
Event system for the Guardian Angel League Discord Bot.

Provides event-driven architecture for real-time updates and
data synchronization across all components.
"""

import logging

from .event_bus import EventBus, Event, EventHandler, EventSubscriber
from .event_types import (
    EventType, EventPriority, EventCategory,
    TournamentEvent, UserEvent, GuildEvent, ConfigurationEvent
)
from .handlers.configuration_events import ConfigurationEventHandler
from .handlers.guild_events import GuildEventHandler
from .handlers.tournament_events import TournamentEventHandler
from .handlers.user_events import UserEventHandler
from .subscribers.dashboard_subscribers import DashboardEventSubscriber
from .subscribers.discord_subscribers import DiscordEventSubscriber


def setup_events(bot):
    """
    Set up event handlers for the bot.
    
    Args:
        bot: The Discord bot instance
    """
    # Initialize event bus
    event_bus = EventBus()

    # Register event handlers
    tournament_handler = TournamentEventHandler()
    user_handler = UserEventHandler()
    guild_handler = GuildEventHandler()
    config_handler = ConfigurationEventHandler()

    # Register subscribers
    discord_subscriber = DiscordEventSubscriber()
    dashboard_subscriber = DashboardEventSubscriber()

    # Add handlers to event bus
    event_bus.subscribe(tournament_handler)
    event_bus.subscribe(user_handler)
    event_bus.subscribe(guild_handler)
    event_bus.subscribe(config_handler)

    # Add subscribers to event bus
    event_bus.subscribe(discord_subscriber)
    event_bus.subscribe(dashboard_subscriber)

    # Store event bus in bot for later access
    bot.event_bus = event_bus

    logging.info("Event system initialized successfully")

    # Register discord.py event listeners
    from ..discord_events import register_discord_events
    register_discord_events(bot)


__all__ = [
    'EventBus', 'Event', 'EventHandler', 'EventSubscriber',
    'EventType', 'EventPriority', 'EventCategory',
    'TournamentEvent', 'UserEvent', 'GuildEvent', 'ConfigurationEvent',
    'TournamentEventHandler', 'UserEventHandler', 'GuildEventHandler', 
    'ConfigurationEventHandler',
    'DiscordEventSubscriber', 'DashboardEventSubscriber',
    'setup_events'
]
