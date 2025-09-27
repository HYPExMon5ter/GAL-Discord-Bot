"""
PostgreSQL storage adapter implementation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .base import StorageAdapter, Base


class PostgreSQLAdapter(StorageAdapter):
    """PostgreSQL storage adapter."""

    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        self.max_retries = 3
        self.retry_delay = 1.0

    async def connect(self) -> bool:
        """Establish connection to PostgreSQL."""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                self.connection_string,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=False  # Set to True for SQL debugging
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Test the connection
            if await self.test_connection():
                self.is_connected = True
                logging.info("PostgreSQL connection established successfully")
                return True
            else:
                logging.error("PostgreSQL connection test failed")
                return False

        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection to PostgreSQL."""
        try:
            if self.engine:
                self.engine.dispose()
                self.is_connected = False
                logging.info("PostgreSQL connection closed")
        except Exception as e:
            logging.error(f"Error closing PostgreSQL connection: {e}")

    async def test_connection(self) -> bool:
        """Test if PostgreSQL connection is working."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logging.error(f"PostgreSQL connection test failed: {e}")
            return False

    async def create_tables(self) -> bool:
        """Create all necessary tables in PostgreSQL."""
        try:
            # Import models to register them with Base
            from ...models import events, graphics, history, sessions

            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logging.info("PostgreSQL tables created successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to create PostgreSQL tables: {e}")
            return False

    async def get_session(self):
        """Get a PostgreSQL database session."""
        if not self.is_connected:
            raise RuntimeError("PostgreSQL adapter not connected")
        return self.SessionLocal()

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a raw SQL query with retry logic."""
        for attempt in range(self.max_retries):
            try:
                with self.engine.connect() as connection:
                    if params:
                        result = connection.execute(text(query), params)
                    else:
                        result = connection.execute(text(query))
                    return result
            except SQLAlchemyError as e:
                if attempt == self.max_retries - 1:
                    logging.error(f"PostgreSQL query failed after {self.max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                logging.warning(f"PostgreSQL query attempt {attempt + 1} failed, retrying: {e}")

    async def bulk_insert(self, table_name: str, records: List[Dict]) -> bool:
        """Bulk insert records into PostgreSQL table."""
        try:
            session = await self.get_session()
            try:
                # Get the model class for the table
                model_class = self._get_model_class(table_name)
                if not model_class:
                    logging.error(f"Unknown table: {table_name}")
                    return False

                # Create model instances
                instances = [model_class(**record) for record in records]

                # Bulk insert
                session.add_all(instances)
                session.commit()
                logging.info(f"Bulk inserted {len(records)} records into {table_name}")
                return True
            finally:
                session.close()
        except Exception as e:
            logging.error(f"Bulk insert failed for table {table_name}: {e}")
            return False

    async def sync_from_other(self, other_adapter: 'StorageAdapter') -> bool:
        """Sync data from another storage adapter (SQLite to PostgreSQL)."""
        try:
            # Tables to sync
            tables_to_sync = [
                'events', 'graphics_templates', 'graphics_state_history',
                'graphics_instances', 'verified_igns', 'sync_queue'
            ]

            for table_name in tables_to_sync:
                try:
                    # Get data from other adapter
                    query = f"SELECT * FROM {table_name}"
                    result = await other_adapter.execute_query(query)

                    if result:
                        rows = result.fetchall()
                        if rows:
                            # Convert rows to dictionaries
                            records = [dict(row._mapping) for row in rows]

                            # Insert into this adapter
                            await self.bulk_insert(table_name, records)
                            logging.info(f"Synced {len(records)} records from {table_name}")

                except Exception as e:
                    logging.error(f"Failed to sync table {table_name}: {e}")
                    continue

            logging.info("Database synchronization completed")
            return True

        except Exception as e:
            logging.error(f"Database sync failed: {e}")
            return False

    def _get_model_class(self, table_name: str):
        """Get SQLAlchemy model class for table name."""
        from ...models.events import Event
        from ...models.graphics import GraphicsTemplate, GraphicsInstance
        from ...models.history import GraphicsStateHistory
        from ...models.sessions import EditingSession

        model_map = {
            'events': Event,
            'graphics_templates': GraphicsTemplate,
            'graphics_instances': GraphicsInstance,
            'graphics_state_history': GraphicsStateHistory,
            'editing_sessions': EditingSession,
        }

        return model_map.get(table_name)