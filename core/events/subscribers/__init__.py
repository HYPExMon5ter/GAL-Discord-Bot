"""
Event subscribers for the Guardian Angel League Discord Bot.

Provides subscribers that react to events and integrate
with external systems like Discord and the dashboard.
"""

from .discord_subscribers import DiscordEventSubscriber
from .dashboard_subscribers import DashboardEventSubscriber

__all__ = [
    'DiscordEventSubscriber',
    'DashboardEventSubscriber'
]
