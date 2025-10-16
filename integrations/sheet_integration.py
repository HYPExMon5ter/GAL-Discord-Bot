# integrations/sheet_integration.py

import logging
from typing import Dict, Any, Optional, Tuple

from config import get_sheet_settings, col_to_index
from core.persistence import get_event_mode_for_guild
from core.migration import ensure_guild_migration
from utils.feature_flags import sheets_refactor_enabled


class SheetIntegrationHelper:
    """
    Helper class to bridge the gap between old config-based and new persistence-based column mappings.
    """

    # Cache to avoid repeated column lookups
    _column_cache = {}
    _cache_ttl = 300  # 5 minutes cache TTL

    @staticmethod
    async def get_column_config(guild_id: str) -> Dict[str, Any]:
        """
        Get column configuration for a guild, falling back to config if needed.
        """
        # Check cache first
        import time
        current_time = time.time()
        cache_key = f"col_config_{guild_id}"

        if cache_key in SheetIntegrationHelper._column_cache:
            cached_data, cached_time = SheetIntegrationHelper._column_cache[cache_key]
            if current_time - cached_time < SheetIntegrationHelper._cache_ttl:
                return cached_data

        column_config: Dict[str, Any] = {}

        if sheets_refactor_enabled():
            # Ensure guild is migrated only when the refactor path is active
            await ensure_guild_migration(guild_id)

            try:
                # Import locally to avoid circular imports
                from integrations.sheet_detector import get_column_mapping

                mapping = await get_column_mapping(guild_id)

                if mapping.discord_column:
                    column_config["discord_col"] = mapping.discord_column
                if mapping.ign_column:
                    column_config["ign_col"] = mapping.ign_column
                if mapping.alt_ign_column:
                    column_config["alt_ign_col"] = mapping.alt_ign_column
                if mapping.pronouns_column:
                    column_config["pronouns_col"] = mapping.pronouns_column
                if mapping.registered_column:
                    column_config["registered_col"] = mapping.registered_column
                if mapping.checkin_column:
                    column_config["checkin_col"] = mapping.checkin_column
                if mapping.team_column:
                    column_config["team_col"] = mapping.team_column
                if mapping.custom_columns:
                    column_config.update(mapping.custom_columns)

            except Exception as exc:  # pragma: no cover - network/persistence edge case
                logging.warning(
                    "Failed to get column mapping from persistence for guild %s: %s",
                    guild_id,
                    exc,
                )
                column_config = {}

        if not column_config:
            # Fallback to config.yaml (legacy behaviour)
            try:
                mode = get_event_mode_for_guild(guild_id)
                settings = get_sheet_settings(mode)

                column_keys = [
                    "discord_col",
                    "ign_col",
                    "alt_ign_col",
                    "pronouns_col",
                    "registered_col",
                    "checkin_col",
                    "team_col",
                ]

                for key in column_keys:
                    if key in settings:
                        column_config[key] = settings[key]

                logging.info("Using config.yaml fallback for guild %s", guild_id)

            except Exception as exc:
                logging.error(
                    "Failed to get column config from all sources for guild %s: %s",
                    guild_id,
                    exc,
                )
                column_config = {}

        SheetIntegrationHelper._column_cache[cache_key] = (column_config, current_time)
        return column_config

    @staticmethod
    async def get_column_indexes(guild_id: str) -> Dict[str, int]:
        """
        Get column indexes for a guild, with fallback logic.
        """
        column_config = await SheetIntegrationHelper.get_column_config(guild_id)
        indexes = {}

        column_mapping = {
            "discord_col": "discord_idx",
            "ign_col": "ign_idx",
            "alt_ign_col": "alt_idx",
            "pronouns_col": "pronouns_idx",
            "registered_col": "registered_idx",
            "checkin_col": "checkin_idx",
            "team_col": "team_idx"
        }

        for config_key, index_key in column_mapping.items():
            if config_key in column_config:
                try:
                    indexes[index_key] = col_to_index(column_config[config_key])
                except Exception as e:
                    logging.warning(f"Invalid column {column_config[config_key]} for {config_key}: {e}")

        return indexes

    @staticmethod
    async def get_sheet_and_column_config(guild_id: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Get both sheet settings and column indexes for a guild.
        """
        mode = get_event_mode_for_guild(guild_id)
        sheet_settings = get_sheet_settings(mode)
        column_indexes = await SheetIntegrationHelper.get_column_indexes(guild_id)

        return sheet_settings, column_indexes

    @staticmethod
    def validate_required_columns(column_config: Dict[str, Any], mode: str) -> Tuple[bool, list]:
        """
        Validate that all required columns are present.
        """
        required_columns = ["discord_col", "ign_col", "registered_col", "checkin_col"]

        if mode == "doubleup":
            required_columns.append("team_col")

        missing_columns = []
        for column in required_columns:
            if column not in column_config:
                missing_columns.append(column)

        return len(missing_columns) == 0, missing_columns

    @staticmethod
    async def get_column_letter(guild_id: str, column_type: str) -> Optional[str]:
        """
        Get a specific column letter for a guild.
        """
        column_config = await SheetIntegrationHelper.get_column_config(guild_id)
        return column_config.get(column_type)

    @staticmethod
    async def update_column_mapping(guild_id: str, column_type: str, column_letter: str) -> bool:
        """
        Update a specific column mapping.
        """
        try:
            from integrations.sheet_detector import get_column_mapping
            mapping = await get_column_mapping(guild_id)

            if column_type == "discord":
                mapping.discord_column = column_letter
            elif column_type == "ign":
                mapping.ign_column = column_letter
            elif column_type == "alt_ign":
                mapping.alt_ign_column = column_letter
            elif column_type == "pronouns":
                mapping.pronouns_column = column_letter
            elif column_type == "registered":
                mapping.registered_column = column_letter
            elif column_type == "checkin":
                mapping.checkin_column = column_letter
            elif column_type == "team":
                mapping.team_column = column_letter
            else:
                mapping.custom_columns[column_type] = column_letter

            from integrations.sheet_detector import save_column_mapping
            await save_column_mapping(guild_id, mapping)

            return True

        except Exception as e:
            logging.error(f"Failed to update column mapping for guild {guild_id}: {e}")
            return False

    @staticmethod
    async def remove_column_mapping(guild_id: str, column_type: str) -> bool:
        """
        Remove a specific column mapping.
        """
        try:
            from integrations.sheet_detector import get_column_mapping
            mapping = await get_column_mapping(guild_id)

            if column_type == "discord":
                mapping.discord_column = None
            elif column_type == "ign":
                mapping.ign_column = None
            elif column_type == "alt_ign":
                mapping.alt_ign_column = None
            elif column_type == "pronouns":
                mapping.pronouns_column = None
            elif column_type == "registered":
                mapping.registered_column = None
            elif column_type == "checkin":
                mapping.checkin_column = None
            elif column_type == "team":
                mapping.team_column = None
            elif column_type in mapping.custom_columns:
                del mapping.custom_columns[column_type]
            else:
                return False

            from integrations.sheet_detector import save_column_mapping
            await save_column_mapping(guild_id, mapping)

            return True

        except Exception as e:
            logging.error(f"Failed to remove column mapping for guild {guild_id}: {e}")
            return False

    @staticmethod
    async def migrate_and_validate(guild_id: str) -> Dict[str, Any]:
        """
        Migrate guild if needed and validate column configuration.
        """
        result = {
            "guild_id": guild_id,
            "migrated": False,
            "valid": False,
            "missing_columns": [],
            "error": None
        }

        try:
            # Ensure migration
            migration_success = await ensure_guild_migration(guild_id)
            result["migrated"] = migration_success

            # Get column config
            column_config = await SheetIntegrationHelper.get_column_config(guild_id)

            # Validate
            mode = get_event_mode_for_guild(guild_id)
            is_valid, missing = SheetIntegrationHelper.validate_required_columns(column_config, mode)

            result["valid"] = is_valid
            result["missing_columns"] = missing

            return result

        except Exception as e:
            result["error"] = str(e)
            logging.error(f"Failed to migrate and validate guild {guild_id}: {e}")
            return result


async def build_event_snapshot(guild_id: int) -> Dict[str, Any]:
    """
    Build a canonical snapshot of event data for the dashboard.
    Pulls data from Google Sheets cache and normalizes it for database consumption.
    
    Args:
        guild_id: Discord guild ID
        
    Returns:
        Dict containing normalized event data with lobbies and standings
    """
    try:
        import time
        from integrations.sheets import sheet_cache, cache_lock
        from core.persistence import get_event_mode_for_guild
        
        gid = str(guild_id)
        mode = get_event_mode_for_guild(gid)
        
        # Get current event information (would typically come from database or active event)
        # For now, we'll create a basic event structure
        event_snapshot = {
            "event_id": 1,  # Would come from database active event
            "event_name": "GAL Tournament",  # Would come from database
            "guild_id": guild_id,
            "mode": mode,
            "round": 1,  # Would come from tournament phase tracking
            "lobbies": [],
            "standings": [],
            "metadata": {
                "last_updated": time.time(),
                "source": "google_sheets",
                "total_players": 0,
                "registered_players": 0,
                "checked_in_players": 0
            }
        }
        
        # Get sheet cache data
        async with cache_lock:
            cache_data = dict(sheet_cache.get("users", {}))
        
        # Process players from cache
        players = []
        registered_players = []
        checked_in_players = []
        
        for discord_tag, user_data in cache_data.items():
            # Cache format: (row, ign, reg_status, ci_status, team, alt_ign, pronouns)
            row, ign, reg_status, ci_status, team, alt_ign, pronouns = user_data
            
            is_registered = str(reg_status).upper() == "TRUE" if reg_status else False
            is_checked_in = str(ci_status).upper() == "TRUE" if ci_status else False
            
            player_data = {
                "discord_tag": discord_tag,
                "ign": ign,
                "alt_ign": alt_ign or "",
                "pronouns": pronouns or "",
                "team": team or "",
                "is_registered": is_registered,
                "is_checked_in": is_checked_in,
                "sheet_row": row
            }
            
            players.append(player_data)
            
            if is_registered:
                registered_players.append(player_data)
                event_snapshot["metadata"]["registered_players"] += 1
                
                if is_checked_in:
                    checked_in_players.append(player_data)
                    event_snapshot["metadata"]["checked_in_players"] += 1
        
        event_snapshot["metadata"]["total_players"] = len(players)
        
        # Build lobbies based on mode and team assignments
        if mode == "doubleup":
            # Group by team for doubleup mode
            teams = {}
            for player in registered_players:
                team_name = player["team"] or f"Team_{player['ign']}"
                if team_name not in teams:
                    teams[team_name] = []
                teams[team_name].append(player)
            
            # Create lobby entries for each team
            lobby_id = 1
            for team_name, team_players in teams.items():
                lobby = {
                    "lobby_id": lobby_id,
                    "name": team_name,
                    "players": [
                        {
                            "discord_tag": p["discord_tag"],
                            "ign": p["ign"],
                            "alt_ign": p["alt_ign"],
                            "pronouns": p["pronouns"],
                            "is_checked_in": p["is_checked_in"],
                            "sheet_row": p["sheet_row"]
                        }
                        for p in team_players
                    ],
                    "status": "active" if any(p["is_checked_in"] for p in team_players) else "pending",
                    "player_count": len(team_players)
                }
                event_snapshot["lobbies"].append(lobby)
                lobby_id += 1
                
        else:
            # Solo mode - create lobbies of appropriate size (typically 8 players)
            lobby_size = 8
            current_lobby = []
            lobby_id = 1
            
            for player in registered_players:
                current_lobby.append(player)
                
                if len(current_lobby) >= lobby_size:
                    lobby = {
                        "lobby_id": lobby_id,
                        "name": f"Lobby {lobby_id}",
                        "players": [
                            {
                                "discord_tag": p["discord_tag"],
                                "ign": p["ign"],
                                "alt_ign": p["alt_ign"],
                                "pronouns": p["pronouns"],
                                "is_checked_in": p["is_checked_in"],
                                "sheet_row": p["sheet_row"]
                            }
                            for p in current_lobby
                        ],
                        "status": "active" if any(p["is_checked_in"] for p in current_lobby) else "pending",
                        "player_count": len(current_lobby)
                    }
                    event_snapshot["lobbies"].append(lobby)
                    current_lobby = []
                    lobby_id += 1
            
            # Add remaining players to last lobby
            if current_lobby:
                lobby = {
                    "lobby_id": lobby_id,
                    "name": f"Lobby {lobby_id}",
                    "players": [
                        {
                            "discord_tag": p["discord_tag"],
                            "ign": p["ign"],
                            "alt_ign": p["alt_ign"],
                            "pronouns": p["pronouns"],
                            "is_checked_in": p["is_checked_in"],
                            "sheet_row": p["sheet_row"]
                        }
                        for p in current_lobby
                    ],
                    "status": "active" if any(p["is_checked_in"] for p in current_lobby) else "pending",
                    "player_count": len(current_lobby)
                }
                event_snapshot["lobbies"].append(lobby)
        
        # Build standings (placeholder - would typically come from match results)
        # For now, base standings on registration order
        standings = []
        for rank, player in enumerate(registered_players, 1):
            standing = {
                "rank_position": rank,  # Matches database column name
                "discord_tag": player["discord_tag"],
                "ign": player["ign"],
                "team": player["team"] or "",
                "points": 0,  # Would come from tournament scoring
                "wins": 0,   # Would come from match results
                "top4": 0,   # Would come from match results (top 4 finishes)
                "average_placement": 0.0  # Would come from match results
            }
            standings.append(standing)
        
        event_snapshot["standings"] = standings
        
        logging.info(f"Built event snapshot for guild {guild_id}: "
                    f"{len(event_snapshot['lobbies'])} lobbies, "
                    f"{len(registered_players)} registered, "
                    f"{len(checked_in_players)} checked in")
        
        return event_snapshot
        
    except Exception as e:
        logging.error(f"Failed to build event snapshot for guild {guild_id}: {e}")
        # Return minimal structure on error
        return {
            "event_id": 1,
            "event_name": "GAL Tournament",
            "guild_id": guild_id,
            "mode": "unknown",
            "round": 1,
            "lobbies": [],
            "standings": [],
            "metadata": {
                "last_updated": time.time(),
                "source": "google_sheets",
                "total_players": 0,
                "registered_players": 0,
                "checked_in_players": 0,
                "error": str(e)
            }
        }
