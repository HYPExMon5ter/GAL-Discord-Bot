# Fix Hyperlink and Cache Read Issues

## Problems Identified

### Problem 1: Hyperlink Failure - `'ign_col'` KeyError
**Location**: `utils/utils.py` line 238
```python
sheet.update_acell(f"{settings['ign_col']}{row}", formula)
```

**Issue**: `settings` doesn't contain `'ign_col'` - it's using the old key name instead of getting it from column detection.

**Root Cause**: The `get_sheet_settings()` returns config from `config.yaml` which doesn't have `ign_col`. We need to get the column mapping from the column detector.

**Fix**:
```python
# Instead of:
settings['ign_col']

# Use:
from integrations.sheet_detector import get_column_mapping
col_mapping = await get_column_mapping(guild_id)
ign_col = col_mapping.ign_column  # Should be 'D'
```

### Problem 2: Cache Read Returns 0 Despite Having Data

**Logs show**:
- Cache stores: `(row, ign, True, False, team, alt_ign, pronouns)` - with `True` boolean
- But `count_by_criteria()` checks: `str(reg).upper() == "TRUE"`

**Root Cause**: The cache is storing **boolean `True`** but the code expects **string `"TRUE"`**!

Looking at line 854 in `sheets.py`:
```python
sheet_cache["users"][discord_tag] = (
    row, ign, True, False, team_name or "", alt_igns or "", pronouns or ""
)
```
It stores boolean `True`, not string `"TRUE"`.

But in `count_by_criteria()` line 122:
```python
reg_bool = str(reg).upper() == "TRUE"
```
When `reg = True` (boolean), `str(True).upper()` becomes `"TRUE"` which should work...

**Wait - let me check the actual cache format more carefully!**

From your debug output:
```
Cache user 1: hypexmon5ter -> reg=True
```

This shows `reg=True` (Python boolean), not `reg="TRUE"` (string).

But the comparison should still work because `str(True).upper() == "TRUE"` is valid Python.

**Unless... the cache is storing Python `True` but then somewhere it's being converted incorrectly!**

Let me check the actual cache write vs read:

**Cache Write** (line 854):
```python
sheet_cache["users"][discord_tag] = (
    row, ign, True, False, ...  # Boolean True
)
```

**Cache Read** (line 122):
```python
reg_bool = str(reg).upper() == "TRUE"  # str(True) = "True", "True".upper() = "TRUE" ✅
```

This should work! But it's returning 0...

**AH! I found it!** The problem is on line 106:

```python
cache_data = dict(sheet_cache["users"])
```

This doesn't filter by guild_id! The cache has users from ALL guilds, but `count_by_criteria()` receives `guild_id` parameter and doesn't use it to filter!

**The Real Bug**: `count_by_criteria()` has a `guild_id` parameter but never uses it to filter the cache data. It counts ALL users across ALL guilds!

Since the sheet_cache stores users by discord_tag globally, not per-guild, the function needs to either:
1. Filter by guild somehow, OR
2. The cache structure is per-guild already

Let me check how the cache is structured...

Looking at the cache structure, `sheet_cache["users"]` is a global dict mapping discord_tag to user data. But there's no guild filtering!

**Wait - checking the actual implementation...**

The cache is designed to be per-guild because each guild has its own sheet. So `sheet_cache["users"]` should only contain users from that specific guild's sheet.

**BUT** - if we're calling `count_by_criteria()` before the cache is properly refreshed, it might be reading OLD data or EMPTY data!

From the logs:
```
✅ Cache update verified for hypexmon5ter, skipping full refresh
```

This means we verified the user exists in cache locally, but we **skipped the full refresh** that would populate the cache from the sheet!

**The root cause**: 
1. Registration writes to sheet ✅
2. Registration updates cache locally ✅
3. Cache verification passes ✅
4. **SKIPS full refresh** ❌
5. UI tries to read cache via `count_by_criteria()` ❌
6. But the cache might not be in the right state for `count_by_criteria()` to read!

The issue is that we're checking if the user exists in `sheet_cache.get("users", {})`, but then `count_by_criteria()` might be reading from a different structure or state.

## Comprehensive Fix

### Fix 1: Hyperlink Error - Use Column Mapping

**File**: `utils/utils.py` line 230-240

