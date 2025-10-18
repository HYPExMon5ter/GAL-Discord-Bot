import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

# Ensure deterministic master password for auth.
os.environ["DASHBOARD_MASTER_PASSWORD"] = "test-secret"

from api.main import app  # type: ignore  # pylint: disable=wrong-import-position
from api.dependencies import SessionLocal  # type: ignore  # noqa: E402
from api.schemas.scoreboard import (  # type: ignore  # noqa: E402
    ScoreboardEntryCreate,
    ScoreboardSnapshotCreate,
)
from api.services.standings_service import StandingsService  # type: ignore  # noqa: E402

client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"master_password": "test-secret"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _build_snapshot_payload() -> ScoreboardSnapshotCreate:
    now = datetime.now(timezone.utc)
    return ScoreboardSnapshotCreate(
        tournament_id="router_test",
        tournament_name="Router Test",
        guild_id="4242",
        source="manual",
        source_timestamp=now,
        round_names=["round_1", "round_2"],
        extras={"test": True},
        entries=[
            ScoreboardEntryCreate(
                player_name="Alice",
                player_id="1",
                discord_id="Alice#0001",
                riot_id="Alice#NA1",
                standing_rank=1,
                total_points=10,
                round_scores={"round_1": 6, "round_2": 4},
                extras=None,
            ),
            ScoreboardEntryCreate(
                player_name="Bob",
                player_id="2",
                discord_id="Bob#0002",
                riot_id="Bob#NA1",
                standing_rank=2,
                total_points=6,
                round_scores={"round_1": 2, "round_2": 4},
                extras=None,
            ),
        ],
    )


@pytest.fixture()
def seeded_snapshot() -> int:
    session = SessionLocal()
    try:
        service = StandingsService(session)
        payload = _build_snapshot_payload()
        snapshot = service.create_snapshot(payload, replace_existing=True)
        return snapshot.id
    finally:
        session.close()


def test_get_latest_scoreboard(seeded_snapshot: int) -> None:
    headers = _auth_headers()
    response = client.get(
        "/api/v1/scoreboard/latest",
        params={"tournament_id": "router_test"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tournament_id"] == "router_test"
    assert data["entries"][0]["player_name"] == "Alice"
    assert "ETag" in response.headers
    assert "Last-Modified" in response.headers


def test_list_snapshots(seeded_snapshot: int) -> None:
    headers = _auth_headers()
    response = client.get("/api/v1/scoreboard/snapshots?limit=5", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["tournament_id"] == "router_test"
    assert body[0]["entry_count"] == 2


def test_get_snapshot_by_id(seeded_snapshot: int) -> None:
    headers = _auth_headers()
    response = client.get(f"/api/v1/scoreboard/{seeded_snapshot}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == seeded_snapshot
    assert payload["entries"][1]["player_name"] == "Bob"

