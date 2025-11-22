# Implementation Plan: Fix Cache Command Error and Duplicate Command Registration

## Issues Identified

### Issue 1: Missing `logging` Import in registration.py
**Error**: `NameError: name 'logging' is not defined` at line 319 in `cache_refresh` command
**Root Cause**: The file imports `logger` from `.common` (a SecureLogger instance), but directly uses `logging.info()` instead of `logger.info()`

**Lines with the problem**:
- Line 319: `logging.info(f"Cleared cached column mappings for guild {guild_id}")`
- Line 326: `logging.warning(f"Failed to re-detect column mappings for guild {guild_id}")`
- Line 330: `logging.info(f"Refreshed user data cache for guild {guild_id}")`
- Line 354: `logging.info(f"Detected columns for guild {guild_id}: {', '.join(detected_columns)}")`
- Line 357: `logging.error(f"Error getting column mapping for guild {guild_id}: {mapping_error}")`

### Issue 2: Duplicate Command Registration in Production
**Problem**: Commands appear twice in Discord (screenshot shows two `/gal cache` commands)
**Root Cause**: Railway is NOT automatically setting `RAILWAY_ENVIRONMENT_NAME=production` for your production environment

**Evidence**:
- Your code already uses `RAILWAY_ENVIRONMENT_NAME` to detect production (in 10+ places: config.py, environment_helpers.py, persistence.py, etc.)
- Railway DOES automatically set this variable, but the environment name must match "production" exactly
- Your Railway environment is likely named something else (like "main" or "prod" or just left default)

**How your existing system works**:
```python
# From environment_helpers.py line 19
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
```

This checks if the environment name is exactly "production" - if Railway named it anything else, it returns False and the bot thinks it's in dev mode.

## Solution

### Fix 1: Replace `logging` with `logger` in registration.py ✅
Change all 5 occurrences of `logging.*()` to `logger.*()` in the `cache_refresh` function.

**Changes needed**:
```python
# Line 319
logging.info(...)  →  logger.info(...)

# Line 326
logging.warning(...)  →  logger.warning(...)

# Line 330
logging.info(...)  →  logger.info(...)

# Line 354
logging.info(...)  →  logger.info(...)

# Line 357
logging.error(...)  →  logger.error(...)
```

### Fix 2: Ensure Railway Environment is Named "production" ✅

**Option A: Rename your Railway environment (RECOMMENDED)**
1. Go to Railway Dashboard → Your Project
2. Click on the environment settings (top right)
3. Rename the environment to exactly `production`
4. Railway will automatically set `RAILWAY_ENVIRONMENT_NAME=production`

**Option B: Check what Railway is calling your environment**
1. Add temporary logging to bot startup to see what Railway sets
2. SSH into Railway: `railway run bash`
3. Run: `echo $RAILWAY_ENVIRONMENT_NAME`
4. If it's not "production", either rename the environment or modify the code

**Option C: Make the detection more flexible (if you can't rename)**
If your Railway environment is named something like "main" or "prod" and you can't rename it, we can update the detection logic to accept multiple names:

```python
# In environment_helpers.py line 19
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") in ["production", "main", "prod"]
```

**Why this fixes duplicates**:
1. Once Railway sets `RAILWAY_ENVIRONMENT_NAME=production`, your bot detects production mode
2. Production mode **only syncs globally** (bot.py lines 156-171)  
3. It explicitly clears guild-specific commands from DEV_GUILD_ID
4. This prevents the double registration

**No new environment variables needed** - you're already using the right system, just need to ensure Railway sets it correctly!

## Testing Plan

### Test Fix 1 (Locally)
1. Apply the logger changes
2. Run bot locally with dev environment
3. Execute `/gal cache` command  
4. Verify no `NameError` occurs
5. Check logs show proper cache refresh messages

### Test Fix 2 (Production)
1. Ensure Railway environment is named "production" (or update detection logic)
2. Deploy to Railway (or just restart if only renaming environment)
3. Wait 30 seconds for command sync to complete
4. Check Discord - duplicate commands should auto-clear on bot startup
5. Verify only ONE `/gal cache` command appears
6. Run `/gal cache` to verify it works

## Files to Modify

1. **core/commands/registration.py** - Replace 5 `logging.*` calls with `logger.*`
2. **Railway Dashboard** - Ensure environment is named "production" (NO code changes)
   - OR **helpers/environment_helpers.py** - Make detection more flexible if needed

## Why Your Existing System is Better

Your approach is actually superior because:
- ✅ **Sheet Selection**: Already uses `RAILWAY_ENVIRONMENT_NAME` to pick correct Google Sheet
- ✅ **Persistence Layer**: Uses it for database file naming  
- ✅ **Consistent**: One environment variable controls all environment-specific behavior
- ✅ **Railway Standard**: Uses Railway's built-in variable (no custom vars needed)

The bot's command sync logic already respects this - just need to ensure Railway environment naming is correct!

## Risk Assessment

- **Fix 1**: Low risk - simple variable rename, no logic changes
- **Fix 2**: Low risk - Railway automatically sets the variable, just need correct environment name
  - Bot already has auto-cleanup logic for duplicate commands (lines 162-169 in bot.py)
  - Worst case: manually clear duplicates via Discord bot portal if auto-clear fails