# Fix LayoutView Dynamic Updates and Visual Issues

## Problems Identified

### 1. **Message Deletion Instead of Edit**
Current code in `update_unified_channel()` deletes and recreates the message. This is disruptive and causes the message to jump in the channel.

**Current (Bad)**:
```python
msg = await channel.fetch_message(msg_id)
await msg.delete()  # ❌ Causes message to disappear/reappear
return await setup_unified_channel(guild)
```

**Solution**: Use `msg.edit(view=view)` to update in place. LayoutView DOES support editing if done correctly.

### 2. **Double Separator Between Registration and Check-in**
Lines 148-149 add separator after registration if check-in exists, THEN lines 152-153 add another separator before check-in.

**Problem Code**:
```python
if show_registration:
    components.extend(self._get_registration_components())
    if show_checkin or show_waitlist:  # ❌ Adds separator
        components.append(discord.ui.Separator(...))

if show_checkin and (show_registration or show_tournament_info):  # ❌ Adds another separator
    components.append(discord.ui.Separator(...))
```

**Solution**: Remove the conditional separator after registration, only add before check-in.

### 3. **Progress Bar Length**
Currently using default 20 squares, need to use 10.

**Solution**: Change `EmbedHelper.create_progress_bar(current, max)` to `EmbedHelper.create_progress_bar(current, max, 10)`

### 4. **Button Layout - Need Two Rows**
Currently all buttons in one row. Need:
- Row 1: Register + Check In
- Row 2: View Players + Admin Panel

**Current**:
```python
# All buttons in row 0
buttons = [Register, CheckIn, ViewPlayers, Admin]
return [discord.ui.ActionRow(*buttons)]  # One row
```

**Solution**:
```python
# Organize into two rows
row1_buttons = []  # Register, Check In
row2_buttons = [ViewPlayers, Admin]  # Always visible

if reg_open:
    row1_buttons.append(LayoutRegisterButton(...))
if ci_open:
    row1_buttons.append(LayoutCheckinButton())

action_rows = []
if row1_buttons:
    action_rows.append(discord.ui.ActionRow(*row1_buttons))
action_rows.append(discord.ui.ActionRow(*row2_buttons))

return action_rows
```

## Implementation Plan

### Fix 1: Enable Dynamic Editing

Update `update_unified_channel()`:
```python
async def update_unified_channel(guild: discord.Guild) -> bool:
    """Update the unified channel with fresh LayoutView data."""
    try:
        chan_id, msg_id = get_persisted_msg(guild.id, "unified")
        if not chan_id or not msg_id:
            return await setup_unified_channel(guild)

        channel = guild.get_channel(chan_id)
        if not channel:
            return False

        try:
            msg = await channel.fetch_message(msg_id)
            
            # Build fresh LayoutView with updated data
            view = await build_unified_view(guild)
            
            # Edit the message in place
            await msg.edit(view=view)
            return True
            
        except discord.NotFound:
            return await setup_unified_channel(guild)
        except discord.HTTPException as e:
            logging.warning(f"HTTP error updating unified channel: {e}")
            # Only recreate if edit fails
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass
            return await setup_unified_channel(guild)
    except Exception as e:
        logging.error(f"Failed to update unified channel: {e}", exc_info=True)
        return False
```

### Fix 2: Remove Double Separators

In `_build_all_components()`:
```python
# Build sections
if show_tournament_info:
    components.extend(self._get_header_components())

if show_registration:
    components.extend(self._get_registration_components())
    # ❌ REMOVE THIS BLOCK - no separator after registration

# ✅ KEEP THIS - add separator before check-in
if show_checkin and (show_registration or show_tournament_info):
    components.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))

if show_checkin:
    components.extend(self._get_checkin_components())

# ... rest of logic unchanged
```

### Fix 3: Update Progress Bar Length

In `_get_registration_components()`:
```python
cap_bar = EmbedHelper.create_progress_bar(self.data['registered'], self.data['max_players'], 10)
```

In `_get_checkin_components()`:
```python
progress_bar = EmbedHelper.create_progress_bar(self.data['checked_in'], self.data['registered'], 10)
```

### Fix 4: Two-Row Button Layout

Update `_get_action_button_components()`:
```python
def _get_action_button_components(self) -> list:
    """Returns action button components as ActionRows for LayoutView."""
    row1_buttons = []  # Primary actions
    row2_buttons = []  # Secondary actions (always visible)
    
    # Primary action buttons (conditional)
    if self.data['reg_open']:
        if self.user and RoleManager.is_registered(self.user):
            row1_buttons.append(LayoutRegisterButton(label="Update Registration"))
        else:
            row1_buttons.append(LayoutRegisterButton(label="Register"))
    
    if self.data['ci_open']:
        row1_buttons.append(LayoutCheckinButton())
    
    # Always include secondary buttons in second row
    row2_buttons.extend([
        LayoutViewPlayersButton(),
        LayoutAdminButton(),
    ])
    
    # Organize into action rows
    action_rows = []
    if row1_buttons:
        action_rows.append(discord.ui.ActionRow(*row1_buttons))
    action_rows.append(discord.ui.ActionRow(*row2_buttons))
    
    return action_rows
```

## Files to Modify

- `core/components_traditional.py`:
  1. Update `update_unified_channel()` - remove delete, use edit
  2. Fix `_build_all_components()` - remove double separator logic
  3. Update `_get_registration_components()` - progress bar length 10
  4. Update `_get_checkin_components()` - progress bar length 10
  5. Update `_get_action_button_components()` - two row layout

## Testing Checklist

- [ ] Toggling registration updates message in place (no delete/recreate)
- [ ] Toggling check-in updates message in place
- [ ] No double separators between sections
- [ ] Progress bars show 10 squares not 20
- [ ] Register/Check-in buttons on first row
- [ ] View Players/Admin buttons on second row

## Benefits

✅ **Smooth Updates**: Message edits in place, no flickering
✅ **Clean Layout**: No double separators
✅ **Compact Progress Bars**: 10 squares instead of 20
✅ **Better Button Organization**: Two logical rows