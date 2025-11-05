# Fix LayoutView Buttons Not Showing and Dynamic Updates Not Working

## Problems Identified

### 1. **Buttons Not Showing in LayoutView**

**Root Cause**: Looking at the test_components.py that works, buttons are added directly in `__init__()`, not in an async `build_view()` method. The LayoutView needs components added during initialization.

**Our Current (Broken) Approach**:
```python
def __init__(self, guild, user):
    super().__init__(timeout=None)
    # Components added later in async build_view()
    
async def build_view(self):
    components = await self._build_all_components()
    self.add_item(discord.ui.Container(*components))
```

**Working Approach (test_components.py)**:
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    components = []
    components.extend(self._get_header_components())
    components.extend(self._get_action_button_components())
    self.container = discord.ui.Container(*components, accent_colour=...)
    self.add_item(self.container)
```

### 2. **Dynamic Updates Not Working**

**Root Cause**: LayoutView doesn't support `msg.edit(view=view)` the same way traditional views do. When you edit a LayoutView message, you need to reconstruct the ENTIRE view, not just update it.

**Current (Broken) Update**:
```python
view = await build_unified_view(guild)
await msg.edit(view=view)
```

**Issue**: This creates a new view instance, but LayoutView messages need special handling. The message needs to be deleted and recreated, OR we need to update the content differently.

## Solution Strategy

### Fix 1: Synchronous Component Building

**Problem**: `__init__` cannot be async, but we need async calls to get player counts, waitlist, etc.

**Solution Options**:

**Option A (Recommended)**: Make component builders synchronous, pass data in
```python
def __init__(self, guild, user, tournament_data):
    super().__init__(timeout=None)
    self.guild = guild
    self.guild_id = str(guild.id)
    self.user = user
    self.tournament_data = tournament_data  # Contains all async-fetched data
    
    # Build components synchronously
    components = self._build_all_components()
    self.container = discord.ui.Container(*components, accent_colour=discord.Colour(15762110))
    self.add_item(self.container)
```

Then fetch data before creating view:
```python
async def build_unified_view(guild, user):
    # Fetch all async data first
    tournament_data = await fetch_tournament_data(guild)
    
    # Create view with data
    view = UnifiedChannelLayoutView(guild, user, tournament_data)
    return view
```

**Option B**: Use factory pattern with async initialization
```python
@classmethod
async def create(cls, guild, user):
    instance = cls.__new__(cls)
    discord.ui.LayoutView.__init__(instance, timeout=None)
    instance.guild = guild
    # ... fetch async data and build
    return instance
```

**Chosen Approach**: Option A - cleaner and follows test_components.py pattern

### Fix 2: Proper Dynamic Updates

**For LayoutView, we have two options**:

**Option A (Recommended)**: Delete and recreate message
```python
async def update_unified_channel(guild):
    chan_id, msg_id = get_persisted_msg(guild.id, "unified")
    channel = guild.get_channel(chan_id)
    
    try:
        msg = await channel.fetch_message(msg_id)
        await msg.delete()
    except:
        pass
    
    # Create fresh message
    return await setup_unified_channel(guild)
```

**Option B**: Edit with fresh view (may work if done correctly)
```python
async def update_unified_channel(guild):
    # ... fetch message
    view = await build_unified_view(guild)
    logo_file = discord.File("assets/GA_Logo_Black_Background.jpg")
    await msg.edit(view=view, attachments=[logo_file])
```

**Chosen Approach**: Try Option B first (less disruptive), fallback to Option A if needed

## Implementation Plan

### Step 1: Create Data Fetching Function

```python
async def fetch_tournament_data(guild: discord.Guild) -> dict:
    """Fetch all async data needed for LayoutView."""
    guild_id = str(guild.id)
    mode = get_event_mode_for_guild(guild_id)
    cfg = get_sheet_settings(mode)
    
    data = {
        'guild_id': guild_id,
        'mode': mode,
        'max_players': cfg.get("max_players", 32),
        'reg_open': persisted.get(guild_id, {}).get("registration_open", False),
        'ci_open': persisted.get(guild_id, {}).get("checkin_open", False),
        'registered': await SheetOperations.count_by_criteria(guild_id, registered=True),
        'checked_in': await SheetOperations.count_by_criteria(guild_id, registered=True, checked_in=True),
        'waitlist_entries': await WaitlistManager.get_all_waitlist_entries(guild_id),
        'reg_open_ts': ScheduleHelper.get_all_schedule_times(guild.id)[0],
        'reg_close_ts': ScheduleHelper.get_all_schedule_times(guild.id)[1],
        'ci_open_ts': ScheduleHelper.get_all_schedule_times(guild.id)[2],
        'ci_close_ts': ScheduleHelper.get_all_schedule_times(guild.id)[3],
    }
    
    if mode == "doubleup":
        data['teams'] = await SheetOperations.get_teams_summary(guild_id)
        data['complete_teams'] = sum(1 for members in data['teams'].values() if len(members) >= 2)
    
    return data
