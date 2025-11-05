# Fix Cache Data Type Inconsistency - Boolean vs String Registration Status

## Critical Issue Identified

**Logs show**:
```
22:56:19 | [CACHE] Cache refreshed: 0 changes, 1 total users  ✅ Cache HAS 1 user
22:56:19 | ✅ Cache verified: 0 users registered             ❌ Returns 0!
22:56:19 | UnifiedChannelLayoutView created                   ❌ Built with 0 users
22:56:20 | ✅ Updated unified channel                         ❌ Shows 0/24 players
```

**The Problem**: Cache contains the user, but `count_by_criteria()` can't find them!

## Root Cause Analysis

### Problem 1: Mixed Boolean/String Handling

**In cache refresh** (lines 473-477 in sheets.py):
```python
reg = str(reg_raw).upper() == "TRUE" if reg_raw else False  # Boolean
ci = str(ci_raw).upper() == "TRUE" if ci_raw else False    # Boolean
new_map[tag] = (idx, ign, reg, ci, team, alt, pronouns)    # Stores boolean
```

**But OLD cache might still have strings!** When we check "0 changes", we're comparing:
- `new_map[tag]` = `(3, "HYPExMon5ter#NA1", True, False, ...)`  (boolean)
- `old_map[tag]` = `(3, "HYPExMon5ter#NA1", "TRUE", "FALSE", ...)` (string)

These DON'T match, so it should show as "changed", but it shows "0 changes"!

### Problem 2: Unregistration Detection Bug

**Line 488-489**:
```python
if old_map[tag][2] and str(old_map[tag][2]).upper() == "TRUE":
```

This tries to handle both boolean and string, but the logic is inconsistent with how we're storing data.

### Problem 3: Cache Comparison Logic

**Line 482**:
```python
changed = {tag for tag in set(new_map) & set(old_map) if new_map[tag] != old_map[tag]}
```

This compares entire tuples:
- `(3, "HYPExMon5ter#NA1", True, False, ...)` ← New (boolean)
- `(3, "HYPExMon5ter#NA1", "TRUE", "FALSE", ...)` ← Old (string)

These are NOT equal (`True != "TRUE"`), so it SHOULD detect a change, but the logs show "0 changes".

**This means the old_map already has boolean values!** So why does count_by_criteria return 0?

### Problem 4: The Real Issue - Guild Filtering!

Looking back at `count_by_criteria()` - it accepts `guild_id` parameter but **NEVER USES IT**!

```python
async def count_by_criteria(
        guild_id: str,  # ← Parameter exists but never used!
        registered: Optional[bool] = None,
        ...
```

The cache stores users globally across all guilds, but we're not filtering by guild! If the cache was cleared or contains users from a different test, it won't find them.

## Comprehensive Solution

### Fix 1: Add Consistent Cache Type Conversion

**File**: `integrations/sheets.py` - Unregistration detection

**Current (line 488)**:
```python
for tag in removed:
    if old_map[tag][2] and str(old_map[tag][2]).upper() == "TRUE":
        unregistered_users.append(tag)
```

**Fixed**:
```python
for tag in removed:
    old_reg = old_map[tag][2]
    # Handle both boolean and string consistently
    was_registered = old_reg if isinstance(old_reg, bool) else str(old_reg).upper() == "TRUE"
    if was_registered:
        unregistered_users.append(tag)
```

**Same fix for line 495-497**:
```python
for tag in changed:
    old_data = old_map[tag]
    new_data = new_map[tag]
    # Consistent boolean handling
    old_reg = old_data[2]
    new_reg = new_data[2]
    old_registered = old_reg if isinstance(old_reg, bool) else str(old_reg).upper() == "TRUE"
    new_registered = new_reg if isinstance(new_reg, bool) else str(new_reg).upper() == "TRUE"
    if old_registered and not new_registered:
        unregistered_users.append(tag)
```

### Fix 2: Force Debug Logging for count_by_criteria

**File**: `core/views.py` - After cache verification

