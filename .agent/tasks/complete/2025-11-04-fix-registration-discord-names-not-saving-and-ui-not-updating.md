# Fix Registration Discord Names and Dynamic Updates

## Root Cause Analysis

### Issue 1: Discord Names Not Being Written to Sheet

**System Architecture (Confirmed)**:
- ✅ Column mappings ARE stored dynamically in the persisted data system
- ✅ Uses `storage/fallback.db` when database is disconnected
- ✅ `sheets_refactor` feature flag is ENABLED (True)
- ✅ Mappings stored via `get_column_mapping()` and `save_column_mapping()`

**Current Guild Data** (`1385739351505240074`):
```json
{
  "unified": [1385739353250201672, 1435152746746740849],
  "registration_open": true,
  "checkin_open": false
}
```

**PROBLEM**: No `column_mapping` key exists in guild data!

**Flow Analysis**:
1. `find_or_register_user()` is called (Line 796 in sheets.py)
2. It calls `await SheetIntegrationHelper.get_column_letter(gid, "discord_col")`
3. `SheetIntegrationHelper.get_column_config()` is called
4. Since `sheets_refactor_enabled()` returns `True`, it tries to get column mapping from persistence
5. Calls `get_column_mapping(guild_id)` which returns from `get_guild_data(guild_id)`
6. **Guild data has NO `column_mapping` key**, so it falls back to detection
7. Detection runs `detect_sheet_columns()` but the mapping is NEVER saved
8. Returns `None` for `discord_col` because no mapping exists
9. Discord name is NOT written to sheet

**Why Column Mapping Doesn't Exist**:
- `ensure_guild_migration()` is called in `SheetIntegrationHelper.get_column_config()`
- But it only migrates if the mapping doesn't exist
- The migration system expects column mappings to be created either:
  1. From config.yaml (but config.yaml has no column definitions - we confirmed this)
  2. From sheet detection (which runs but never saves)
  3. Manual setup via config UI

### Issue 2: UI Not Updating After Registration

**Flow Analysis**:
1. Registration completes in `complete_registration()` (core/views.py Line 311)
2. `await update_unified_channel(guild)` is called
3. `update_unified_channel()` calls `build_unified_view(guild)` 
4. `build_unified_view()` calls `fetch_tournament_data(guild)` to get fresh data
5. `fetch_tournament_data()` calls `await SheetOperations.count_by_criteria(guild_id, registered=True)`
6. **This reads from cached data**, which hasn't been updated yet
7. The cache is only updated in `find_or_register_user()` at the END (Lines 756-760, 857-862)
8. But `update_unified_channel()` is called BEFORE cache has propagated

**Race Condition**: Cache update happens AFTER the UI update call.

## Solution Strategy

### Fix 1: Initialize Column Mappings (CRITICAL)

The system is expecting column mappings to be detected and saved automatically, but this isn't happening. We need to:

1. **Run column detection on bot startup** for the guild
2. **Save the detected mappings** to persistence
3. **Ensure this happens before any registration attempts**

**Implementation**:
```python
# In bot.py or wherever bot starts
@bot.event
async def on_ready():
    # ... existing startup code ...
    
    # Detect and save column mappings for all guilds
    for guild in bot.guilds:
        await ensure_column_mappings_initialized(guild.id)
```

**New helper function in `integrations/sheet_detector.py`**:
```python
async def ensure_column_mappings_initialized(guild_id: str) -> bool:
    """
    Ensure column mappings are detected and saved for a guild.
    Returns True if mappings exist or were created successfully.
    """
    # Check if mappings already exist
    existing_mapping = await get_column_mapping(guild_id)
    if existing_mapping and existing_mapping.discord_column:
        logging.info(f"Column mappings already exist for guild {guild_id}")
        return True
    
    logging.info(f"Detecting column mappings for guild {guild_id}")
    
    # Detect columns from sheet
    detections = await detect_sheet_columns(guild_id, force_refresh=True)
    
    if not detections:
        logging.error(f"Failed to detect columns for guild {guild_id}")
        return False
    
    # Create mapping from detections
    mapping = ColumnMapping()
    if "discord" in detections:
        mapping.discord_column = detections["discord"].column_letter
    if "ign" in detections:
        mapping.ign_column = detections["ign"].column_letter
    if "registered" in detections:
        mapping.registered_column = detections["registered"].column_letter
    if "checkin" in detections:
        mapping.checkin_column = detections["checkin"].column_letter
    if "team" in detections:
        mapping.team_column = detections["team"].column_letter
    if "alt_ign" in detections:
        mapping.alt_ign_column = detections["alt_ign"].column_letter
    if "pronouns" in detections:
        mapping.pronouns_column = detections["pronouns"].column_letter
    
    # Save the mapping
    await save_column_mapping(guild_id, mapping)
    
    logging.info(f"Column mappings saved for guild {guild_id}: "
                f"discord={mapping.discord_column}, ign={mapping.ign_column}, "
                f"registered={mapping.registered_column}")
    
    return True
```

