# integrations/__init__.py
"""
External service integrations for the GAL Discord Bot.
"""

# Optional imports for cleaner access
from .sheet_base import (
    SheetsError,
    AuthenticationError,
    get_sheet_for_guild,
    retry_until_successful,
)
from .sheets import (
    cache_lock,
    sheet_cache,
    refresh_sheet_cache,
    find_or_register_user,
    unregister_user,
    mark_checked_in_async,
    unmark_checked_in_async,
)

__all__ = [
    'refresh_sheet_cache',
    'find_or_register_user',
    'unregister_user',
    'mark_checked_in_async',
    'unmark_checked_in_async',
    'get_sheet_for_guild',
    'SheetsError',
    'AuthenticationError',
    'retry_until_successful',
    'sheet_cache',
    'cache_lock'
]
