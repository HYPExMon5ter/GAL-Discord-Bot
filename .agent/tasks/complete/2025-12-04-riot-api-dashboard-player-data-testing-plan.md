## Testing Plan: Dashboard Player Data & Riot API Placements

### System Overview
The data flow is:
1. **Google Sheets** → `sheet_integration.py::build_event_snapshot()` → Player data (IGN, Discord, team, etc.)
2. **Riot API** → `riot_api.py::get_latest_placement()` → Placement data from TFT matches
3. **Aggregator** → `standings_aggregator.py::refresh_scoreboard()` → Combines sheet + Riot data into scoreboard snapshots
4. **Dashboard API** → `/api/v1/scoreboard/*` endpoints → Frontend consumption

---

### Testing Strategy (No Live Tournament Required)

#### 1. **Unit Tests with Mock Riot API Responses**
Create test fixtures that mock Riot API responses:
```python
# Mock data for RiotAPI methods
MOCK_ACCOUNT_DATA = {"puuid": "test-puuid-123", "gameName": "TestPlayer", "tagLine": "NA1"}
MOCK_MATCH_HISTORY = ["NA1_1234567890"]
MOCK_MATCH_DETAILS = {
    "info": {
        "game_datetime": 1701648000000,
        "game_length": 1800,
        "game_version": "13.24",
        "participants": [
            {"puuid": "test-puuid-123", "placement": 3},
            # ... other participants
        ]
    }
}
```

**Test cases:**
- `test_get_latest_placement_success` - Valid Riot ID returns correct placement
- `test_get_latest_placement_no_matches` - Player has no recent games
- `test_get_latest_placement_invalid_riot_id` - 404 handling
- `test_get_placements_batch_mixed_results` - Batch with some successes/failures
- `test_placement_to_points_conversion` - Verify 1st→8pts, 2nd→7pts, etc.

#### 2. **Integration Tests with Snapshot Override**
Use the existing `snapshot_override` parameter (already in your tests):
```python
snapshot_override = {
    "standings": [
        {"player_name": "Player1", "ign": "Player1#NA1", "discord_tag": "Player1#0001", "points": 0},
        {"player_name": "Player2", "ign": "Player2#NA1", "discord_tag": "Player2#0002", "points": 0},
    ]
}

# Test with fetch_riot=True but mocked Riot client
snapshot = await aggregator.refresh_scoreboard(
    guild_id=123,
    fetch_riot=True,
    snapshot_override=snapshot_override,
)
```

#### 3. **Mock Riot API Service for E2E Testing**
Create a `MockRiotAPI` class that returns deterministic data:
```python
class MockRiotAPI:
    """Deterministic Riot API for testing without live API calls."""
    
    PLACEMENT_MAP = {
        "TestPlayer1#NA1": 1,
        "TestPlayer2#NA1": 4,
        "TestPlayer3#NA1": 8,
    }
    
    async def get_latest_placement(self, region, riot_id):
        placement = self.PLACEMENT_MAP.get(riot_id, 5)
        return {"success": True, "placement": placement, ...}
```

#### 4. **API Endpoint Tests**
Test the `/api/v1/scoreboard/refresh` endpoint:
```python
def test_refresh_scoreboard_with_riot_data():
    # Patch RiotAPI with mock
    with patch('api.services.standings_aggregator.RiotAPI', MockRiotAPI):
        response = client.post("/api/v1/scoreboard/refresh", json={
            "guild_id": 123,
            "fetch_riot": True,
            "sync_sheet": False,  # Skip live sheet fetch
        })
        assert response.status_code == 200
        assert response.json()["entries"][0]["total_points"] > 0
```

---

### Key Verification Points

| Component | What to Verify |
|-----------|----------------|
| `RiotAPI.get_latest_placement()` | Returns correct placement from match details |
| `RiotAPI._parse_riot_id()` | Handles `Name#Tag` and `Name` formats |
| `StandingsAggregator._fetch_riot_round_scores()` | Converts placements to points (1st=8, 8th=1) |
| `StandingsAggregator.refresh_scoreboard()` | Merges sheet + Riot data correctly |
| `/scoreboard/latest` | Returns correct player standings with riot_id |
| `/players/ranked` | Returns sorted players with round_scores |

---

### Implementation Steps

1. **Add `tests/test_riot_api.py`** - Unit tests for `RiotAPI` class with mocked HTTP responses
2. **Add `tests/test_standings_integration.py`** - Integration tests combining sheet + Riot data
3. **Extend `test_standings_aggregator.py`** - Add tests with `fetch_riot=True` using mocked client
4. **Create `api/services/mock_riot_api.py`** - Reusable mock for development/testing

Would you like me to implement this testing plan?