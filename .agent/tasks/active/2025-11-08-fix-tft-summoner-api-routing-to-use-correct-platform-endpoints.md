# Fix TFT Summoner API Routing to Use Correct Platform Endpoints

## Issue Analysis

### Problem
The TFT rank fetching system successfully verifies IGNs but fails to get summoner IDs, resulting in "No summoner ID available" errors. This prevents rank data from being fetched.

### Root Cause
Looking at the logs:
- **Account API succeeds**: IGN verification finds the accounts
- **Summoner API fails**: Returns empty response or no `id` field
- **Error pattern**: "No summoner ID available for {IGN} in {REGION}"

The issue is the **routing mismatch** between regional and platform endpoints:

1. **Account API** (`/riot/account/v1/`) uses **regional routing**: `americas`, `europe`, `asia`
2. **Summoner API** (`/tft/summoner/v1/`) uses **platform routing**: `na1`, `euw1`, `kr`, etc.

**Current flow**:
```python
# Step 1: Get Account (WORKS)
regional = self._get_regional_endpoint(region)  # "na" -> "americas"
url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

# Step 2: Get Summoner (FAILS)
platform = self._get_platform_endpoint(region)  # "na" -> "na1"
url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
# Problem: puuid is from "americas" but we're querying "na1"
```

### The Issue
The PUUID obtained from the Account API (which uses regional routing) might not be directly usable with platform-specific endpoints without proper routing. The summoner might exist in the regional database but the platform-specific query fails.

## Solution 1: Debug Current API Response (Recommended First Step)

Before changing the logic, let's understand what the API is actually returning.

### Add Detailed Debug Logging

**File**: `integrations/riot_api.py`

**In `get_highest_rank_across_accounts()` method** around line 519:

```python
# Get summoner info
try:
    summoner_data = await self.get_summoner_by_puuid(region, puuid)
    
    # ADD THIS DEBUG LOGGING:
    logger.info(f"🔍 DEBUG: Summoner API response for {riot_id_display} in {region.upper()}: {summoner_data}")
    logger.info(f"🔍 DEBUG: Response keys: {list(summoner_data.keys()) if isinstance(summoner_data, dict) else 'Not a dict'}")
    logger.info(f"🔍 DEBUG: Response type: {type(summoner_data)}")
    
    summoner_id = summoner_data.get("id")
    
    # ADD THIS:
    if not summoner_id:
        logger.error(f"🔍 DEBUG: summoner_data.get('id') returned None. Full response: {summoner_data}")
    
except Exception as summoner_error:
    logger.warning(f"Failed to get summoner data for {riot_id_display} in {region.upper()}: {summoner_error}")
    logger.error(f"🔍 DEBUG: Exception details: {type(summoner_error).__name__}: {summoner_error}")
    continue
```

This will tell us:
- Is the API returning a response?
- What fields does the response contain?
- Is `id` missing or just `None`?

## Solution 2: Alternative - Use League API Directly (If Summoner API is Unreliable)

If the TFT Summoner API is problematic, we can bypass it and query the League API directly with PUUID.

### Background
According to Riot API docs, the **League Entries endpoint** has an alternative:
- `/tft/league/v1/entries/by-summoner/{summonerId}` (current - requires summoner ID)
- But we can also iterate through league entries by tier/division

However, this is not practical for individual lookups.

## Solution 3: Use Correct Regional/Platform Routing

The real fix might be ensuring we're using the correct platform endpoint for each region.

### Verify Platform Endpoint Mapping

**File**: `integrations/riot_api.py`

Check if the platform endpoints are correct:

```python
PLATFORM_ENDPOINTS = {
    "na": "na1",
    "euw": "euw1",
    "eune": "eun1",
    "kr": "kr",
    "jp": "jp1",
    "oce": "oc1",
    "br": "br1",
    "lan": "la1",
    "las": "la2",
    "ru": "ru",
    "tr": "tr1"
}
```

These look correct, so the issue isn't the mapping.

## Solution 4: Implement Fallback to LoL Summoner API

Since the logs show "Summoner not found" which suggests the endpoint itself is working but returning 404, we might need to use the LoL Summoner API as a fallback.

### Update `get_summoner_by_puuid()` with Fallback

**File**: `integrations/riot_api.py` - Line ~287

