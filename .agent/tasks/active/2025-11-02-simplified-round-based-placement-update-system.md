# Simplified Round-Based Placement Update System

## Overview
Replace existing `standings_refresh` and `placement` commands with a single streamlined `/gal updateplacements <round>` command that:
1. Fetches all player placements from Riot API for ALL lobbies in the specified round
2. Updates the Google Sheets "Lobbies" tab with placements
3. Triggers live graphics dashboard updates via WebSocket
4. Sends ephemeral confirmation message

**Simplified Design**:
- **Required**: `round` parameter only (1, 2, 3, 4, or finals)
- **Optional**: `preview` parameter (default: False)
  - If `preview=True`: Show what would be updated without making changes
  - If `preview=False` or not specified: Update sheet + dashboard, send confirmation

## Commands to Remove

1. **`/gal placement`** (`core/commands/utility.py:placement_cmd`) - Single player lookup
2. **`standings_refresh` functionality** (`core/commands/registration.py:_refresh_scoreboard_snapshot`) - Complex database system

## Implementation Plan

### Phase 1: Remove Old Commands
**Files to Modify**: `core/commands/utility.py`, `core/commands/registration.py`

**Changes**:
- Delete `placement_cmd` function and command registration
- Delete `_refresh_scoreboard_snapshot()` helper function
- Delete `_format_standings_summary()` helper function
- Clean up unused imports

**Commit**: "refactor: remove legacy placement and standings_refresh commands"

---

### Phase 2: Lobbies Tab Manager
**Files to Create**: `integrations/lobby_manager.py`

**Core Functionality**:
```python
@dataclass
class LobbyStructure:
    lobbies: Dict[str, LobbyInfo]  # {"Lobby A": LobbyInfo(...), ...}
    rounds: List[str]  # ["Round 1", "Round 2", ...]

@dataclass
class LobbyInfo:
    name: str  # "Lobby A"
    start_row: int
    players: List[PlayerPosition]
    round_columns: Dict[str, str]  # {"Round 1": "C", "Round 2": "D"}

@dataclass
class PlayerPosition:
    ign: str
    riot_id: str
    row_number: int
    lobby: str

class LobbyManager:
    async def detect_structure(guild_id: str) -> LobbyStructure:
        """Detect lobbies tab layout and player positions."""
        
    async def get_players_for_round(guild_id: str, round: str) -> List[PlayerPosition]:
        """Get all players across all lobbies for a specific round."""
        
    async def update_placements_batch(
        guild_id: str, 
        round: str, 
        placements: Dict[str, int]  # {riot_id: placement}
    ) -> BatchResult:
        """Update placements for all players in specified round."""
```

**Detection Algorithm**:
1. Open "Lobbies" worksheet
2. Find lobby headers ("Lobby A:", "Lobby B:", etc.)
3. Extract players under each lobby (until next lobby or empty rows)
4. Find round columns in header row
5. Build complete mapping

**Commit**: "feat: add lobby manager with structure detection"

---

### Phase 3: Batch Riot API Enhancement
**Files to Modify**: `integrations/riot_api.py`

**New Methods**:
```python
class RiotAPI:
    async def get_placements_batch(
        self,
        riot_ids: List[str],
        region: str = "na"
    ) -> Dict[str, PlacementResult]:
        """
        Fetch placements for multiple players.
        Uses existing rate limiting (semaphore).
        Returns partial results on failures.
        """

@dataclass
class PlacementResult:
    riot_id: str
    placement: int
    success: bool
    error: Optional[str] = None
```

**Strategy**:
- Use existing `_semaphore` for concurrency (already configured)
- Process in batches with 1s delay
- Continue on individual player failures
- Return dict mapping riot_id to result

**Commit**: "feat: add batch placement fetching to Riot API"

---

### Phase 4: Simplified Discord Command
**Files to Create**: `core/commands/placement.py`

**Command Signature**:
```python
@gal.command(
    name="updateplacements",
    description="Update player placements for a specific round from Riot API"
)
@app_commands.describe(
    round="Which round to update (1, 2, 3, 4, or finals)",
    preview="Preview changes without updating (optional, default: False)"
)
@app_commands.choices(
    round=[
        app_commands.Choice(name="Round 1", value="1"),
        app_commands.Choice(name="Round 2", value="2"),
        app_commands.Choice(name="Round 3", value="3"),
        app_commands.Choice(name="Round 4", value="4"),
        app_commands.Choice(name="Finals", value="finals"),
    ]
)
async def updateplacements_cmd(
    interaction: discord.Interaction,
    round: str,
    preview: bool = False
):
    """Update all lobby placements for the specified round."""
```

**Workflow**:

**If `preview=True`**:
1. Defer with ephemeral response
2. Detect lobby structure
3. Get all players for the round
4. Fetch placements from Riot API
5. Display preview embed showing what would be updated
6. No sheet updates, no dashboard updates

**If `preview=False` (default)**:
1. Defer with ephemeral response
2. Detect lobby structure
3. Get all players for the round
4. Fetch placements from Riot API
5. Update Google Sheets "Lobbies" tab
6. Trigger live dashboard WebSocket update
7. Send simple confirmation embed

