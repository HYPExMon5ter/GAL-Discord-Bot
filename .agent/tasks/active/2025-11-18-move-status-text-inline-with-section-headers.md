## Spec: Move Status Text Inline with Section Headers

### Current Structure
**Registration Section** (lines 220-250):
- Line 221: `"# 📝 Registration"` (header on its own line)
- Line 225: `"**🟢 Open**"` or line 244: `"**🔴 Closed**"` (status on separate line)

**Check-In Section** (lines 253-284):
- Line 255: `"# ✔️ Check In"` (header on its own line)
- Line 259: `"**🟢 Open**"` or line 276: `"**🔴 Closed**"` (status on separate line)

### Proposed Changes

#### 1. Registration Section (`_get_registration_components`)

**When open (line 221 + 225):**
- Current: `"# 📝 Registration"` then `"**🟢 Open**"`
- New: `"# 📝 Registration • **🟢 Open**"`

**When closed (line 221 + 244):**
- Current: `"# 📝 Registration"` then `"**🔴 Closed**"`
- New: `"# 📝 Registration • **🔴 Closed**"`

**Implementation:**
- Replace the initial `TextDisplay` with status-specific header
- Remove the separate status `TextDisplay` line

#### 2. Check-In Section (`_get_checkin_components`)

**When open (line 255 + 259):**
- Current: `"# ✔️ Check In"` then `"**🟢 Open**"`
- New: `"# ✔️ Check In • **🟢 Open**"`

**When closed (line 255 + 276):**
- Current: `"# ✔️ Check In"` then `"**🔴 Closed**"`
- New: `"# ✔️ Check In • **🔴 Closed**"`

**Implementation:**
- Replace the initial `TextDisplay` with status-specific header
- Remove the separate status `TextDisplay` line

### Code Changes

**Registration method:**
```python
def _get_registration_components(self) -> list:
    """Returns registration section components."""
    components = []
    
    if self.data['reg_open']:
        components.append(discord.ui.TextDisplay(content="# 📝 Registration • **🟢 Open**"))
        # (rest of open logic without the separate status line)
    else:
        components.append(discord.ui.TextDisplay(content="# 📝 Registration • **🔴 Closed**"))
        # (rest of closed logic without the separate status line)
    
    return components
```

**Check-in method:**
```python
def _get_checkin_components(self) -> list:
    """Returns check-in section components."""
    components = []
    
    if self.data['ci_open']:
        components.append(discord.ui.TextDisplay(content="# ✔️ Check In • **🟢 Open**"))
        # (rest of open logic without the separate status line)
    else:
        components.append(discord.ui.TextDisplay(content="# ✔️ Check In • **🔴 Closed**"))
        # (rest of closed logic without the separate status line)
    
    return components
```

### Result
Cleaner, more compact display with status integrated directly into the section headers using a dot separator.