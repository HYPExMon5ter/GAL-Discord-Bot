import asyncio

import pytest
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
