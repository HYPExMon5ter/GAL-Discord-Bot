# core/__init__.py
"""
Core functionality for the GAL Discord Bot.
"""

# These imports are optional but can make imports cleaner elsewhere
from .commands import gal
from .events import setup_events
from .persistence import (
    get_event_mode_for_guild,
    set_event_mode_for_guild,
    get_persisted_msg,
    set_persisted_msg
)
from .views import (
    DMActionView,
    update_live_embeds
)

__all__ = [
    'gal',
    'setup_events',
    'get_event_mode_for_guild',
    'set_event_mode_for_guild',
    'get_persisted_msg',
    'set_persisted_msg',
    'DMActionView',
    'update_live_embeds'
]
