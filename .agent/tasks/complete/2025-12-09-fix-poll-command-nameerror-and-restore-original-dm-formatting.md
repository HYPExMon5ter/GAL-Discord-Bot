# Fix Plan: Poll Command NameError and DM Formatting Issues

## Problems Identified

### 1. NameError: `elapsed` is not defined
**Error Location**: `core/commands/poll.py` line 88
```python
total_time = elapsed  # ❌ elapsed is only available in update_progress callback
```

**Root Cause**: 
- `elapsed` is a parameter in the `update_progress` callback function
- It's being accessed outside of that function's scope
- Need to track the elapsed time at the command level

### 2. DM Formatting Does Not Match Original

**Original Format** (from screenshot):
```
🌟 Hello Angel!

We need your input! 🗳️

📋 Poll Details
Please take a moment to vote on when you'd like our next Guardian Angel League 
tournament to be held. Your schedule matters, and we want to pick the best time 
for everyone! 🏆

🔗 How to vote:
Click the "Go to Poll" button below to access the voting form. It only takes a 
few seconds! 😊

💙 Thank you for helping make GAL tournaments even better!
```

**Current Format** (from screenshot):
- Missing proper section headers (📋 Poll Details)
- Incorrect markdown formatting (using ### which Discord doesn't support in embeds)
- Missing visual separation between sections
- Footer appears as subtext instead of proper footer

## Solutions

### Solution 1: Fix NameError

**Update `core/commands/poll.py`:**

Add a variable to track elapsed time at command level:

```python
# Track elapsed time for final summary
final_elapsed_time = 0

# Progress callback function
async def update_progress(embed, current, total, elapsed):
    nonlocal final_elapsed_time  # ✅ Use nonlocal to update outer scope
    final_elapsed_time = elapsed  # Track the elapsed time
    try:
        await progress_message.edit(embed=embed)
    except discord.NotFound:
        logger.warning("Progress message was deleted")
    except discord.HTTPException as e:
        logger.warning(f"Failed to update progress message: {e}")

# Send DMs to all Angels
success_count, failed_count, failed_users = await notifier.send_to_all_angels(update_progress)

# Create final summary using tracked time
summary_embed = notifier.create_summary_embed(final_elapsed_time)  # ✅ Use tracked variable
```

### Solution 2: Fix DM Formatting

**Update `config.yaml` poll section:**

Remove markdown formatting (###, #, -#) and use proper embed structure:

```yaml
poll:
  dm_embed:
    title: "🌟 Hello Angel!"  # Remove # markdown
    color: "#f8c8dc"
    
    header: "We need your input! 🗳️"  # Remove ### markdown
    
    body: |
      Please take a moment to vote on when you'd like our next **Guardian Angel League** tournament to be held. Your schedule matters, and we want to pick the best time for everyone! 🏆
    
    how_to_vote:
      title: "🔗 How to vote:"  # Remove ### markdown
      content: "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊"  # Use 😊 emoji
    
    footer: "💙 Thank you for helping make GAL tournaments even better!"  # Remove -# markdown
    
    button:
      label: "🗳️ Go to Poll"  # Use 🗳️ emoji
```

**Update `helpers/poll_helpers.py` create_dm_embed():**

Ensure the embed structure matches original with proper field names:

```python
def create_dm_embed(self) -> discord.Embed:
    """Create the DM embed for poll notification."""
    dm_config = self.config.get("dm_embed", {})
    
    # Override with custom message if provided
    if self.custom_message:
        embed = discord.Embed(
            title=dm_config.get("title", "🌟 Hello Angel!"),
            description=self.custom_message,
            color=int(dm_config.get("color", "#f8c8dc").replace("#", ""), 16)
        )
    else:
        embed = discord.Embed(
            title=dm_config.get("title", "🌟 Hello Angel!"),
            color=int(dm_config.get("color", "#f8c8dc").replace("#", ""), 16)
        )
        
        # Add header as description
        header = dm_config.get("header", "We need your input! 🗳️")
        embed.description = header
        
        # Add body as "📋 Poll Details" field (not just body)
        body = dm_config.get("body", "")
        if body:
            embed.add_field(
                name="📋 Poll Details",  # ✅ Keep this header
                value=body,
                inline=False
            )
        
        # Add how to vote section with proper emoji
        how_to_vote = dm_config.get("how_to_vote", {})
        if how_to_vote:
            embed.add_field(
                name=how_to_vote.get("title", "🔗 How to vote:"),  # ✅ Keep emoji
                value=how_to_vote.get("content", "Click the **\"Go to Poll\"** button below to access the voting form."),
                inline=False
            )
    
    # Add footer (this creates proper footer text at bottom)
    footer = dm_config.get("footer", "💙 Thank you for helping make GAL tournaments even better!")
    embed.set_footer(text=footer)
    
    # Add timestamp
    embed.timestamp = datetime.utcnow()
    
    return embed
```

## Implementation Steps

1. **Fix NameError in `core/commands/poll.py`:**
   - Add `final_elapsed_time = 0` before progress callback
   - Use `nonlocal final_elapsed_time` inside callback
   - Update `final_elapsed_time = elapsed` in callback
   - Change line 88 to use `final_elapsed_time` instead of `elapsed`

2. **Fix Config Formatting in `config.yaml`:**
   - Remove `#` markdown from title
   - Remove `###` markdown from header and how_to_vote title
   - Remove `-#` markdown from footer
   - Change emoji from 📊 to 🗳️ in button label
   - Change emoji from ⏱️ to 😊 in how_to_vote content

3. **Verify Embed Creation (no changes needed to `helpers/poll_helpers.py`):**
   - Current implementation already adds "📋 Poll Details" field name
   - Already uses proper footer
   - Just need config.yaml fixes

## Expected Results

### After Fix 1 (NameError):
✅ No more `NameError: name 'elapsed' is not defined`
✅ Final summary shows correct elapsed time
✅ Progress tracking works correctly

### After Fix 2 (Formatting):
✅ Title: "🌟 Hello Angel!" (clean, no markdown)
✅ Description: "We need your input! 🗳️" (clean header)
✅ Field 1: "📋 Poll Details" with body text
✅ Field 2: "🔗 How to vote:" with instructions
✅ Footer: "💙 Thank you for helping make GAL tournaments even better!" (proper footer)
✅ Button: "🗳️ Go to Poll" (proper emoji)
✅ Proper spacing between sections (automatic with fields)

## Files to Modify

1. `core/commands/poll.py` - Fix elapsed variable scope
2. `config.yaml` - Remove markdown formatting, fix emojis

## Testing

1. Run `/gal poll <link>` - should not error
2. Check DM received by Angels - should match original formatting
3. Verify progress tracking works
4. Verify final summary shows correct time