# Round Scoring System Usage Guide

This guide explains how to use the new round-based scoring system for Guardian Angel League tournaments.

## Overview

The round scoring system allows you to:
- Automatically detect round columns in your Google Sheet
- Apply scores for each player per round
- View current standings with round-by-round breakdown
- Manage scores through Discord commands
- Use a two-tab architecture for data management

## Two-Tab Architecture

### GAL Database Tab
The GAL Database tab is used for:
- **Player Registration**: User registration and profile information
- **Check-in Management**: Tournament check-in status tracking
- **User Cache**: Discord username mapping and player data
- **Player Information**: Names, pronouns, teams, and other user details

### Standings Tab
The standings tab is used for:
- **Score Storage**: Round scores and tournament totals
- **Rankings**: Automatic ranking calculations using formulas
- **Score Aggregation**: Total scores and performance metrics
- **Display Data**: Player standings and tournament progression

### How It Works
```
Discord Commands → GAL Database (player lookup) → Standings Tab (score updates)
```

1. **Player Lookup**: The system reads player information from GAL Database tab
2. **Row Mapping**: Maps players from GAL Database to corresponding rows in Standings tab
3. **Score Updates**: Writes round scores to the correct rows in Standings tab
4. **Formula Integration**: Standings tab formulas calculate totals and rankings automatically

## Google Sheet Setup

### Round Column Naming

The system automatically detects columns that follow these naming patterns:

**Standard Patterns:**
- `Round 1`, `Round 2`, `Round 3`, etc.
- `R1`, `R2`, `R3`, etc.
- `Round-1`, `Round-2`, etc.
- `Round_1`, `Round_2`, etc.

**Word-based Patterns:**
- `Round One`, `Round Two`, etc.
- `Stage 1`, `Stage 2`, etc.
- `Phase 1`, `Phase 2`, etc.
- `Week 1`, `Week 2`, etc.

**Score-related Patterns:**
- `Score Round 1`, `Round 1 Score`
- `Points Round 1`, `Round 1 Points`

### Sheet Structure Example

```
| A          | B     | C         | D   | E        | F | G | H      | I     | J     | K    |
|------------|-------|-----------|-----|----------|---|---|--------|-------|-------|------|
| Discord    | IGN   | Pronouns  | Alt | Status   | CI| Team| Round 1| Round 2| Total| Rank |
| User#1234  | Player1| they/them|     | TRUE     |   |     | 8      | 6     |      |      |
| User#5678  | Player2| she/her  |     | TRUE     |   |     | 4      | 7     |      |      |
```

## Discord Commands

### `/rounds` Command

The main command for managing round scores.

#### List Available Rounds
```
/rounds action:List Available Rounds
```
Shows all detected round columns in your sheet.

#### Show Round Scores
```
/rounds action:Show Round Scores round_name:"round_1"
```
Displays current scores for a specific round, sorted by rank.

#### Apply Player Score
```
/rounds action:Apply Player Score round_name:"round_1" player:"User#1234" score:8
```
Applies a score for a specific player in a specific round.

#### Clear Round Scores
```
/rounds action:Clear Round Scores round_name:"round_1"
```
Clears all scores for a specific round (requires confirmation).

## API Usage

### Programmatic Score Management

```python
from integrations.sheets import (
    apply_round_scores,
    get_round_scores,
    list_available_rounds,
    clear_round_scores
)

# List available rounds
rounds = await list_available_rounds(guild_id)

# Get scores for a specific round
scores = await get_round_scores(guild_id, "round_1")

# Apply scores to multiple players
success_count, errors = await apply_round_scores(
    guild_id=guild_id,
    round_name="round_1",
    scores={
        "User#1234": 8,
        "User#5678": 6,
        "User#9012": 4
    }
)

# Clear all scores for a round
cleared_count, errors = await clear_round_scores(guild_id, "round_1")
```

### Standings Aggregation

The round scores are automatically included in standings aggregation:

```python
from api.services.standings_aggregator import StandingsAggregator
from integrations.sheet_integration import build_event_snapshot

# Build event snapshot with round scores
snapshot = await build_event_snapshot(guild_id)

# Refresh scoreboard (includes round scores)
aggregator = StandingsAggregator(standings_service)
snapshot = await aggregator.refresh_scoreboard(
    guild_id=guild_id,
    fetch_riot=False  # Use sheet scores only
)
```

## Integration with Existing Systems

### Dashboard Integration

The round scores are automatically displayed in:
- Live Graphics Dashboard
- Tournament standings views
- Player performance breakdowns

### Formula Support

Your Google Sheet can use formulas for automatic calculations:
- **Total Score**: `=SUM(I2:K2)` (sum of all round columns)
- **Ranking**: `=RANK(L2, L:L, 0)` (rank based on total score)
- **Average**: `=AVERAGE(I2:K2)` (average score across rounds)

## Best Practices

### 1. Consistent Naming
- Use consistent round column naming throughout your sheet
- Prefer simple patterns like "Round 1", "Round 2", etc.

### 2. Score Validation
- Scores should be integers (whole numbers)
- Empty cells are treated as 0
- Invalid values are ignored and set to 0

### 3. Regular Updates
- Refresh sheet cache after making changes: `/gal cache`
- Update scores immediately after matches complete
- Use dry-run mode for testing: `dry_run=True` in API calls

