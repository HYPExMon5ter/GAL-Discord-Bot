"""Lobby manager for Google Sheets integration."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from integrations.sheets import get_sheet_for_guild

logger = logging.getLogger(__name__)


@dataclass
class PlayerPosition:
    """Represents a player's position in the lobbies tab."""
    ign: str
    riot_id: str
    row_number: int
    lobby: str


@dataclass
class LobbyInfo:
    """Information about a specific lobby."""
    name: str  # "Lobby A"
    start_row: int  # Row where this lobby starts
    players: List[PlayerPosition]  # Player rows in this lobby
    round_columns: Dict[str, str]  # "Round 1" -> "C", "Round 2" -> "D"


@dataclass
class LobbyStructure:
    """Represents the detected lobbies tab structure."""
    lobbies: Dict[str, LobbyInfo]  # "Lobby A" -> LobbyInfo
    rounds: List[str]  # ["Round 1", "Round 2", "Round 3", "Round 4", "Finals"]
    sheet_name: str = "Lobbies"


@dataclass
class PlacementUpdate:
    """Placement update data."""
    lobby: str
    player_ign: str
    player_riot_id: str
    round: str
    placement: int
    row_number: int


@dataclass
class BatchResult:
    """Result of batch placement updates."""
    successful: int
    failed: List[FailedPlayer]
    total: int


@dataclass
class FailedPlayer:
    """Failed placement update details."""
    ign: str
    riot_id: str
    reason: str
    retry_possible: bool


