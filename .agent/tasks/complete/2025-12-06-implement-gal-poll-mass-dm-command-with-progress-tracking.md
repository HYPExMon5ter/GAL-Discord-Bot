# Implementation Plan: /gal poll Mass DM Command

## Overview
Implement `/gal poll <link>` command that sends a customizable DM to all users with the "Angels" role, with batch processing, rate limiting, progress tracking, and success/failure reporting.

## Command Functionality

### Command Structure
```bash
/gal poll <link> [custom_message_override]
```

### Core Features
1. **Mass DM System**: Send DMs to all users with "Angels" role
2. **Batch Processing**: Handle hundreds of users without Discord rate limits
3. **Progress Tracking**: Real-time ephemeral message updates with progress
4. **Success/Failure Reporting**: Detailed summary of DM delivery results
5. **Customizable Message**: Config-based DM content with embed support
6. **"Go to Poll" Button**: Discord button that links to the poll message

## Implementation Details

### 1. Command Handler (`core/commands/poll.py` - NEW)

```python
@gal.command(name="poll", description="Send poll notification to all Angels")
@app_commands.describe(
    link="Link to the Discord poll message",
    custom_message="Optional custom message override"
)
async def poll_notify(
    interaction: discord.Interaction,
    link: str,
    custom_message: str = None
):
    """
    Send poll DM to all Angels with progress tracking.
    
    Process:
    1. Defer response (ephemeral)
    2. Validate link format
    3. Get all members with Angels role
    4. Send DMs in batches with rate limiting
    5. Update progress message continuously
    6. Show final summary with stats
    """
```

### 2. Mass DM System (`helpers/poll_helpers.py` - NEW)

**Key Components:**

**PollNotifier Class:**
```python
class PollNotifier:
    def __init__(self, guild, poll_link, custom_message=None):
        self.guild = guild
        self.poll_link = poll_link
        self.custom_message = custom_message
        self.success_count = 0
        self.failed_count = 0
        self.failed_users = []
        
    async def send_to_all_angels(self, progress_callback):
        """
        Send DMs to all Angels with progress tracking.
        
        Features:
        - Batch processing (10 users per batch)
        - Rate limiting (1 second between batches)
        - Progress callbacks for UI updates
        - Failure tracking with user mentions
        """
```

**Batch Processing:**
- Process 10 users per batch
- 1-second delay between batches (Discord safety)
- Asyncio.gather for concurrent sends within batch
- Retry logic for transient failures

**Rate Limiting:**
- Built-in delays to avoid Discord rate limits
- Exponential backoff for errors
- Safe for 100-500+ users

### 3. DM Embed Configuration

**config.yaml (MODIFY):**
```yaml
# Poll notification system
poll:
  # DM embed configuration
  dm_embed:
    title: "🌟 Hello Angel!"
    color: "#f8c8dc"  # GAL pink
    
    # Message sections
    header: "We need your input! 🗳️"
    
    body: |
      Please take a moment to vote on when you'd like our next **Guardian Angel League** tournament to be held. Your schedule matters, and we want to pick the best time for everyone! 🏆
    
    how_to_vote:
      title: "🔗 How to vote:"
      content: "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊"
    
    footer: "💙 Thank you for helping make GAL tournaments even better!"
    
    # Button configuration
    button:
      label: "🗳️ Go to Poll"
      emoji: "🗳️"
  
  # Role to send DMs to
  target_role: "Angels"
  
  # Batch processing settings
  batch_size: 10  # Users per batch
  batch_delay: 1.0  # Seconds between batches
  
  # Progress update frequency
  progress_update_interval: 5  # Update every N users
```

### 4. Progress Tracking System

**Ephemeral Progress Message:**
```
📨 Sending Poll Notifications

⏳ Progress: 45/150 (30%)
[▰▰▰▱▱▱▱▱▱▱] 30%

✅ Successful: 42
❌ Failed: 3
⏱️ Elapsed: 12s

Estimated time remaining: 28s
```

**Update Strategy:**
- Update every 5 users (configurable)
- Update every 2 seconds minimum
- Show progress bar, percentages, counts
- Real-time elapsed time
- Estimated time remaining

**Final Summary:**
```
✅ Poll Notifications Sent!

📊 Results:
✅ Successful: 142
❌ Failed: 8

Failed users:
• @User1 (DMs disabled)
• @User2 (Privacy settings)
• @User3 (Not found)
... (showing 3 of 8)

⏱️ Total time: 47 seconds

Note: Users who failed will not receive the notification. Please reach out to them manually if needed.
```

### 5. DM View with Button

**PollDMView Class:**
```python
class PollDMView(discord.ui.View):
    def __init__(self, poll_link: str):
        super().__init__(timeout=None)
        # Add URL button
        self.add_item(discord.ui.Button(
            label="🗳️ Go to Poll",
            url=poll_link,
            style=discord.ButtonStyle.link
        ))
```

### 6. Error Handling

**DM Failure Reasons:**
- `discord.Forbidden`: User has DMs disabled or blocked bot
- `discord.HTTPException`: Network/API errors
- `discord.NotFound`: User no longer in server

**Failure Tracking:**
- Store failed user mentions
- Log failure reasons
- Display summary in final message
- Truncate list if >10 failures (show "... and N more")

### 7. Security & Permissions

**Permission Checks:**
- Staff only (uses existing `allowed_roles` from config)
- Validates poll link format (Discord message links only)
- Confirms Angels role exists

**Link Validation:**
```python
def validate_discord_link(link: str) -> bool:
    """
    Validate Discord message link format:
    https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
    """
    pattern = r"https://discord\.com/channels/\d+/\d+/\d+"
    return bool(re.match(pattern, link))
```

## Implementation Steps

1. **Create `helpers/poll_helpers.py`:**
   - PollNotifier class with batch processing
   - PollDMView class for button
   - Progress tracking utilities
   - Link validation

2. **Create `core/commands/poll.py`:**
   - `/gal poll` slash command
   - Permission checks
   - Progress message management
   - Integration with PollNotifier

3. **Update `core/commands/__init__.py`:**
   - Register poll command module

4. **Update `config.yaml`:**
   - Add poll DM configuration section
   - Embed customization options
   - Batch processing settings

5. **Update help documentation:**
   - Add poll command to help embed

## Performance Characteristics

**For 150 Angels:**
- Batch size: 10 users
- Batches: 15 batches
- Delay per batch: 1 second
- Total time: ~15-20 seconds

**For 500 Angels:**
- Batch size: 10 users
- Batches: 50 batches
- Delay per batch: 1 second
- Total time: ~50-60 seconds

**Discord Rate Limits:**
- Current approach: ~10 DMs/second
- Discord limit: ~5-10 DMs/second per bot
- Safe margin maintained

## Files to Create/Modify

- `core/commands/poll.py` (NEW) - Command implementation
- `helpers/poll_helpers.py` (NEW) - Mass DM and progress tracking
- `core/commands/__init__.py` (MODIFY) - Register poll command
- `config.yaml` (MODIFY) - Add poll DM configuration

## Testing Considerations

1. Test with small group (5-10 users) first
2. Verify rate limiting doesn't trigger Discord warnings
3. Test with users who have DMs disabled
4. Verify progress updates work correctly
5. Test link validation with various formats
6. Confirm final summary displays correctly

## Key Benefits

✅ **Scalable**: Handles hundreds of users safely
✅ **User-Friendly**: Real-time progress tracking
✅ **Configurable**: Easy DM customization via config
✅ **Reliable**: Comprehensive error handling
✅ **Informative**: Detailed success/failure reporting
✅ **Safe**: Rate-limited to avoid Discord restrictions