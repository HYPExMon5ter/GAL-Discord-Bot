## Root Cause Analysis

The IGN verification in `ign_verification.py` has the **same bug** as the rank detection had:

**Current Flow (BROKEN):**
```python
for region in ["na", "euw", "eune", ...]:
    account_data = await riot_client.get_account_by_riot_id(region, game_name, tag_line)
    # get_account_by_riot_id converts "na" -> "americas" internally
    # Returns account from americas
    # But then tries to get summoner data from "na" platform
    # HYPExMon5ter exists globally but has NO SUMMONER on na1 platform
    # Verification fails!
```

**Problem:**
1. Account API is called correctly (gets account from regional)
2. But then it tries `get_summoner_by_puuid(region="na", puuid=...)`
3. This checks `na1` platform - but HYPExMon5ter has no TFT summoner on na1
4. Verification **fails** even though account exists!

---

## Solution

The IGN verification should use the **exact same logic** as the rank detection fix:

1. Get PUUID once (accounts are global)
2. **Don't require summoner data** - account existence is enough for verification!
3. If summoner check fails, still return success (account exists = valid IGN)

---

## Implementation Plan

### Update `_verify_ign_with_riot_api` in `ign_verification.py`

**Current Code (BROKEN):**
```python
for region in regions_to_try:
    # Get account (works - account is global)
    account_data = await riot_client.get_account_by_riot_id(region, game_name, tag_line)
    
    # Try to get summoner (FAILS if no TFT summoner on this platform)
    summoner_data = await riot_client.get_summoner_by_puuid(region, puuid)
    # If this raises exception, verification fails!
```

**New Code (FIXED):**
```python
# Step 1: Get PUUID (account is global, use any regional)
game_name, tag_line = riot_client._parse_riot_id(ign, default_region)
url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
account_data = await riot_client._make_request(url)

if not account_data or "puuid" not in account_data:
    return False, f"IGN '{ign}' not found", None

# Account exists - this is enough for verification!
puuid = account_data['puuid']
found_ign = f"{account_data['gameName']}#{account_data['tagLine']}"

# Step 2 (OPTIONAL): Try to get summoner data but DON'T fail verification if it doesn't exist
summoner_id = None
summoner_level = 0
profile_icon_id = 0

# Try to find summoner on ANY platform (not critical for verification)
try:
    # Could try multiple platforms here, but it's optional
    # For now, just try default region's platform
    summoner_data = await riot_client.get_summoner_by_puuid(default_region, puuid)
    summoner_id = summoner_data.get('id')
    summoner_level = summoner_data.get('summonerLevel', 0)
    profile_icon_id = summoner_data.get('profileIconId', 0)
except Exception:
    # This is OK - account exists, summoner data is just bonus
    pass

riot_data = {
    "ign": found_ign,
    "gameName": account_data['gameName'],
    "tagLine": account_data['tagLine'],
    "puuid": puuid,
    "summonerId": summoner_id,  # May be None
    "summonerLevel": summoner_level,
    "region": "GLOBAL",  # Account is global
    "profileIconId": profile_icon_id
}

return True, f"Verified (account exists)", riot_data
```

---

## Key Changes

1. **Single Account API call** using americas regional (accounts are global)
2. **Account existence = valid IGN** (don't require summoner data)
3. **Summoner data is optional** (nice to have but not required)
4. **No region loop** (account API returns same result from any regional)

---

## Expected Behavior After Fix

**Test Case: HYPExMon5ter#NA1**
- Step 1: Get account from americas → ✓ Found (PUUID: PKN1yqtS...)
- Step 2: Try to get summoner on na1 → Fails (no TFT summoner)
- Result: **✓ VERIFICATION SUCCESS** (account exists, summoner data optional)

**Test Case: Baceha#0000**
- Step 1: Get account from americas → ✓ Found (PUUID: aYUmeE1B...)
- Step 2: Try to get summoner on na1 → Fails (plays on EUW)
- Result: **✓ VERIFICATION SUCCESS** (account exists, summoner data optional)

**Test Case: InvalidName#1234**
- Step 1: Get account from americas → ❌ 404 not found
- Result: **✗ VERIFICATION FAILED** (account doesn't exist)

---

## Why This is Better

**Current Approach Problems:**
- ❌ Requires summoner data (not always available)
- ❌ Loops through all regions unnecessarily
- ❌ Fails valid accounts that have no summoner on default platform
- ❌ Inconsistent with rank detection logic

**New Approach Benefits:**
- ✓ Account existence is enough (correct definition of "valid IGN")
- ✓ Single API call (faster, fewer rate limit issues)
- ✓ Works for accounts with no TFT summoner
- ✓ Consistent with rank detection logic
- ✓ Summoner data is bonus (nice to have)

---

## Files to Modify

1. **`integrations/ign_verification.py`**
   - Simplify `_verify_ign_with_riot_api` to use global account lookup
   - Make summoner data optional (don't fail verification without it)
   - Remove region loop (accounts are global)

---

## Testing Checklist

1. ✓ HYPExMon5ter#NA1 - should verify successfully
2. ✓ Baceha#0000 - should verify successfully  
3. ✓ LaurenTheCorgi#NA1 - should verify successfully
4. ✓ InvalidName#1234 - should fail verification
5. ✓ Registration with main + alt should work for all combinations