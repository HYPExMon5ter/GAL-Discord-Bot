"""
SQLite storage adapter implementation for local fallback.
"""

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .base import StorageAdapter, Base


class SQLiteAdapter(StorageAdapter):
    """SQLite storage adapter for local fallback."""

    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        # Extract database path from connection string
        self.db_path = connection_string.replace("sqlite:///", "")
        self.max_retries = 3
        self.retry_delay = 0.5

    async def connect(self) -> bool:
        """Establish connection to SQLite."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # Create engine
            self.engine = create_engine(
                self.connection_string,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}  # For SQLite threading
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
                logging.info(f"SQLite connection established: {self.db_path}")
                return True
            else:
                logging.error("SQLite connection test failed")
                return False

        except Exception as e:
            logging.error(f"Failed to connect to SQLite: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection to SQLite."""
        try:
            if self.engine:
                self.engine.dispose()
                self.is_connected = False
                logging.info("SQLite connection closed")
        except Exception as e:
            logging.error(f"Error closing SQLite connection: {e}")

    async def test_connection(self) -> bool:
        """Test if SQLite connection is working."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logging.error(f"SQLite connection test failed: {e}")
            return False

    async def create_tables(self) -> bool:
        """Create all necessary tables in SQLite."""
        try:
            # Import models to register them with Base
            from models import events, graphics, history, sessions

            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logging.info("SQLite tables created successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to create SQLite tables: {e}")
            return False

    async def get_session(self):
        """Get a SQLite database session."""
        if not self.is_connected:
            raise RuntimeError("SQLite adapter not connected")
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
                    logging.error(f"SQLite query failed after {self.max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                logging.warning(f"SQLite query attempt {attempt + 1} failed, retrying: {e}")

    async def bulk_insert(self, table_name: str, records: List[Dict]) -> bool:
        """Bulk insert records into SQLite table."""
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
        """Sync data from another storage adapter (PostgreSQL to SQLite)."""
        try:
            # Tables to sync
            tables_to_sync = [
                'events', 'graphics_templates', 'graphics_state_history',
                'graphics_instances', 'verified_igns', 'sync_queue'
            ]

            for table_name in tables_to_sync:
                try:
                    # Clear existing data in SQLite table first
                    await self.execute_query(f"DELETE FROM {table_name}")

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
                            logging.info(f"Synced {len(records)} records to {table_name}")

                except Exception as e:
                    logging.error(f"Failed to sync table {table_name}: {e}")
                    continue

            logging.info("SQLite sync completed")
            return True

        except Exception as e:
            logging.error(f"SQLite sync failed: {e}")
            return False

    def _get_model_class(self, table_name: str):
        """Get SQLAlchemy model class for table name."""
        from models.events import Event
        from models.graphics import GraphicsTemplate, GraphicsInstance
        from models.history import GraphicsStateHistory
        from models.sessions import EditingSession

        model_map = {
            'events': Event,
            'graphics_templates': GraphicsTemplate,
            'graphics_instances': GraphicsInstance,
            'graphics_state_history': GraphicsStateHistory,
            'editing_sessions': EditingSession,
        }

        return model_map.get(table_name)

    async def backup_to_json(self, backup_path: str = "data/backups") -> bool:
        """Create JSON backup of all data."""
        try:
            import json
            os.makedirs(backup_path, exist_ok=True)

            tables_to_backup = [
                'events', 'graphics_templates', 'graphics_state_history',
                'graphics_instances', 'verified_igns'
            ]

            for table_name in tables_to_backup:
                try:
                    result = await self.execute_query(f"SELECT * FROM {table_name}")
                    rows = result.fetchall()

                    if rows:
                        # Convert to dictionaries and handle datetime serialization
                        records = []
                        for row in rows:
                            record = dict(row._mapping)
                            # Convert datetime objects to strings
                            for key, value in record.items():
                                if hasattr(value, 'isoformat'):
                                    record[key] = value.isoformat()
                            records.append(record)

                        # Write to JSON file
                        with open(f"{backup_path}/{table_name}.json", "w") as f:
                            json.dump(records, f, indent=2)

                        logging.info(f"Backed up {len(records)} records from {table_name}")

                except Exception as e:
                    logging.error(f"Failed to backup table {table_name}: {e}")
                    continue

            logging.info(f"JSON backup completed in {backup_path}")
            return True

        except Exception as e:
            logging.error(f"JSON backup failed: {e}")
            return False

    async def restore_from_json(self, backup_path: str = "data/backups") -> bool:
        """Restore data from JSON backup."""
        try:
            import json

            tables_to_restore = [
                'events', 'graphics_templates', 'graphics_state_history',
                'graphics_instances', 'verified_igns'
            ]

            for table_name in tables_to_restore:
                backup_file = f"{backup_path}/{table_name}.json"
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, "r") as f:
                            records = json.load(f)

                        if records:
                            await self.bulk_insert(table_name, records)
                            logging.info(f"Restored {len(records)} records to {table_name}")

                    except Exception as e:
                        logging.error(f"Failed to restore table {table_name}: {e}")
                        continue

            logging.info(f"JSON restoration completed from {backup_path}")
            return True

        except Exception as e:
            logging.error(f"JSON restoration failed: {e}")
            return False