class LobbyManager:
    """Manages lobbies tab operations for placement updates."""

    _structure_cache: Dict[str, Tuple[LobbyStructure, float]] = {}
    _CACHE_TTL = 300  # 5 minutes

    @staticmethod
    async def detect_structure(guild_id: str) -> LobbyStructure:
        """
        Detect lobbies tab structure.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            LobbyStructure with detected layout
        """
        import time
        current_time = time.time()
        
        # Check cache
        if guild_id in LobbyManager._structure_cache:
            cached_structure, cached_time = LobbyManager._structure_cache[guild_id]
            if current_time - cached_time < LobbyManager._CACHE_TTL:
                return cached_structure
        
        sheet = await get_sheet_for_guild(guild_id, "Lobbies")
        
        # Get all data
        all_data = sheet.get_all_values()
        if not all_data:
            raise ValueError("Lobbies tab is empty or not accessible")
        
        # Find header row (round columns)
        header_row = 0
        round_columns = {}
        
        for i, row in enumerate(all_data):
            if any("Round" in str(cell) or "Finals" in str(cell) for cell in row):
                header_row = i
                # Find round columns
                for j, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    if cell_str and ("Round" in cell_str or "Finals" in cell_str):
                        # Convert column index to letter
                        col_letter = chr(65 + j) if j < 26 else chr(65 + j // 26 - 1) + chr(65 + j % 26)
                        round_columns[cell_str] = col_letter
                break
        
        if not round_columns:
            raise ValueError("No round columns found in Lobbies tab")
        
        rounds = list(round_columns.keys())
        logger.info(f"Found rounds: {rounds}")
        
        # Detect lobbies
        lobbies = {}
        current_lobby = None
        current_lobby_start = 0
        
        # Start after header row
        for i in range(header_row + 1, len(all_data)):
            row = all_data[i]
            if not row or not any(row):
                continue  # Skip empty rows
            
            # Check if this is a lobby header
            first_cell = str(row[0]).strip()
            if first_cell and re.match(r"Lobby\s+[A-Z]$", first_cell, re.IGNORECASE):
                # Save previous lobby if exists
                if current_lobby:
                    lobbies[current_lobby.name] = current_lobby
                
                # Start new lobby
                current_lobby = LobbyInfo(
                    name=first_cell,
                    start_row=i + 1,  # 1-indexed for sheet operations
                    players=[],
                    round_columns=round_columns
                )
                current_lobby_start = i + 1
                continue
            
            # If we're in a lobby and have player data
            if current_lobby and len(row) > 0:
                # Get IGN (usually in column A or B)
                ign = None
                riot_id = None
                
                # Look for IGN in first few columns
                for j in range(min(3, len(row))):
                    if row[j] and str(row[j]).strip():
                        potential_ign = str(row[j]).strip()
                        # Skip if it looks like a number or empty
                        if not potential_ign.replace("#", "").replace(" ", "").isdigit():
                            ign = potential_ign
                            # Try to extract Riot ID from IGN format
                            if "#" in ign:
                                riot_id = ign
                            break
                
                if ign:
                    player = PlayerPosition(
                        ign=ign,
                        riot_id=riot_id or ign,
                        row_number=i + 1,  # 1-indexed for sheet operations
                        lobby=current_lobby.name
                    )
                    current_lobby.players.append(player)
        
        # Add the last lobby
        if current_lobby:
            lobbies[current_lobby.name] = current_lobby
        
        if not lobbies:
            raise ValueError("No lobbies found in Lobbies tab")
        
        # Create structure
        structure = LobbyStructure(
            lobbies=lobbies,
            rounds=rounds,
            sheet_name="Lobbies"
        )
        
        # Cache the structure
        LobbyManager._structure_cache[guild_id] = (structure, current_time)
        
        logger.info(f"Detected lobby structure for guild {guild_id}: {len(lobbies)} lobbies, {len(rounds)} rounds")
        
        return structure

    @staticmethod
    async def get_players_for_round(guild_id: str, round_name: str) -> List[PlayerPosition]:
        """
        Get all players across all lobbies for a specific round.
        
        Args:
            guild_id: Discord guild ID
            round_name: Round name (e.g., "Round 1", "Finals")
            
        Returns:
            List of PlayerPosition objects
        """
        structure = await LobbyManager.detect_structure(guild_id)
        
        # Verify round exists
        if round_name not in structure.rounds:
            raise ValueError(f"Round '{round_name}' not found. Available rounds: {structure.rounds}")
        
        all_players = []
        for lobby_info in structure.lobbies.values():
            all_players.extend(lobby_info.players)
        
        logger.info(f"Found {len(all_players)} players for round '{round_name}' across {len(structure.lobbies)} lobbies")
        
        return all_players

    @staticmethod
    async def update_placements_batch(
        guild_id: str,
        round_name: str,
        placements: Dict[str, int]  # {riot_id: placement}
    ) -> BatchResult:
        """
        Update placements for all players in specified round.
        
        Args:
            guild_id: Discord guild ID
            round_name: Round name (e.g., "Round 1", "Finals")
            placements: Dictionary mapping riot_id to placement
            
        Returns:
            BatchResult with success/failure details
        """
        structure = await LobbyManager.detect_structure(guild_id)
        
        # Verify round exists
        if round_name not in structure.rounds:
            raise ValueError(f"Round '{round_name}' not found. Available rounds: {structure.rounds}")
        
        # Get column for this round
        round_col = structure.rounds.get(round_name)
        if not round_col:
            raise ValueError(f"Column not found for round '{round_name}'")
        
        successful = 0
        failed = []
        total = len(placements)
        
        # Prepare batch updates
        updates = []
        for lobby_info in structure.lobbies.values():
            for player in lobby_info.players:
                if player.riot_id in placements:
                    placement = placements[player.riot_id]
                    # Validate placement
                    if placement < 1 or placement > 8:
                        failed.append(FailedPlayer(
                            ign=player.ign,
                            riot_id=player.riot_id,
                            reason=f"Invalid placement: {placement} (must be 1-8)",
                            retry_possible=False
                        ))
                        continue
                    
                    # Create cell reference and value
                    cell_ref = f"{round_col}{player.row_number}"
                    updates.append((cell_ref, placement))
        
        if not updates:
            logger.warning("No valid placements to update")
            return BatchResult(
                successful=0,
                failed=failed,
                total=total
            )
        
        try:
            sheet = await get_sheet_for_guild(guild_id, "Lobbies")
            
            # Batch update all placements
            from integrations.sheets import apply_sheet_updates
            success = await apply_sheet_updates(sheet, updates)
            
            if success:
                successful = len(updates)
                logger.info(f"Successfully updated {successful} placements for round '{round_name}'")
            else:
                # If batch failed, report all as failed
                for lobby_info in structure.lobbies.values():
                    for player in lobby_info.players:
                        if player.riot_id in placements:
                            failed.append(FailedPlayer(
                                ign=player.ign,
                                riot_id=player.riot_id,
                                reason="Sheet update failed",
                                retry_possible=True
                            ))
            
        except Exception as e:
            logger.error(f"Failed to update placements for guild {guild_id}: {e}")
            # Report all as failed
            for lobby_info in structure.lobbies.values():
                for player in lobby_info.players:
                    if player.riot_id in placements:
                        failed.append(FailedPlayer(
                            ign=player.ign,
                            riot_id=player.riot_id,
                            reason=f"Sheet error: {str(e)}",
                            retry_possible=True
                        ))
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total=total
        )

    @staticmethod
    async def validate_round(guild_id: str, round_name: str) -> bool:
        """
        Validate that a round exists in the lobbies tab.
        
        Args:
            guild_id: Discord guild ID
            round_name: Round name to validate
            
        Returns:
            True if round exists, False otherwise
        """
        try:
            structure = await LobbyManager.detect_structure(guild_id)
            return round_name in structure.rounds
        except Exception as e:
            logger.error(f"Failed to validate round '{round_name}' for guild {guild_id}: {e}")
            return False
