# Fix Plan: Restructure PollDMLayoutView to Use discord.ui.Section

## Problems Identified

### 1. **Invalid Form Body Error**
**Error**: `400 Bad Request (error code: 50035): Invalid Form Body`
- **Location**: When sending LayoutView with Discord

**Likely Cause**: Discord is rejecting the LayoutView structure - possibly because:
   - `discord.ui.Button` has invalid parameters
   - LayoutView structure is not properly formatted for DMs
   - Form Body content isn't structured correctly

### 2. **Component Structure Issues**
**Current (BROKEN)**:
- Using individual components (`TextDisplay`, `Separator`, `Button`)
- Container with unpacking syntax (`*components`)
- `discord.ui.Button` may have incompatible parameters

**Pattern from Tournament Channel**:
```python
components = [
    discord.ui.Section(
        discord.ui.TextDisplay(content="# 🏆 Tournament Hub"),
        discord.ui.TextDisplay(content="Welcome to the Guardian Angel League tournament hub!"),
        discord.ui.Separator(),
        discord.ui.Button(...)
    )
]
```

## Solution: Restructure PollDMLayoutView to Match Tournament Channel Pattern

### File: `helpers/poll_helpers.py`

**Update `PollDMLayoutView` structure:**

**New Pattern:**
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
    how_to_vote_content = how_to_vote.get("content", "Click the **\"Go to Poll** button...")
    footer = dm_config.get("footer", "-# 💙 Thank you for helping...")
    button_config = dm_config.get("button", {})
    button_label = button_config.get("label", "🗳️ Go to Poll")
    
    # Build components list following tournament channel pattern
    components = []
    
    # Main title
    components.append(discord.ui.TextDisplay(content=title))
    
    # Header section
    if header:
        components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        components.append(discord.ui.TextDisplay(content=header))
    
    # Body section
    if body:
        components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        components.append(discord.ui.TextDisplay(content=f"📋 **Poll Details**\n{body}"))
    
    # How to vote section  
    if how_to_vote:
        components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        components.append(discord.ui.TextDisplay(content=how_to_vote_title))
        if how_to_vote_content:
            components.append(discord.ui.TextDisplay(content=how_to_vote_content))
    
    # Footer
    if footer:
        components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        components.append(discord.ui.TextDisplay(content=footer))
    
    # Add separator before button
    components.append(discord.Separator(
        visible=True,
        spacing=discord.SeparatorSpacing.small
    ))
    
    # Add poll button
    components.append(discord.ui.Button(
        label=button_label,
        url=self.poll_link,
        style=discord.ButtonStyle.link
    ))
    
    # Create container with all components
    return discord.ui.Container(*components)
```

## Key Changes

1. **Component Structure**: Switch from `Container + TextDisplay + Separator + Button` to `discord.ui.Section` pattern
2. **Color Removal**: Remove unsupported `color` parameter from TextDisplay
3. **Container Creation**: Use `discord.ui.Container(*components)` unpacking syntax
4. **Section Pattern**: Use nested `discord.ui.Section` like tournament channel

## Expected Results

### DM Appearance After Fix:
```
┌─────────────────────────────────────────────┐# 🌟 Hello Angel!

### We need your input! 🗳️

📋 **Poll Details**
Please take a moment to vote on when you'd like our next **Guardian Angel League** tournament to be held. Your schedule matters, and we want to pick the best time for everyone! 🏆

### 🔗 How to vote:
Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊

-# 💙 Thank you for helping make GAL tournaments even better!

┌─────────────────────────────────────
[🗳️ Go to Poll]
```

## Benefits of Using Section

1. **Discord Native Support**: `discord.ui.Section` is specifically designed for Components V2
2. **Proper Spacing**: Built-in separators and spacing management
3. **Hierarchical Structure**: Can nest sections if needed
4. **Consistency**: Matches tournament channel implementation
5. **Future-Proof**: Uses Components V2 patterns

## Files to Modify

**File**: `helpers/poll_helpers.py`

**Methods to Update:**
- `build_container()` - Replace current implementation
- Add proper Section-based structure
- Remove color from TextDisplay
- Use Container unpacking

## Testing

After fix, run `/gal poll` should:
1. ✅ Create LayoutView successfully without errors
2. ✅ Send DMs with proper formatting
3. ✅ Support Discord markdown (#, ###, -#)
4. ✅ Show button that links to poll
5. ✅ Track progress correctly

The new structure should be compatible with Discord's latest Components V2 system and resolve the current "Invalid Form Body" error.