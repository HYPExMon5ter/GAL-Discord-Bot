"""
Unified Storage Service

Provides a unified interface for data storage with PostgreSQL primary storage
and SQLite fallback. Handles all JSON file storage operations through a
consistent API with proper error handling and fallback mechanisms.
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, UTC
from typing import Dict, Any, Optional, Union, List, Tuple
from pathlib import Path

from config import DATABASE_URL


class StorageError(Exception):
    """Custom exception for storage operations."""
    pass


class UnifiedStorageService:
    """
    Unified storage service with PostgreSQL primary and SQLite fallback.
    
    Provides a consistent API for all data storage operations, automatically
    handling the transition between PostgreSQL and SQLite based on availability.
    """
    
    def __init__(self):
        self._postgres_pool = None
        self._sqlite_path = os.path.join(os.path.dirname(__file__), "..", "storage", "fallback.db")
        self._sqlite_lock = threading.Lock()
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize database connections based on availability."""
        # Initialize PostgreSQL connection pool if DATABASE_URL is a PostgreSQL URL
        if DATABASE_URL and self._is_postgresql_url(DATABASE_URL):
            try:
                import psycopg2
                from psycopg2 import pool
                
                # Ensure proper URL format
                db_url = DATABASE_URL
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                # Create connection pool
                self._postgres_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 10,  # min and max connections
                    db_url,
                    sslmode="require"
                )
                
                # Initialize PostgreSQL schema
                self._initialize_postgres_schema()
                logging.info("PostgreSQL connection pool initialized successfully")
                
            except Exception as e:
                logging.error(f"Failed to initialize PostgreSQL connection: {e}")
                self._postgres_pool = None
                logging.info("Falling back to SQLite storage")
        
        # Initialize SQLite fallback (always available)
        self._initialize_sqlite_schema()
        logging.info(f"SQLite fallback initialized at {self._sqlite_path}")
    
    def _is_postgresql_url(self, url: str) -> bool:
        """Check if the URL is a PostgreSQL connection string."""
        return url.startswith(("postgresql://", "postgres://"))
    
    def _initialize_postgres_schema(self):
        """Initialize PostgreSQL database schema."""
        if not self._postgres_pool:
            return
        
        try:
            with self._get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    # Create persisted_views table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS persisted_views (
                            key TEXT PRIMARY KEY,
                            data JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create waitlist_data table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS waitlist_data (
                            guild_id TEXT PRIMARY KEY,
                            data JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create indexes for better performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_persisted_views_updated_at 
                        ON persisted_views(updated_at);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_waitlist_data_updated_at 
                        ON waitlist_data(updated_at);
                    """)
                    
                    conn.commit()
                    logging.info("PostgreSQL schema initialized successfully")
                    
        except Exception as e:
            logging.error(f"Failed to initialize PostgreSQL schema: {e}")
            raise
    
    def _initialize_sqlite_schema(self):
        """Initialize SQLite fallback database schema."""
        try:
            # Ensure storage directory exists
            os.makedirs(os.path.dirname(self._sqlite_path), exist_ok=True)
            
            with sqlite3.connect(self._sqlite_path) as conn:
                cursor = conn.cursor()
                
                # Create persisted_views table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS persisted_views (
                        key TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create waitlist_data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS waitlist_data (
                        guild_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persisted_views_updated_at 
                    ON persisted_views(updated_at);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_waitlist_data_updated_at 
                    ON waitlist_data(updated_at);
                """)
                
                conn.commit()
                logging.info("SQLite fallback schema initialized successfully")
                
        except Exception as e:
            logging.error(f"Failed to initialize SQLite fallback schema: {e}")
            raise StorageError(f"SQLite initialization failed: {e}")
    
    @contextmanager
    def _get_postgres_connection(self):
        """Context manager for PostgreSQL connections."""
        if not self._postgres_pool:
            raise StorageError("PostgreSQL connection pool not available")
        
        conn = None
        try:
            conn = self._postgres_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._postgres_pool.putconn(conn)
    
    @contextmanager
    def _get_sqlite_connection(self):
        """Context manager for SQLite connections with thread safety."""
        with self._sqlite_lock:
            conn = None
            try:
                conn = sqlite3.connect(self._sqlite_path)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                yield conn
            except Exception as e:
                if conn:
                    conn.rollback()
                raise
            finally:
                if conn:
                    conn.close()
    
    def _is_postgres_available(self) -> bool:
        """Check if PostgreSQL is available."""
        return self._postgres_pool is not None
    
    def _execute_with_fallback(self, operation_name: str, postgres_operation, sqlite_operation):
        """
        Execute an operation with PostgreSQL primary and SQLite fallback.
        
        Args:
            operation_name: Name of the operation for logging
            postgres_operation: Function that takes a connection and performs the operation
            sqlite_operation: Function that takes a connection and performs the operation
        """
        # Try PostgreSQL first
        if self._is_postgres_available():
            try:
                with self._get_postgres_connection() as conn:
                    result = postgres_operation(conn)
                    conn.commit()
                    logging.debug(f"{operation_name} executed via PostgreSQL")
                    return result
            except Exception as e:
                logging.warning(f"PostgreSQL {operation_name} failed, falling back to SQLite: {e}")
        
        # Fallback to SQLite
        try:
            with self._get_sqlite_connection() as conn:
                result = sqlite_operation(conn)
                conn.commit()
                logging.debug(f"{operation_name} executed via SQLite fallback")
                return result
        except Exception as e:
            logging.error(f"SQLite fallback {operation_name} failed: {e}")
            raise StorageError(f"Both PostgreSQL and SQLite {operation_name} failed: {e}")
    
    # Persisted Views Operations
    
    def get_persisted_views(self) -> Dict[str, Any]:
        """Load persisted views data."""
        def postgres_get(conn):
            with conn.cursor() as cursor:
                cursor.execute("SELECT key, data FROM persisted_views")
                rows = cursor.fetchall()
                if rows:
                    result = {}
                    for row in rows:
                        key, data = row
                        if key == "default":
                            return data
                    return {}
                return {}
        
        def sqlite_get(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT key, data FROM persisted_views WHERE key = ?", ("default",))
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return {}
        
        return self._execute_with_fallback("get_persisted_views", postgres_get, sqlite_get)
    
    def save_persisted_views(self, data: Dict[str, Any]) -> None:
        """Save persisted views data."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        def postgres_save(conn):
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO persisted_views (key, data, updated_at) 
                    VALUES (%s, %s, CURRENT_TIMESTAMP) 
                    ON CONFLICT (key) 
                    DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
                """, ("default", json.dumps(data)))
        
        def sqlite_save(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO persisted_views (key, data, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, ("default", json.dumps(data)))
        
        self._execute_with_fallback("save_persisted_views", postgres_save, sqlite_save)
    
    # Waitlist Operations
    
    def get_waitlist_data(self) -> Dict[str, Any]:
        """Load waitlist data."""
        def postgres_get(conn):
            with conn.cursor() as cursor:
                cursor.execute("SELECT guild_id, data FROM waitlist_data")
                rows = cursor.fetchall()
                result = {}
                for row in rows:
                    guild_id, data = row
                    result[guild_id] = data if isinstance(data, dict) else json.loads(data)
                return result
        
        def sqlite_get(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT guild_id, data FROM waitlist_data")
            rows = cursor.fetchall()
            result = {}
            for row in rows:
                result[row["guild_id"]] = json.loads(row["data"])
            return result
        
        return self._execute_with_fallback("get_waitlist_data", postgres_get, sqlite_get)
    
    def save_waitlist_data(self, data: Dict[str, Any]) -> None:
        """Save waitlist data."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        def postgres_save(conn):
            with conn.cursor() as cursor:
                for guild_id, guild_data in data.items():
                    cursor.execute("""
                        INSERT INTO waitlist_data (guild_id, data, updated_at) 
                        VALUES (%s, %s, CURRENT_TIMESTAMP) 
                        ON CONFLICT (guild_id) 
                        DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
                    """, (guild_id, json.dumps(guild_data)))
        
        def sqlite_save(conn):
            cursor = conn.cursor()
            for guild_id, guild_data in data.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO waitlist_data (guild_id, data, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (guild_id, json.dumps(guild_data)))
        
        self._execute_with_fallback("save_waitlist_data", postgres_save, sqlite_save)
    
    # Generic Operations
    
    def get_data(self, table: str, key: str) -> Optional[Any]:
        """Get data from a specific table by key."""
        def postgres_get(conn):
            with conn.cursor() as cursor:
                if table == "persisted_views":
                    cursor.execute("SELECT data FROM persisted_views WHERE key = %s", (key,))
                elif table == "waitlist_data":
                    cursor.execute("SELECT data FROM waitlist_data WHERE guild_id = %s", (key,))
                else:
                    raise ValueError(f"Unknown table: {table}")
                
                row = cursor.fetchone()
                if row:
                    data = row[0]
                    return data if isinstance(data, dict) else json.loads(data)
                return None
        
        def sqlite_get(conn):
            cursor = conn.cursor()
            if table == "persisted_views":
                cursor.execute("SELECT data FROM persisted_views WHERE key = ?", (key,))
            elif table == "waitlist_data":
                cursor.execute("SELECT data FROM waitlist_data WHERE guild_id = ?", (key,))
            else:
                raise ValueError(f"Unknown table: {table}")
            
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return None
        
        return self._execute_with_fallback(f"get_data from {table}", postgres_get, sqlite_get)
    
    def set_data(self, table: str, key: str, data: Any) -> None:
        """Set data in a specific table by key."""
        if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
            raise ValueError("Data must be JSON-serializable")
        
        def postgres_set(conn):
            with conn.cursor() as cursor:
                if table == "persisted_views":
                    cursor.execute("""
                        INSERT INTO persisted_views (key, data, updated_at) 
                        VALUES (%s, %s, CURRENT_TIMESTAMP) 
                        ON CONFLICT (key) 
                        DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
                    """, (key, json.dumps(data)))
                elif table == "waitlist_data":
                    cursor.execute("""
                        INSERT INTO waitlist_data (guild_id, data, updated_at) 
                        VALUES (%s, %s, CURRENT_TIMESTAMP) 
                        ON CONFLICT (guild_id) 
                        DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
                    """, (key, json.dumps(data)))
                else:
                    raise ValueError(f"Unknown table: {table}")
        
        def sqlite_set(conn):
            cursor = conn.cursor()
            if table == "persisted_views":
                cursor.execute("""
                    INSERT OR REPLACE INTO persisted_views (key, data, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(data)))
            elif table == "waitlist_data":
                cursor.execute("""
                    INSERT OR REPLACE INTO waitlist_data (guild_id, data, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(data)))
            else:
                raise ValueError(f"Unknown table: {table}")
        
        self._execute_with_fallback(f"set_data in {table}", postgres_set, sqlite_set)
    
    # Utility Methods
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get the current storage status and statistics."""
        status = {
            "postgres_available": self._is_postgres_available(),
            "sqlite_fallback": True,
            "sqlite_path": self._sqlite_path,
            "persisted_views_count": 0,
            "waitlist_data_count": 0,
        }
        
        try:
            # Get persisted views count
            persisted_data = self.get_persisted_views()
            status["persisted_views_count"] = len(persisted_data) if persisted_data else 0
            
            # Get waitlist data count
            waitlist_data = self.get_waitlist_data()
            status["waitlist_data_count"] = len(waitlist_data) if waitlist_data else 0
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data from both storage backends."""
        def postgres_cleanup(conn):
            with conn.cursor() as cursor:
                # Clean persisted_views
                cursor.execute("""
                    DELETE FROM persisted_views 
                    WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days,))
                persisted_deleted = cursor.rowcount
                
                # Clean waitlist_data
                cursor.execute("""
                    DELETE FROM waitlist_data 
                    WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days,))
                waitlist_deleted = cursor.rowcount
                
                return {
                    "persisted_views_deleted": persisted_deleted,
                    "waitlist_data_deleted": waitlist_deleted
                }
        
        def sqlite_cleanup(conn):
            cursor = conn.cursor()
            # Clean persisted_views
            cursor.execute("""
                DELETE FROM persisted_views 
                WHERE updated_at < datetime('now', '-{} days')
            """.format(days))
            persisted_deleted = cursor.rowcount
            
            # Clean waitlist_data
            cursor.execute("""
                DELETE FROM waitlist_data 
                WHERE updated_at < datetime('now', '-{} days')
            """.format(days))
            waitlist_deleted = cursor.rowcount
            
            return {
                "persisted_views_deleted": persisted_deleted,
                "waitlist_data_deleted": waitlist_deleted
            }
        
        return self._execute_with_fallback("cleanup_old_data", postgres_cleanup, sqlite_cleanup)
    
    def backup_data(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of all data to a JSON file."""
        if backup_path is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                os.path.dirname(self._sqlite_path), 
                f"backup_{timestamp}.json"
            )
        
        try:
            # Get all data
            persisted_data = self.get_persisted_views()
            waitlist_data = self.get_waitlist_data()
            
            backup = {
                "timestamp": datetime.now(UTC).isoformat(),
                "storage_status": self.get_storage_status(),
                "persisted_views": persisted_data,
                "waitlist_data": waitlist_data,
            }
            
            # Write backup file
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Data backed up to {backup_path}")
            return backup_path
            
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            raise StorageError(f"Backup failed: {e}")
    
    def close(self):
        """Close all database connections."""
        if self._postgres_pool:
            try:
                self._postgres_pool.closeall()
                logging.info("PostgreSQL connection pool closed")
            except Exception as e:
                logging.warning(f"Error closing PostgreSQL pool: {e}")
            finally:
                self._postgres_pool = None


# Global storage service instance
_storage_service = None


def get_storage_service() -> UnifiedStorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = UnifiedStorageService()
        logging.info("Unified storage service initialized")
    return _storage_service


def close_storage_service():
    """Close the global storage service."""
    global _storage_service
    if _storage_service:
        _storage_service.close()
        _storage_service = None
        logging.info("Unified storage service closed")
