# Fix Deadlock and Optimize Column Detection

## Critical Issues Identified

### Problem 1: Deadlock Causing 27-Second Timeout
**Symptoms**:
- Logs hang at "Extracted 6 columns from batch fetch"
- 27-second timeout at startup
- Registration hangs at same spot
- Never reaches "[CACHE] Cache refreshed"

**Root Cause - DEADLOCK**:
```python
# Line 359: Outer lock
async with cache_lock:
    try:
        # ... lots of code ...
        
        # Line 503: Inner lock - DEADLOCK!
        async with cache_lock:  # ❌ Trying to acquire lock we already hold!
            sheet_cache["users"] = new_map
            cache_manager.mark_refresh()
```

**Explanation**: 
- Python's `asyncio.Lock` is NOT reentrant
- Once acquired, trying to acquire it again in the same task causes deadlock
- The task waits forever for itself to release the lock
- After timeout, system continues with stale data

### Problem 2: Column Detection Every Time
**Current Behavior**:
- Column detection runs on every cache refresh
- Adds latency to every registration
- Unnecessary API calls to Google Sheets

**Opportunity**:
- Column headers rarely change
- Should be cached and persisted
- Only re-detect when explicitly requested

## Comprehensive Solution

### Fix 1: Remove Nested Lock (CRITICAL)

**File**: `integrations/sheets.py` line 503

**Current (DEADLOCK)**:
```python
# Line 359: Outer lock
async with cache_lock:
    try:
        # ... process data ...
        
        # Line 503: DEADLOCK - nested lock!
        async with cache_lock:
            sheet_cache["users"] = new_map
            cache_manager.mark_refresh()
```

**Fixed (NO DEADLOCK)**:
```python
# Line 359: Outer lock
async with cache_lock:
    try:
        # ... process data ...
        
        # Line 503: NO nested lock - already inside outer lock!
        sheet_cache["users"] = new_map
        cache_manager.mark_refresh()
```

**Why This Works**:
- We're already inside `cache_lock` from line 359
- Don't need to acquire it again
- Direct assignment is safe within the outer lock

### Fix 2: Cache Column Mappings to File

**New File**: `storage/column_mappings.json`

**Structure**:
```json
{
  "1385739351505240074": {
    "discord_column": "B",
    "ign_column": "D",
    "pronouns_column": "C",
    "alt_ign_column": "E",
    "registered_column": "F",
    "checkin_column": "G",
    "team_column": null,
    "last_updated": "2025-11-04T22:30:00Z",
    "sheet_url": "https://docs.google.com/spreadsheets/d/..."
  }
}
```

**Implementation**:

**File**: `integrations/sheet_detector.py`

Add functions:
```python
import json
import os
from datetime import datetime
from pathlib import Path

COLUMN_CACHE_FILE = "storage/column_mappings.json"

async def load_cached_column_mapping(guild_id: str) -> Optional[ColumnMapping]:
    """Load column mapping from file cache."""
    try:
        if not os.path.exists(COLUMN_CACHE_FILE):
            return None
            
        with open(COLUMN_CACHE_FILE, 'r') as f:
            data = json.load(f)
            
        if guild_id not in data:
            return None
            
        cached = data[guild_id]
        mapping = ColumnMapping()
        mapping.discord_column = cached.get("discord_column")
        mapping.ign_column = cached.get("ign_column")
        mapping.pronouns_column = cached.get("pronouns_column")
        mapping.alt_ign_column = cached.get("alt_ign_column")
        mapping.registered_column = cached.get("registered_column")
        mapping.checkin_column = cached.get("checkin_column")
        mapping.team_column = cached.get("team_column")
        
        logging.info(f"✅ Loaded cached column mapping for guild {guild_id}")
        return mapping
        
    except Exception as e:
        logging.warning(f"Failed to load cached column mapping: {e}")
        return None

async def save_cached_column_mapping(guild_id: str, mapping: ColumnMapping, sheet_url: str):
    """Save column mapping to file cache."""
    try:
        # Ensure storage directory exists
        Path("storage").mkdir(exist_ok=True)
        
        # Load existing data
        data = {}
        if os.path.exists(COLUMN_CACHE_FILE):
            with open(COLUMN_CACHE_FILE, 'r') as f:
                data = json.load(f)
        
        # Update with new mapping
        data[guild_id] = {
            "discord_column": mapping.discord_column,
            "ign_column": mapping.ign_column,
            "pronouns_column": mapping.pronouns_column,
            "alt_ign_column": mapping.alt_ign_column,
            "registered_column": mapping.registered_column,
            "checkin_column": mapping.checkin_column,
            "team_column": mapping.team_column,
            "last_updated": datetime.utcnow().isoformat(),
            "sheet_url": sheet_url
        }
        
        # Write back to file
        with open(COLUMN_CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        logging.info(f"✅ Saved cached column mapping for guild {guild_id}")
        
    except Exception as e:
        logging.error(f"Failed to save cached column mapping: {e}")

async def clear_cached_column_mapping(guild_id: str):
    """Clear cached column mapping (for /gal cache command)."""
    try:
        if not os.path.exists(COLUMN_CACHE_FILE):
            return
            
        with open(COLUMN_CACHE_FILE, 'r') as f:
            data = json.load(f)
        
        if guild_id in data:
            del data[guild_id]
            
        with open(COLUMN_CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        logging.info(f"✅ Cleared cached column mapping for guild {guild_id}")
        
    except Exception as e:
        logging.error(f"Failed to clear cached column mapping: {e}")
```

