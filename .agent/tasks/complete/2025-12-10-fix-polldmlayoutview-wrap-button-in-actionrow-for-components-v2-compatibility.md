# Fix Plan: Wrap Button in ActionRow for Components V2 Compatibility

## Root Cause Analysis

### The Error
```
400 Bad Request (error code: 50035): Invalid Form Body
In components.0.components.2: Value of field "type" must be one of (1, 9, 10, 12, 13, 14).
```

**Translation**: Discord is rejecting the Button at position 2 in the Container because:
- **Buttons cannot be direct children of Container**
- **Buttons MUST be wrapped in `discord.ui.ActionRow`** for LayoutView

### Proof from Working Code

**File**: `core/components_traditional.py` (lines 333-363)

```python
def _get_action_button_components(self) -> list:
    """Returns action button components as ActionRows for LayoutView."""
    row1_buttons = []
    row2_buttons = []
    
    # Add buttons to lists
    row1_buttons.append(LayoutRegisterButton(label="Register"))
    row2_buttons.append(LayoutViewPlayersButton())
    
    # ✅ CRITICAL: Wrap buttons in ActionRow!
    action_rows = []
    if row1_buttons:
        action_rows.append(discord.ui.ActionRow(*row1_buttons))  # ✅ Buttons in ActionRow
        action_rows.append(discord.ui.ActionRow(*row2_buttons))  # ✅ Buttons in ActionRow
    
    return action_rows
```

### Current Broken Pattern

**File**: `helpers/poll_helpers.py` (lines 66-87)

```python
# ❌ WRONG: Button added directly to Container
components.append(discord.ui.Button(
    label=button_label,
    url=self.poll_link,
    style=discord.ButtonStyle.link
))

return discord.ui.Container(*components)  # ❌ Discord rejects this!
```

## Solution: Wrap Button in ActionRow

### Updated Code Structure

**File**: `helpers/poll_helpers.py`

**Method**: `build_container()`

```python
def build_container(self) -> discord.ui.Container:
    """Build the poll DM container with Discord markdown support."""
    dm_config = self.config.get("dm_embed", {})
    
    # Extract config values with proper fallbacks
    title = dm_config.get("title", "# 🌟 Hello Angel!")
    header = dm_config.get("header", "### We need your input! 🗳️")
    body = dm_config.get("body", "")
    how_to_vote = dm_config.get("how_to_vote", {})
    how_to_vote_title = how_to_vote.get("title", "### 🔗 How to vote:")
    how_to_vote_content = how_to_vote.get("content", "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊")
    footer = dm_config.get("footer", "-# 💙 Thank you for helping make GAL tournaments even better!")
    button_config = dm_config.get("button", {})
    button_label = button_config.get("label", "🗳️ Go to Poll")
    
    # Build text content with proper spacing
    text_content = f"{title}\n\n"
    text_content += f"{header}\n\n"
    text_content += f"📋 **Poll Details**\n{body}\n\n"
    text_content += f"{how_to_vote_title}\n{how_to_vote_content}\n\n"
    text_content += footer
    
    # Build components list
    components = []
    
    # Add text component (supports Discord markdown!)
    components.append(discord.ui.TextDisplay(
        content=text_content
    ))
    
    # Add separator
    components.append(discord.ui.Separator(
        visible=True,
        spacing=discord.SeparatorSpacing.small
    ))
    
    # ✅ FIX: Wrap button in ActionRow!
    poll_button = discord.ui.Button(
        label=button_label,
        url=self.poll_link,
        style=discord.ButtonStyle.link
    )
    components.append(discord.ui.ActionRow(poll_button))  # ✅ Button wrapped in ActionRow
    
    # Return container with all components
    return discord.ui.Container(*components)
```

## Key Changes

### Before (BROKEN):
```python
# ❌ Direct button addition
components.append(discord.ui.Button(
    label=button_label,
    url=self.poll_link,
    style=discord.ButtonStyle.link
))
```

### After (FIXED):
```python
# ✅ Button wrapped in ActionRow
poll_button = discord.ui.Button(
    label=button_label,
    url=self.poll_link,
    style=discord.ButtonStyle.link
)
components.append(discord.ui.ActionRow(poll_button))  # ✅ Proper structure
```

## Component Hierarchy

### Correct LayoutView Structure:
```
LayoutView
└── Container
    ├── TextDisplay (markdown text)
    ├── Separator (visual spacing)
    └── ActionRow ✅ (REQUIRED wrapper for buttons!)
        └── Button (link to poll)
```

## Expected Results

### After Fix:

1. ✅ **No 50035 Errors**: Discord accepts the properly structured LayoutView
2. ✅ **DMs Sent Successfully**: Users receive poll notifications
3. ✅ **Markdown Support**: `#`, `###`, `-#` render correctly
4. ✅ **Button Works**: "Go to Poll" button links correctly
5. ✅ **Progress Tracking**: Success/failure counts work

### DM Appearance:
```
┌─────────────────────────────────────────────┐
# 🌟 Hello Angel!

### We need your input! 🗳️

📋 **Poll Details**
Please take a moment to vote on when you'd like our next 
**Guardian Angel League** tournament to be held.

### 🔗 How to vote:
Click the **"Go to Poll"** button below to access the voting 
form. It only takes a few seconds! 😊

-# 💙 Thank you for helping make GAL tournaments even better!

───────────────────────────────────────────────

[🗳️ Go to Poll]
```

## Files to Modify

**File**: `helpers/poll_helpers.py`

**Method**: `build_container()` (lines 44-87)

**Changes**:
- Wrap `discord.ui.Button` in `discord.ui.ActionRow`
- Maintain all existing text formatting and structure
- Keep separator before button for visual spacing

## Testing Steps

1. Run `/gal poll` command
2. Verify DM is sent without 400/50035 errors
3. Check markdown rendering in DM
4. Click button to verify poll link works
5. Verify progress tracking shows success

## Technical Details

### Discord Components V2 Requirements:

1. **TextDisplay**: Can be direct child of Container ✅
2. **Separator**: Can be direct child of Container ✅
3. **Button**: MUST be wrapped in ActionRow ✅
4. **ActionRow**: Can be direct child of Container ✅

### Component Type IDs (from error message):
- Type 1: ActionRow
- Type 9: TextDisplay
- Type 10: Separator  
- Type 12: Section
- Type 13: Thumbnail
- Type 14: MediaGallery

**Button** is NOT in this list because it's not a valid direct Container child!

## References

- **Working Example**: `core/components_traditional.py` lines 333-363
- **Discord Docs**: Components V2 requires ActionRow wrapper for interactive components
- **Error Message**: "Value of field 'type' must be one of (1, 9, 10, 12, 13, 14)"

This fix aligns with Discord's Components V2 specification and matches the proven pattern from the tournament channel implementation.