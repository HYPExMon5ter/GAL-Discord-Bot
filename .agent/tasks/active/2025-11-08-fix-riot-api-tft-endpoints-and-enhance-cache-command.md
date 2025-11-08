# Fix Riot API TFT Endpoints and Enhance Cache Command

## Issue 1: Riot API KeyError - Using Wrong Endpoints

### Problem
The code is currently using LoL (`/lol/summoner/v4/`) endpoints instead of TFT (`/tft/summoner/v1/`) endpoints, causing the response to not contain expected fields like `id`.

### Root Cause
In `integrations/riot_api.py`:
- `get_summoner_by_puuid()` uses `/lol/summoner/v4/summoners/by-puuid/{puuid}`
- `get_league_entries()` uses `/tft/league/v1/entries/by-summoner/{summonerId}` (correct)
- **Mismatch**: TFT league API expects summoner ID from TFT summoner API, not LoL

### Solution
**Update `riot_api.py`** to use correct TFT endpoints:

```python
# CURRENT (WRONG):
async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
    """Get summoner information by PUUID."""
    platform = self._get_platform_endpoint(region)
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await self._make_request(url)

# FIXED (CORRECT):
async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
    """Get TFT summoner information by PUUID."""
    platform = self._get_platform_endpoint(region)
    url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    return await self._make_request(url)
```

**Verification Steps**:
1. Change `/lol/` to `/tft/` in the summoner endpoint
2. Response structure should be identical (both return `id`, `puuid`, `summonerLevel`, etc.)
3. Test with a known TFT player IGN

### Alternative Approach (If TFT endpoint doesn't work)
If the TFT summoner endpoint has issues, we can simplify the verification:
- **Remove** the `get_summoner_by_puuid()` call entirely from IGN verification
- **Only** use the Account API to verify the IGN exists
- The `summonerId` is only needed for fetching rank data, not for IGN verification
- Move the summoner API call to rank fetching code only

---

## Issue 2: /gal cache Command Doesn't Re-Detect Columns

### Problem
Running `/gal cache` only refreshes user data from Google Sheets but doesn't re-detect column mappings. If you add a new column (like rank), the bot won't detect it.

### Current Behavior
```python
@gal.command(name="cache", ...)
async def cache_refresh(interaction: discord.Interaction):
    await refresh_sheet_cache(force=True)  # Only refreshes user data
    await interaction.followup.send("✅ Sheet cache refresh triggered.")
```

### Solution
**Enhance the cache command** to also clear and re-detect column mappings:

```python
@gal.command(name="cache", ...)
async def cache_refresh(interaction: discord.Interaction):
    """Force a complete cache refresh including column mappings."""
    if not await ensure_staff(interaction, context="Cache Command"):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        # Step 1: Clear cached column mappings
        from integrations.sheet_detector import clear_cached_column_mapping
        await clear_cached_column_mapping(guild_id)
        
        # Step 2: Re-detect column mappings from sheet
        from integrations.sheet_detector import ensure_column_mappings_initialized
        mappings_detected = await ensure_column_mappings_initialized(guild_id)
        
        # Step 3: Refresh user data cache
        await refresh_sheet_cache(force=True)
        
        # Provide detailed feedback
        if mappings_detected:
            await interaction.followup.send(
                "✅ Complete cache refresh:\n"
                "• Column mappings re-detected\n"
                "• User data refreshed from sheet\n\n"
                "All new columns should now be detected.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "⚠️ Cache refresh completed but column mapping detection had issues.\n"
                "Check logs for details.",
                ephemeral=True,
            )
    except Exception as exc:
        await handle_command_exception(interaction, exc, "Cache Command")
```

### Additional Enhancement
**Add logging** to show what columns were detected:

```python
# After ensure_column_mappings_initialized():
from integrations.sheet_detector import get_column_mapping
mapping = await get_column_mapping(guild_id)

detected_columns = []
if mapping.discord_column:
    detected_columns.append(f"Discord: {mapping.discord_column}")
if mapping.ign_column:
    detected_columns.append(f"IGN: {mapping.ign_column}")
if mapping.rank_column:
    detected_columns.append(f"Rank: {mapping.rank_column}")
# ... add others

logger.info(f"Detected columns for guild {guild_id}: {', '.join(detected_columns)}")
```

---

## Implementation Order

1. **Fix Riot API endpoint** (`integrations/riot_api.py`)
   - Change `/lol/summoner/v4/` to `/tft/summoner/v1/` in `get_summoner_by_puuid()`
   - OR remove summoner API call from IGN verification entirely
   
2. **Enhance cache command** (`core/commands/registration.py`)
   - Import `clear_cached_column_mapping()` and `ensure_column_mappings_initialized()`
   - Add column mapping refresh before user data refresh
   - Update response message to reflect complete refresh

3. **Test both fixes**:
   - Test IGN verification with a known TFT player
   - Add a new column to Google Sheets
   - Run `/gal cache` and verify new column is detected
   - Register a player and verify rank is written

---

## Testing Checklist

**Riot API Fix**:
- [ ] IGN verification succeeds for valid TFT players
- [ ] No `'id'` KeyError in logs
- [ ] Summoner data is retrieved correctly
- [ ] Rank fetching works with the summoner ID

**Cache Command Fix**:
- [ ] `/gal cache` clears old column mappings
- [ ] New columns are detected after cache refresh
- [ ] User data is still refreshed correctly
- [ ] Detailed feedback message shows what was refreshed
- [ ] Logs show detected columns

---

## Alternative Solutions (If Issues Persist)

### For Riot API Issue:
If the TFT summoner endpoint still has issues, we can:
1. **Skip summoner data in verification**: Only verify the account exists via Account API
2. **Fetch summoner ID only when needed**: Move it to rank fetching code
3. **Use fallback logic**: Try TFT endpoint first, fallback to LoL endpoint

### For Cache Command:
If re-detection is slow or problematic:
1. **Add force parameter**: `/gal cache force:True` to re-detect columns
2. **Separate command**: `/gal detect-columns` for column mapping refresh
3. **Auto-detect on errors**: If column not found, trigger re-detection automatically

---

## Files to Modify

1. **`integrations/riot_api.py`**
   - Line ~265: `get_summoner_by_puuid()` method
   - Change endpoint from `/lol/` to `/tft/`

2. **`core/commands/registration.py`**
   - Line ~300: `cache_refresh()` command
   - Add column mapping refresh logic

3. **`integrations/ign_verification.py`** (optional)
   - Line ~100: `_verify_ign_with_riot_api()`
   - Remove or make optional the summoner API call

---

## Expected Outcomes

✅ **Riot API Fixed**: IGN verification works correctly without KeyError  
✅ **Cache Enhanced**: `/gal cache` now refreshes both user data AND column mappings  
✅ **Rank System Working**: Players can register and have their rank automatically fetched and stored  
✅ **Better UX**: Clear feedback on what was refreshed