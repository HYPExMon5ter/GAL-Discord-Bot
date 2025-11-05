# Fix LayoutView Buttons and Layout Issues

## Problems Identified

### 1. **Buttons Not Working**
The LayoutView creates plain `discord.ui.Button` objects without callback handlers. In Components V2, buttons inside a LayoutView need to reference the actual button classes (ManageRegistrationButton, etc.) that have callback methods, OR we need to use a different approach with persistent custom_ids.

**Root Cause**: Creating standalone Button objects in `_get_action_button_components()` without callbacks or proper persistence setup.

### 2. **Double Separator Before Buttons**
The logic adds a separator when `show_waitlist` is true after check-in section, then ALWAYS adds another separator before buttons. When there's a waitlist, this creates two consecutive separators.

**Root Cause**: Line 166 adds separator after waitlist, line 164 always adds separator before buttons.

### 3. **Buttons in Multiple ActionRows**
Currently splitting buttons into 2-button rows. Discord supports up to 5 buttons per ActionRow, so all buttons should fit in one row.

**Root Cause**: Lines 373-376 split buttons into groups of 2.

## Solution Strategy

### Fix 1: Implement Proper Button Persistence

**Option A (Recommended)**: Use `discord.ui.button` decorator in LayoutView
- Add button callback methods directly to UnifiedChannelLayoutView class
- Use `@discord.ui.button()` decorator with stable custom_ids
- Components V2 automatically handles persistence for these

**Option B**: Create separate persistent button classes
- Keep existing ManageRegistrationButton, etc. classes
- Add them as children to LayoutView container
- Requires more complex registration

**Chosen Approach**: Option A - cleaner and uses native Components V2 patterns

### Fix 2: Smart Separator Logic

Change separator logic to:
```python
# Only add separator before buttons if there are previous sections
if show_tournament_info or show_registration or show_checkin:
    components.append(discord.ui.Separator(...))
```

OR better yet:
```python
# Add separator after waitlist ONLY if waitlist exists
if waitlist_components:
    components.extend(waitlist_components)
    # Separator is added here only if we have waitlist content
```

### Fix 3: Single ActionRow

Change button organization:
```python
# Put all buttons in one ActionRow (max 5 buttons)
if len(buttons) > 0:
    action_rows = [discord.ui.ActionRow(*buttons)]
```

## Implementation Plan

### Step 1: Refactor Button System

Replace `_get_action_button_components()` method with direct button methods:

```python
class UnifiedChannelLayoutView(discord.ui.LayoutView):
    # ... existing code ...
    
    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="uc_register",  # Unique stable ID
        row=0  # All buttons in row 0
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delegate to existing ManageRegistrationButton callback logic
        from core.persistence import persisted
        guild_id = str(interaction.guild.id)
        reg_open = persisted.get(guild_id, {}).get("registration_open", False)
        
        if not reg_open:
            await interaction.response.send_message(...)
            return
        # ... rest of callback logic
    
    @discord.ui.button(
        label="Check In",
        style=discord.ButtonStyle.success,
        emoji="✔️",
        custom_id="uc_checkin",
        row=0
    )
    async def checkin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delegate to existing ManageCheckInButton callback logic
        ...
    
    @discord.ui.button(
        label="View Players",
        style=discord.ButtonStyle.secondary,
        emoji="🎮",
        custom_id="uc_view_players",
        row=0
    )
    async def view_players_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delegate to existing ViewListButton callback logic
        ...
    
    @discord.ui.button(
        label="Admin Panel",
        style=discord.ButtonStyle.danger,
        emoji="🔧",
        custom_id="uc_admin",
        row=0
    )
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delegate to existing AdminPanelButton callback logic
        ...
```

**Challenge**: Buttons with decorators are always visible. We need conditional visibility.

**Solution**: Override `__init__` to remove buttons conditionally:
```python
async def build_view(self):
    # Build components first
    components = await self._build_all_components()
    
    # Handle conditional button visibility
    reg_open = persisted.get(self.guild_id, {}).get("registration_open", False)
    ci_open = persisted.get(self.guild_id, {}).get("checkin_open", False)
    
    # Remove buttons that shouldn't be shown
    items_to_remove = []
    for item in self.children:
        if isinstance(item, discord.ui.Button):
            if item.custom_id == "uc_register" and not reg_open:
                items_to_remove.append(item)
            elif item.custom_id == "uc_checkin" and not ci_open:
                items_to_remove.append(item)
    
    for item in items_to_remove:
        self.remove_item(item)
    
    # Build container with content components
    self.container = discord.ui.Container(*components, accent_colour=discord.Colour(15762110))
    self.add_item(self.container)
    
    return self
```

### Step 2: Fix Separator Logic

Change in `_build_all_components()`:

```python
# Build sections
if show_tournament_info:
    components.extend(await self._get_header_components())

if show_registration:
    components.extend(await self._get_registration_components())

if show_checkin and (show_registration or show_tournament_info):
    # Add separator before check-in only if there's content before it
    components.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))

if show_checkin:
    components.extend(await self._get_checkin_components())

# Handle waitlist
if show_waitlist:
    waitlist_comps = await self._get_waitlist_components()
    if waitlist_comps:  # Only add if waitlist has entries
        if show_checkin or show_registration or show_tournament_info:
            components.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
        components.extend(waitlist_comps)

# No events message
if not show_tournament_info:
    components.extend(self._get_no_event_components())

# Remove old separator logic - buttons are added via decorator, not in components list
```

### Step 3: Remove Old Button Component Method

Delete `_get_action_button_components()` entirely since buttons are now handled by decorators.

## Files to Modify

- `core/components_traditional.py`:
  - Add 4 button decorator methods to `UnifiedChannelLayoutView`
  - Update `build_view()` to handle conditional button visibility
  - Fix separator logic in `_build_all_components()`
  - Delete `_get_action_button_components()`
  - Extract callback logic from existing button classes to reuse

## Testing Checklist

- [ ] Registration button appears when reg_open=True
- [ ] Registration button hidden when reg_open=False
- [ ] Check-in button appears when ci_open=True
- [ ] Check-in button hidden when ci_open=False
- [ ] View Players and Admin buttons always visible
- [ ] All buttons work (callbacks execute)
- [ ] All buttons in single row
- [ ] No double separators
- [ ] Buttons persist after bot restart
- [ ] Button callbacks access correct interaction data

## Benefits

✅ **Native Persistence**: Uses discord.py's built-in button persistence  
✅ **Cleaner Code**: No manual ActionRow management  
✅ **Conditional Visibility**: Buttons show/hide based on state  
✅ **Single Row Layout**: All buttons in one clean row  
✅ **No Double Separators**: Smart separator logic