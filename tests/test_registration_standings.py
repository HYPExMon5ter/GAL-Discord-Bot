from datetime import datetime, timezone

from api.schemas.scoreboard import ScoreboardEntry, ScoreboardSnapshot
from core.commands.registration import _format_standings_summary


def _entry(rank: int, name: str, total_points: int) -> ScoreboardEntry:
    return ScoreboardEntry(
        id=rank,
        snapshot_id=1,
        player_name=name,
        player_id=str(rank),
        discord_id=f"{name}#000{rank}",
        riot_id=f"{name}#NA1",
        standing_rank=rank,
        total_points=total_points,
        round_scores={"round_1": total_points},
        extras=None,
        created_at=datetime.now(timezone.utc),
    )


def test_format_standings_summary_includes_top_entries() -> None:
    snapshot = ScoreboardSnapshot(
        id=1,
        tournament_id="test",
        tournament_name="Test Event",
        guild_id="123",
        source="manual",
        source_timestamp=datetime.now(timezone.utc),
        round_names=["round_1", "round_2"],
        extras={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        entries=[
            _entry(1, "Alice", 8),
            _entry(2, "Bob", 6),
            _entry(3, "Charlie", 4),
        ],
    )

    summary = _format_standings_summary(
        snapshot,
        elapsed_seconds=1.23,
        fetch_riot=True,
        sheet_refresh=(2, 10),
    )

    assert "snapshot #1" in summary
    assert "Test Event" in summary
    assert "Rounds: round_1, round_2" in summary
    assert "Entries: 3" in summary
    assert "Sheet cache refresh: 2 updates across 10 rows" in summary
    assert "Riot data included" in summary
    assert "- #1 Alice — 8 pts" in summary
    assert "- #3 Charlie — 4 pts" in summary
