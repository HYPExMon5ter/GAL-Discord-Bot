## Problem Analysis

The 4-step flow implementation has a **critical flaw**:

**Current Behavior:**
1. ✅ Step 1 finds account in regional (americas, europe)
2. ❌ Step 2 returns `null` from Active Shard API (account hasn't played TFT recently)
3. ❌ Code skips to next IGN → **No rank detection happens**

**Root Cause:**
The Active Shard API only returns data for accounts that have **recent TFT activity**. For inactive or old accounts (like your `Baceha#0000` in EUW), it returns `null` even though the account has rank/match history.

**Evidence from Logs:**
```
HYPExMon5ter#NA1: No active TFT shard → skipped rank detection
Baceha#0000: No active TFT shard → skipped rank detection (BUT THIS HAS RANK IN EUW!)
```

---

## Proposed Solution

Add a **smart fallback strategy** when Active Shard API returns `null`:

### Strategy: Try Platform Endpoints Based on Regional
When no active shard is found, intelligently try platform endpoints that belong to the found regional:

**Regional → Platform Mapping:**
- `americas` → Try: `na1`, `br1`, `la1`, `la2`, `oc1`
- `europe` → Try: `euw1`, `eun1`, `tr1`, `ru`
- `asia` → Try: `kr`, `jp1`
- `sea` → Try: `sg2`, `ph2`, `vn2`, `th2`, `tw2`

**Priority Order:**
1. Start with most common platform for that regional
2. Stop as soon as we find rank data

---

## Implementation Plan

### 1. Add Regional-to-Platforms Mapping
Add constant after `PLATFORM_TO_REGION`:

```python
# Maps regional to list of platforms to try (in priority order)
REGIONAL_TO_PLATFORMS = {
    "americas": ["na1", "br1", "la1", "la2", "oc1"],
    "europe": ["euw1", "eun1", "tr1", "ru"],
    "asia": ["kr", "jp1"],
    "sea": ["sg2", "ph2", "vn2", "th2", "tw2"]
}
```

### 2. Refactor Step 2 Logic in `get_highest_rank_across_accounts()`

**Current Code:**
```python
# Step 2: Get active TFT platform
active_platform = await self.get_active_tft_platform(found_regional, account_puuid)

if active_platform:
    logger.info(f"✅ Step 2: Active TFT platform: {active_platform}")
else:
    logger.info(f"ℹ️ Step 2: No active TFT shard (player hasn't played TFT)")
    continue  # ❌ THIS IS THE BUG - we give up too early!
```

**New Code:**
```python
# Step 2: Get active TFT platform (preferred method)
active_platform = await self.get_active_tft_platform(found_regional, account_puuid)

if active_platform:
    logger.info(f"✅ Step 2: Active TFT platform: {active_platform}")
    platforms_to_check = [active_platform]  # Only check the active one
else:
    logger.info(f"ℹ️ Step 2: No active TFT shard - using regional fallback")
    # Fallback: Try all platforms in this regional
    platforms_to_check = self.REGIONAL_TO_PLATFORMS.get(found_regional, [])
    
if not platforms_to_check:
    logger.warning(f"❌ No platforms to check for {found_regional}")
    continue

# Step 3 & 4: Try each platform until we find rank data
rank_found = False
for platform in platforms_to_check:
    # Map platform to region name
    region_name = None
    for region, plat in self.PLATFORM_ENDPOINTS.items():
        if plat == platform:
            region_name = region
            break
    
    if not region_name:
        continue
    
    # Try to get summoner and rank data on this platform
    try:
        logger.debug(f"🔍 Step 3: Trying platform {platform} for {riot_id_display}")
        
        # [Rest of Steps 3 & 4 logic here]
        # If we find rank, set rank_found = True and break
        
        if rank_found:
            break  # Stop trying other platforms
            
    except RiotAPIError as e:
        if "404" in str(e):
            logger.debug(f"No summoner on {platform}, trying next...")
            continue  # Try next platform
        else:
            logger.warning(f"Error on {platform}: {e}")
            continue
```

### 3. Update Steps 3 & 4 to Work in Loop

Current Steps 3 & 4 assume single platform. Need to:
- Move them inside a `for platform in platforms_to_check:` loop
- Track if rank was found with `rank_found` flag
- Break loop early if rank found
- Continue to next platform if 404/not found

---

## Expected Behavior After Fix

**Test Case: Your Accounts**

1. **HYPExMon5ter#NA1** (no TFT history):
   - Step 1: ✅ Found in americas
   - Step 2: ℹ️ No active shard → fallback to platforms: [na1, br1, la1, la2, oc1]
   - Step 3-4: Try na1 → 404 not found, try br1 → 404, ... → Eventually: Unranked
   - Result: ✅ "Iron IV" (default)

2. **Baceha#0000** (has rank in EUW):
   - Step 1: ✅ Found in europe (from americas search, account is global)
   - Step 2: ℹ️ No active shard → fallback to platforms: [euw1, eun1, tr1, ru]
   - Step 3: Try euw1 → ✅ Found summoner ID
   - Step 4: ✅ Found rank "Gold II" (or whatever it actually is)
   - Result: ✅ Returns actual rank

3. **Highest Rank Logic**:
   - HYPExMon5ter: Iron IV
   - Baceha: Gold II
   - **Returns: Gold II** ✅

---

## Files to Modify

1. **`integrations/riot_api.py`**
   - Add `REGIONAL_TO_PLATFORMS` constant
   - Refactor Step 2 in `get_highest_rank_across_accounts()`
   - Move Steps 3 & 4 into loop over platforms
   - Add proper error handling for platform fallback

---

## Testing Checklist

1. ✅ Account with active shard (normal flow)
2. ✅ Account with no active shard but has rank (your Baceha case)
3. ✅ Account with no TFT history at all (your HYPExMon5ter case)
4. ✅ Multiple alts across regions with different ranks
5. ✅ Verify highest rank is selected correctly

---

## Performance Considerations

**Worst Case:** Account found in americas, no active shard, no rank anywhere
- Will try: na1, br1, la1, la2, oc1 (5 API calls)
- With rate limiting: ~2-3 seconds total
- **Acceptable** for registration flow

**Best Case:** Account has active shard
- Only 1 platform checked (current behavior)
- ~0.5 seconds

**Your Case:** Account in europe regional, rank on euw1
- Will try: euw1 (first platform) → ✅ Found immediately
- ~0.5 seconds