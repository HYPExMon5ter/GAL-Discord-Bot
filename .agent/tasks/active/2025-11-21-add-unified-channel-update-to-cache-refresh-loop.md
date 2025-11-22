# Implementation Plan: Add Unified Channel Update to Cache Refresh Loop

## Problem Identified

The timed cache refresh (runs every 10 minutes by default) updates the sheet data and syncs roles, but **does not update the unified channel embed**. This causes:
- Player count doesn't update in the main embed
- Capacity bar doesn't update
- Check-in progress bar doesn't update
- Registered/checked-in users see stale data

## Root Cause

Looking at `integrations/sheets.py`:

1. **`refresh_sheet_cache()` function** (lines 255-569):
   - Refreshes user data from Google Sheets
   - Syncs Discord roles with sheet data
   - Processes waitlist
   - **Does NOT update unified channel** (intentionally removed per comment on line 563)

2. **`cache_refresh_loop()` function** (lines 573-605):
   - Calls `refresh_sheet_cache(bot=bot, force=True)`
   - **Does NOT call `update_unified_channel()` afterward**
   - Only logs "Periodic cache refresh completed"

## Why This Happens

The comment on line 563 explains:
```python
# NOTE: Removed duplicate UI update - let callers handle UI updates
# This prevents race conditions where cache refresh triggers UI update
# before the calling function completes its operations
```

This design choice means:
- **Manual cache refresh** (`/gal cache` command) - ✅ Updates unified channel (handled by command)
- **User registration/check-in** - ✅ Updates unified channel (handled by views)
- **Timed background refresh** - ❌ Does NOT update unified channel

## Solution

Add `update_unified_channel()` call after `refresh_sheet_cache()` in the `cache_refresh_loop()` function.

### Changes Needed

**File**: `integrations/sheets.py`
**Function**: `cache_refresh_loop()` (lines 573-605)

**Before**:
```python
async def cache_refresh_loop(bot):
    """Background task to refresh cache periodically."""
    from config import _FULL_CFG
    cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)
    
    await asyncio.sleep(cache_refresh_seconds)
    
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    while True:
        try:
            # Process each guild separately to update unified channels
            for guild in bot.guilds:
                await refresh_sheet_cache(bot=bot, force=True)
            logger.debug("Periodic cache refresh completed")
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Periodic cache refresh failed: {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many cache refresh failures, waiting 5 minutes")
                await asyncio.sleep(300)
                consecutive_errors = 0
                continue
        
        cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)
        await asyncio.sleep(cache_refresh_seconds)
```

**After**:
```python
async def cache_refresh_loop(bot):
    """Background task to refresh cache periodically."""
    from config import _FULL_CFG
    from core.components_traditional import update_unified_channel
    
    cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)
    
    await asyncio.sleep(cache_refresh_seconds)
    
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    while True:
        try:
            # Refresh cache for all guilds
            await refresh_sheet_cache(bot=bot, force=True)
            
            # Update unified channel for each guild after cache refresh
            for guild in bot.guilds:
                try:
                    await update_unified_channel(guild)
                    logger.debug(f"Updated unified channel for guild {guild.name} after cache refresh")
                except Exception as e:
                    logger.error(f"Failed to update unified channel for guild {guild.name}: {e}")
            
            logger.debug("Periodic cache refresh and UI update completed")
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Periodic cache refresh failed ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many cache refresh failures, waiting 5 minutes before retry")
                await asyncio.sleep(300)
                consecutive_errors = 0
                continue
        
        cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)
        await asyncio.sleep(cache_refresh_seconds)
```

## Key Changes

1. **Import added**: `from core.components_traditional import update_unified_channel`
2. **Loop structure changed**: Call `refresh_sheet_cache()` once (not in guild loop)
3. **Added unified channel update**: After cache refresh, iterate through guilds and update each unified channel
4. **Better error handling**: Each guild's unified channel update is wrapped in try/except
5. **Better logging**: Log which guild was updated and if it failed

## Why This Solution

### Benefits:
- ✅ **Unified channel always stays in sync** with sheet data
- ✅ **No race conditions** - cache refresh completes first, then UI updates
- ✅ **Per-guild error handling** - if one guild fails, others still update
- ✅ **Minimal performance impact** - only 1 extra operation per guild per refresh cycle

### Safety:
- ✅ **Non-breaking** - only adds functionality, doesn't remove anything
- ✅ **Error-isolated** - if unified channel update fails, cache refresh still succeeded
- ✅ **Backwards compatible** - manual refresh and user actions still work as before

## Testing Plan

1. **Test Timed Refresh**:
   - Remove a user from Google Sheet
   - Wait for next cache refresh (default: 10 minutes, or configure shorter for testing)
   - Check unified channel - player count and capacity bar should update

2. **Test Manual Refresh**:
   - Remove a user from Google Sheet
   - Run `/gal cache` command
   - Verify it still works as expected

3. **Test User Actions**:
   - Register a user
   - Check-in a user
   - Verify unified channel updates immediately (existing behavior)

4. **Test Multi-Guild**:
   - If bot is in multiple guilds, verify all update correctly
   - Verify one guild's failure doesn't break others

## Alternative Considered

**Option**: Add `update_unified_channel()` inside `refresh_sheet_cache()` at the end

**Rejected because**:
- Would cause duplicate updates when called from commands/views
- Original comment explains this was intentionally removed to prevent race conditions
- Better to handle UI updates at the caller level

## Risk Assessment

- **Risk**: Low
- **Impact**: High (fixes visible user-facing issue)
- **Rollback**: Simple - just remove the added loop if issues occur

## Performance Impact

- **Per refresh cycle**: 1 additional `update_unified_channel()` call per guild
- **Typical impact**: < 100ms per guild (just fetches cached data and edits Discord message)
- **Network calls**: Only 1 Discord API call (message edit) per guild, no Sheet API calls

## Files Modified

1. `integrations/sheets.py` - Update `cache_refresh_loop()` function (lines 573-605)