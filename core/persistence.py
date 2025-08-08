# core/persistence.py

import json
import logging
import os
from contextlib import contextmanager
from typing import Dict, Any, Optional, Tuple, Union

from config import DATABASE_URL

PERSIST_FILE = os.path.join("./persisted_views.json")

# Database connection management
if DATABASE_URL:
    import psycopg2
    from psycopg2 import pool

    # Ensure proper URL format
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Create connection pool for better performance
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,  # min and max connections
            DATABASE_URL,
            sslmode="require"
        )

        # Initialize database schema - check what columns exist first
        with connection_pool.getconn() as conn:
            with conn.cursor() as cursor:
                # Create table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS persisted_views (
                        key TEXT PRIMARY KEY,
                        data JSONB
                    );
                """)

                # Check if updated_at column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'persisted_views' 
                    AND column_name = 'updated_at';
                """)

                if not cursor.fetchone():
                    # Add updated_at column if it doesn't exist
                    try:
                        cursor.execute("""
                            ALTER TABLE persisted_views 
                            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                        """)
                        cursor.execute("""
                            ALTER TABLE persisted_views 
                            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                        """)
                        conn.commit()
                        logging.info("Added timestamp columns to persisted_views table")
                    except Exception as e:
                        logging.warning(f"Could not add timestamp columns (they may already exist): {e}")
                        conn.rollback()

                # Try to add index, but don't fail if column doesn't exist
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_persisted_views_updated_at 
                        ON persisted_views(updated_at);
                    """)
                    conn.commit()
                except Exception as e:
                    # Index creation failed, probably because column doesn't exist
                    # This is okay, we can work without it
                    logging.debug(f"Could not create index on updated_at: {e}")
                    conn.rollback()

        logging.info("Database connection pool initialized successfully")

    except Exception as e:
        logging.error(f"Failed to initialize database connection pool: {e}")
        connection_pool = None
else:
    connection_pool = None


@contextmanager
def get_db_connection():
    """Context manager for database connections with proper cleanup."""
    if not connection_pool:
        raise RuntimeError("Database connection pool not available")

    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            connection_pool.putconn(conn)


def load_persisted() -> Dict[str, Any]:
    """Load persisted data with proper error handling."""
    if connection_pool:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT data FROM persisted_views WHERE key = %s", ("default",))
                    row = cursor.fetchone()
                    return row[0] if row else {}
        except Exception as e:
            logging.error(f"Failed to load from database, falling back to file: {e}")

    # File fallback
    try:
        with open(PERSIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.info("No persisted data file found, starting fresh")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Corrupted persisted data file: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error loading persisted data: {e}")
        return {}


def save_persisted(data: Dict[str, Any]) -> None:
    """Save persisted data with proper error handling."""
    if connection_pool:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Try with updated_at column first
                    try:
                        cursor.execute(
                            """INSERT INTO persisted_views (key, data, updated_at) 
                               VALUES (%s, %s, CURRENT_TIMESTAMP) 
                               ON CONFLICT (key) 
                               DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP""",
                            ("default", json.dumps(data))
                        )
                    except psycopg2.errors.UndefinedColumn:
                        # Fallback to without updated_at column
                        cursor.execute(
                            """INSERT INTO persisted_views (key, data) 
                               VALUES (%s, %s) 
                               ON CONFLICT (key) 
                               DO UPDATE SET data = EXCLUDED.data""",
                            ("default", json.dumps(data))
                        )
                    conn.commit()
            return
        except Exception as e:
            logging.error(f"Failed to save to database, falling back to file: {e}")

    # File fallback
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PERSIST_FILE), exist_ok=True)

        # Write to temporary file first for atomic operation
        temp_file = PERSIST_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Atomic rename
        os.replace(temp_file, PERSIST_FILE)

    except Exception as e:
        logging.error(f"Failed to save persisted data to file: {e}")
        # Clean up temp file if it exists
        try:
            os.remove(temp_file)
        except:
            pass


# Load initial data
persisted = load_persisted()


def set_persisted_msg(guild_id: Union[str, int], key: str, channel_id: int, msg_id: int) -> None:
    """
    Store [channel_id, msg_id] for the given guild/key.

    Args:
        guild_id: Guild ID
        key: Message key (e.g., "registration", "checkin")
        channel_id: Channel ID where message is stored
        msg_id: Message ID
    """
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}

    persisted[gid][key] = [channel_id, msg_id]
    save_persisted(persisted)

    logging.debug(f"Set persisted message for guild {gid}, key {key}: {channel_id}/{msg_id}")


def get_persisted_msg(guild_id: Union[str, int], key: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Return (channel_id, msg_id) tuple, or (None, None) if missing.
    Supports legacy format where only msg_id was stored.

    Args:
        guild_id: Guild ID
        key: Message key

    Returns:
        Tuple of (channel_id, msg_id) or (None, None)
    """
    guild_data = persisted.get(str(guild_id), {})
    value = guild_data.get(key)

    if isinstance(value, list) and len(value) == 2:
        return value[0], value[1]
    elif isinstance(value, int):
        # Legacy support
        return None, value

    return None, None


