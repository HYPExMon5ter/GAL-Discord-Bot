# helpers/waitlist_helpers.py

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

import discord

from config import embed_from_cfg, get_sheet_settings, LOG_CHANNEL_NAME, DATABASE_URL
from core.persistence import get_event_mode_for_guild
from helpers.error_handler import ErrorHandler
from helpers.role_helpers import RoleManager
from helpers.sheet_helpers import SheetOperations
from helpers.logging_helper import BotLogger
from integrations.sheets import find_or_register_user


class WaitlistError(Exception):
    """Custom exception for waitlist-related errors."""
    pass


class WaitlistManager:
    """
    Enhanced waitlist manager with team-aware logic and database integration.
    """

    WAITLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "waitlist_data.json")
    _db_initialized = False
    _connection_pool = None

    @classmethod
    def _initialize_database(cls):
        """
        Initialize database connection pool using singleton pattern.
        
        Sets up PostgreSQL connection pool for waitlist data storage.
        Falls back to file storage if database is unavailable.
        """
        if cls._db_initialized:
            return

        cls._db_initialized = True

        if not DATABASE_URL:
            BotLogger.info("No database URL configured, using file storage for waitlist", "WAITLIST")
            return

        try:
            import psycopg2
            from psycopg2 import pool

            db_url = DATABASE_URL
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)

            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 5, db_url, sslmode="require"
            )

            # Initialize database schema
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
                    
                    # Add indexes for better performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_waitlist_guild_updated 
                        ON waitlist_data(guild_id, updated_at);
                    """)
                    
                    conn.commit()

            BotLogger.info("Waitlist database connection pool initialized", "WAITLIST")

        except Exception as e:
            BotLogger.warning(f"Failed to initialize waitlist database: {e}", "WAITLIST")
            cls._connection_pool = None

    @classmethod
    @contextmanager
    def _get_db_connection(cls):
        """
        Context manager for database connections.
        """
        if not cls._connection_pool:
            raise RuntimeError("Database connection pool not available")

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
    def _load_waitlist_data() -> Dict[str, Any]:
        """
        Load waitlist data from database or file.
        """
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
                                # Handle both JSONB and JSON string data
                                if isinstance(data, dict):
                                    result[guild_id] = data
                                else:
                                    try:
                                        result[guild_id] = json.loads(data)
                                    except json.JSONDecodeError as e:
                                        BotLogger.error(f"Invalid JSON in waitlist data for guild {guild_id}: {e}", "WAITLIST")
                                        result[guild_id] = {"waitlist": []}
                            return result
                        return {}
            except Exception as e:
                BotLogger.warning(f"Database load failed, falling back to file: {e}", "WAITLIST")

        # File fallback
        try:
            if os.path.exists(WaitlistManager.WAITLIST_FILE):
                with open(WaitlistManager.WAITLIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Validate data structure
                    if isinstance(data, dict):
                        return data
                    else:
                        BotLogger.warning("Invalid waitlist file structure, starting fresh", "WAITLIST")
                        return {}
            return {}
        except json.JSONDecodeError as e:
            BotLogger.error(f"Corrupted waitlist file: {e}", "WAITLIST")
            # Backup corrupted file
            try:
                backup_name = f"{WaitlistManager.WAITLIST_FILE}.backup.{int(datetime.now().timestamp())}"
                os.rename(WaitlistManager.WAITLIST_FILE, backup_name)
                BotLogger.info(f"Backed up corrupted waitlist file to {backup_name}", "WAITLIST")
            except Exception:
                pass
            return {}
        except Exception as e:
            BotLogger.error(f"Error loading waitlist file: {e}", "WAITLIST")
            return {}

    @staticmethod
    def _save_waitlist_data(data: Dict[str, Any]) -> None:
        """
        Save waitlist data to database or file.
        """
        # Validate data structure before saving
        if not isinstance(data, dict):
            raise WaitlistError("Invalid data structure for waitlist save")

        # Try database first
        if WaitlistManager._connection_pool:
            try:
                with WaitlistManager._get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        for guild_id, guild_data in data.items():
                            if not isinstance(guild_data, dict):
                                BotLogger.warning(f"Invalid guild data structure for {guild_id}", "WAITLIST")
                                continue
                                
                            cursor.execute(
                                """INSERT INTO waitlist_data (guild_id, data, updated_at) 
                                   VALUES (%s, %s, CURRENT_TIMESTAMP) 
                                   ON CONFLICT (guild_id) 
                                   DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP""",
                                (guild_id, json.dumps(guild_data))
                            )
                        conn.commit()
                        BotLogger.debug("Waitlist data saved to database", "WAITLIST")
                        return
            except Exception as e:
                BotLogger.warning(f"Database save failed, falling back to file: {e}", "WAITLIST")

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
            BotLogger.debug("Waitlist data saved to file", "WAITLIST")
            
        except Exception as e:
            BotLogger.error(f"Failed to save waitlist data to file: {e}", "WAITLIST")
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
        Add a user to the waitlist.
        """
        if not guild or not member or not ign:
            raise WaitlistError("Guild, member, and IGN are required")

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
                if entry.get("discord_tag") == discord_tag:
                    # Update existing entry
                    waitlist[i] = {
                        "discord_tag": discord_tag,
                        "member_id": member.id,
                        "ign": ign.strip(),
                        "pronouns": pronouns.strip() if pronouns else "",
                        "team_name": team_name.strip() if team_name else None,
                        "alt_igns": alt_igns.strip() if alt_igns else None,
                        "added_at": entry.get("added_at", datetime.utcnow().isoformat()),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    WaitlistManager._save_waitlist_data(all_data)
                    BotLogger.info(f"Updated waitlist entry for {discord_tag} at position {i + 1}", "WAITLIST")
                    return i + 1

            # Add new entry
            new_entry = {
                "discord_tag": discord_tag,
                "member_id": member.id,
                "ign": ign.strip(),
                "pronouns": pronouns.strip() if pronouns else "",
                "team_name": team_name.strip() if team_name else None,
                "alt_igns": alt_igns.strip() if alt_igns else None,
                "added_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            waitlist.append(new_entry)
            WaitlistManager._save_waitlist_data(all_data)

            position = len(waitlist)
            BotLogger.info(f"Added {discord_tag} to waitlist at position {position}", "WAITLIST")
            return position

        except Exception as e:
            if isinstance(e, WaitlistError):
                raise
            raise WaitlistError(f"Failed to add {discord_tag} to waitlist: {e}")

    @staticmethod
    async def remove_from_waitlist(guild_id: str, discord_tag: str) -> bool:
        """
        Remove a user from the waitlist.
        """
        if not guild_id or not discord_tag:
            raise WaitlistError("Guild ID and discord tag are required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return False

            waitlist = all_data[guild_id]["waitlist"]
            original_len = len(waitlist)

            # Remove user and preserve order
            all_data[guild_id]["waitlist"] = [
                entry for entry in waitlist
                if entry.get("discord_tag") != discord_tag
            ]

            if len(all_data[guild_id]["waitlist"]) < original_len:
                WaitlistManager._save_waitlist_data(all_data)
                BotLogger.info(f"Removed {discord_tag} from waitlist for guild {guild_id}", "WAITLIST")
                return True

            return False
            
        except Exception as e:
            if isinstance(e, WaitlistError):
                raise
            raise WaitlistError(f"Failed to remove {discord_tag} from waitlist: {e}")

    @staticmethod
    async def get_waitlist_position(guild_id: str, discord_tag: str) -> Optional[int]:
        """
        Get a user's position in the waitlist.
        """
        if not guild_id or not discord_tag:
            return None

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return None

            waitlist = all_data[guild_id]["waitlist"]
            for i, entry in enumerate(waitlist):
                if entry.get("discord_tag") == discord_tag:
                    return i + 1
            return None
            
        except Exception as e:
            BotLogger.error(f"Error getting waitlist position for {discord_tag}: {e}", "WAITLIST")
            return None

    @staticmethod
    async def get_waitlist_entry(guild_id: str, discord_tag: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's complete waitlist entry data.
        """
        if not guild_id or not discord_tag:
            return None

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return None

            waitlist = all_data[guild_id]["waitlist"]
            for entry in waitlist:
                if entry.get("discord_tag") == discord_tag:
                    return dict(entry)  # Return a copy
            return None
            
        except Exception as e:
            BotLogger.error(f"Error getting waitlist entry for {discord_tag}: {e}", "WAITLIST")
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
        if not guild_id or not discord_tag or not ign:
            raise WaitlistError("Guild ID, discord tag, and IGN are required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return False

            waitlist = all_data[guild_id]["waitlist"]

            for i, entry in enumerate(waitlist):
                if entry.get("discord_tag") == discord_tag:
                    # Preserve original timestamps and member ID
                    original_added = entry.get("added_at", datetime.utcnow().isoformat())
                    original_member_id = entry.get("member_id", 0)

                    waitlist[i] = {
                        "discord_tag": discord_tag,
                        "member_id": original_member_id,
                        "ign": ign.strip(),
                        "pronouns": pronouns.strip() if pronouns else "",
                        "team_name": team_name.strip() if team_name else None,
                        "alt_ings": alt_igns.strip() if alt_igns else None,
                        "added_at": original_added,
                        "updated_at": datetime.utcnow().isoformat()
                    }

                    WaitlistManager._save_waitlist_data(all_data)
                    BotLogger.info(f"Updated waitlist entry for {discord_tag}", "WAITLIST")
                    return True

            return False
            
        except Exception as e:
            if isinstance(e, WaitlistError):
                raise
            raise WaitlistError(f"Failed to update waitlist entry for {discord_tag}: {e}")

    @staticmethod
    async def process_waitlist_with_team_logic(guild: discord.Guild) -> List[Dict[str, Any]]:
        """
        Enhanced waitlist processing with team-aware logic.
        """
        if not guild:
            raise WaitlistError("Guild is required for waitlist processing")

        BotLogger.info(f"Starting enhanced waitlist processing for guild {guild.id}", "WAITLIST")
        registered_users = []

        try:
            guild_id = str(guild.id)
            mode = get_event_mode_for_guild(guild_id)
            cfg = get_sheet_settings(mode)
            max_players = cfg.get("max_players", 0)
            max_per_team = cfg.get("max_per_team", 2)

            # Keep processing while there are spots and waitlist entries
            processing_rounds = 0
            max_processing_rounds = 50  # Prevent infinite loops
            
            while processing_rounds < max_processing_rounds:
                processing_rounds += 1
                
                # Check current capacity
                current_registered = await SheetOperations.count_by_criteria(
                    guild_id, registered=True
                )

                available_spots = max_players - current_registered
                if available_spots <= 0:
                    BotLogger.info(f"Guild {guild_id} is at capacity ({current_registered}/{max_players})", "WAITLIST")
                    break

                # Get current waitlist
                all_data = WaitlistManager._load_waitlist_data()
                if guild_id not in all_data or not all_data[guild_id]["waitlist"]:
                    BotLogger.info(f"No waitlist entries for guild {guild_id}", "WAITLIST")
                    break

                waitlist = all_data[guild_id]["waitlist"]
                BotLogger.info(f"Processing {len(waitlist)} waitlist entries, {available_spots} spots available", "WAITLIST")

                # Find the next processable user
                processed_user = None
                user_index = None

                for i, user_entry in enumerate(waitlist):
                    if not isinstance(user_entry, dict):
                        BotLogger.warning(f"Invalid waitlist entry at index {i}", "WAITLIST")
                        continue

                    team_name = user_entry.get("team_name")
                    discord_tag = user_entry.get("discord_tag")

                    if not discord_tag:
                        BotLogger.warning(f"Waitlist entry missing discord_tag at index {i}", "WAITLIST")
                        continue

                    if mode == "doubleup" and team_name:
                        # Check if user can join their specified team
                        can_join, reason = await SheetOperations.can_user_join_team(
                            guild_id, team_name, discord_tag, max_per_team
                        )

                        if can_join:
                            processed_user = user_entry
                            user_index = i
                            BotLogger.info(f"Can register {discord_tag} to team {team_name}: {reason}", "WAITLIST")
                            break
                        else:
                            BotLogger.debug(f"Cannot register {discord_tag} to team {team_name}: {reason}", "WAITLIST")
                            continue
                    else:
                        # Normal mode or no team specified
                        processed_user = user_entry
                        user_index = i
                        break

                if not processed_user or user_index is None:
                    BotLogger.info("No waitlist users can be processed at this time", "WAITLIST")
                    break

                # Remove user from waitlist
                waitlist.pop(user_index)
                WaitlistManager._save_waitlist_data(all_data)

                # Try to register the user
                member = guild.get_member(processed_user.get("member_id", 0))
                if not member:
                    BotLogger.warning(f"Member {processed_user.get('discord_tag', 'unknown')} left server", "WAITLIST")
                    continue

                try:
                    # Register in sheet
                    discord_tag = processed_user["discord_tag"]
                    ign = processed_user["ign"]
                    team_name = processed_user.get("team_name")
                    
                    row = await find_or_register_user(
                        discord_tag,
                        ign,
                        guild_id=guild_id,
                        team_name=team_name
                    )

                    # Update additional fields
                    updates = {}
                    if processed_user.get("pronouns"):
                        updates[cfg['pronouns_col']] = processed_user["pronouns"]
                    if processed_user.get("alt_ings"):
                        updates[cfg['alt_ign_col']] = processed_user["alt_ings"]
                    if mode == "doubleup" and team_name:
                        updates[cfg['team_col']] = team_name

                    if updates:
                        await SheetOperations.batch_update_cells(guild_id, updates, row)

                    # Add registered role
                    await RoleManager.add_role(member, "Registered")

                    # Send DM notification
                    try:
                        from helpers.async_helpers import AsyncHelpers
                        from core.views import DMActionView

                        # Clear previous DMs
                        deleted = await AsyncHelpers.clear_user_dms(member, guild.me)
                        if deleted > 0:
                            BotLogger.debug(f"Cleared {deleted} previous DMs for {discord_tag}", "WAITLIST")

                        # Send new DM
                        dm_embed = embed_from_cfg("waitlist_registered")
                        await AsyncHelpers.safe_dm_user(
                            member,
                            embed=dm_embed,
                            view=DMActionView(guild, member)
                        )
                    except Exception as dm_error:
                        BotLogger.warning(f"Failed to DM {discord_tag}: {dm_error}", "WAITLIST")

                    # Log to bot-log channel
                    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
                    if log_channel:
                        try:
                            log_embed = discord.Embed(
                                title="✅ Waitlist Registration",
                                description=f"**{discord_tag}** ({ign}) has been automatically registered from the waitlist.",
                                color=discord.Color.green(),
                                timestamp=datetime.utcnow()
                            )
                            if mode == "doubleup" and team_name:
                                log_embed.add_field(
                                    name="Team",
                                    value=team_name,
                                    inline=True
                                )
                            await log_channel.send(embed=log_embed)
                        except Exception as log_error:
                            BotLogger.warning(f"Failed to log waitlist registration: {log_error}", "WAITLIST")

                    registered_users.append(processed_user)
                    BotLogger.info(f"Successfully registered {discord_tag} from waitlist", "WAITLIST")

                except Exception as reg_error:
                    BotLogger.error(f"Registration failed for {processed_user.get('discord_tag', 'unknown')}: {reg_error}", "WAITLIST")
                    # Add user back to front of waitlist if registration failed
                    waitlist.insert(0, processed_user)
                    WaitlistManager._save_waitlist_data(all_data)
                    continue

            BotLogger.info(f"Waitlist processing complete after {processing_rounds} rounds. Registered {len(registered_users)} users", "WAITLIST")
            return registered_users

        except Exception as e:
            BotLogger.error(f"Waitlist processing error: {e}", "WAITLIST")
            # Don't raise here to allow partial success
            return registered_users

    # Alias for backward compatibility
    @staticmethod
    async def process_waitlist(guild: discord.Guild) -> List[Dict[str, Any]]:
        """
        Process waitlist using enhanced team logic.
        """
        return await WaitlistManager.process_waitlist_with_team_logic(guild)

    @staticmethod
    async def get_waitlist_length(guild_id: str) -> int:
        """
        Get the current waitlist length for a guild.
        """
        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return 0
            return len(all_data[guild_id].get("waitlist", []))
        except Exception as e:
            BotLogger.error(f"Error getting waitlist length for guild {guild_id}: {e}", "WAITLIST")
            return 0

    @staticmethod
    async def get_full_waitlist(guild_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete waitlist for a guild with all user details.
        """
        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return []
            
            waitlist = all_data[guild_id].get("waitlist", [])
            # Return copies to prevent external modification
            return [dict(entry) for entry in waitlist if isinstance(entry, dict)]
            
        except Exception as e:
            BotLogger.error(f"Error getting full waitlist for guild {guild_id}: {e}", "WAITLIST")
            return []

    @staticmethod
    async def clear_waitlist(guild_id: str) -> int:
        """
        Clear the entire waitlist for a guild.
        """
        if not guild_id:
            raise WaitlistError("Guild ID is required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return 0

            removed_count = len(all_data[guild_id].get("waitlist", []))
            all_data[guild_id]["waitlist"] = []
            WaitlistManager._save_waitlist_data(all_data)
            
            BotLogger.info(f"Cleared waitlist for guild {guild_id}, removed {removed_count} users", "WAITLIST")
            return removed_count
            
        except Exception as e:
            if isinstance(e, WaitlistError):
                raise
            raise WaitlistError(f"Failed to clear waitlist for guild {guild_id}: {e}")

    @staticmethod
    async def get_waitlist_stats(guild_id: str) -> Dict[str, Any]:
        """
        Get comprehensive waitlist statistics for a guild.
        """
        try:
            waitlist = await WaitlistManager.get_full_waitlist(guild_id)
            
            stats = {
                "total_users": len(waitlist),
                "teams": {},
                "oldest_entry": None,
                "newest_entry": None
            }

            if not waitlist:
                return stats

            # Analyze team distribution
            for entry in waitlist:
                team = entry.get("team_name", "No Team")
                if team not in stats["teams"]:
                    stats["teams"][team] = 0
                stats["teams"][team] += 1

            # Find oldest and newest entries
            entries_with_dates = []
            for entry in waitlist:
                added_at = entry.get("added_at")
                if added_at:
                    try:
                        dt = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                        entries_with_dates.append((dt, entry["discord_tag"]))
                    except:
                        pass

            if entries_with_dates:
                entries_with_dates.sort()
                stats["oldest_entry"] = {
                    "discord_tag": entries_with_dates[0][1],
                    "added_at": entries_with_dates[0][0].isoformat()
                }
                stats["newest_entry"] = {
                    "discord_tag": entries_with_dates[-1][1],
                    "added_at": entries_with_dates[-1][0].isoformat()
                }

            return stats
            
        except Exception as e:
            BotLogger.error(f"Error getting waitlist stats for guild {guild_id}: {e}", "WAITLIST")
            return {"total_users": 0, "teams": {}, "oldest_entry": None, "newest_entry": None}

    @staticmethod
    def validate_waitlist_data() -> Dict[str, Any]:
        """
        Validate waitlist data integrity across all guilds.
        """
        validation = {
            "valid": True,
            "total_guilds": 0,
            "total_waitlist_users": 0,
            "issues": [],
            "guild_stats": {}
        }

        try:
            all_data = WaitlistManager._load_waitlist_data()
            validation["total_guilds"] = len(all_data)

            for guild_id, guild_data in all_data.items():
                if not isinstance(guild_data, dict):
                    validation["issues"].append(f"Guild {guild_id}: Invalid data structure")
                    validation["valid"] = False
                    continue

                waitlist = guild_data.get("waitlist", [])
                if not isinstance(waitlist, list):
                    validation["issues"].append(f"Guild {guild_id}: Waitlist is not a list")
                    validation["valid"] = False
                    continue

                guild_issues = []
                valid_entries = 0

                for i, entry in enumerate(waitlist):
                    if not isinstance(entry, dict):
                        guild_issues.append(f"Entry {i}: Not a dictionary")
                        continue

                    # Check required fields
                    required_fields = ["discord_tag", "ign", "member_id"]
                    missing_fields = [field for field in required_fields if not entry.get(field)]
                    
                    if missing_fields:
                        guild_issues.append(f"Entry {i}: Missing fields: {missing_fields}")
                    else:
                        valid_entries += 1

                validation["guild_stats"][guild_id] = {
                    "total_entries": len(waitlist),
                    "valid_entries": valid_entries,
                    "issues": guild_issues
                }

                if guild_issues:
                    validation["issues"].extend([f"Guild {guild_id}: {issue}" for issue in guild_issues])
                    validation["valid"] = False

                validation["total_waitlist_users"] += valid_entries

        except Exception as e:
            validation["issues"].append(f"Validation error: {e}")
            validation["valid"] = False

        return validation

    @staticmethod
    async def cleanup_invalid_entries(guild_id: str) -> int:
        """
        Clean up invalid waitlist entries for a guild.
        """
        if not guild_id:
            raise WaitlistError("Guild ID is required")

        try:
            all_data = WaitlistManager._load_waitlist_data()
            if guild_id not in all_data:
                return 0

            waitlist = all_data[guild_id].get("waitlist", [])
            original_count = len(waitlist)
            
            # Filter out invalid entries
            valid_entries = []
            required_fields = ["discord_tag", "ign", "member_id"]
            
            for entry in waitlist:
                if (isinstance(entry, dict) and 
                    all(entry.get(field) for field in required_fields)):
                    valid_entries.append(entry)

            all_data[guild_id]["waitlist"] = valid_entries
            WaitlistManager._save_waitlist_data(all_data)
            
            removed_count = original_count - len(valid_entries)
            
            if removed_count > 0:
                BotLogger.info(f"Cleaned up {removed_count} invalid waitlist entries for guild {guild_id}", "WAITLIST")
            
            return removed_count
            
        except Exception as e:
            if isinstance(e, WaitlistError):
                raise
            raise WaitlistError(f"Failed to cleanup waitlist for guild {guild_id}: {e}")

    @staticmethod
    async def migrate_legacy_data() -> Dict[str, int]:
        """
        Migrate legacy waitlist data to current format.
        """
        migration_stats = {
            "guilds_processed": 0,
            "entries_migrated": 0,
            "errors": 0
        }

        try:
            all_data = WaitlistManager._load_waitlist_data()
            
            for guild_id, guild_data in all_data.items():
                migration_stats["guilds_processed"] += 1
                
                if not isinstance(guild_data, dict):
                    migration_stats["errors"] += 1
                    continue

                waitlist = guild_data.get("waitlist", [])
                migrated_entries = []
                
                for entry in waitlist:
                    try:
                        if isinstance(entry, dict):
                            # Ensure all required fields exist
                            migrated_entry = {
                                "discord_tag": entry.get("discord_tag", ""),
                                "member_id": entry.get("member_id", 0),
                                "ign": entry.get("ign", ""),
                                "pronouns": entry.get("pronouns", ""),
                                "team_name": entry.get("team_name"),
                                "alt_ings": entry.get("alt_ings"),
                                "added_at": entry.get("added_at", datetime.utcnow().isoformat()),
                                "updated_at": entry.get("updated_at", datetime.utcnow().isoformat())
                            }
                            
                            # Only keep entries with essential data
                            if migrated_entry["discord_tag"] and migrated_entry["ign"]:
                                migrated_entries.append(migrated_entry)
                                migration_stats["entries_migrated"] += 1
                                
                    except Exception as entry_error:
                        BotLogger.warning(f"Failed to migrate waitlist entry: {entry_error}", "WAITLIST")
                        migration_stats["errors"] += 1

                all_data[guild_id]["waitlist"] = migrated_entries

            # Save migrated data
            WaitlistManager._save_waitlist_data(all_data)
            BotLogger.info(f"Waitlist migration complete: {migration_stats}", "WAITLIST")
            
        except Exception as e:
            BotLogger.error(f"Waitlist migration failed: {e}", "WAITLIST")
            migration_stats["errors"] += 1

        return migration_stats


# Utility functions for external use
async def add_user_to_waitlist(
        guild: discord.Guild, 
        member: discord.Member, 
        ign: str, 
        pronouns: str = "", 
        team_name: str = None,
        alt_ings: str = None
) -> int:
    """
    Convenience function to add a user to the waitlist.
    """
    return await WaitlistManager.add_to_waitlist(
        guild, member, ign, pronouns, team_name, alt_ings
    )


async def remove_user_from_waitlist(guild_id: str, discord_tag: str) -> bool:
    """
    Convenience function to remove a user from the waitlist.
    """
    return await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)


async def process_guild_waitlist(guild: discord.Guild) -> List[Dict[str, Any]]:
    """
    Convenience function to process a guild's waitlist.
    """
    return await WaitlistManager.process_waitlist(guild)


async def get_user_waitlist_info(guild_id: str, discord_tag: str) -> Optional[Dict[str, Any]]:
    """
    Get complete waitlist information for a user.
    """
    entry = await WaitlistManager.get_waitlist_entry(guild_id, discord_tag)
    if not entry:
        return None
        
    position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)
    
    return {
        "position": position,
        "entry": entry
    }


def is_waitlist_enabled() -> bool:
    """
    Check if waitlist functionality is enabled.
    """
    try:
        WaitlistManager._initialize_database()
        return True
    except Exception:
        return False


# Export important functions and classes
__all__ = [
    # Main class
    'WaitlistManager',
    
    # Exception
    'WaitlistError',
    
    # Convenience functions
    'add_user_to_waitlist',
    'remove_user_from_waitlist', 
    'process_guild_waitlist',
    'get_user_waitlist_info',
    'is_waitlist_enabled'
]