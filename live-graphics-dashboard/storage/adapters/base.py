"""
Base storage adapter interface for hybrid PostgreSQL/SQLite system.
Defines the contract that both storage adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


Base = declarative_base()


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.SessionLocal = None
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the database."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the database connection is working."""
        pass

    @abstractmethod
    async def create_tables(self) -> bool:
        """Create all necessary tables."""
        pass

    @abstractmethod
    async def get_session(self):
        """Get a database session."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a raw SQL query."""
        pass

    @abstractmethod
    async def bulk_insert(self, table_name: str, records: List[Dict]) -> bool:
        """Bulk insert records into a table."""
        pass

    @abstractmethod
    async def sync_from_other(self, other_adapter: 'StorageAdapter') -> bool:
        """Sync data from another storage adapter."""
        pass

    def get_db_type(self) -> str:
        """Return the database type (postgresql or sqlite)."""
        return self.__class__.__name__.lower().replace('adapter', '')


class DatabaseManager:
    """Manages connections to both PostgreSQL and SQLite databases."""

    def __init__(self, postgresql_url: Optional[str] = None, sqlite_path: str = "data/graphics.db"):
        self.postgresql_url = postgresql_url
        self.sqlite_path = sqlite_path
        self.primary_adapter = None
        self.fallback_adapter = None
        self.current_adapter = None

    async def initialize(self):
        """Initialize database adapters and determine which one to use."""
        from .postgresql import PostgreSQLAdapter
        from .sqlite import SQLiteAdapter

        # Always create SQLite adapter as fallback
        self.fallback_adapter = SQLiteAdapter(f"sqlite:///{self.sqlite_path}")
        await self.fallback_adapter.connect()

        # Try to create PostgreSQL adapter if URL provided
        if self.postgresql_url:
            try:
                self.primary_adapter = PostgreSQLAdapter(self.postgresql_url)
                if await self.primary_adapter.connect():
                    self.current_adapter = self.primary_adapter
                    print("✅ Connected to PostgreSQL (primary)")
                else:
                    self.current_adapter = self.fallback_adapter
                    print("⚠️  PostgreSQL unavailable, using SQLite fallback")
            except Exception as e:
                print(f"❌ PostgreSQL connection failed: {e}")
                self.current_adapter = self.fallback_adapter
                print("⚠️  Using SQLite fallback")
        else:
            self.current_adapter = self.fallback_adapter
            print("ℹ️  No PostgreSQL URL provided, using SQLite")

        # Create tables in current adapter
        await self.current_adapter.create_tables()

    async def get_session(self):
        """Get a session from the current adapter."""
        return await self.current_adapter.get_session()

    async def switch_to_fallback(self):
        """Switch to fallback storage if primary fails."""
        if self.current_adapter != self.fallback_adapter:
            print("🔄 Switching to SQLite fallback")
            self.current_adapter = self.fallback_adapter
            return True
        return False

    async def try_switch_to_primary(self):
        """Try to switch back to primary storage if it becomes available."""
        if self.primary_adapter and self.current_adapter == self.fallback_adapter:
            try:
                if await self.primary_adapter.test_connection():
                    print("🔄 Switching back to PostgreSQL")
                    self.current_adapter = self.primary_adapter
                    # TODO: Sync any pending changes from SQLite to PostgreSQL
                    return True
            except Exception as e:
                print(f"❌ PostgreSQL still unavailable: {e}")
        return False

    def is_using_fallback(self) -> bool:
        """Check if currently using fallback storage."""
        return self.current_adapter == self.fallback_adapter

    def get_current_adapter_type(self) -> str:
        """Get the type of current adapter."""
        return self.current_adapter.get_db_type() if self.current_adapter else "none"