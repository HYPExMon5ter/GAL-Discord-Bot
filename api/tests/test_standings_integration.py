"""Integration tests for standings with Riot API data."""

import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.models import Base
from api.services.standings_aggregator import StandingsAggregator
from api.services.standings_service import StandingsService
from api.services.mock_riot_api import MockRiotAPI


@pytest.mark.anyio
async def test_refresh_scoreboard_with_riot_data() -> None:
    """Test scoreboard refresh with live Riot API data fetching."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        # Create test player data with IGNs
        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                {
                    "player_name": "Alice Smith",
                    "ign": "Alice#NA1",
                    "discord_tag": "alice#1234",
                    "points": 0,  # Will be populated from Riot
                    "round_scores": {},  # Will be populated from Riot
                    "sheet_row": "5",
                },
                {
                    "player_name": "Bob Johnson",
                    "ign": "Bob#NA1",
                    "discord_tag": "bob#5678",
                    "points": 0,
                    "round_scores": {},
                    "sheet_row": "6",
                },
                {
                    "player_name": "Charlie Brown",
                    "ign": "Charlie#EUW",
                    "discord_tag": "charlie#9999",
                    "points": 0,
                    "round_scores": {},
                    "sheet_row": "7",
                },
                {
                    "player_name": "No Games Player",
                    "ign": "NoGames#NA1",
                    "discord_tag": "nogames#0000",
                    "points": 0,
                    "round_scores": {},
                    "sheet_row": "8",
                },
                {
                    "player_name": "Invalid Player",
                    "ign": "Invalid#NA1",
                    "discord_tag": "invalid#1111",
                    "points": 0,
                    "round_scores": {},
                    "sheet_row": "9",
                },
            ],
        }

        # Patch RiotAPI with our mock at the module level
        with patch('integrations.riot_api.RiotAPI', MockRiotAPI):
            snapshot = await aggregator.refresh_scoreboard(
                guild_id=12345,
                tournament_id="integration_test",
                tournament_name="Integration Test Tournament",
                fetch_riot=True,
                region="na",
                source="riot_api_test",
                snapshot_override=snapshot_override,
            )

        # Verify tournament metadata
        assert snapshot.tournament_id == "integration_test"
        assert snapshot.tournament_name == "Integration Test Tournament"
        assert snapshot.source == "riot_api_test"
        assert snapshot.round_names == ["round_1"]  # Auto-generated from Riot data

        # Verify entries were created
        assert len(snapshot.entries) == 5

        # Check Alice (1st placement = 8 points)
        alice = next(e for e in snapshot.entries if e.player_name == "Alice Smith")
        assert alice.total_points == 8
        assert alice.round_scores == {"round_1": 8}
        assert alice.standing_rank == 1  # Highest points
        assert alice.riot_id == "Alice#NA1"

        # Check Bob (5th placement = 4 points)
        bob = next(e for e in snapshot.entries if e.player_name == "Bob Johnson")
        assert bob.total_points == 4
        assert bob.round_scores == {"round_1": 4}
        assert bob.standing_rank == 4  # 4th highest points
        assert bob.riot_id == "Bob#NA1"

        # Check Charlie (2nd placement = 7 points)
        charlie = next(e for e in snapshot.entries if e.player_name == "Charlie Brown")
        assert charlie.total_points == 7
        assert charlie.round_scores == {"round_1": 7}
        assert charlie.standing_rank == 2  # 2nd highest points
        assert charlie.riot_id == "Charlie#EUW"

        # Check NoGames player (no matches = 0 points)
        nogames = next(e for e in snapshot.entries if e.player_name == "No Games Player")
        assert nogames.total_points == 0
        assert nogames.round_scores == {"round_1": 0}
        assert nogames.standing_rank == 4  # Tied with Bob

        # Check Invalid player (error = 0 points)
        invalid = next(e for e in snapshot.entries if e.player_name == "Invalid Player")
        assert invalid.total_points == 0
        assert invalid.round_scores == {"round_1": 0}
        assert invalid.standing_rank == 4  # Tied with Bob and NoGames

    finally:
        session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_refresh_scoreboard_without_riot_data() -> None:
    """Test scoreboard refresh without Riot API data (fetch_riot=False)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        # Create test player data with pre-existing points
        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                {
                    "player_name": "PreRanked Player",
                    "ign": "Player#NA1",
                    "discord_tag": "player#1234",
                    "points": 15,  # Pre-existing points
                    "round_scores": {"round_1": 8, "round_2": 7},
                    "sheet_row": "5",
                },
                {
                    "player_name": "Another Player",
                    "ign": "Another#NA1",
                    "discord_tag": "another#5678",
                    "points": 10,
                    "round_scores": {"round_1": 5, "round_2": 5},
                    "sheet_row": "6",
                },
            ],
        }

        snapshot = await aggregator.refresh_scoreboard(
            guild_id=12345,
            tournament_id="no_riot_test",
            tournament_name="No Riot Test",
            fetch_riot=False,  # Disable Riot API fetching
            source="manual",
            round_names=["round_1", "round_2"],
            snapshot_override=snapshot_override,
        )

        # Verify data was used as-is without Riot modification
        assert len(snapshot.entries) == 2
        assert snapshot.round_names == ["round_1", "round_2"]

        player1 = next(e for e in snapshot.entries if e.player_name == "PreRanked Player")
        assert player1.total_points == 15  # Unchanged
        assert player1.round_scores == {"round_1": 8, "round_2": 7}
        assert player1.standing_rank == 1

        player2 = next(e for e in snapshot.entries if e.player_name == "Another Player")
        assert player2.total_points == 10  # Unchanged
        assert player2.round_scores == {"round_1": 5, "round_2": 5}
        assert player2.standing_rank == 2

    finally:
        session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_placement_to_points_conversion() -> None:
    """Test that placements are correctly converted to tournament points."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        # Create players with known placements from mock data
        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                # Alice has placement 1 -> 8 points
                {"player_name": "First Place", "ign": "Alice#NA1", "discord_tag": "first#1234"},
                # Charlie has placement 2 -> 7 points
                {"player_name": "Second Place", "ign": "Charlie#EUW", "discord_tag": "second#5678"},
                # Diana has placement 8 -> 1 point
                {"player_name": "Last Place", "ign": "Diana#KR", "discord_tag": "last#9999"},
            ],
        }

        with patch('integrations.riot_api.RiotAPI', MockRiotAPI):
            snapshot = await aggregator.refresh_scoreboard(
                guild_id=54321,
                tournament_id="points_test",
                fetch_riot=True,
                region="na",
                snapshot_override=snapshot_override,
            )

        # Verify point conversion
        entries = {e.player_name: e for e in snapshot.entries}
        
        assert entries["First Place"].total_points == 8  # 1st place
        assert entries["Second Place"].total_points == 7  # 2nd place
        assert entries["Last Place"].total_points == 1  # 8th place

        # Verify ranking by points
        assert entries["First Place"].standing_rank == 1
        assert entries["Second Place"].standing_rank == 2
        assert entries["Last Place"].standing_rank == 3

    finally:
        session.close()
        engine.dispose()
