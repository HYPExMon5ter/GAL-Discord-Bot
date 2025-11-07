# Update Tournament Format Section Spec

## Current State Analysis

The tournament hub embed has **TWO different implementations** that both need updating:

### 1. **Modern Layout View** (Components V2) - Lines 182-217 in `components_traditional.py`
Used by the newer Discord Components API

**Current Tournament Format Section**:
```python
# Normal Mode:
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Individual Players\n"
    f"**Max Players**: {self.data['max_players']}\n"
    f"**Players**: {self.data['registered']} registered"  # ❌ REMOVE THIS
)

# Double-Up Mode:
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Double-Up Teams\n"
    f"**Max Teams**: {self.data['max_players'] // 2}\n"
    f"**Teams**: {self.data.get('complete_teams', 0)} complete, "  # ❌ REMOVE THIS
    f"{len(self.data.get('teams', {}))} total"  # ❌ REMOVE THIS
)
```

**Issues**:
- Shows current registered player/team count (needs removal)
- Section header is `### 🎮 Tournament format` (lowercase 'f' - needs capitalization)
- No capacity/progress bar

### 2. **Legacy Embed View** - Lines 1051-1066 in `components_traditional.py`
Used by the older embed-based system (fallback)

**Current Tournament Format Section**:
```python
# Normal Mode:
embed.add_field(
    name=f"🎮 {tournament_name} Tournament Format",  # ❌ lowercase 'f'
    value=f"**Mode:** Individual Players\n**Players:** {registered} registered\n**Max Players:** {max_players}",
    inline=False
)

# Double-Up Mode:
embed.add_field(
    name=f"🎮 {tournament_name} Tournament Format",  # ❌ lowercase 'f'
    value=f"**Mode:** Double‑Up Teams\n**Teams:** {complete_teams} complete, {len(teams)} total\n**Max Teams:** {max_players // 2}",
    inline=False
)
```

**Issues**:
- Shows current player/team counts (needs removal)
- Lowercase 'f' in "Tournament format" (needs capitalization)
- No capacity/progress bar

## Required Changes

### Change 1: Capitalize "Format" in Header
**Both implementations** need this change.

### Change 2: Remove Current Player/Team Counts
Remove lines showing:
- Normal mode: `**Players**: X registered`
- Double-Up mode: `**Teams**: X complete, Y total`

### Change 3: Add 12-Square Capacity Bar
Add a visual capacity indicator using the existing `EmbedHelper.create_progress_bar()` function with **length=12**.

**Note**: The progress bar function already exists in `helpers/embed_helpers.py` and uses:
- 🟩 (green squares) for filled capacity
- ⬜ (white squares) for available capacity

## Implementation Plan

### File: `core/components_traditional.py`

#### Update 1: Modern Layout View (Lines 182-217)

**Change the header** (Line 195):
```python
# BEFORE:
discord.ui.TextDisplay(content="### 🎮 Tournament format"),

# AFTER:
discord.ui.TextDisplay(content="### 🎮 Tournament Format"),  # Capitalized 'F'
```

**Update Normal Mode format** (Lines 210-215):
```python
# BEFORE:
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Individual Players\n"
    f"**Max Players**: {self.data['max_players']}\n"
    f"**Players**: {self.data['registered']} registered"
)

# AFTER:
# Create 12-square capacity bar
capacity_bar = EmbedHelper.create_progress_bar(
    self.data['registered'], 
    self.data['max_players'], 
    length=12
)
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Individual Players\n"
    f"**Max Players**: {self.data['max_players']}\n"
    f"**Capacity**: {capacity_bar}"
)
```

**Update Double-Up Mode format** (Lines 202-208):
```python
# BEFORE:
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Double-Up Teams\n"
    f"**Max Teams**: {self.data['max_players'] // 2}\n"
    f"**Teams**: {self.data.get('complete_teams', 0)} complete, "
    f"{len(self.data.get('teams', {}))} total"
)

# AFTER:
# Create 12-square capacity bar for teams
capacity_bar = EmbedHelper.create_progress_bar(
    len(self.data.get('teams', {})), 
    self.data['max_players'] // 2, 
    length=12
)
format_text = (
    f"**Event Name**: {tournament_name}\n"
    f"**Mode**: Double-Up Teams\n"
    f"**Max Teams**: {self.data['max_players'] // 2}\n"
    f"**Capacity**: {capacity_bar}"
)
```

#### Update 2: Legacy Embed View (Lines 1051-1066)

**Update Normal Mode** (Lines 1063-1066):
```python
# BEFORE:
embed.add_field(
    name=f"🎮 {tournament_name} Tournament format",  # lowercase 'f'
    value=f"**Mode:** Individual Players\n**Players:** {registered} registered\n**Max Players:** {max_players}",
    inline=False
)

# AFTER:
# Create 12-square capacity bar
capacity_bar = EmbedHelper.create_progress_bar(registered, max_players, length=12)
embed.add_field(
    name=f"🎮 {tournament_name} Tournament Format",  # Capitalized 'F'
    value=f"**Mode:** Individual Players\n**Max Players:** {max_players}\n**Capacity:** {capacity_bar}",
    inline=False
)
```

**Update Double-Up Mode** (Lines 1056-1061):
```python
# BEFORE:
embed.add_field(
    name=f"🎮 {tournament_name} Tournament Format",  # lowercase 'f'
    value=f"**Mode:** Double‑Up Teams\n**Teams:** {complete_teams} complete, {len(teams)} total\n**Max Teams:** {max_players // 2}",
    inline=False
)

# AFTER:
# Create 12-square capacity bar for teams
capacity_bar = EmbedHelper.create_progress_bar(len(teams), max_players // 2, length=12)
embed.add_field(
    name=f"🎮 {tournament_name} Tournament Format",  # Capitalized 'F'
    value=f"**Mode:** Double‑Up Teams\n**Max Teams:** {max_players // 2}\n**Capacity:** {capacity_bar}",
    inline=False
)
```

## Visual Before/After

### Before:
```
🎮 Curse of the Carousel Tournament format
Event Name: Curse of the Carousel
Mode: Individual Players
Max Players: 24
Players: 8 registered
```

### After:
```
🎮 Curse of the Carousel Tournament Format
Event Name: Curse of the Carousel
Mode: Individual Players
Max Players: 24
Capacity: 🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜
```

## Testing Checklist

1. ✅ Verify "Format" is capitalized in both implementations
2. ✅ Verify player count removed from normal mode
3. ✅ Verify team counts removed from double-up mode
4. ✅ Verify 12-square capacity bar appears in normal mode
5. ✅ Verify 12-square capacity bar appears in double-up mode
6. ✅ Verify capacity bar accurately reflects current capacity
7. ✅ Test with 0%, 50%, and 100% capacity scenarios
8. ✅ Test in both modern LayoutView and legacy embed view

## Notes

- The capacity bar will automatically show in the Registration section as well (already implemented with 10 squares)
- This change affects ONLY the Tournament Format section at the top
- The `EmbedHelper.create_progress_bar()` function already exists and is tested
- Both modern and legacy implementations need identical updates for consistency

---

**Summary**: Remove current player/team counts from Tournament Format section, capitalize "Format", and add a 12-square visual capacity bar for cleaner presentation.