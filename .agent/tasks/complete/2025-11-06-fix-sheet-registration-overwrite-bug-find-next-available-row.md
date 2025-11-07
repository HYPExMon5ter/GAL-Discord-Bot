# Fix Sheet Registration Overwrite Bug

## Problem Analysis

The issue is in `integrations/sheets.py` in the `find_or_register_user` function (around line 680-750). When registering a new user, the code **doesn't properly find the next available empty row**. Here's what's happening:

### Current Broken Logic (Lines 728-742):
```python
# Find first empty slot - check from header+1 to header+max_players for empty text content
target_row = None
start_row = hline + 1  # Start from header + 1 (skip header row)
end_row = hline + maxp  # End at header + max_players

for i in range(start_row - 1, end_row):  # -1 because array is 0-indexed, check full range
    # Convert to string and strip, then check if empty (matches cache refresh logic)
    cell_content = str(discord_vals[i]).strip() if i < len(discord_vals) else ""
    if not cell_content:
        target_row = i + 1  # Row numbers are 1-indexed
        break
```

**The bug**: The loop uses `i` which ranges from `start_row - 1` to `end_row`, but then accesses `discord_vals[i]`. The `discord_vals` array is already offset-adjusted from the fetch, so this creates an **off-by-one error** that causes it to always write to the same row.

### Root Cause:
1. `fetch_required_columns` returns data starting AFTER the header (already sliced)
2. The loop incorrectly indexes into this already-sliced array
3. Result: Always finds the same "empty" position and overwrites the previous user

## Optimal Solution (Best Performance)

### Strategy: **Use Cached Discord Column + Single Verification**

Since we already have the full discord column cached from the batch fetch, we can:
1. **Iterate through the cached column** to find the first empty slot (no API calls)
2. **Verify the target row is actually empty** with a single range read (1 API call for safety)
3. **Write to that row** using batch update (1 API call)

**Total: 2 API calls maximum** (vs current buggy 1-2 calls, but actually functional)

### Why This is Optimal:

1. **No Rate Limiting Risk**: Only 2 API calls per registration
2. **Fast**: Uses already-fetched column data for initial scan
3. **Safe**: Verifies target row before writing (prevents race conditions)
4. **Consistent**: Uses the same data structure as cache refresh
5. **Sheet-Aware**: Checks if target row has formatting (formatted rows are pre-allocated)

## Implementation Plan

### Changes to `integrations/sheets.py` - `find_or_register_user` function:

**Section 1: Fix the array indexing logic** (around line 728-742):
```python
# Find first empty slot in the discord column
target_row = None

# discord_vals is already post-header, 0-indexed array
# discord_vals[0] corresponds to row (hline + 1)
# discord_vals[i] corresponds to row (hline + 1 + i)

for array_idx in range(len(discord_vals)):
    cell_content = str(discord_vals[array_idx]).strip()
    if not cell_content:
        # Found empty slot - convert array index to actual sheet row number
        target_row = hline + 1 + array_idx
        logger.debug(f"Found empty slot at row {target_row} (array index {array_idx})")
        break
```

**Section 2: Add verification step** (new, insert after the above):
```python
# Verify the target row is actually empty (safety check for race conditions)
if target_row:
    try:
        # Read just the discord column cell for this row to verify
        verify_cell = await retry_until_successful(
            sheet.acell, 
            f"{cfg['discord_col']}{target_row}"
        )
        
        if verify_cell.value and str(verify_cell.value).strip():
            # Row is not actually empty, scan for next empty row
            logger.warning(f"Row {target_row} verification failed, scanning for next empty row")
            target_row = None
            
            # Fall back to appending new row if no empty slots found
            
    except Exception as e:
        logger.warning(f"Row verification failed: {e}, proceeding with target row {target_row}")
```

**Section 3: Update existing write logic** (already correct, just verify it handles both paths):
```python
if target_row:
    # Write to existing formatted row using batch update
    updates = [(f"{col}{target_row}", val) for col, val in writes.items()]
    success = await apply_sheet_updates(sheet, updates)
    if not success:
        raise SheetsError("Failed to update user data in batch")
    row = target_row
else:
    # Append new row (existing logic is fine)
    # ... existing append logic ...
```

### Testing Strategy:

1. **Unit Test**: Register 3 users sequentially, verify each gets a unique row
2. **Load Test**: Register 10 users rapidly, check for overwrites
3. **Cache Verification**: Confirm cache refresh shows all registered users
4. **Role Sync**: Verify all registered users have correct Discord roles

### Performance Characteristics:

- **API Calls**: 2 per registration (1 verification + 1 batch write)
- **Time Complexity**: O(n) where n = max_players, but only scans cached data
- **Rate Limit Impact**: Minimal (well within Google's 100 req/100sec/user limit)
- **Race Condition**: Mitigated by verification step

### Alternative Approaches Considered (and why rejected):

1. **❌ Append-only**: Would work but loses pre-formatted rows and breaks max_players logic
2. **❌ Fetch entire sheet each time**: Too many API calls, rate limit risk
3. **❌ Track last used row in cache**: Complex state management, race conditions
4. **❌ Use formula to find empty row**: Not supported by gspread efficiently

---

**This fix is minimal, performant, and leverages existing infrastructure. It corrects the indexing bug while adding a safety verification step.**