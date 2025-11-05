# Simplify Cache System and Fix Multi-Guild Cache Access

## Root Cause - Multi-Guild Cache Design Flaw

**CRITICAL DISCOVERY**: The cache appears to be **GLOBAL** across all guilds, not per-guild!

```python
sheet_cache = {
    "users": {
        "hypexmon5ter": (3, "HYPExMon5ter#NA1", True, False, ...)
    }
}
```

But we're calling `count_by_criteria(guild_id="1385739351505240074")` with a guild_id that **isn't being used** to filter!

**The Problem**:
1. Cache is global (stores users from all guilds)
2. `count_by_criteria()` accepts `guild_id` but doesn't filter by it
3. Direct cache access shows 1 user
4. But count_by_criteria shows 0 users

**Why "Cache is EMPTY" warnings**:
- When `count_by_criteria()` tries to access `sheet_cache["users"]` 
- It gets the dict but then the for-loop might not iterate properly
- Or there's a different cache instance being accessed

## The Real Issue - Multiple Cache Instances

Looking at the imports:
- `core/views.py`: `from integrations.sheets import sheet_cache`
- `helpers/sheet_helpers.py`: `from integrations.sheets import sheet_cache`

They should be the same cache object, but the behavior suggests they're not!

**Possible causes**:
1. **Import timing**: Cache imported before initialization
2. **Legacy adapter override**: Line 325 in sheets.py replaces sheet_cache
3. **Circular imports**: Different modules getting different cache instances

## Comprehensive Cleanup and Fix

### Step 1: Remove Legacy Adapter Cache Replacement

**File**: `integrations/sheets.py` line 315-326

**Current**:
```python
_legacy_adapter = None

async def get_legacy_adapter():
    global _legacy_adapter
    if _legacy_adapter is None:
        from core.data_access.legacy_adapter import get_legacy_adapter as get_adapter
        _legacy_adapter = await get_adapter()
        # Replace the global cache with the adapter's cache for consistency
        global sheet_cache
        sheet_cache = _legacy_adapter.get_legacy_sheet_cache()  # ❌ REPLACES cache!
    return _legacy_adapter
```

**This is the smoking gun!** The legacy adapter might be replacing the cache with its own instance!

**Remove this** or ensure it's not being called during refresh.

### Step 2: Simplify Cache Access - Always Use .get()

**File**: `helpers/sheet_helpers.py` - count_by_criteria()

**Current**:
```python
try:
    cache_data = dict(sheet_cache["users"])  # ❌ KeyError if missing
except:
    async with cache_lock:
        cache_data = dict(sheet_cache["users"])
```

**Fixed**:
```python
# Simple and safe - no exception handling needed
cache_data = dict(sheet_cache.get("users", {}))

# If we need the lock, use it consistently
async with cache_lock:
    cache_data = dict(sheet_cache.get("users", {}))
```

### Step 3: Per-Guild Cache Structure (RECOMMENDED)

**Current Structure** (Global):
```python
sheet_cache = {
    "users": {
        "discord_tag": (row, ign, reg, ci, ...)
    }
}
```

**Proposed Structure** (Per-Guild):
```python
sheet_cache = {
    "guilds": {
        "1385739351505240074": {
            "users": {
                "discord_tag": (row, ign, reg, ci, ...)
            }
        }
    }
}
```

**Benefits**:
- Clear separation between guilds
- No confusion about which guild's data we're accessing
- Easier to clear cache for specific guild
- More maintainable

### Step 4: Simplify count_by_criteria

**File**: `helpers/sheet_helpers.py`

**Simplified**:
```python
@staticmethod
async def count_by_criteria(
        guild_id: str,
        registered: Optional[bool] = None,
        checked_in: Optional[bool] = None,
        team_name: Optional[str] = None
) -> int:
    """Count users matching specific criteria."""
    count = 0
    
    # Simple cache access with lock
    async with cache_lock:
        users = sheet_cache.get("users", {})
        
    logging.debug(f"count_by_criteria for guild {guild_id}: {len(users)} total users in cache")
    
    for discord_tag, user_data in users.items():
        try:
            # Unpack user data
            if len(user_data) < 4:
                continue
                
            row, ign, reg, ci = user_data[0], user_data[1], user_data[2], user_data[3]
            team = user_data[4] if len(user_data) > 4 else None
            
            # Convert to boolean properly
            if isinstance(reg, bool):
                is_registered = reg
            elif isinstance(reg, str):
                is_registered = reg.upper() == "TRUE"
            else:
                is_registered = False
                
            if isinstance(ci, bool):
                is_checked_in = ci
            elif isinstance(ci, str):
                is_checked_in = ci.upper() == "TRUE"
            else:
                is_checked_in = False
            
            # Apply filters
            if registered is not None and is_registered != registered:
                continue
            if checked_in is not None and is_checked_in != checked_in:
                continue
            if team_name is not None and team != team_name:
                continue
                
            count += 1
            logging.debug(f"  ✅ {discord_tag} matches criteria")
            
        except Exception as e:
            logging.warning(f"Error processing user {discord_tag}: {e}")
            continue
    
    logging.debug(f"count_by_criteria result: {count} matched")
    return count
```

### Step 5: Remove Legacy Adapter Usage

**Files to check**:
- `integrations/sheets.py` line 315-350
- Find where `get_legacy_adapter()` is called during cache refresh
- Remove or comment out if not essential

### Step 6: Ensure Single Cache Instance

**File**: `integrations/sheets.py` top of file

**Current**:
```python
sheet_cache = cache_manager.data  # Line 81
```

**Verify** this is the ONLY place where `sheet_cache` is defined and never reassigned.

## Implementation Order

### Phase 1: Critical Fixes (IMMEDIATE)
1. ✅ Fix count_by_criteria to use .get() instead of direct access
2. ✅ Remove or disable legacy adapter cache replacement
3. ✅ Simplify cache access logic
4. ✅ Test registration - should work immediately

### Phase 2: Cache System Simplification
5. ✅ Remove legacy adapter entirely if not needed
6. ✅ Simplify cache structure
7. ✅ Add proper guild filtering if needed

### Phase 3: Clean Legacy Code
8. ✅ Remove old conversion code
9. ✅ Remove migration logic
10. ✅ Clean up unnecessary complexity

## Expected Results

After fixes:
```
23:24:18 | [CACHE] Cache refreshed: 1 changes, 1 total users
23:24:18 | count_by_criteria: 1 users in cache          ✅ Finds users!
23:24:18 | ✅ Cache verified: 1 users registered         ✅ Correct count!
23:24:18 | 📊 fetch_tournament_data: registered=1        ✅ Correct data!
23:24:18 | UnifiedChannelLayoutView created with data: registered=1
23:24:18 | ✅ Main embed shows 1/24 players              ✅ UI updates!
```

This comprehensive cleanup will eliminate all the legacy complexity and make the cache system work reliably! 🎉