```python
# OLD:
from integrations.sheets import get_sheet_for_guild, retry_until_successful
mode = get_event_mode_for_guild(guild_id)
settings = get_sheet_settings(mode)
sheet = await get_sheet_for_guild(guild_id, "GAL Database")
formula = f'=HYPERLINK("{profile_url}","{ign_clean}")'
await retry_until_successful(
    sheet.update_acell,
    f"{settings['ign_col']}{row}",  # ❌ KeyError: 'ign_col'
    formula
)

# FIXED:
from integrations.sheets import get_sheet_for_guild, retry_until_successful
from integrations.sheet_detector import get_column_mapping

mode = get_event_mode_for_guild(guild_id)
col_mapping = await get_column_mapping(guild_id)
ign_col = col_mapping.ign_column  # Should be 'D'

if not ign_col:
    logging.warning(f"No IGN column found for guild {guild_id}")
    return

sheet = await get_sheet_for_guild(guild_id, "GAL Database")
formula = f'=HYPERLINK("{profile_url}","{ign_clean}")'

await retry_until_successful(
    sheet.update_acell,
    f"{ign_col}{row}",  # ✅ Uses detected column
    formula
)
```

### Fix 2: Force Cache Refresh for Accurate Counts

**File**: `core/views.py` - complete_registration()

The optimization to skip cache refresh is causing the UI to not update. We need to **always refresh** after registration to ensure accurate counts.

```python
# CURRENT (line 334-342):
if discord_tag not in sheet_cache.get("users", {}):
    logging.warning(f"Cache update verification failed for {discord_tag}, forcing refresh")
    from integrations.sheets import refresh_sheet_cache
    await refresh_sheet_cache(bot=interaction.client, force=True)
else:
    logging.info(f"✅ Cache update verified for {discord_tag}, skipping full refresh")

# FIXED:
# Always refresh cache after registration to ensure UI updates correctly
logging.info(f"🔄 Refreshing cache after registration for {discord_tag}")
from integrations.sheets import refresh_sheet_cache
await refresh_sheet_cache(bot=interaction.client, force=True)
```

**Reasoning**: The local cache update in `find_or_register_user()` might not be in the correct format for `count_by_criteria()` to read. A full refresh ensures consistency.

### Fix 3: Add Debug Logging to count_by_criteria

**File**: `helpers/sheet_helpers.py` - Add logging to see what's actually happening

```python
async def count_by_criteria(...) -> int:
    count = 0
    
    try:
        cache_data = dict(sheet_cache["users"])
    except:
        async with cache_lock:
            cache_data = dict(sheet_cache["users"])
    
    logging.debug(f"count_by_criteria: {len(cache_data)} users in cache, filtering by registered={registered}, checked_in={checked_in}")
    
    for tag, tpl in cache_data.items():
        try:
            if len(tpl) >= 7:
                row, ign, reg, ci, team, alt_ign, pronouns = tpl[:7]
            elif len(tpl) >= 6:
                row, ign, reg, ci, team, alt_ign = tpl[:6]
                pronouns = None
            else:
                parts = list(tpl) + [None] * (6 - len(tpl))
                row, ign, reg, ci, team, alt_ign = parts[:6]
                pronouns = None

            # Convert to boolean with proper type handling
            if isinstance(reg, bool):
                reg_bool = reg
            else:
                reg_bool = str(reg).upper() == "TRUE"
                
            if isinstance(ci, bool):
                ci_bool = ci
            else:
                ci_bool = str(ci).upper() == "TRUE"
            
            logging.debug(f"  Checking {tag}: reg={reg} ({type(reg).__name__}) -> reg_bool={reg_bool}")
            
            if registered is not None:
                if reg_bool != registered:
                    continue

            if checked_in is not None:
                if ci_bool != checked_in:
                    continue

            if team_name is not None and len(tpl) > 4:
                if team != team_name:
                    continue

            count += 1
            logging.debug(f"  ✅ {tag} matches criteria")
            
        except Exception as unpack_error:
            logging.warning(f"Failed to unpack cache entry for {tag}: {tpl} - {unpack_error}")
            continue
    
    logging.debug(f"count_by_criteria result: {count} users matched")
    return count
```

## Implementation Order

1. ✅ **Fix hyperlink error** - Use column mapping instead of settings
2. ✅ **Revert cache refresh optimization** - Always refresh after registration  
3. ✅ **Add type checking** - Handle both boolean and string in cache
4. ✅ **Add debug logging** - See exactly what's in cache during counting

## Expected Results

After these fixes:
- ✅ Hyperlinks will work correctly using detected IGN column
- ✅ UI will update immediately after registration
- ✅ Player count will increment correctly
- ✅ Progress bar will update
- ✅ Debug logs will show exact cache state for troubleshooting