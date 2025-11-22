## Overview
Enhance both `/gal cache` command and the background `cache_refresh_loop` to perform comprehensive system refreshes including unified channel updates, role synchronization, and column re-detection.

## Current State Analysis

### What Currently Works
1. **`/gal cache` command** (in `core/commands/registration.py`):
   - Clears cached column mappings
   - Re-detects columns from sheet
   - Refreshes user data cache
   - Shows detected columns in response
   - ❌ Does NOT update unified channel embed
   - ❌ Does NOT show role sync results

2. **`cache_refresh_loop`** (in `integrations/sheets.py`):
   - Runs every N seconds (configurable)
   - Calls `refresh_sheet_cache(bot=bot, force=True)`
   - Updates unified channel for each guild
   - ✅ Already updates unified channel after cache refresh
   - ✅ Already handles multiple guilds

3. **`refresh_sheet_cache`** (in `integrations/sheets.py`):
   - Fetches all user data from Google Sheets
   - Updates in-memory cache
   - ✅ Already syncs Discord roles (lines 447-527)
   - ✅ Already processes waitlist
   - ❌ Does NOT re-detect columns
   - ❌ Does NOT update unified channel directly

### Role Synchronization (Already Implemented)
The `refresh_sheet_cache` function already performs comprehensive role sync:
- Grants "Registered" role to users who are registered in sheet
- Grants "Checked In" role to users who are checked in
- Removes stale roles from users not in cache
- Uses `RoleManager.sync_user_roles()` helper

## Proposed Changes

### 1. Enhance `/gal cache` Command
**File:** `core/commands/registration.py` (lines 305-370)

**Changes:**
```python
@command_tracer("gal.cache")
async def cache_refresh(interaction: discord.Interaction):
    """Force a complete cache refresh including column mappings, roles, and UI."""
    if not await ensure_staff(interaction, context="Cache Command"):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        start_time = time.time()
        
        # Step 1: Clear cached column mappings
        from integrations.sheet_detector import clear_cached_column_mapping
        await clear_cached_column_mapping(guild_id)
        
        # Step 2: Re-detect column mappings
        from integrations.sheet_detector import ensure_column_mappings_initialized
        mappings_detected = await ensure_column_mappings_initialized(guild_id)
        
        # Step 3: Refresh user data cache (includes role sync)
        total_changes, total_users = await refresh_sheet_cache(bot=interaction.client, force=True)
        
        # Step 4: Update unified channel embed
        from core.components_traditional import update_unified_channel
        ui_updated = await update_unified_channel(interaction.guild)
        
        # Step 5: Get detected mappings for reporting
        from integrations.sheet_detector import get_column_mapping
        mapping = await get_column_mapping(guild_id)
        
        # Build response with detailed results
        elapsed = time.time() - start_time
        
        # Column detection section
        detected_columns = []
        if mapping.discord_column:
            detected_columns.append(f"Discord: {mapping.discord_column}")
        # ... (all other columns)
        
        column_info = "\n• " + "\n• ".join(detected_columns) if detected_columns else "No columns detected"
        
        # Create comprehensive embed response
        embed = discord.Embed(
            title="🔄 Cache Refresh Complete",
            description=f"✅ Full system refresh completed in **{elapsed:.2f}s**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 User Data Cache",
            value=f"• Updated **{total_changes}** changes\n• Total users: **{total_users}**",
            inline=False
        )
        
        embed.add_field(
            name="📋 Column Detection",
            value=column_info,
            inline=False
        )
        
        embed.add_field(
            name="🔐 Role Synchronization",
            value="✅ Discord roles synced with sheet data",
            inline=False
        )
        
        embed.add_field(
            name="🎨 UI Update",
            value=f"{'✅ Unified channel updated' if ui_updated else '⚠️ UI update failed'}",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        # ... error handling
```

**What This Adds:**
- ✅ Step 4: Updates unified channel embed after cache refresh
- ✅ Detailed reporting of all operations performed
- ✅ Shows role sync was performed (already happens in refresh_sheet_cache)
- ✅ Shows UI update status
- ✅ Performance timing

### 2. Enhance `cache_refresh_loop` (Already Complete!)
**File:** `integrations/sheets.py` (lines 573-614)

**Current Implementation Analysis:**
```python
async def cache_refresh_loop(bot):
    """Background task to refresh cache periodically."""
    # ...
    while True:
        try:
            # 1. Refresh cache for all guilds (includes role sync)
            await refresh_sheet_cache(bot=bot, force=True)
            
            # 2. Update unified channel for each guild
            for guild in bot.guilds:
                try:
                    await update_unified_channel(guild)
                    logger.debug(f"Updated unified channel for guild {guild.name}")
                except Exception as e:
                    logger.error(f"Failed to update unified channel: {e}")
            
            logger.debug("Periodic cache refresh and UI update completed")
```

**Status:** ✅ **NO CHANGES NEEDED!** 

The loop already:
- Refreshes cache (which includes role sync)
- Updates unified channel for all guilds
- Handles errors gracefully
- Processes waitlist automatically

**Optional Enhancement:** Add column re-detection periodically (e.g., once per day)
```python
# Inside the loop, before refresh_sheet_cache
# Re-detect columns once per day (if it's been 24h since last detection)
if should_redetect_columns():  # Check timestamp
    for guild in bot.guilds:
        try:
            await clear_cached_column_mapping(str(guild.id))
            await ensure_column_mappings_initialized(str(guild.id))
        except Exception as e:
            logger.error(f"Column re-detection failed for {guild.name}: {e}")
```

### 3. Document Role Sync Behavior
**No code changes needed** - just document that `refresh_sheet_cache` already:
- Syncs roles for all users in cache
- Grants "Registered" role to registered users
- Grants "Checked In" role to checked-in users
- Removes stale roles from users not in sheet
- Logs role sync activity

## Summary of Changes

### Files to Modify:
1. **`core/commands/registration.py`** - Enhance `/gal cache` command with:
   - Unified channel update after cache refresh
   - Comprehensive status reporting
   - Performance metrics

### Files Already Complete:
1. **`integrations/sheets.py`** - `cache_refresh_loop` already updates UI
2. **`integrations/sheets.py`** - `refresh_sheet_cache` already syncs roles

### Benefits:
- ✅ `/gal cache` now performs full system refresh (cache + roles + UI + columns)
- ✅ Background loop already maintains consistency automatically
- ✅ Better visibility into what cache refresh does
- ✅ All changes are in one centralized location
- ✅ No breaking changes to existing behavior
- ✅ Comprehensive error handling and logging