```python
async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
    """Get TFT summoner information by PUUID with LoL fallback."""
    platform = self._get_platform_endpoint(region)
    
    # Try TFT endpoint first
    tft_url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    try:
        result = await self._make_request(tft_url)
        if result and result.get("id"):
            logger.debug(f"✅ Got summoner data from TFT API for {puuid[:8]}... in {region}")
            return result
        else:
            logger.warning(f"⚠️ TFT API returned empty/incomplete data for {puuid[:8]}... in {region}")
    except RiotAPIError as e:
        logger.warning(f"TFT Summoner API failed for {puuid[:8]}... in {region}: {e}")
    
    # Fallback to LoL endpoint (might work for TFT players too)
    lol_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    try:
        result = await self._make_request(lol_url)
        if result and result.get("id"):
            logger.info(f"✅ Got summoner data from LoL API fallback for {puuid[:8]}... in {region}")
            return result
        else:
            logger.error(f"❌ LoL API also returned empty data for {puuid[:8]}... in {region}")
            raise RiotAPIError("Both TFT and LoL Summoner APIs returned empty data")
    except RiotAPIError as e:
        logger.error(f"❌ Both TFT and LoL Summoner APIs failed for {puuid[:8]}... in {region}")
        raise RiotAPIError(f"Summoner not found: {e}")
```

## Solution 5: Check API Key Permissions

Another possibility is that the API key doesn't have proper TFT permissions.

### Verify API Key Has TFT Access

Check in Riot Developer Portal:
1. Go to https://developer.riotgames.com/
2. Check API key permissions
3. Ensure TFT API access is enabled
4. Try regenerating the API key if needed

## Recommended Implementation Order

### Phase 1: Debug (Do First)
1. ✅ Add detailed debug logging (Solution 1)
2. ✅ Run a test registration to see what the API actually returns
3. ✅ Analyze the logs to understand the exact issue

### Phase 2: Fix (Based on Debug Results)
If API returns empty but no error:
- Implement Solution 4 (Fallback to LoL API)

If API returns 404:
- Check API key permissions (Solution 5)
- Implement fallback logic

If API returns data but wrong format:
- Fix parsing logic

### Phase 3: Verify
1. Test with known accounts in different regions
2. Verify rank fetching works
3. Check that both TFT and LoL summoner data work

## Implementation Code

### File 1: `integrations/riot_api.py`

**Add debug logging** around line 519:

```python
# Current problematic section
try:
    summoner_data = await self.get_summoner_by_puuid(region, puuid)
    logger.info(f"🔍 Summoner API response for {riot_id_display}: {summoner_data}")
    summoner_id = summoner_data.get("id")
    if not summoner_id:
        logger.error(f"❌ No 'id' in response. Keys: {list(summoner_data.keys())}")
except Exception as summoner_error:
    logger.error(f"❌ Summoner API exception: {type(summoner_error).__name__}: {summoner_error}")
    continue
```

**Update `get_summoner_by_puuid()` with fallback** around line 287:

```python
async def get_summoner_by_puuid(self, region: str, puuid: str) -> Dict[str, Any]:
    """Get summoner information by PUUID (tries TFT, falls back to LoL)."""
    platform = self._get_platform_endpoint(region)
    
    # Try TFT API first
    tft_url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    try:
        result = await self._make_request(tft_url)
        if result and result.get("id"):
            return result
    except RiotAPIError:
        pass  # Try fallback
    
    # Fallback to LoL API
    lol_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await self._make_request(lol_url)
```

## Expected Results

After implementing the fixes:

✅ **Debug logs show exact API response** 
✅ **Summoner ID successfully retrieved**
✅ **Rank fetching works for all regions**
✅ **Fallback to LoL API if TFT fails**
✅ **Clear error messages for actual failures**

## Testing Checklist

- [ ] Add debug logging
- [ ] Test with HYPExMon5ter#NA1 (NA region)
- [ ] Test with Baceha#0000 (EUW region)
- [ ] Test with Baceha#yay (EUW region)
- [ ] Verify summoner ID is retrieved
- [ ] Verify rank data is fetched
- [ ] Check logs for API response details
- [ ] Confirm both TFT and LoL APIs are tried

## Notes

- The issue is **NOT** with IGN verification (that works)
- The issue is with the **Summoner API call** after getting PUUID
- Need to understand **what the API actually returns** before implementing a fix
- Fallback to LoL API is a safe solution that should work