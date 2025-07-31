# helpers/waitlist_helpers.py

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict

import discord

from config import embed_from_cfg, get_sheet_settings, LOG_CHANNEL_NAME, DATABASE_URL
from core.persistence import get_event_mode_for_guild
from helpers.error_handler import ErrorHandler
from helpers.role_helpers import RoleManager
from integrations.sheets import find_or_register_user


class WaitlistError(Exception):
    """Custom exception for waitlist-related errors."""
    pass


class WaitlistManager:
    """Manages waitlist functionality with improved database/file persistence."""

    WAITLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "waitlist_data.json")

    # Database connection management
    _connection_pool = None

    @classmethod
    def _initialize_database(cls):
        """Initialize database connection pool if available."""
        if not DATABASE_URL or cls._connection_pool is not None:
            return

        try:
            import psycopg2
            from psycopg2 import pool

            # Ensure proper URL format
            db_url = DATABASE_URL
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)

            # Create connection pool
            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 5,  # min and max connections
                db_url,
                sslmode="require"
            )

            # Initialize schema
            with cls._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS waitlist_data (
                            guild_id TEXT PRIMARY KEY,
                            data JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Add index for better performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_waitlist_updated_at 
                        ON waitlist_data(updated_at);
                    """)

                    conn.commit()

            logging.info("Waitlist database connection pool initialized")

        except Exception as e:
            logging.warning(f"Failed to initialize waitlist database: {e}")
            cls._connection_pool = None

    @classmethod
    @contextmanager
    def _get_db_connection(cls):
        """Context manager for database connections."""
        if not cls._connection_pool:
            raise WaitlistError("Database connection pool not available")

        conn = None
        try:
            conn = cls._connection_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cls._connection_pool.putconn(conn)

    @staticmethod
    def _load_waitlist_data() -> Dict:
        """Load waitlist data from database or file with proper error handling."""
        # Initialize database connection if needed
        WaitlistManager._initialize_database()

        # Try database first
        if WaitlistManager._connection_pool:
            try:
                with WaitlistManager._get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT guild_id, data FROM waitlist_data")
                        rows = cursor.fetchall()

                        if rows:
                            result = {}
                            for row in rows:
                                guild_id, data = row
                                result[guild_id] = data if isinstance(data, dict) else json.loads(data)
                            return result

                        return {}

            except Exception as e:
                logging.warning(f"Database load failed, falling back to file: {e}")

        # File fallback
        try:
            if os.path.exists(WaitlistManager.WAITLIST_FILE):
                with open(WaitlistManager.WAITLIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logging.debug("Loaded waitlist data from file")
                    return data
            return {}

        except json.JSONDecodeError as e:
            logging.error(f"Corrupted waitlist file: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error loading waitlist file: {e}")
            return {}

    @staticmethod
    def _save_waitlist_data(data: Dict) -> None:
        """Save waitlist data to database or file with proper error handling."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        # Try database first
        if WaitlistManager._connection_pool:
            try:
                with WaitlistManager._get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        for guild_id, guild_data in data.items():
                            cursor.execute(
                                """INSERT INTO waitlist_data (guild_id, data, updated_at) 
                                   VALUES (%s, %s, CURRENT_TIMESTAMP) 
                                   ON CONFLICT (guild_id) 
                                   DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP""",
                                (guild_id, json.dumps(guild_data))
                            )
                        conn.commit()
                        logging.debug("Saved waitlist data to database")
                        return

            except Exception as e:
                logging.warning(f"Database save failed, falling back to file: {e}")

        # File fallback
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(WaitlistManager.WAITLIST_FILE), exist_ok=True)

            # Write to temporary file first for atomic operation
            temp_file = WaitlistManager.WAITLIST_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            os.replace(temp_file, WaitlistManager.WAITLIST_FILE)
            logging.debug("Saved waitlist data to file")

        except Exception as e:
            logging.error(f"Failed to save waitlist data: {e}")
            # Clean up temp file if it exists
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            raise WaitlistError(f"Failed to save waitlist data: {e}")

    @staticmethod
    async def add_to_waitlist(
            guild: discord.Guild,
            member: discord.Member,
            ign: str,
            pronouns: str,
            team_name: Optional[str] = None,
            alt_igns: Optional[str] = None
    ) -> int:
        """
        Add a user to the waitlist with validation.

        Args:
            guild: Discord guild
            member: Discord member
            ign: In-game name
            pronouns: User pronouns
            team_name: Team name (for double-up mode)
            alt_igns: Alternative IGNs

        Returns:
            Position in waitlist (1-based)

        Raises:
            WaitlistError: If operation fails
        """
        if not all([guild, member, ign]):
            raise ValueError("Guild, member, and IGN are required")

        try:
            guild_id = str(guild.id)
            discord_tag = str(member)

            # Load current data
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                all_data[guild_id] = {"waitlist": []}

            waitlist = all_data[guild_id]["waitlist"]

            # Check if already in waitlist and update
            for i, entry in enumerate(waitlist):
                if entry["discord_tag"] == discord_tag:
                    waitlist[i] = {
                        "discord_tag": discord_tag,
                        "member_id": member.id,
                        "ign": ign.strip(),
                        "pronouns": pronouns.strip() if pronouns else "",
                        "team_name": team_name.strip() if team_name else None,
                        "alt_igns": alt_igns.strip() if alt_igns else None,
                        "added_at": datetime.utcnow().isoformat()
                    }
                    WaitlistManager._save_waitlist_data(all_data)
                    logging.info(f"Updated waitlist entry for {discord_tag} at position {i + 1}")
                    return i + 1

            # Add new entry
            new_entry = {
                "discord_tag": discord_tag,
                "member_id": member.id,
                "ign": ign.strip(),
                "pronouns": pronouns.strip() if pronouns else "",
                "team_name": team_name.strip() if team_name else None,
                "alt_igns": alt_igns.strip() if alt_igns else None,
                "added_at": datetime.utcnow().isoformat()
            }

            waitlist.append(new_entry)
            WaitlistManager._save_waitlist_data(all_data)

            position = len(waitlist)
            logging.info(f"Added {discord_tag} to waitlist at position {position}")
            return position

        except Exception as e:
            if isinstance(e, (ValueError, WaitlistError)):
                raise
            raise WaitlistError(f"Failed to add user to waitlist: {e}")

    @staticmethod
    async def remove_from_waitlist(guild_id: str, discord_tag: str) -> bool:
        """
        Remove a user from the waitlist.

        Args:
            guild_id: Guild ID
            discord_tag: Discord tag to remove

        Returns:
            True if user was removed, False if not found

        Raises:
            WaitlistError: If operation fails
        """
        if not guild_id or not discord_tag:
            raise ValueError("Guild ID and discord tag are required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return False

            waitlist = all_data[guild_id]["waitlist"]
            original_len = len(waitlist)

            # Remove matching entry
            all_data[guild_id]["waitlist"] = [
                entry for entry in waitlist
                if entry["discord_tag"] != discord_tag
            ]

            if len(all_data[guild_id]["waitlist"]) < original_len:
                WaitlistManager._save_waitlist_data(all_data)
                logging.info(f"Removed {discord_tag} from waitlist")
                return True

            return False

        except Exception as e:
            if isinstance(e, (ValueError, WaitlistError)):
                raise
            raise WaitlistError(f"Failed to remove user from waitlist: {e}")

    @staticmethod
    async def get_waitlist_position(guild_id: str, discord_tag: str) -> Optional[int]:
        """Get a user's position in the waitlist (1-based)."""
        if not guild_id or not discord_tag:
            return None

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return None

            waitlist = all_data[guild_id]["waitlist"]
            for i, entry in enumerate(waitlist):
                if entry["discord_tag"] == discord_tag:
                    return i + 1
            return None

        except Exception as e:
            logging.error(f"Error getting waitlist position: {e}")
            return None

    @staticmethod
    async def get_waitlist_entry(guild_id: str, discord_tag: str) -> Optional[Dict]:
        """Get a user's waitlist entry data."""
        if not guild_id or not discord_tag:
            return None

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return None

            waitlist = all_data[guild_id]["waitlist"]
            for entry in waitlist:
                if entry["discord_tag"] == discord_tag:
                    return entry
            return None

        except Exception as e:
            logging.error(f"Error getting waitlist entry: {e}")
            return None

    @staticmethod
    async def update_waitlist_entry(
            guild_id: str,
            discord_tag: str,
            ign: str,
            pronouns: str,
            team_name: Optional[str] = None,
            alt_igns: Optional[str] = None
    ) -> bool:
        """
        Update a user's waitlist entry while preserving their position.

        Returns:
            True if updated, False if not found
        """
        if not all([guild_id, discord_tag, ign]):
            raise ValueError("Guild ID, discord tag, and IGN are required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return False

            waitlist = all_data[guild_id]["waitlist"]

            for i, entry in enumerate(waitlist):
                if entry["discord_tag"] == discord_tag:
                    # Preserve the original added_at time
                    original_time = entry.get("added_at")

                    # Update the entry
                    waitlist[i] = {
                        "discord_tag": discord_tag,
                        "member_id": entry["member_id"],
                        "ign": ign.strip(),
                        "pronouns": pronouns.strip() if pronouns else "",
                        "team_name": team_name.strip() if team_name else None,
                        "alt_igns": alt_igns.strip() if alt_igns else None,
                        "added_at": original_time
                    }

                    WaitlistManager._save_waitlist_data(all_data)
                    logging.info(f"Updated waitlist entry for {discord_tag}")
                    return True

            return False

        except Exception as e:
            if isinstance(e, (ValueError, WaitlistError)):
                raise
            raise WaitlistError(f"Failed to update waitlist entry: {e}")

    @staticmethod
    async def process_waitlist(guild: discord.Guild) -> Optional[Dict]:
        """
        Process the waitlist when a spot opens up with comprehensive error handling.

        Returns:
            Dict with registered user info if someone was registered, None otherwise
        """
        if not guild:
            raise ValueError("Guild is required")

        print(f"[WAITLIST] Starting process_waitlist for guild {guild.id}")

        try:
            from helpers.sheet_helpers import SheetOperations
            from core.views import DMActionView

            guild_id = str(guild.id)

            # Check if there's space
            mode = get_event_mode_for_guild(guild_id)
            cfg = get_sheet_settings(mode)
            max_players = cfg.get("max_players", 0)

            print(f"[WAITLIST] Checking capacity: mode={mode}, max_players={max_players}")

            current_registered = await SheetOperations.count_by_criteria(
                guild_id, registered=True
            )

            print(f"[WAITLIST] Current registered: {current_registered}/{max_players}")

            if current_registered >= max_players:
                logging.debug(f"Guild {guild_id} is at capacity ({current_registered}/{max_players})")
                print(f"[WAITLIST] At capacity, skipping")
                return None

            # Get waitlist
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data or not all_data[guild_id]["waitlist"]:
                logging.debug(f"No waitlist entries for guild {guild_id}")
                print(f"[WAITLIST] No entries in waitlist")
                return None

            waitlist = all_data[guild_id]["waitlist"]
            print(f"[WAITLIST] Found {len(waitlist)} entries in waitlist")

            # Process first person in waitlist
            next_user = waitlist.pop(0)
            WaitlistManager._save_waitlist_data(all_data)

            print(f"[WAITLIST] Processing user: {next_user['discord_tag']}")

            # Register the user
            member = guild.get_member(next_user["member_id"])
            if not member:
                logging.warning(f"Member {next_user['discord_tag']} left server, processing next in waitlist")
                print(f"[WAITLIST] Member not found, trying next")
                return await WaitlistManager.process_waitlist(guild)

            try:
                # Register in sheet
                print(f"[WAITLIST] Registering user in sheet...")
                row = await find_or_register_user(
                    next_user["discord_tag"],
                    next_user["ign"],
                    guild_id=guild_id,
                    team_name=next_user.get("team_name")
                )

                # Update additional fields
                updates = {}
                if next_user.get("pronouns"):
                    updates[cfg['pronouns_col']] = next_user["pronouns"]
                if next_user.get("alt_igns"):
                    updates[cfg['alt_ign_col']] = next_user["alt_igns"]
                if mode == "doubleup" and next_user.get("team_name"):
                    updates[cfg['team_col']] = next_user["team_name"]

                if updates:
                    await SheetOperations.batch_update_cells(guild_id, updates, row)

                # Add registered role
                print(f"[WAITLIST] Adding registered role...")
                await RoleManager.add_role(member, "Registered")

                # Send DM notification
                print(f"[WAITLIST] Sending DM notification...")
                try:
                    # Clear previous DMs first
                    from utils.utils import clear_user_dms
                    deleted = await clear_user_dms(member, guild.me)
                    if deleted > 0:
                        logging.debug(f"Cleared {deleted} previous DMs for {next_user['discord_tag']}")

                    # Send new DM
                    dm_embed = embed_from_cfg("waitlist_registered")
                    await member.send(
                        embed=dm_embed,
                        view=DMActionView(guild, member)
                    )
                except discord.Forbidden:
                    logging.debug(f"Could not DM {next_user['discord_tag']} - DMs disabled")
                except Exception as dm_error:
                    logging.warning(f"Failed to DM {next_user['discord_tag']}: {dm_error}")

                # Log to bot-log channel
                log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
                if log_channel:
                    try:
                        log_embed = discord.Embed(
                            title="✅ Waitlist Registration",
                            description=f"**{next_user['discord_tag']}** ({next_user['ign']}) has been automatically registered from the waitlist.",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        await log_channel.send(embed=log_embed)
                    except Exception as log_error:
                        logging.warning(f"Failed to log waitlist registration: {log_error}")

                logging.info(f"Successfully registered {next_user['discord_tag']} from waitlist")
                print(f"[WAITLIST] Successfully registered {next_user['discord_tag']}")
                return next_user

            except Exception as reg_error:
                print(f"[WAITLIST] Registration error: {reg_error}")
                await ErrorHandler.log_warning(
                    guild,
                    f"Failed to auto-register {next_user['discord_tag']} from waitlist: {reg_error}",
                    "Waitlist Processing"
                )
                # Try next person
                return await WaitlistManager.process_waitlist(guild)

        except Exception as e:
            print(f"[WAITLIST] ERROR: {e}")
            if isinstance(e, (ValueError, WaitlistError)):
                raise
            raise WaitlistError(f"Failed to process waitlist: {e}")

    @staticmethod
    async def get_waitlist_length(guild_id):
        """Get the current waitlist length."""
        if not guild_id:
            return 0

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return 0
            return len(all_data[guild_id].get("waitlist", []))
        except Exception as e:
            logging.error(f"Error getting waitlist length: {e}")
            return 0