### Fix 2: Force Cache Refresh After Registration

Add a cache refresh call immediately after `find_or_register_user()` completes and BEFORE `update_unified_channel()`.

**In `core/views.py` - `complete_registration()` function (around Line 311)**:
```python
# Current code:
row = await find_or_register_user(...)
await RoleManager.add_role(member, get_registered_role())
await hyperlink_lolchess_profile(discord_tag, gid)
await update_unified_channel(guild)  # ❌ Uses stale cache

# Fixed code:
row = await find_or_register_user(...)
await RoleManager.add_role(member, get_registered_role())
await hyperlink_lolchess_profile(discord_tag, gid)

# Force cache refresh to ensure fresh data
from integrations.sheets import refresh_sheet_cache
await refresh_sheet_cache(bot=interaction.client, force=True)

await update_unified_channel(guild)  # ✅ Now uses fresh data
```

### Fix 3: Add Logging to Diagnose Issues

Add comprehensive logging to track the flow:

**In `integrations/sheets.py` - `find_or_register_user()` around Line 801**:
```python
if discord_col:
    writes[discord_col] = discord_tag
    logging.info(f"✅ Writing Discord tag to column {discord_col}: {discord_tag}")
else:
    logging.error(f"❌ discord_col is None! Cannot write Discord tag for {discord_tag}")
    logging.error(f"Column config: {await SheetIntegrationHelper.get_column_config(gid)}")
```

**In `core/views.py` - after registration**:
```python
logging.info(f"✅ Registration complete for {discord_tag}")
logging.info(f"Cache state before UI update: registered_count={await SheetOperations.count_by_criteria(gid, registered=True)}")
```

## Implementation Plan

### Step 1: Add Column Mapping Initialization Helper
- **File**: `integrations/sheet_detector.py`
- **Action**: Add `ensure_column_mappings_initialized()` function
- **Purpose**: Detect and save column mappings if they don't exist

### Step 2: Initialize Mappings on Bot Startup
- **File**: `bot.py` (or main bot initialization file)
- **Action**: Call `ensure_column_mappings_initialized()` for each guild in `on_ready()`
- **Purpose**: Ensure all guilds have column mappings before any operations

### Step 3: Add Cache Refresh After Registration
- **File**: `core/views.py`
- **Function**: `complete_registration()`
- **Action**: Add `await refresh_sheet_cache(bot=interaction.client, force=True)` before `update_unified_channel()`
- **Purpose**: Ensure UI uses fresh data

### Step 4: Add Diagnostic Logging
- **Files**: `integrations/sheets.py`, `core/views.py`
- **Action**: Add logging to track Discord name writes and cache state
- **Purpose**: Help diagnose if issues persist

### Step 5: Test Complete Flow
1. Start bot (mappings should be detected and saved)
2. Check logs for "Column mappings saved for guild..."
3. Register a user
4. Check logs for "Writing Discord tag to column..."
5. Verify Discord name appears in sheet
6. Verify UI updates immediately

## Expected Outcomes

✅ Column mappings automatically detected and saved on bot startup  
✅ Discord names written to correct column in Google Sheet  
✅ Registration count updates immediately in LayoutView  
✅ Progress bars reflect new registrations instantly  
✅ No more stale cache data in UI  
✅ Comprehensive logging for troubleshooting

## Files to Modify

1. **`integrations/sheet_detector.py`**: Add initialization helper
2. **`bot.py`**: Add startup column mapping initialization
3. **`core/views.py`**: Add cache refresh before UI update
4. **`integrations/sheets.py`**: Add diagnostic logging

## Risk Assessment

**Low Risk**: 
- Column detection already exists and works
- We're just adding persistence of detected columns
- Cache refresh is already used elsewhere
- Logging is non-invasive

**Testing Requirements**:
- Test with fresh guild (no existing mappings)
- Test registration flow end-to-end
- Verify sheet writes
- Verify UI updates