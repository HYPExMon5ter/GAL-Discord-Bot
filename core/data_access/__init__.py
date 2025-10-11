"""
Data Access Layer (DAL) for the Guardian Angel League Discord Bot.

Provides unified access to all data sources with consistent interfaces,
caching, and transaction management.
"""

from .base_repository import BaseRepository, RepositoryError, NotFoundError
from .tournament_repository import TournamentRepository
from .user_repository import UserRepository
from .guild_repository import GuildRepository
from .configuration_repository import ConfigurationRepository
from .cache_manager import CacheManager, CacheLevel
from .connection_manager import ConnectionManager, DatabaseConnection

__all__ = [
    'BaseRepository', 'RepositoryError', 'NotFoundError',
    'TournamentRepository', 'UserRepository', 'GuildRepository', 
    'ConfigurationRepository',
    'CacheManager', 'CacheLevel',
    'ConnectionManager', 'DatabaseConnection'
]
