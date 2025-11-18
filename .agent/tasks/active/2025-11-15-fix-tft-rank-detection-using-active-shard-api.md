## Problem Analysis

Your current TFT rank detection has **2 critical issues**:

1. **Missing Active Shard API**: You're checking all regions blindly instead of using the `/active-shards` endpoint to find where the player actually plays TFT
2. **Incomplete Region Mapping**: Missing the `PLATFORM_TO_REGION` mapping needed for the correct regional routing flow

The ChatGPT example code shows the correct 4-step flow that you need.

---

## Proposed Solution

### 1. Add Missing Platform-to-Region Mapping
Add this constant to `integrations/riot_api.py` (after `REGIONAL_ENDPOINTS`):

```python
# Maps platform routing (e.g., "na1") to regional routing (e.g., "americas")
PLATFORM_TO_REGION = {
    # AMERICAS
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas", "oc1": "americas",
    # EUROPE
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
    # ASIA
    "kr": "asia", "jp1": "asia",
    # SEA (TFT-specific)
    "sg2": "sea", "ph2": "sea", "vn2": "sea", "th2": "sea", "tw2": "sea"
}
```

### 2. Add Active Shard API Method
Add new method to `RiotAPI` class:

```python
async def get_active_tft_platform(self, regional: str, puuid: str) -> Optional[str]:
    """
    Get the active TFT platform/shard for a player.
    This tells us which platform server the player is actively playing on.
    
    Returns:
        Platform code (e.g., "na1", "kr", "euw1") or None if not found
    """
    url = f"https://{regional}.api.riotgames.com/riot/account/v1/active-shards/by-game/tft/by-puuid/{puuid}"
    try:
        data = await self._make_request(url)
        return data.get("activeShard")  # e.g., "na1"
    except RiotAPIError as e:
        logger.debug(f"No active shard found for {puuid[:8]}... in {regional}: {e}")
        return None
```

### 3. Refactor `get_highest_rank_across_accounts()` Method

**Current Flow (WRONG)**:
- Loop through all IGNs → Loop through all regions → Try each one
- Results in unnecessary API calls and timeouts

**New Flow (CORRECT)**:
```
For each IGN:
  1. Try each REGIONAL endpoint (americas, europe, asia, sea) to find account
  2. Use Active Shard API to get exact platform where they play TFT
  3. Use that platform to get summoner data
  4. Use that platform to get rank data
  5. Compare ranks and keep highest
```

**Key Changes**:
- Replace `regions_to_check = ["na", "euw", ...]` with checking **regionals first** to find account
- After finding account, use **active shard** to get exact platform
- Only check **one platform** per IGN (the active one)
- Use `PLATFORM_TO_REGION` to map platform back to regional for match API

### 4. Implementation Details

The refactored method should:
- Loop through `["americas", "europe", "asia", "sea"]` to find each account
- Call `get_active_tft_platform()` to get the active platform
- Use that platform for summoner and league API calls
- Keep the existing fallback search logic for API bug cases
- Properly handle accounts with no TFT activity

### 5. Error Handling
- Handle case where account exists but has no active TFT shard (unranked/no games)
- Keep existing fallback tier search as last resort
- Log clear debug messages at each step for troubleshooting

---

## Files to Modify

1. **`integrations/riot_api.py`**
   - Add `PLATFORM_TO_REGION` constant
   - Add `get_active_tft_platform()` method
   - Refactor `get_highest_rank_across_accounts()` to use 4-step flow
   - Update docstrings to reflect new logic

---

## Expected Outcome

After implementation:
- ✅ Correctly detects which region/platform each IGN is active on
- ✅ Fetches rank from the correct platform only (no wasted API calls)
- ✅ Works properly for alt accounts across different regions
- ✅ Returns highest rank across all main + alt IGNs
- ✅ Reduces API timeout issues from blind region searching

---

## Testing Checklist

1. Test with NA main account + EUW alt
2. Test with unranked accounts
3. Test with accounts that have no TFT games
4. Test with invalid IGNs
5. Verify rank comparison logic works correctly