**Add temporary debug**:
```python
# 11b) Immediately verify cache state after refresh
from helpers.sheet_helpers import SheetOperations
import logging

# Force debug level temporarily
old_level = logging.getLogger().level
logging.getLogger().setLevel(logging.DEBUG)

registered_count = await SheetOperations.count_by_criteria(gid, registered=True)

# Restore log level
logging.getLogger().setLevel(old_level)

logging.info(f"✅ Cache verified: {registered_count} users registered")
```

This will show us the debug output to see what's actually happening in count_by_criteria.

### Fix 3: Add Direct Cache Inspection

**File**: `core/views.py` - After count_by_criteria

**Add direct cache check**:
```python
# Debug: Check cache directly
from integrations.sheets import sheet_cache
cache_users = dict(sheet_cache.get("users", {}))
logging.info(f"🔍 Direct cache check: {len(cache_users)} users in cache")
for tag, data in list(cache_users.items())[:3]:
    logging.info(f"  User: {tag}, reg_value={data[2]}, reg_type={type(data[2]).__name__}")
```

This will show us exactly what's in the cache and what data types are being used.

### Fix 4: Verify LayoutView Gets Correct Data

**File**: `core/components_traditional.py` - fetch_tournament_data()

**Add logging**:
```python
async def fetch_tournament_data(guild: discord.Guild) -> dict:
    """Fetch all async data needed for LayoutView."""
    guild_id = str(guild.id)
    # ... existing code ...
    
    # Get player counts using optimized cache snapshot
    cache_snapshot = await SheetOperations.get_cache_snapshot(guild_id)
    data['registered'] = cache_snapshot['registered_count']
    data['checked_in'] = cache_snapshot['checked_in_count']
    
    # DEBUG: Log what we're about to use
    logging.info(f"📊 fetch_tournament_data: registered={data['registered']}, checked_in={data['checked_in']}")
    
    # ... rest of function ...
```

### Fix 5: Possible Alternative - Clear and Rebuild Cache

If the cache has stale data, we might need to clear it completely:

**File**: `core/views.py` - Before cache refresh

```python
# 11) Force complete cache rebuild
logging.info(f"🔄 Forcing complete cache rebuild for {discord_tag}")
from integrations.sheets import refresh_sheet_cache, sheet_cache

# Option A: Clear cache entirely before refresh
async with cache_lock:
    sheet_cache["users"] = {}
    
await refresh_sheet_cache(bot=interaction.client, force=True)
```

## Implementation Order

### Phase 1: Diagnostic Logging (IMMEDIATE)
1. ✅ Add forced debug logging to count_by_criteria call
2. ✅ Add direct cache inspection after count
3. ✅ Add logging to fetch_tournament_data
4. ✅ Test registration and capture full logs

### Phase 2: Fix Type Handling
5. ✅ Fix unregistration detection to handle both types consistently
6. ✅ Verify cache comparison logic works correctly
7. ✅ Test registration flow again

### Phase 3: Nuclear Option
8. ✅ If still broken, clear cache before refresh
9. ✅ Force complete rebuild from sheet

## Expected Debug Output

After adding diagnostic logging, we should see:
```
✅ Cache verified: 0 users registered
🔍 count_by_criteria: 1 users in cache, filtering by registered=True
  Checking hypexmon5ter: reg=True (bool) -> reg_bool=True
  ✅ hypexmon5ter matches criteria
count_by_criteria result: 1 users matched
🔍 Direct cache check: 1 users in cache
  User: hypexmon5ter, reg_value=True, reg_type=bool
📊 fetch_tournament_data: registered=1, checked_in=0
```

If we see this, the issue is somewhere else. If we don't see the debug logs, that's the problem.

## Most Likely Root Cause

Based on the logs showing "0 changes", I suspect:
1. **Cache is being reused** from a previous registration attempt
2. **User is already in cache** with registration=False
3. **Cache refresh sees no changes** because user already exists
4. **count_by_criteria** correctly returns 0 because reg=False

**Solution**: Clear the cache entry for this user before registration, or force a complete cache rebuild.

This comprehensive diagnostic approach will reveal the exact issue! 🔍