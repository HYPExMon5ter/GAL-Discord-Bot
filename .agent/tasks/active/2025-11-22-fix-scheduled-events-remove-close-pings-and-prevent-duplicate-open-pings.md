## Problem
When scheduled events close (registration/check-in), they are pinging roles when they shouldn't. Pings should **only** happen when channels **open**, not when they close.

## Root Cause Analysis

After reviewing the code, I found the actual issue:

### Current Code Structure
1. **`schedule_system_open()`** (lines 40-140) - Handles opening events
   - ✅ Updates state to open
   - ✅ Updates unified channel
   - ✅ Sends log embed
   - ✅ Sends role pings (Registration → @Angels, Check-in → @Registered)
   
2. **`schedule_system_close()`** (lines 143-189) - Handles closing events
   - ✅ Updates state to closed
   - ✅ Updates unified channel
   - ✅ Sends log embed
   - ✅ **Correctly has NO ping logic**

### The Real Problem
The close function doesn't ping, **BUT** there's a risk of duplicate pings when:
- Scheduled events are edited/rescheduled (triggers open again)
- System transitions from closed → open without checking previous state

## Solution

**1. Add state-checking to prevent duplicate open pings**

In `schedule_system_open()`, check if the system is already open before pinging:

```python
# Check previous state BEFORE updating
was_already_open = persisted[guild_id].get(f"{system_type}_open", False)

# Update state
if system_type == "registration":
    persisted[guild_id]["registration_open"] = True
elif system_type == "checkin":
    persisted[guild_id]["checkin_open"] = True

save_persisted(persisted)

# ... update unified channel ...

# Only ping if this is a NEW opening (not already open)
if unified_channel and not was_already_open:
    # ... existing ping logic (lines 88-133) ...
```

**2. Ensure close function never pings** (already correct, but verify)

The `schedule_system_close()` function correctly has **no ping logic** - just confirm it stays that way.

## Changes Required

**File: `core/discord_events.py`**
- Modify `schedule_system_open()` to check previous state before pinging
- Add `was_already_open` check around lines 59-61 (before state update)
- Wrap ping logic (lines 88-133) with `if not was_already_open:` condition

## Expected Behavior After Fix

| Event | Action | Ping? | Notes |
|-------|--------|-------|-------|
| Registration opens (scheduled) | Opens for first time | ✅ Yes - @Angels | One-time ping |
| Registration opens (edited event) | Already open | ❌ No ping | Prevents duplicate |
| Registration closes (scheduled) | Closes | ❌ No ping | Never pings on close |
| Check-in opens (scheduled) | Opens for first time | ✅ Yes - @Registered | One-time ping |
| Check-in opens (edited event) | Already open | ❌ No ping | Prevents duplicate |
| Check-in closes (scheduled) | Closes | ❌ No ping | Never pings on close |

## Summary
- ✅ Close events will **never** ping (already working correctly)
- ✅ Open events will **only ping once** when actually opening (new fix)
- ✅ Editing scheduled events won't cause duplicate pings (new fix)