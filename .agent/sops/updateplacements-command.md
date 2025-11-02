# /gal updateplacements Command

## Overview
The `/gal updateplacements` command fetches player placements from Riot API and updates the Google Sheets "Lobbies" tab with placement data for all players in a specified round.

## Usage

### Basic Usage
Update all lobbies for a specific round:
```
/gal updateplacements round:1
/gal updateplacements round:2
/gal updateplacements round:3
/gal updateplacements round:4
/gal updateplacements round:finals
```

### Preview Changes
Preview what would be updated without making changes:
```
/gal updateplacements round:2 preview:True
/gal updateplacements round:finals preview:True
```

## Parameters

- **round** (required): Which round to update
  - `1` - Round 1
  - `2` - Round 2
  - `3` - Round 3
  - `4` - Round 4
  - `finals` - Finals round

- **preview** (optional): Preview changes without updating
  - `True` - Show preview of what would be updated
  - `False` or omitted - Update Google Sheets and dashboard

## Workflow

When `preview=False` (default):
1. Detects lobby structure from Google Sheets
2. Gets all players in the specified round across all lobbies
3. Fetches placements from Riot API with rate limiting
4. Updates Google Sheets Lobbies tab with placements
5. Triggers live graphics dashboard update
6. Shows confirmation message with success/failure details

When `preview=True`:
1. Detects lobby structure from Google Sheets
2. Gets all players in the specified round
3. Fetches placements from Riot API
4. Shows preview of what would be updated
5. Does NOT update Google Sheets or dashboard

## Examples

### Standard Usage
```
/gal updateplacements round:1
```
This will:
- Get all players in Round 1 across Lobbies A, B, C, D
- Fetch their latest placements from Riot API
- Update placement columns in the Lobbies tab
- Refresh the live dashboard

### Preview Mode
```
/gal updateplacements round:3 preview:True
```
This will show you exactly what would be updated without making any changes.

## Error Handling

The command handles various error scenarios gracefully:

### Common Errors
- **Round not found**: `Round '5' not found. Available rounds: Round 1, Round 2, Round 3, Round 4, Finals`
- **No players found**: `No players found for Round 2`
- **Sheet access errors**: Various Google Sheets access issues
- **Riot API errors**: Rate limiting, player not found, network issues

### Partial Success
If some players fail to update, the command will:
- Show successful updates count
- List failed players with reasons
- Continue with other successful updates
- Still trigger dashboard update for successful placements

## Progress Indicators

The command provides real-time progress updates:
1. Detecting lobby structure...
2. Fetching placements from Riot API (0/24 complete)...
3. Updating Google Sheets...
4. Live dashboard updated

## Rate Limiting

The command respects Riot API rate limits:
- Processes players in batches of 10
- Adds 1-second delays between batches
- Shows progress during API calls
- Continues on individual player failures

## Live Dashboard Integration

When placements are successfully updated:
- Dashboard receives WebSocket notifications
- Standings data refreshes automatically
- Toast notifications show updates
- All connected clients see changes in real-time

## Requirements

- Must have staff permissions to use the command
- Google Sheets "Lobbies" tab must be accessible
- Lobbies tab must have proper structure with round columns
- Players must have valid Riot IDs in the sheet

## Troubleshooting

### Command Not Available
Ensure you have staff permissions and the bot is properly configured.

### Lobbies Tab Not Found
Check that the Google Sheet has a "Lobbies" tab and that the bot has access permissions.

### Round Not Detected
Verify the Lobbies tab has proper column headers (e.g., "Round 1", "Round 2", etc.).

### Players Not Found
Ensure players are listed in the correct lobby sections with valid Riot IDs.

### Dashboard Not Updating
Check WebSocket connections and that the dashboard is running when updates are made.
