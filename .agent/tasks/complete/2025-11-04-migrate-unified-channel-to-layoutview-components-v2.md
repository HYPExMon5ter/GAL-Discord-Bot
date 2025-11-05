# Migration Plan: Clean LayoutView Implementation with Native Persistence

## Overview
Replace the traditional embed system with Discord.py Components V2 (LayoutView) using native persistence. No data migration needed - just clean, modern code leveraging built-in features.

## Key Insight: Native Persistence
Components V2 buttons in LayoutView automatically persist across bot restarts when using `timeout=None`. The buttons have stable `custom_id` values that Discord.py handles automatically.

## Implementation Approach

### 1. Create `UnifiedChannelLayoutView` Class
Replace `build_unified_embed()` with a clean LayoutView class:

```python
class UnifiedChannelLayoutView(discord.ui.LayoutView):
    """Modern unified channel using Components V2."""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)  # Native persistence
        self.guild = guild
        self.guild_id = str(guild.id)
        
        # Build dynamic components
        components = self._build_all_components()
        
        # Single container with accent color
        self.container = discord.ui.Container(
            *components,
            accent_colour=discord.Colour(15762110)  # GAL purple
        )
        self.add_item(self.container)
```

### 2. Dynamic Component Builders (Modular & Clean)

**`_build_all_components()`**: Main orchestrator
- Checks all states (reg_open, ci_open, scheduled times)
- Calls appropriate builder methods
- Returns flat list of components

**`_get_header_components()`**: Tournament info
- Section with logo thumbnail
- Tournament name and format
- Only shown when events exist

**`_get_registration_components()`**: Registration section
- Shows if: `reg_open OR reg_open_ts exists`
- Dynamic status: 🟢 Open / 🔴 Closed
- Discord timestamps: `<t:{timestamp}:F>`
- Capacity bar using existing `EmbedHelper.create_progress_bar()`
- Player count with formatting

**`_get_checkin_components()`**: Check-in section  
- Shows if: `ci_open OR ci_open_ts exists`
- Dynamic status indicators
- Progress bar (checked_in/registered ratio)
- Percentage display

**`_get_waitlist_components()`**: Waitlist display
- Shows if: `waitlist exists AND show_waitlist flag`
- Mode-aware formatting (normal vs doubleup)
- Code block with numbered list

**`_get_no_event_components()`**: Friendly empty state
- Shows if: Both closed AND no scheduled times
- "No events right now" message

**`_get_action_buttons()`**: Interactive buttons
- Conditional rendering based on states
- Register button: Only if `reg_open`
- Check-in button: Only if `ci_open`  
- View Players & Admin: Always visible
- Uses ActionRow for proper layout

### 3. Button Integration (Native Persistence)

Existing button classes already have `custom_id` and work with Components V2:
- `ManageRegistrationButton(custom_id="manage_registration")`
- `ManageCheckInButton(custom_id="manage_checkin")`
- `ViewListButton(custom_id="view_list")`
- `AdminPanelButton(custom_id="admin_panel")`

**Keep them as-is** - they're already persistent with `timeout=None` in parent view.

### 4. Update Core Functions

**`setup_unified_channel(guild)`**:
```python
# Build view
view = UnifiedChannelLayoutView(guild)

# Send with logo file
logo_file = discord.File("assets/GA_Logo_Black_Background.jpg")
msg = await channel.send(view=view, files=[logo_file])

# Store message ID for updates
set_persisted_msg(guild.id, "unified", channel.id, msg.id)
```

**`update_unified_channel(guild)`**:
```python
# Rebuild view with fresh data
view = UnifiedChannelLayoutView(guild)

# Edit message
await msg.edit(view=view)
```

### 5. Dynamic State Mapping

All existing logic preserved, just rendered differently:

| State | Condition | Components Shown |
|-------|-----------|------------------|
| **No Events** | `!reg_open && !ci_open && !scheduled` | No event message only |
| **Scheduled** | `!reg_open && !ci_open && scheduled` | Closed sections with timestamps |
| **Reg Open** | `reg_open` | Header + Reg (open) + buttons |
| **Both Open** | `reg_open && ci_open` | Header + Reg + Check-in + buttons |
| **With Waitlist** | `waitlist_entries > 0` | All above + waitlist section |

### 6. Visual Structure (Clean Hierarchy)

```
Container (GAL purple accent)
├─ Header Section (with logo thumbnail)
│  ├─ Title: "🏆 Tournament Hub"
│  ├─ Welcome text
│  └─ Tournament format info
├─ Separator (visible, small)
├─ Registration Section (conditional)
│  ├─ "# 📝 Registration"
│  ├─ Status: 🟢 Open / 🔴 Closed
│  ├─ Timestamp (if scheduled)
│  ├─ Capacity bar + count
│  └─ Player count text
├─ Separator (visible, large)
├─ Check-in Section (conditional)
│  ├─ "# ✔️ Check In"
│  ├─ Status: 🟢 Open / 🔴 Closed
│  ├─ Timestamp (if scheduled)
│  ├─ Progress bar + percentage
│  └─ Ready count text
├─ Separator (visible, large)
├─ Waitlist Section (conditional)
│  └─ Code block with player list
├─ Separator (visible, large)
└─ Action Buttons (ActionRow)
   ├─ Register (conditional)
   ├─ Check In (conditional)
   ├─ View Players (always)
   └─ Admin Panel (always)
```

### 7. Files Modified

**Only one file**: `core/components_traditional.py`

Changes:
- Add `UnifiedChannelLayoutView` class (~200 lines)
- Add modular builder methods (~150 lines total)
- Update `setup_unified_channel()` (~10 lines changed)
- Update `update_unified_channel()` (~5 lines changed)
- Keep all existing button classes unchanged
- Remove old `build_unified_embed()` and `UnifiedView` (~150 lines removed)

Net result: **~200 lines added, ~150 removed = +50 lines total**

### 8. Benefits

✅ **Native Persistence**: Buttons work across restarts automatically  
✅ **Cleaner Code**: Modular builders, no manual persistence logic  
✅ **Modern UI**: Components V2 with better mobile rendering  
✅ **Maintainable**: Easy to add/remove sections  
✅ **All Features Preserved**: Every dynamic behavior maintained  
✅ **No Migration**: Works immediately, no data changes

### 9. Testing Checklist

- [ ] No events state displays correctly
- [ ] Registration open shows green indicator + capacity
- [ ] Registration closed with timestamp shows correctly
- [ ] Check-in section appears when active
- [ ] Waitlist displays when tournament full
- [ ] Doubleup mode shows team info
- [ ] Buttons appear/disappear based on states
- [ ] Logo thumbnail loads from assets folder
- [ ] Updates refresh correctly
- [ ] Buttons persist after bot restart