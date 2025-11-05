# Format Adjustments for LayoutView

## Changes Required

### Change 1: Tournament Format - Reorder Max Players Above Players

**Current Order** (Lines 201-214):
```python
if self.data['mode'] == "doubleup":
    format_text = (
        f"**Event Name**: {tournament_name}\n"
        f"**Mode**: Double-Up Teams\n"
        f"**Teams**: {self.data.get('complete_teams', 0)} complete, {len(self.data.get('teams', {}))} total\n"
        f"**Max Teams**: {self.data['max_players'] // 2}"
    )
else:
    format_text = (
        f"**Event Name**: {tournament_name}\n"
        f"**Mode**: Individual Players\n"
        f"**Players**: {self.data['registered']} registered\n"
        f"**Max Players**: {self.data['max_players']}"
    )
```

**New Order** (Max Players before Players):
```python
if self.data['mode'] == "doubleup":
    format_text = (
        f"**Event Name**: {tournament_name}\n"
        f"**Mode**: Double-Up Teams\n"
        f"**Max Teams**: {self.data['max_players'] // 2}\n"
        f"**Teams**: {self.data.get('complete_teams', 0)} complete, {len(self.data.get('teams', {}))} total"
    )
else:
    format_text = (
        f"**Event Name**: {tournament_name}\n"
        f"**Mode**: Individual Players\n"
        f"**Max Players**: {self.data['max_players']}\n"
        f"**Players**: {self.data['registered']} registered"
    )
```

### Change 2: Registration Status - Use Bold Instead of Heading

**Current** (Lines 227 and 244):
```python
# Line 227 - Open status
components.append(discord.ui.TextDisplay(content="### 🟢 Open"))

# Line 244 - Closed status  
components.append(discord.ui.TextDisplay(content="### 🔴 Closed"))
```

**New** (Bold instead of heading):
```python
# Open status
components.append(discord.ui.TextDisplay(content="**🟢 Open**"))

# Closed status
components.append(discord.ui.TextDisplay(content="**🔴 Closed**"))
```

### Change 3: Check-In Status - Use Bold Instead of Heading

**Current** (Lines 262 and 279):
```python
# Line 262 - Open status
components.append(discord.ui.TextDisplay(content="### 🟢 Open"))

# Line 279 - Closed status
components.append(discord.ui.TextDisplay(content="### 🔴 Closed"))
```

**New** (Bold instead of heading):
```python
# Open status
components.append(discord.ui.TextDisplay(content="**🟢 Open**"))

# Closed status
components.append(discord.ui.TextDisplay(content="**🔴 Closed**"))
```

## Implementation Summary

**File**: `core/components_traditional.py`

**Functions to Modify**:
1. `_get_header_components()` - Lines 201-214 (Tournament format order)
2. `_get_registration_components()` - Lines 227 and 244 (Registration status formatting)
3. `_get_checkin_components()` - Lines 262 and 279 (Check-in status formatting)

**Total Changes**: 6 line modifications

## Expected Visual Impact

### Tournament Format Section
**Before**:
```
Event Name: Curse of the Carousel
Mode: Individual Players
Players: 5 registered
Max Players: 24
```

**After**:
```
Event Name: Curse of the Carousel
Mode: Individual Players
Max Players: 24
Players: 5 registered
```

### Registration Section
**Before**:
```
📝 Registration
### 🟢 Open
```

**After**:
```
📝 Registration
🟢 Open
```

### Check-In Section
**Before**:
```
✔️ Check In
### 🟢 Open
```

**After**:
```
✔️ Check In
🟢 Open
```

This creates a cleaner, more consistent visual hierarchy where:
- Main sections use heading level 1 (`#`)
- Subsections use heading level 3 (`###`)
- Status indicators use bold (`**`) for less visual weight