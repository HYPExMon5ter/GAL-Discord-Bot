# helpers/waitlist_helpers.py

import json
import logging
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Optional, Dict, List

import discord
from rapidfuzz import fuzz, process

from config import embed_from_cfg, get_sheet_settings, DATABASE_URL, get_log_channel_name
from core.persistence import get_event_mode_for_guild
from helpers.error_handler import ErrorHandler
from helpers.role_helpers import RoleManager
from integrations.sheets import find_or_register_user, cache_lock, sheet_cache, refresh_sheet_cache


class WaitlistError(Exception):
    """Custom exception for waitlist-related errors."""
    pass


def utcnow() -> datetime:
    """Provide a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class WaitlistManager:
    """Manages waitlist functionality with improved database/file persistence."""
    WAITLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "waitlist_data.json")

    # Database connection management
    _connection_pool = None
    _data_loaded = False  # Track if data has been loaded this session

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
                            # Only log once per session
                            if not WaitlistManager._data_loaded:
                                logging.debug("Loaded waitlist data from database")
                                WaitlistManager._data_loaded = True
                            return result

                        return {}

            except Exception as e:
                logging.warning(f"Database load failed, falling back to file: {e}")

        # File fallback
        try:
            if os.path.exists(WaitlistManager.WAITLIST_FILE):
                with open(WaitlistManager.WAITLIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Only log once per session
                    if not WaitlistManager._data_loaded:
                        logging.debug("Loaded waitlist data from file")
                        WaitlistManager._data_loaded = True
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
    async def _find_similar_team(team_name: str, guild_id: str) -> Optional[str]:
        """
        Find a similar team name from both registered players and waitlist.
        """
        if not team_name:
            return None

        # Collect all existing teams
        all_teams = set()

        # Get registered teams from cache
        async with cache_lock:
            for tag, tpl in sheet_cache["users"].items():
                if str(tpl[2]).upper() == "TRUE" and len(tpl) > 4 and tpl[4]:
                    all_teams.add(tpl[4])

        # Get waitlisted teams
        all_data = WaitlistManager._load_waitlist_data()
        if guild_id in all_data:
            for entry in all_data[guild_id].get("waitlist", []):
                if entry.get("team_name"):
                    all_teams.add(entry["team_name"])

        if not all_teams:
            return None

        # Check for similarity
        team_lower = team_name.lower()
        team_list = list(all_teams)

        # Use fuzzy matching to find similar team names
        result = process.extractOne(
            team_name,
            team_list,
            scorer=fuzz.ratio,
            score_cutoff=80
        )

        if result:
            suggested_team, score = result[0], result[1]
            # Only suggest if it's not an exact match (case-insensitive)
            if suggested_team.lower() != team_lower:
                return suggested_team

        return None

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
        Add a user to the waitlist with validation and team similarity check.
        """
        if not all([guild, member, ign]):
            raise ValueError("Guild, member, and IGN are required")

        try:
            guild_id = str(guild.id)
            discord_tag = str(member)

            # Check for team similarity before adding/updating
            if team_name:
                similar_team = await WaitlistManager._find_similar_team(team_name, guild_id)
                if similar_team:
                    # Note: In the actual implementation, you'd want to prompt the user
                    # For now, we'll use the suggested team
                    logging.info(f"Using similar team '{similar_team}' instead of '{team_name}'")
                    team_name = similar_team

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
                        "added_at": entry.get("added_at", utcnow().isoformat())  # Preserve original time
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
                "added_at": utcnow().isoformat()
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
    async def process_waitlist(guild: discord.Guild) -> List[Dict]:
        """
        Process the waitlist with smart team pairing and priority logic.
        Validates team existence and capacity before registering.
        """
        if not guild:
            raise ValueError("Guild is required")

        print(f"[WAITLIST] Starting smart process_waitlist for guild {guild.id}")
        registered_users = []

        try:
            from helpers.sheet_helpers import SheetOperations
            from core.views import WaitlistRegistrationDMView
            from utils.utils import hyperlink_lolchess_profile  # Add import

            guild_id = str(guild.id)
            mode = get_event_mode_for_guild(guild_id)
            cfg = get_sheet_settings(mode)
            max_players = cfg.get("max_players", 0)
            max_per_team = cfg.get("max_per_team", 2)
            max_teams = max_players // max_per_team

            # Keep processing while there are spots and waitlist entries
            while True:
                # Check available capacity
                current_registered = await SheetOperations.count_by_criteria(
                    guild_id, registered=True
                )
                available_spots = max_players - current_registered

                print(f"[WAITLIST] Available spots: {available_spots}")

                if available_spots <= 0:
                    print(f"[WAITLIST] At capacity, stopping")
                    break

                # Get current waitlist
                all_data = WaitlistManager._load_waitlist_data()
                if guild_id not in all_data or not all_data[guild_id]["waitlist"]:
                    print(f"[WAITLIST] No entries in waitlist")
                    break

                waitlist = all_data[guild_id]["waitlist"]
                print(f"[WAITLIST] Processing {len(waitlist)} waitlist entries")

                # Track who we'll register in this iteration
                to_register = []

                # In double-up mode, apply smart prioritization
                if mode == "doubleup":
                    # Get current team status
                    team_member_counts = {}
                    async with cache_lock:
                        for tag, tpl in sheet_cache["users"].items():
                            if str(tpl[2]).upper() == "TRUE" and len(tpl) > 4 and tpl[4]:
                                team_lower = tpl[4].lower()
                                if team_lower not in team_member_counts:
                                    team_member_counts[team_lower] = []
                                team_member_counts[team_lower].append(tag)

                    num_existing_teams = len(team_member_counts)

                    # Priority 1: Check for team pairs if 2+ spots available
                    if available_spots >= 2:
                        print("[WAITLIST] Checking for team pairs...")

                        # Group waitlist by team name
                        team_groups = {}
                        for entry in waitlist:
                            team = entry.get("team_name")
                            if team:
                                team_lower = team.lower()
                                if team_lower not in team_groups:
                                    team_groups[team_lower] = []
                                team_groups[team_lower].append(entry)

                        # Look for teams with 2+ waitlisted members
                        for team_lower, team_members in team_groups.items():
                            if len(team_members) >= 2:
                                # Check if this team exists or can be created
                                team_exists = team_lower in team_member_counts
                                current_count = len(team_member_counts.get(team_lower, []))

                                if team_exists:
                                    # Team exists - check if there's room for both
                                    spots_in_team = max_per_team - current_count
                                    if spots_in_team >= 2:
                                        print(
                                            f"[WAITLIST] Found team pair for existing team '{team_lower}' - registering both")
                                        to_register = team_members[:2]
                                        break
                                else:
                                    # Team doesn't exist - check if we can create new team
                                    if num_existing_teams < max_teams:
                                        print(
                                            f"[WAITLIST] Found team pair for new team '{team_lower}' - registering both")
                                        to_register = team_members[:2]
                                        break

                    # Priority 2: Check for individuals joining existing teams
                    if not to_register:
                        print("[WAITLIST] Checking for individuals to join existing teams...")

                        for entry in waitlist:
                            team = entry.get("team_name")
                            if team:
                                team_lower = team.lower()

                                # Check if team exists and has space
                                if team_lower in team_member_counts:
                                    current_count = len(team_member_counts[team_lower])
                                    if current_count < max_per_team:
                                        print(f"[WAITLIST] Found user to complete existing team '{team}'")
                                        to_register = [entry]
                                        break
                                else:
                                    # Team doesn't exist - check if we can create it
                                    if num_existing_teams < max_teams:
                                        print(f"[WAITLIST] Found user to create new team '{team}'")
                                        to_register = [entry]
                                        break

                    # Priority 3: Solo players without teams (if space for new teams)
                    if not to_register:
                        print("[WAITLIST] Checking for solo players...")

                        for entry in waitlist:
                            if not entry.get("team_name"):
                                # Solo player - can register if there's space
                                print(f"[WAITLIST] Found solo player")
                                to_register = [entry]
                                break

                else:
                    # Normal mode - just take first in line
                    print("[WAITLIST] Normal mode - taking first person in queue")
                    to_register = [waitlist[0]]

                # If we have no one to register, stop
                if not to_register:
                    print("[WAITLIST] No suitable candidates found")
                    break

                # Remove selected users from waitlist FIRST
                for user in to_register:
                    waitlist.remove(user)
                WaitlistManager._save_waitlist_data(all_data)

                # Register each selected user
                for next_user in to_register:
                    print(f"[WAITLIST] Processing user: {next_user['discord_tag']}")

                    # Get member object
                    member = guild.get_member(next_user["member_id"])
                    if not member:
                        logging.warning(f"Member {next_user['discord_tag']} left server, skipping")
                        print(f"[WAITLIST] Member not found, skipping")
                        continue

                    try:
                        # Register in sheet
                        print(f"[WAITLIST] Registering user in sheet...")
                        row = await find_or_register_user(
                            next_user["discord_tag"],
                            next_user["ign"],
                            guild_id=guild_id,
                            team_name=next_user.get("team_name"),
                            alt_igns=next_user.get("alt_igns"),
                            pronouns=next_user.get("pronouns")
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

                        # HYPERLINK THE IGN - THIS WAS MISSING!
                        print(f"[WAITLIST] Creating hyperlink for IGN...")
                        await hyperlink_lolchess_profile(next_user["discord_tag"], guild_id)

                        # Send DM notification
                        print(f"[WAITLIST] Sending DM notification...")
                        try:
                            # Clear previous DMs first
                            from utils.utils import clear_user_dms
                            deleted = await clear_user_dms(member, guild.me)
                            if deleted > 0:
                                logging.debug(f"Cleared {deleted} previous DMs for {next_user['discord_tag']}")

                            # Send new DM with channel button
                            from core.views import WaitlistRegistrationDMView
                            dm_embed = embed_from_cfg("waitlist_registered")
                            dm_view = WaitlistRegistrationDMView(guild)
                            await member.send(embed=dm_embed, view=dm_view)
                        except discord.Forbidden:
                            logging.debug(f"Could not DM {next_user['discord_tag']} - DMs disabled")
                        except Exception as dm_error:
                            logging.warning(f"Failed to DM {next_user['discord_tag']}: {dm_error}")

                        # Log to bot-log channel
                        log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())
                        if log_channel:
                            try:
                                team_info = f" for team **{next_user.get('team_name')}**" if next_user.get(
                                    "team_name") else ""
                                log_embed = discord.Embed(
                                    title="✅ Waitlist Registration",
                                    description=f"**{next_user['discord_tag']}** ({next_user['ign']}) has been automatically registered from the waitlist{team_info}.",
                                    color=discord.Color.green(),
                                    timestamp=utcnow()
                                )
                                await log_channel.send(embed=log_embed)
                            except Exception as log_error:
                                logging.warning(f"Failed to log waitlist registration: {log_error}")

                        registered_users.append(next_user)
                        logging.info(f"Successfully registered {next_user['discord_tag']} from waitlist")
                        print(f"[WAITLIST] Successfully registered {next_user['discord_tag']}")

                    except Exception as reg_error:
                        print(f"[WAITLIST] Registration error: {reg_error}")
                        await ErrorHandler.log_warning(
                            guild,
                            f"Failed to auto-register {next_user['discord_tag']} from waitlist: {reg_error}",
                            "Waitlist Processing"
                        )
                        # Continue to next iteration
                        continue

                # Refresh cache after each registration batch
                await refresh_sheet_cache(force=True)

            # After loop ends
            if registered_users:
                print(f"[WAITLIST] Registered {len(registered_users)} users from waitlist")

                # Update embeds after successful registrations
                from core.components_traditional import setup_unified_channel
                await setup_unified_channel(guild)
            else:
                print(f"[WAITLIST] No users registered from waitlist")

            return registered_users

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

    @staticmethod
    async def get_all_waitlist_entries(guild_id: str):
        """Get all waitlist entries for a guild."""
        if not guild_id:
            return []

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return []
            return all_data[guild_id].get("waitlist", [])
        except Exception as e:
            logging.error(f"Error getting all waitlist entries: {e}")
            return []
