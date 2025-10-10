# utils/__init__.py
"""
Utility functions for the GAL Discord Bot.
"""

from .utils import (
    resolve_member,
    send_reminder_dms,
    hyperlink_lolchess_profile, UtilsError, MemberNotFoundError
)

# Import renderer with lazy loading to avoid circular imports
def get_renderer():
    """Lazy import renderer to avoid circular dependencies"""
    from .renderer import GraphicsRenderer, render_graphic
    return GraphicsRenderer, render_graphic

__all__ = [
    'resolve_member',
    'send_reminder_dms',
    'hyperlink_lolchess_profile',
    'UtilsError',
    'MemberNotFoundError',
    'get_renderer',
    'GraphicsRenderer',
    'render_graphic'
]