**Update**: `integrations/sheet_detector.py` - `get_column_mapping()`

```python
async def get_column_mapping(guild_id: str, force_redetect: bool = False) -> ColumnMapping:
    """
    Get column mapping for a guild, using cache when available.
    
    Args:
        guild_id: Guild ID
        force_redetect: If True, bypass cache and re-detect columns
    """
    # Check file cache first (unless force redetect)
    if not force_redetect:
        cached = await load_cached_column_mapping(guild_id)
        if cached and cached.discord_column:  # Verify we have required columns
            return cached
    
    # Not in cache or force redetect - perform detection
    logging.info(f"Detecting columns for guild {guild_id}...")
    
    # ... existing detection logic ...
    
    # Save to file cache
    mode = get_event_mode_for_guild(guild_id)
    cfg = get_sheet_settings(mode)
    sheet_url = cfg.get("sheet_url_dev") or cfg.get("sheet_url_prod")
    await save_cached_column_mapping(guild_id, mapping, sheet_url)
    
    return mapping
```

### Fix 3: Add /gal cache Command to Force Redetection

**File**: `core/commands/admin.py` or wherever `/gal` commands are

```python
@gal_group.command(name="cache", description="Force cache refresh and column redetection")
@app_commands.checks.has_permissions(administrator=True)
async def cache_refresh(interaction: discord.Interaction):
    """Force full cache refresh including column redetection."""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    try:
        # Clear cached column mapping
        from integrations.sheet_detector import clear_cached_column_mapping
        await clear_cached_column_mapping(guild_id)
        
        # Force cache refresh with column redetection
        from integrations.sheets import refresh_sheet_cache
        await refresh_sheet_cache(bot=interaction.client, force=True)
        
        await interaction.followup.send(
            "✅ Cache refreshed and columns re-detected successfully!",
            ephemeral=True
        )
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Cache refresh failed: {e}",
            ephemeral=True
        )
```

### Fix 4: Check for Other Nested Locks

**Files to check**:
- `integrations/sheets.py` lines 530, 699, 878, 934, 978
- Make sure none of these are inside the outer `cache_lock` at line 359

## Implementation Order

### Phase 1: Critical Deadlock Fix (IMMEDIATE)
1. ✅ Remove nested lock at line 503 in `integrations/sheets.py`
2. ✅ Test that cache refresh completes without hanging
3. ✅ Verify registration works and UI updates

### Phase 2: Column Caching (OPTIMIZATION)
4. ✅ Implement file-based column mapping cache
5. ✅ Update `get_column_mapping()` to use cache
6. ✅ Save mappings after detection
7. ✅ Add `/gal cache` command for manual refresh

### Phase 3: Verification
8. ✅ Test registration flow is fast (no 27-second delay)
9. ✅ Test UI updates work correctly
10. ✅ Test `/gal cache` command forces redetection

## Expected Results

### Before Fixes:
```
22:27:58 | Extracted 6 columns from batch fetch
[27-second hang - DEADLOCK]
22:28:25 | ERROR Cache refresh timed out
```

### After Fixes:
```
22:27:58 | Extracted 6 columns from batch fetch
22:27:58 | [CACHE] Cache refreshed: 1 changes, 1 total users  ✅ No hang!
22:27:58 | ✅ Updated unified channel
22:27:58 | ✅ Main embed updated successfully
```

### Performance Improvements:
- **Cache refresh**: 27 seconds → <2 seconds (no deadlock, no column detection)
- **Registration**: Fast and responsive
- **UI updates**: Immediate

### Column Detection:
- **First time**: Detect and cache to file (~2-3 seconds)
- **Subsequent times**: Load from file cache (<0.1 seconds)
- **Manual refresh**: `/gal cache` command forces redetection

This comprehensive fix will eliminate the deadlock and make the system much faster! 🎉