### 4. Backup Management
- Keep backup copies of your sheet before bulk changes
- Test new round columns in a copy first
- Document any custom scoring rules

## Troubleshooting

### Round Columns Not Detected
- Check column headers match the naming patterns
- Ensure the sheet is properly connected to the bot
- Refresh the sheet cache: `/gal cache`
- Verify column detection with: `/gal config`

### Scores Not Updating
- Check if the player is registered in the system
- Verify the round column exists and is spelled correctly
- Ensure the bot has write permissions to the sheet
- Check for sheet quota limits

### Standings Not Showing Scores
- Verify round scores are present in the sheet
- Refresh the standings: `/gal cache`
- Check the dashboard for real-time updates
- Verify the standings aggregation is running

### API Errors
- Check bot permissions to the Google Sheet
- Verify the guild ID is correct
- Check rate limits on Google Sheets API
- Ensure the bot is authenticated properly

## Examples

### Tournament Workflow

1. **Setup**: Create round columns in your Google Sheet
2. **Detect**: Use `/rounds list` to verify detection
3. **Score**: Apply scores after each round using `/rounds apply`
4. **Display**: Check standings automatically update
5. **Archive**: Total scores and ranks are calculated automatically

### Scoring Script Example

```python
import asyncio
from integrations.sheets import apply_round_scores

async def update_tournament_scores():
    # Example: Update scores for Round 3
    round_scores = {
        "Player#1234": 8,   # 1st place
        "Player#5678": 6,   # 2nd place  
        "Player#9012": 4,   # 3rd place
        "Player#3456": 2,   # 4th place
        # ... more players
    }
    
    success, errors = await apply_round_scores(
        guild_id="your_guild_id",
        round_name="round_3", 
        scores=round_scores
    )
    
    print(f"Updated {success} scores")
    if errors:
        print(f"Errors: {errors}")

# Run the update
asyncio.run(update_tournament_scores())
```

## Player Mapping System

The round scoring system includes an intelligent mapping system that connects players between the GAL Database and Standings tabs:

### Mapping Process
1. **Discord Tag Matching**: System matches players by Discord username (@User#1234 format)
2. **Flexible Column Detection**: Supports multiple column names (Discord, Player, Name, etc.)
3. **Automatic Row Detection**: Finds corresponding rows in each tab
4. **Fallback Logic**: Handles missing or mismatched players gracefully

### Supported Discord Column Names
The system automatically detects Discord usernames in any of these columns:
- `Discord` (recommended)
- `Player`
- `Name` 
- `discord` (case-insensitive)
- `player`
- `name`

### Example Mapping
```
GAL Database Tab        →  Standings Tab
| Discord    | IGN      |    | Player    | Round 1 | Round 2 | Total |
| User#1234  | Player1  | →  | User#1234 | 8       | 6       | =SUM  |
| User#5678  | Player2  | →  | User#5678 | 4       | 7       | =SUM  |
| User#9012  | Player3  | →  | User#9012 | 2       | 3       | =SUM  |
```

### Troubleshooting Mapping Issues

#### Players Not Found in Standings
**Symptom**: Error messages like "User not found in standings tab"

**Solutions**:
1. **Check Column Names**: Ensure Standings tab has Discord username column
2. **Verify Data Format**: Ensure usernames match format (User#1234)
3. **Remove @ Symbols**: System automatically strips @ from usernames
4. **Refresh Data**: Use `/gal cache` to refresh player data

#### Incorrect Row Mapping
**Symptom**: Scores applied to wrong players

**Solutions**:
1. **Check Row Order**: Ensure player order matches between tabs
2. **Verify Data Integrity**: Check for duplicate usernames
3. **Manual Verification**: Compare player lists between tabs

## Configuration Requirements

### Required Tab Structure
Your Google Sheet must have both tabs:

**GAL Database Tab:**
- Must contain player registration data
- Must have Discord username column
- Player rows must be numbered consistently

**Standings Tab:**
- Must have round score columns
- Must have matching Discord username column
- Should contain formulas for automatic calculations

### Column Configuration
```yaml
# config.yaml
sheet_configuration:
  # GAL Database Tab settings
  gal_database:
    header_line: 1
    discord_col: "A"  # Column with Discord usernames
    max_players: 32
    
  # Standings Tab settings  
  standings:
    header_line: 1
    round_columns: ["F", "G", "H"]  # Round score columns
    total_column: "I"              # Total score column
    rank_column: "J"               # Rank column
```

## Formula Integration

### Recommended Formulas for Standings Tab

#### Total Score Calculation
```excel
=SUM(F2:G2)  // Sum all round columns
```

#### Automatic Ranking
```excel
=RANK(I2, I:I, 0)  // Rank by total score (descending)
```

#### Average Score
```excel
=AVERAGE(F2:G2)  // Average score across rounds
```

#### Position Tracking
```excel
=ROW()-1  // Player position in standings
```

### Formula Best Practices
1. **Use Relative References**: Formulas should update when rows are added/removed
2. **Include Headers**: Adjust formulas to account for header rows
3. **Error Handling**: Use `IFERROR` for robust calculations
4. **Consistent Formatting**: Keep formula patterns consistent across columns

This system provides a comprehensive solution for managing round-based tournament scores with automatic detection, real-time updates, and seamless integration with existing Guardian Angel League functionality.