**Confirmation Embed** (preview=False):
```
✅ Placements Updated - Round 1

📊 Successfully updated 20/24 players

⚠️ Failed: 4 players
- Player1#NA1: No recent games
- Player2#NA1: Summoner not found  
- Player3#NA1: Summoner not found
- Player4#NA1: Rate limited (retry in 30s)

✅ Live dashboard updated
```

**Preview Embed** (preview=True):
```
👁️ Preview: Round 1 Placement Updates

The following changes would be made:

Lobby A:
  Player1 → 1st place
  Player2 → 5th place
  Player3 → 3rd place
  ...

Lobby B:
  Player5 → 2nd place
  ...

Lobby C:
  ...

Lobby D:
  ...

⚠️ 4 players would fail (see details above)

Run without preview=True to apply changes.
```

**Error Handling**:
- Staff permission check
- Lobbies tab existence
- Round validation
- Graceful handling of missing players
- Partial success reporting

**Commit**: "feat: implement simplified /gal updateplacements command"

---

### Phase 5: Live Dashboard Integration
**Files to Modify**: `api/routers/websocket.py`

**New Broadcast Function**:
```python
async def send_placement_update(round_name: str):
    """
    Notify dashboard clients that placements were updated.
    Dashboard should refresh standings data.
    """
    await manager.broadcast({
        "type": "placement_update",
        "data": {
            "round": round_name,
            "action": "refresh",
            "timestamp": utcnow().isoformat(),
        }
    })
```

**Integration**:
In `core/commands/placement.py`, after successful sheet update:
```python
from api.routers.websocket import send_placement_update

# After sheet update succeeds
await send_placement_update(round_name)
```

**Dashboard Frontend** (reference only - may already exist):
- WebSocket handler listens for `placement_update` type
- Refreshes standings/scoreboard UI
- Shows toast: "Round X placements updated"

**Commit**: "feat: integrate placement updates with live dashboard"

---

### Phase 6: Error Handling & Polish
**Files to Modify**: All command files

**Validation**:
- Staff-only command (use `@ensure_staff`)
- Verify Lobbies tab exists
- Verify round exists in detected structure
- Validate placement values (1-8 range)

**User-Friendly Messages**:
- "Lobbies tab not found in Google Sheet"
- "Round X not found (available: 1-4, finals)"  
- "No players found for Round X"
- "Riot API temporarily unavailable - please try again"

**Partial Failure Handling**:
```python
@dataclass
class BatchResult:
    successful: int
    failed: List[FailedPlayer]
    total: int

@dataclass
class FailedPlayer:
    ign: str
    riot_id: str
    reason: str
```

**Commit**: "feat: add error handling and validation"

---

### Phase 7: Testing & Documentation
**Files to Create**:
- `tests/test_lobby_manager.py`
- `tests/test_placement_command.py`
- `.agent/sops/updateplacements-command.md` (user guide)

**Test Coverage**:
- Lobby structure detection
- Player extraction
- Batch API calls
- Sheet updates
- Error scenarios

**User Documentation**:
```markdown
# /gal updateplacements Command

## Usage

Update all lobbies for a specific round:
/gal updateplacements round:1

Preview changes without updating:
/gal updateplacements round:2 preview:True

## Parameters

- **round** (required): 1, 2, 3, 4, or finals
- **preview** (optional): True to preview, False or omitted to update

## Behavior

When preview=False (default):
1. Fetches placements from Riot API
2. Updates Google Sheets Lobbies tab
3. Updates live graphics dashboard
4. Shows confirmation message

When preview=True:
1. Fetches placements from Riot API
2. Shows what would be updated
3. Does NOT update sheets or dashboard
```

**Commit**: "docs: add testing and documentation for placement system"

---

## Data Flow (Simplified)

```
/gal updateplacements round:1
           ↓
[Check preview parameter]
           ↓
[Detect Lobbies tab structure]
           ↓
[Get ALL players in Round 1 across ALL lobbies]
           ↓
[Fetch placements from Riot API - batch with rate limiting]
           ↓
    ┌─────┴─────┐
    ↓           ↓
preview=True  preview=False (default)
    ↓           ↓
[Show preview] [Update Google Sheets]
               ↓
           [Update live dashboard via WebSocket]
               ↓
           [Send confirmation embed (ephemeral)]
```

## Command Examples

```bash
# Standard usage - update all lobbies for Round 1
/gal updateplacements round:1

# Preview what would change in Round 2
/gal updateplacements round:2 preview:True

# Update Finals round
/gal updateplacements round:finals

# Preview Finals
/gal updateplacements round:finals preview:True
```

## Configuration

Add to `config.yaml`:
```yaml
placement_system:
  lobbies_sheet_name: "Lobbies"
  default_region: "na"  # Hardcoded for now
  batch_delay: 1.0  # Seconds between batches
  max_retries: 3
```

## Success Criteria

- [x] Simple command interface (round + preview only)
- [x] Updates all lobbies automatically for specified round
- [x] Default behavior updates sheet + dashboard
- [x] Preview mode shows changes without updating
- [x] Ephemeral confirmation messages
- [x] Graceful error handling
- [x] Live dashboard integration via WebSocket
- [x] Each phase committed separately

## Timeline

**7 commits total**, one per phase:
1. Remove old commands
2. Add lobby manager
3. Enhance Riot API
4. Implement command
5. Dashboard integration
6. Error handling
7. Tests + docs