def get_event_mode_for_guild(guild_id: Union[str, int]) -> str:
    """
    Get event mode for guild.

    Args:
        guild_id: Guild ID

    Returns:
        Event mode ("normal" or "doubleup")
    """
    gid = str(guild_id)
    return persisted.get(gid, {}).get("event_mode", "normal")


def set_event_mode_for_guild(guild_id: Union[str, int], mode: str) -> None:
    """
    Set event mode for guild.

    Args:
        guild_id: Guild ID
        mode: Event mode ("normal" or "doubleup")
    """
    if mode not in ["normal", "doubleup"]:
        raise ValueError(f"Invalid event mode: {mode}")

    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}

    persisted[gid]["event_mode"] = mode
    save_persisted(persisted)

    logging.info(f"Set event mode for guild {gid}: {mode}")


def get_schedule(guild_id: Union[str, int], key: str) -> Optional[str]:
    """
    Get scheduled time for a specific key.

    Args:
        guild_id: Guild ID
        key: Schedule key

    Returns:
        ISO datetime string or None
    """
    data = persisted.get(str(guild_id), {})
    return data.get(f"{key}_schedule")


def set_schedule(guild_id: Union[str, int], key: str, dtstr: Optional[str]) -> None:
    """
    Set scheduled time for a specific key.

    Args:
        guild_id: Guild ID
        key: Schedule key
        dtstr: ISO datetime string or None to clear
    """
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}

    schedule_key = f"{key}_schedule"
    if dtstr is None:
        persisted[gid].pop(schedule_key, None)
        logging.debug(f"Cleared schedule for guild {gid}, key {key}")
    else:
        persisted[gid][schedule_key] = dtstr
        logging.debug(f"Set schedule for guild {gid}, key {key}: {dtstr}")

    save_persisted(persisted)


def migrate_legacy_format() -> None:
    """Migrate legacy persisted message format to new format."""
    changed = False

    for gid, data in persisted.items():
        for key in ["registration", "checkin"]:
            val = data.get(key)
            if isinstance(val, int):
                data[key] = [None, val]
                changed = True
                logging.info(f"Migrated legacy format for guild {gid}, key {key}")

    if changed:
        save_persisted(persisted)
        logging.info("Completed migration of legacy persisted message format")


def cleanup_old_data(days: int = 30) -> None:
    """
    Clean up old persisted data (only works with database).

    Args:
        days: Number of days to keep data
    """
    if not connection_pool:
        logging.info("Database not available, skipping cleanup")
        return

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if updated_at column exists before trying to use it
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'persisted_views' 
                    AND column_name = 'updated_at';
                """)

                if cursor.fetchone():
                    cursor.execute(
                        """DELETE FROM persisted_views 
                           WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'""",
                        (days,)
                    )
                    deleted_rows = cursor.rowcount
                    conn.commit()

                    if deleted_rows > 0:
                        logging.info(f"Cleaned up {deleted_rows} old persisted data entries")
                else:
                    logging.debug("No updated_at column, skipping cleanup")

    except Exception as e:
        logging.error(f"Failed to cleanup old data: {e}")


def get_guild_statistics() -> Dict[str, int]:
    """Get statistics about persisted data."""
    stats = {
        "total_guilds": len(persisted),
        "guilds_with_registration": 0,
        "guilds_with_checkin": 0,
        "guilds_with_schedules": 0,
    }

    for guild_data in persisted.values():
        if "registration" in guild_data:
            stats["guilds_with_registration"] += 1
        if "checkin" in guild_data:
            stats["guilds_with_checkin"] += 1
        if any(key.endswith("_schedule") for key in guild_data.keys()):
            stats["guilds_with_schedules"] += 1

    return stats


# Run migration on import if needed
#try:
#    migrate_legacy_format()
#except Exception as e:
#    logging.error(f"Failed to run migration: {e}")

# Log initialization
logging.info(f"Persistence system initialized. Stats: {get_guild_statistics()}")