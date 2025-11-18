## Root Cause Analysis

The critical bug is in **Step 1** logic:

**Current (WRONG) Flow:**
```
For each IGN:
  For each regional (americas, europe, asia, sea):
    Try Account API → Found in americas → STOP searching
    Use Active Shard → null
    Fallback to americas platforms [na1, br1, la1, la2, oc1]
    ❌ NEVER tries europe platforms where player actually plays!
```

**Why This Happens:**
- Riot Account API is **GLOBAL** - the same account/PUUID exists on ALL regionals
- `Baceha#0000` is found in `americas` because ALL accounts exist in ALL regionals
- But the player actually plays TFT on `euw1` (europe)
- We stop searching after finding account in `americas`, so we never check `europe`

---

## Correct Solution

**Don't stop after finding account in one regional!** The account exists in ALL regionals. We need to:

1. Try Active Shard API on **ALL regionals** (not just the first one that returns the account)
2. If Active Shard returns null everywhere, try **ALL platforms across ALL regionals**

---

## Implementation Plan

### Option A: Remove Step 1 Entirely (RECOMMENDED)

**New Flow:**
```
For each IGN:
  Parse game_name and tag_line
  
  // Step 1+2 Combined: Try Active Shard on all regionals
  For each regional (americas, europe, asia, sea):
    Get PUUID (we know account exists globally, just get it once)
    Try Active Shard API for this regional
    
    If active_platform found:
      Try to get rank on that platform → If found, compare and continue
      
  // Step 3: If no active shard anywhere, try all platforms
  If no rank found yet:
    For each regional (americas, europe, asia, sea):
      For each platform in regional:
        Try to get summoner and rank
        If found, compare and break
```

This fixes the issue because:
- We try Active Shard on **ALL regionals**, not just the first one
- We fallback to trying **ALL platforms** if no active shard found
- `Baceha#0000` will be checked: americas platforms → europe platforms (euw1 ✓) → found!

### Option B: Modify Step 1 to Get PUUID Once, Then Check All Regionals

```python
For each IGN:
    # Get PUUID once (works from any regional)
    puuid = get_puuid_from_any_regional(ign)
    
    if not puuid:
        continue  # Account doesn't exist
    
    # Try Active Shard API on EVERY regional
    platforms_to_check = []
    for regional in [americas, europe, asia, sea]:
        active_platform = get_active_shard(regional, puuid)
        if active_platform:
            platforms_to_check.append(active_platform)
    
    # If no active shards, fall back to ALL platforms
    if not platforms_to_check:
        platforms_to_check = [all platforms from all regionals]
    
    # Try each platform
    for platform in platforms_to_check:
        try_get_rank(platform, puuid)
```

---

## Recommended Implementation (Option A - Cleaner)

### 1. Simplify Account Lookup

Instead of looping through regionals to find account, just use `americas` (accounts are global):

```python
# Step 1: Get PUUID (account is global, use any regional)
try:
    game_name, tag_line = self._parse_riot_id(ign, default_region)
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    account_data = await self._make_request(url)
    puuid = account_data["puuid"]
    riot_id_display = f"{account_data['gameName']}#{account_data['tagLine']}"
except:
    logger.warning(f"Account not found: {ign}")
    continue
```

### 2. Check Active Shard on ALL Regionals

```python
# Step 2: Try Active Shard on ALL regionals
active_platforms = []
for regional in ["americas", "europe", "asia", "sea"]:
    platform = await self.get_active_tft_platform(regional, puuid)
    if platform:
        logger.info(f"Found active shard {platform} in {regional}")
        active_platforms.append(platform)

if active_platforms:
    platforms_to_check = active_platforms
else:
    # Fallback: Try ALL platforms from ALL regionals
    platforms_to_check = (
        self.REGIONAL_TO_PLATFORMS["americas"] +
        self.REGIONAL_TO_PLATFORMS["europe"] +
        self.REGIONAL_TO_PLATFORMS["asia"] +
        self.REGIONAL_TO_PLATFORMS["sea"]
    )
    logger.info(f"No active shards found - trying all {len(platforms_to_check)} platforms")
```

### 3. Try Each Platform (unchanged)

The rest of Steps 3 & 4 remain the same - loop through platforms and try to get rank.

---

## Expected Behavior After Fix

**Test Case 1: HYPExMon5ter#NA1**
- Step 1: Get PUUID from americas ✓
- Step 2: Try Active Shard on americas, europe, asia, sea → all return null
- Step 3: Fallback to ALL platforms: [na1, br1, la1, la2, oc1, euw1, eun1, tr1, ru, kr, jp1, sg2, ph2, vn2, th2, tw2]
- Step 4: Try each platform → No summoner found anywhere → Return Iron IV ✓

**Test Case 2: Baceha#0000 (plays on EUW)**
- Step 1: Get PUUID from americas ✓
- Step 2: Try Active Shard on americas, europe, asia, sea → all return null
- Step 3: Fallback to ALL platforms: [na1, br1, ..., **euw1**, ...]
- Step 4: Try na1 → 404, try br1 → 404, ..., **try euw1 → Found rank!** ✓
- Result: Returns actual rank from EUW ✓

**Test Case 3: LaurenTheCorgi#NA1**
- Step 1: Get PUUID from americas ✓
- Step 2: Check active shards → might find `na1` active
- Step 3: Only check `na1` platform
- Step 4: Get rank from na1 ✓

---

## Performance Impact

**Worst Case (no active shard, no rank anywhere):**
- 4 Active Shard API calls (one per regional)
- 16 Summoner API calls (one per platform)
- ~8-10 seconds total

**Best Case (active shard found):**
- 1-4 Active Shard API calls (stops when found)
- 1 Summoner API call
- ~1 second total

**Your Case (Baceha - rank on euw1, no active shard):**
- 4 Active Shard calls
- ~6-8 Summoner calls (tries americas platforms first, then finds on euw1)
- ~3-4 seconds total
- **Acceptable for registration flow**

---

## Files to Modify

1. **`integrations/riot_api.py`**
   - Simplify Step 1: Get PUUID once from any regional (use americas)
   - Fix Step 2: Try Active Shard on ALL regionals, collect all active platforms
   - Fix fallback: Use ALL platforms from ALL regionals if no active shards

---

## Testing Plan

Create test script that verifies:
1. `Baceha#0000` - finds rank on EUW even with no active shard
2. `LaurenTheCorgi#NA1` - finds rank on NA platform
3. Multiple alts with highest rank selection works correctly