```

### Step 2: Refactor UnifiedChannelLayoutView

```python
class UnifiedChannelLayoutView(discord.ui.LayoutView):
    """Modern unified channel using Components V2 LayoutView."""
    
    def __init__(self, guild: discord.Guild, user: Optional[discord.Member], tournament_data: dict):
        super().__init__(timeout=None)
        self.guild = guild
        self.guild_id = str(guild.id)
        self.user = user
        self.data = tournament_data
        
        # Build components synchronously using pre-fetched data
        components = self._build_all_components()
        
        # Create and add container
        self.container = discord.ui.Container(
            *components,
            accent_colour=discord.Colour(15762110)
        )
        self.add_item(self.container)
    
    def _build_all_components(self) -> list:
        """Build all components synchronously using self.data."""
        # All the same logic, but using self.data instead of async calls
        components = []
        
        if self.data['reg_open'] or self.data['ci_open'] or self.data.get('has_scheduled_events'):
            components.extend(self._get_header_components())
        
        if self.data['reg_open'] or self.data['reg_open_ts']:
            components.extend(self._get_registration_components())
            
        # ... etc, all synchronous now
        
        return components
```

### Step 3: Update build_unified_view

```python
async def build_unified_view(guild: discord.Guild, user: Optional[discord.Member] = None):
    """Build the unified view with fresh data."""
    # Fetch all async data first
    tournament_data = await fetch_tournament_data(guild)
    
    # Calculate derived values
    tournament_data['has_scheduled_events'] = (
        tournament_data['reg_open_ts'] or 
        tournament_data['reg_close_ts'] or 
        tournament_data['ci_open_ts'] or 
        tournament_data['ci_close_ts']
    )
    tournament_data['spots_remaining'] = max(0, tournament_data['max_players'] - tournament_data['registered'])
    
    # Create view with data
    view = UnifiedChannelLayoutView(guild, user, tournament_data)
    return view
```

### Step 4: Update update_unified_channel

```python
async def update_unified_channel(guild: discord.Guild) -> bool:
    """Update the unified channel by recreating the message."""
    try:
        chan_id, msg_id = get_persisted_msg(guild.id, "unified")
        if not chan_id or not msg_id:
            return await setup_unified_channel(guild)

        channel = guild.get_channel(chan_id)
        if not channel:
            return False

        try:
            msg = await channel.fetch_message(msg_id)
            
            # Delete old message
            await msg.delete()
            
            # Create fresh message
            return await setup_unified_channel(guild)
            
        except discord.NotFound:
            return await setup_unified_channel(guild)
        except discord.HTTPException as e:
            logging.warning(f"HTTP error updating unified channel: {e}")
            return await setup_unified_channel(guild)
    except Exception as e:
        logging.error(f"Failed to update unified channel: {e}", exc_info=True)
        return False
```

### Step 5: Make All Component Builders Synchronous

Change all `async def` to `def` and use `self.data` instead of async calls:

```python
def _get_header_components(self) -> list:
    # Use self.data['mode'], self.data['max_players'], etc.
    pass

def _get_registration_components(self) -> list:
    # Use self.data['reg_open'], self.data['registered'], etc.
    pass
```

## Files to Modify

- `core/components_traditional.py`:
  - Add `fetch_tournament_data()` function
  - Refactor `UnifiedChannelLayoutView.__init__()` to be synchronous
  - Make all component builders synchronous (remove `async`)
  - Update `build_unified_view()` to fetch data first
  - Update `update_unified_channel()` to delete/recreate

## Testing Checklist

- [ ] Buttons appear when creating unified channel
- [ ] All 2-4 buttons visible depending on state
- [ ] Toggling registration updates the display
- [ ] Toggling check-in updates the display  
- [ ] Button clicks work correctly
- [ ] Updates happen without errors
- [ ] Logo attachment persists across updates

## Why This Will Work

✅ **Synchronous Init**: Matches test_components.py pattern that works
✅ **Pre-fetched Data**: No async calls during component building
✅ **Delete/Recreate**: Most reliable way to update LayoutView messages
✅ **Clean Separation**: Data fetching separated from UI building