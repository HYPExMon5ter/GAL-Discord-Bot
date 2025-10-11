"""
Database connection management and pooling.

Provides efficient connection management with pooling, health checks,
and automatic reconnection for database systems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import aiosqlite
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


@dataclass
class ConnectionConfig:
    """Database connection configuration."""
    
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    ssl_mode: Optional[str] = None
    application_name: str = "gal_bot"
    connect_timeout: int = 10
    command_timeout: int = 30
    
    def validate(self) -> None:
        """Validate connection configuration."""
        if not self.url:
            raise ValueError("Database URL is required")
        if self.pool_size < 1:
            raise ValueError("Pool size must be at least 1")
        if self.max_overflow < 0:
            raise ValueError("Max overflow cannot be negative")


@dataclass
class ConnectionStats:
    """Database connection statistics."""
    
    pool_size: int = 0
    pool_available: int = 0
    pool_in_use: int = 0
    total_connections: int = 0
    active_connections: int = 0
    connection_errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    uptime: timedelta = field(default_factory=timedelta)
    query_count: int = 0
    average_query_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_size": self.pool_size,
            "pool_available": self.pool_available,
            "pool_in_use": self.pool_in_use,
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "connection_errors": self.connection_errors,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "uptime_seconds": self.uptime.total_seconds(),
            "query_count": self.query_count,
            "average_query_time_ms": self.average_query_time * 1000
        }


class DatabaseConnection:
    """Abstract base class for database connections."""
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize database connection.
        
        Args:
            config: Connection configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._pool = None
        self._stats = ConnectionStats()
        self._connected_at = None
        self._health_check_interval = timedelta(minutes=5)
        self._last_health_check = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass
    
    @abstractmethod
    async def execute(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a database query.
        
        Args:
            query: SQL query
            args: Query parameters
            
        Returns:
            Query result
        """
        pass
    
    @abstractmethod
    async def fetch(self, query: str, *args, **kwargs) -> list:
        """
        Execute a query and fetch all results.
        
        Args:
            query: SQL query
            args: Query parameters
            
        Returns:
            List of result rows
        """
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[dict]:
        """
        Execute a query and fetch first result.
        
        Args:
            query: SQL query
            args: Query parameters
            
        Returns:
            First result row or None
        """
        pass
    
    @abstractmethod
    async def fetch_val(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a query and fetch first column of first row.
        
        Args:
            query: SQL query
            args: Query parameters
            
        Returns:
            First column value
        """
        pass
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        
        Yields:
            Transaction context
        """
        raise NotImplementedError("Subclasses must implement transaction")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the database connection.
        
        Returns:
            Health check results
        """
        try:
            # Simple health check query
            await self.fetch_val("SELECT 1")
            
            self._last_health_check = datetime.utcnow()
            
            return {
                "status": "healthy",
                "timestamp": self._last_health_check.isoformat(),
                "stats": self._stats.to_dict()
            }
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "stats": self._stats.to_dict()
            }
    
    def _update_stats(self, query_time: float) -> None:
        """Update connection statistics."""
        self._stats.query_count += 1
        
        # Update average query time
        if self._stats.query_count == 1:
            self._stats.average_query_time = query_time
        else:
            self._stats.average_query_time = (
                (self._stats.average_query_time * (self._stats.query_count - 1) + query_time) /
                self._stats.query_count
            )
    
    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        if self._connected_at:
            self._stats.uptime = datetime.utcnow() - self._connected_at
        return self._stats


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection using asyncpg."""
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize PostgreSQL connection.
        
        Args:
            config: Connection configuration
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg is required for PostgreSQL connections")
        
        super().__init__(config)
        self._connection_class = asyncpg.Connection
    
    async def connect(self) -> None:
        """Establish PostgreSQL connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.config.url,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=self.config.command_timeout,
                server_settings={
                    "application_name": self.config.application_name
                }
            )
            
            self._connected_at = datetime.utcnow()
            self.logger.info("PostgreSQL connection pool established")
            
            # Test connection
            await self.health_check()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info("PostgreSQL connection pool closed")
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """Execute PostgreSQL query."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *args, **kwargs)
                
                query_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_stats(query_time)
                
                if self.config.echo:
                    self.logger.debug(f"Query executed in {query_time:.3f}s: {query}")
                
                return result
                
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query execution failed: {e}")
            raise
    
    async def fetch(self, query: str, *args, **kwargs) -> list:
        """Execute PostgreSQL query and fetch all results."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetch(query, *args, **kwargs)
                
                query_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_stats(query_time)
                
                return [dict(row) for row in result]
                
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[dict]:
        """Execute PostgreSQL query and fetch first result."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(query, *args, **kwargs)
                
                query_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_stats(query_time)
                
                return dict(result) if result else None
                
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch_one failed: {e}")
            raise
    
    async def fetch_val(self, query: str, *args, **kwargs) -> Any:
        """Execute PostgreSQL query and fetch first column value."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval(query, *args, **kwargs)
                
                query_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_stats(query_time)
                
                return result
                
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch_val failed: {e}")
            raise
    
    @asynccontextmanager
    async def transaction(self):
        """PostgreSQL transaction context manager."""
        if not self._pool:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection using aiosqlite."""
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize SQLite connection.
        
        Args:
            config: Connection configuration
        """
        if not SQLITE_AVAILABLE:
            raise ImportError("aiosqlite is required for SQLite connections")
        
        # Override URL for SQLite
        if config.url.startswith("sqlite://"):
            config.url = config.url[10:]  # Remove sqlite:// prefix
        
        super().__init__(config)
    
    async def connect(self) -> None:
        """Establish SQLite connection."""
        try:
            self._pool = await aiosqlite.connect(
                self.config.url,
                timeout=self.config.connect_timeout
            )
            
            # Enable WAL mode for better concurrency
            await self._pool.execute("PRAGMA journal_mode=WAL")
            await self._pool.execute("PRAGMA foreign_keys=ON")
            
            self._connected_at = datetime.utcnow()
            self.logger.info(f"SQLite connection established: {self.config.url}")
            
            # Test connection
            await self.health_check()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close SQLite connection."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info("SQLite connection closed")
    
    async def execute(self, query: str, *args, **kwargs) -> int:
        """Execute SQLite query."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            cursor = await self._pool.execute(query, args)
            await self._pool.commit()
            
            query_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(query_time)
            
            if self.config.echo:
                self.logger.debug(f"Query executed in {query_time:.3f}s: {query}")
            
            return cursor.rowcount
            
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query execution failed: {e}")
            await self._pool.rollback()
            raise
    
    async def fetch(self, query: str, *args, **kwargs) -> list:
        """Execute SQLite query and fetch all results."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            self._pool.row_factory = aiosqlite.Row
            cursor = await self._pool.execute(query, args)
            rows = await cursor.fetchall()
            
            query_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(query_time)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch failed: {e}")
            raise
    
    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[dict]:
        """Execute SQLite query and fetch first result."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            self._pool.row_factory = aiosqlite.Row
            cursor = await self._pool.execute(query, args)
            row = await cursor.fetchone()
            
            query_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(query_time)
            
            return dict(row) if row else None
            
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch_one failed: {e}")
            raise
    
    async def fetch_val(self, query: str, *args, **kwargs) -> Any:
        """Execute SQLite query and fetch first column value."""
        if not self._pool:
            await self.connect()
        
        start_time = datetime.utcnow()
        try:
            cursor = await self._pool.execute(query, args)
            row = await cursor.fetchone()
            
            query_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(query_time)
            
            return row[0] if row else None
            
        except Exception as e:
            self._stats.connection_errors += 1
            self._stats.last_error = str(e)
            self._stats.last_error_time = datetime.utcnow()
            self.logger.error(f"Query fetch_val failed: {e}")
            raise
    
    @asynccontextmanager
    async def transaction(self):
        """SQLite transaction context manager."""
        if not self._pool:
            await self.connect()
        
        try:
            yield self._pool
            await self._pool.commit()
        except Exception:
            await self._pool.rollback()
            raise


class ConnectionManager:
    """
    Database connection manager.
    
    Manages multiple database connections with pooling, health checks,
    and automatic reconnection.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.logger = logging.getLogger("ConnectionManager")
        self._connections: Dict[str, DatabaseConnection] = {}
        self._configs: Dict[str, ConnectionConfig] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._start_health_checks()
    
    def register_connection(self, 
                           name: str, 
                           config: ConnectionConfig,
                           connection_type: str = "auto") -> None:
        """
        Register a database connection.
        
        Args:
            name: Connection name
            config: Connection configuration
            connection_type: Type of connection (postgres, sqlite, auto)
        """
        config.validate()
        self._configs[name] = config
        
        # Auto-detect connection type if not specified
        if connection_type == "auto":
            if config.url.startswith(("postgresql://", "postgres://")):
                connection_type = "postgres"
            elif config.url.startswith(("sqlite://", "./", "/")):
                connection_type = "sqlite"
            else:
                raise ValueError(f"Cannot auto-detect connection type for URL: {config.url}")
        
        # Create appropriate connection
        if connection_type == "postgres":
            connection = PostgreSQLConnection(config)
        elif connection_type == "sqlite":
            connection = SQLiteConnection(config)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")
        
        self._connections[name] = connection
        self.logger.info(f"Registered database connection: {name} ({connection_type})")
    
    async def connect(self, name: str) -> None:
        """
        Connect to a specific database.
        
        Args:
            name: Connection name
        """
        if name not in self._connections:
            raise ValueError(f"Connection '{name}' not registered")
        
        await self._connections[name].connect()
    
    async def connect_all(self) -> None:
        """Connect to all registered databases."""
        for name in self._connections:
            try:
                await self.connect(name)
            except Exception as e:
                self.logger.error(f"Failed to connect to '{name}': {e}")
    
    async def disconnect(self, name: str) -> None:
        """
        Disconnect from a specific database.
        
        Args:
            name: Connection name
        """
        if name in self._connections:
            await self._connections[name].disconnect()
    
    async def disconnect_all(self) -> None:
        """Disconnect from all databases."""
        for name in self._connections:
            await self.disconnect(name)
    
    def get_connection(self, name: str) -> DatabaseConnection:
        """
        Get a database connection.
        
        Args:
            name: Connection name
            
        Returns:
            Database connection instance
        """
        if name not in self._connections:
            raise ValueError(f"Connection '{name}' not registered")
        
        return self._connections[name]
    
    async def health_check(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform health check on connections.
        
        Args:
            name: Specific connection name (optional)
            
        Returns:
            Health check results
        """
        if name:
            if name not in self._connections:
                raise ValueError(f"Connection '{name}' not registered")
            return await self._connections[name].health_check()
        
        # Check all connections
        results = {}
        for conn_name, connection in self._connections.items():
            try:
                results[conn_name] = await connection.health_check()
            except Exception as e:
                results[conn_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results
    
    async def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection statistics.
        
        Args:
            name: Specific connection name (optional)
            
        Returns:
            Connection statistics
        """
        if name:
            if name not in self._connections:
                raise ValueError(f"Connection '{name}' not registered")
            return self._connections[name].stats.to_dict()
        
        # Get stats for all connections
        return {
            name: connection.stats.to_dict()
            for name, connection in self._connections.items()
        }
    
    def _start_health_checks(self) -> None:
        """Start background health check task."""
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Check every 5 minutes
                    await self.health_check()
                except Exception as e:
                    self.logger.error(f"Health check error: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
    
    async def shutdown(self) -> None:
        """Shutdown connection manager."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        await self.disconnect_all()
        self.logger.info("Connection manager shutdown complete")
