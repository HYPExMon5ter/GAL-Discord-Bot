import asyncio

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.models import Base
from api.services.standings_aggregator import StandingsAggregator
from api.services.standings_service import StandingsService


@pytest.mark.anyio
async def test_refresh_scoreboard_uses_snapshot_override() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                {
                    "player_name": "Alice",
                    "ign": "Alice#NA1",
                    "discord_tag": "Alice#0001",
                    "points": 7,
                    "round_scores": {"round_1": 4, "round_2": 3},
                    "sheet_row": "5",
                },
                {
                    "player_name": "Bob",
                    "ign": "Bob#NA1",
                    "discord_tag": "Bob#0002",
                    "points": 5,
                    "round_scores": {"round_1": 2, "round_2": 3},
                    "sheet_row": "6",
                },
            ],
        }

        snapshot = await aggregator.refresh_scoreboard(
            guild_id=123,
            tournament_id="test",
            tournament_name="Test Event",
            round_names=["round_1", "round_2"],
            source="manual",
            fetch_riot=False,
            snapshot_override=snapshot_override,
        )

        assert snapshot.tournament_id == "test"
        assert snapshot.tournament_name == "Test Event"
        assert snapshot.source == "manual"
        assert snapshot.round_names == ["round_1", "round_2"]
        assert snapshot.entries
        assert [entry.player_name for entry in snapshot.entries] == ["Alice", "Bob"]
        alice = snapshot.entries[0]
        assert alice.total_points == 7
        assert alice.round_scores == {"round_1": 4, "round_2": 3}
        assert alice.standing_rank == 1
        bob = snapshot.entries[1]
        assert bob.total_points == 5
        assert bob.standing_rank == 2
    finally:
        session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_refresh_scoreboard_with_riot_api() -> None:
    """Test scoreboard refresh with Riot API integration."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        # Create test data with players that have IGNs
        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                {
                    "player_name": "Alice",
                    "ign": "Alice#NA1",
                    "discord_tag": "Alice#0001",
                    "points": 0,  # Will be populated from Riot
                    "round_scores": {},  # Will be populated from Riot
                    "sheet_row": "5",
                },
                {
                    "player_name": "Bob",
                    "ign": "Bob#NA1",
                    "discord_tag": "Bob#0002",
                    "points": 0,
                    "round_scores": {},
                    "sheet_row": "6",
                },
            ],
        }

        # Mock the Riot API to use our mock implementation
        from api.services.mock_riot_api import MockRiotAPI
        with patch('integrations.riot_api.RiotAPI', MockRiotAPI):
                snapshot = await aggregator.refresh_scoreboard(
                    guild_id=123,
                    tournament_id="riot_test",
                    tournament_name="Riot API Test",
                    fetch_riot=True,  # Enable Riot API fetching
                    region="na",
                    source="riot_api",
                    snapshot_override=snapshot_override,
                )

        # Verify tournament metadata
        assert snapshot.tournament_id == "riot_test"
        assert snapshot.tournament_name == "Riot API Test"
        assert snapshot.source == "riot_api"
        assert snapshot.round_names == ["round_1"]  # Auto-generated from Riot data

        # Verify entries were created with Riot data
        assert len(snapshot.entries) == 2

        # Alice should have 8 points (1st placement from mock data)
        alice = next(e for e in snapshot.entries if e.player_name == "Alice")
        assert alice.total_points == 8
        assert alice.round_scores == {"round_1": 8}
        assert alice.riot_id == "Alice#NA1"

        # Bob should have 4 points (5th placement from mock data)
        bob = next(e for e in snapshot.entries if e.player_name == "Bob")
        assert bob.total_points == 4
        assert bob.round_scores == {"round_1": 4}
        assert bob.riot_id == "Bob#NA1"

    finally:
        session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_refresh_scoreboard_mixed_riot_and_sheet_data() -> None:
    """Test mixing pre-existing sheet scores with new Riot API data."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session: Session = SessionLocal()
    try:
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)

        # Player with pre-existing round 1 score, getting round 2 from Riot
        snapshot_override = {
            "mode": "normal",
            "metadata": {"source": "test"},
            "standings": [
                {
                    "player_name": "Returning Player",
                    "ign": "Alice#NA1",
                    "discord_tag": "alice#0001",
                    "points": 10,  # From round 1
                    "round_scores": {"round_1": 10},  # Pre-existing score
                    "sheet_row": "5",
                },
            ],
        }

        with patch('api.services.standings_aggregator.RiotAPI'):
            from api.services.mock_riot_api import MockRiotAPI
            with patch('integrations.riot_api.RiotAPI', MockRiotAPI):
                snapshot = await aggregator.refresh_scoreboard(
                    guild_id=123,
                    tournament_id="mixed_test",
                    tournament_name="Mixed Data Test",
                    fetch_riot=True,
                    region="na",
                    round_names=["round_1", "round_2"],  # Specify existing round
                    source="mixed",
                    snapshot_override=snapshot_override,
                )

        # Verify scores were merged
        assert len(snapshot.entries) == 1
        entry = snapshot.entries[0]
        
        # Should have both pre-existing and new Riot data
        assert entry.round_scores == {
            "round_1": 10,  # Pre-existing from sheet
            "round_2": 8,   # New from Riot API (Alice's 1st placement)
        }
        
        # Total should be sum of both rounds
        assert entry.total_points == 18  # 10 + 8

    finally:
        session.close()
        engine.dispose()
