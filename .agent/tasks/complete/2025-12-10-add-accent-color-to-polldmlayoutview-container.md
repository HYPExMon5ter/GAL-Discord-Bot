# Fix Plan: Add Accent Color to PollDMLayoutView Container

## Problem Identified

**Issue 1: No Color on Poll DM**
- The poll DM appears with default Discord styling (no accent color)
- Configuration has `color: "#f8c8dc"` (GAL pink) but it's not being applied

**Issue 2: Config Not Being Used**
- The `config.yaml` has proper poll configuration but the color isn't applied to the Container

## Root Cause

Looking at the working tournament channel code:

**File**: `core/components_traditional.py` (lines 116-121)

```python
# Create and add container
self.container = discord.ui.Container(
    *components,
    accent_colour=discord.Colour(15762110)  # ✅ Accent color applied here!
)
self.add_item(self.container)
```

**Current PollDMLayoutView** (MISSING COLOR):

**File**: `helpers/poll_helpers.py` (line 87)

```python
# Return container with all components
return discord.ui.Container(*components)  # ❌ No accent_colour parameter!
```

## Solution: Add Accent Color to Container

### Updated Code

**File**: `helpers/poll_helpers.py`

**Method**: `build_container()` (lines 44-87)

```python
def build_container(self) -> discord.ui.Container:
    """Build the poll DM container with Discord markdown support."""
    dm_config = self.config.get("dm_embed", {})
    
    # Extract config values with proper fallbacks
    title = dm_config.get("title", "# 🌟 Hello Angel!")
    header = dm_config.get("header", "### We need your input! 📊")
    body = dm_config.get("body", "")
    how_to_vote = dm_config.get("how_to_vote", {})
    how_to_vote_title = how_to_vote.get("title", "### 🔗 How to vote:")
    how_to_vote_content = how_to_vote.get("content", "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! ⏱️")
    footer = dm_config.get("footer", "-# 💙 Thank you for helping make GAL tournaments even better!")
    button_config = dm_config.get("button", {})
    button_label = button_config.get("label", "📊 Go to Poll")
    
    # ✅ NEW: Get color from config
    color_hex = dm_config.get("color", "#f8c8dc")  # Default GAL pink
    
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
    
    # Add poll button wrapped in ActionRow (required for Components V2)
    poll_button = discord.ui.Button(
        label=button_label,
        url=self.poll_link,
        style=discord.ButtonStyle.link
    )
    components.append(discord.ui.ActionRow(poll_button))
    
    # ✅ FIX: Return container with accent color from config
    return discord.ui.Container(
        *components,
        accent_colour=discord.Colour.from_str(color_hex)  # ✅ Apply GAL pink color!
    )
```

## Key Changes

### Before (NO COLOR):
```python
# ❌ No color applied
return discord.ui.Container(*components)
```

### After (WITH COLOR):
```python
# ✅ Get color from config
color_hex = dm_config.get("color", "#f8c8dc")  # Default GAL pink

# ✅ Apply color to container
return discord.ui.Container(
    *components,
    accent_colour=discord.Colour.from_str(color_hex)
)
```

## Configuration Structure

**File**: `config.yaml` (lines 347-370)

```yaml
poll:
  dm_embed:
    title: "# 🌟 Hello Angel!"
    color: "#f8c8dc"  # ✅ GAL pink - will now be applied!
    
    header: "### We need your input! 📊"
    
    body: |
      Please take a moment to vote on when you'd like our next **Guardian Angel League** tournament to be held.
    
    how_to_vote:
      title: "### 🔗 How to vote:"
      content: "Click the **\"Go to Poll\"** button below to access the voting form."
    
    footer: "-# 💙 Thank you for helping make GAL tournaments even better!"
    
    button:
      label: "📊 Go to Poll"
```

## Expected Results

### Visual Appearance After Fix:

**Before**:
- DM appears with default Discord gray/white styling
- No visual accent color

**After**:
- DM has GAL pink accent color (#f8c8dc)
- Professional, branded appearance
- Matches tournament channel styling

### Color Breakdown:

| Component | Color |
|-----------|-------|
| **Accent Bar** | GAL Pink (#f8c8dc) |
| **Text** | Default Discord text color |
| **Background** | Default Discord background |
| **Button** | Discord link button style (blue) |

## Benefits

1. ✅ **Brand Consistency**: Matches GAL's signature pink color
2. ✅ **Professional Look**: Polished, branded DM appearance
3. ✅ **Config Utilization**: Actually uses the configured color value
4. ✅ **Tournament Channel Match**: Same styling pattern as tournament channel
5. ✅ **Visual Appeal**: More attractive and recognizable to users

## Files to Modify

**File**: `helpers/poll_helpers.py`

**Method**: `build_container()` (lines 44-87)

**Changes**:
1. Add line to extract `color` from config (after line 54)
2. Update `return` statement to include `accent_colour` parameter (line 87)

## Testing Steps

1. Run `/gal poll` command
2. Check DM for GAL pink accent color
3. Verify all config values are being used (title, header, body, button label)
4. Confirm markdown rendering still works
5. Test button functionality

## Technical Details

### Discord.py Color API:

**Method 1: Integer** (tournament channel uses this)
```python
accent_colour=discord.Colour(15762110)  # Decimal for GAL pink
```

**Method 2: Hex String** (we'll use this)
```python
accent_colour=discord.Colour.from_str("#f8c8dc")  # Hex string
```

### Color Conversion:

- **Hex**: `#f8c8dc` (from config)
- **RGB**: `(248, 200, 220)`  
- **Decimal**: `16304348`

Both methods produce the same visual result. We use `Colour.from_str()` because:
- ✅ Reads directly from config hex value
- ✅ More maintainable (no manual conversion needed)
- ✅ Easier to update via config

## References

- **Working Example**: `core/components_traditional.py` line 119
- **Config File**: `config.yaml` line 351
- **Discord.py Docs**: `discord.Colour.from_str()` method
- **GAL Branding**: Pink color (#f8c8dc) is the official GAL accent color

This fix ensures the poll DM matches GAL's branding and uses the configured color value properly.