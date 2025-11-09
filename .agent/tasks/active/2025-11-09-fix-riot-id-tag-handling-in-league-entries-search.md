# Fix Riot ID Tag Handling in League Entries Search

## Root Cause Identified

The matching logic is **comparing Riot IDs WITH tags** against **summoner names WITHOUT tags**.

### What's Happening

**Search Input**: `'HYPExMon5ter#NA1'`
- After processing: `game_name = "hypexmon5ter#na1"` (lowercase with tag)
- After cleaning: `clean_game_name = "hypexmon5terna1"` (tag becomes part of name)

**API Returns**: Summoner entries with names like:
- `summonerName: "HYPExMon5ter"` (NO TAG)
- After processing: `"hypexmon5ter"` (no tag)

**Comparison**:
- `"hypexmon5terna1"` vs `"hypexmon5ter"` → ❌ NO MATCH
- Even with fuzzy matching, the tag prevents matches

### The Fix

**Extract game name WITHOUT the tag** before searching:

```python
# BEFORE (broken):
game_name = riot_id.split("#")[0].lower() if "#" in riot_id else riot_id.lower()
# Result: "hypexmon5ter" BUT still has "#na1" in original riot_id being passed

# AFTER (fixed):
# Extract just the game name, ignoring the tag completely
game_name = riot_id.split("#")[0] if "#" in riot_id else riot_id
game_name = game_name.lower()
```

## Implementation Plan

### Step 1: Fix Name Extraction Logic

**File**: `integrations/riot_api.py` - Line ~359

```python
async def find_summoner_in_league_entries(
    self, 
    region: str, 
    riot_id: str,
    max_tier: str = None
) -> Optional[Dict[str, Any]]:
    """Search TFT league entries to find a summoner's rank."""
    platform = self._get_platform_endpoint(region)
    
    # FIXED: Extract ONLY the game name, completely ignore the tag
    if "#" in riot_id:
        game_name = riot_id.split("#")[0]  # Get name before #
    else:
        game_name = riot_id
    
    game_name = game_name.lower()  # Lowercase for comparison
    
    logger.info(f"🔍 Searching league entries for '{riot_id}' (game name: '{game_name}') in {region.upper()}")
```

### Step 2: Simplify Matching Logic

Since we now have clean names without tags, simplify the matching:

```python
# Search entries for matching summoner
for entry in entries:
    entry_name = entry.get("summonerName", "").lower()
    
    # Clean both names (remove spaces, special chars)
    clean_game_name = game_name.replace(" ", "").replace("_", "")
    clean_entry_name = entry_name.replace(" ", "").replace("_", "")
    
    # Exact match check
    if clean_game_name == clean_entry_name:
        logger.info(f"✅ Found '{riot_id}' (exact match: '{entry.get('summonerName')}') in {tier_display} {division or ''}: {lp} LP ({wins}W/{losses}L)")
        
        return {
            "tier": tier_display,
            "rank": division or "I",
            "leaguePoints": lp,
            "wins": wins,
            "losses": losses,
            "summonerId": entry.get("summonerId"),
            "queueType": "RANKED_TFT",
            "source": "league_entries_search",
            "matched_name": entry.get("summonerName")  # For debugging
        }
```

### Step 3: Add Fuzzy Matching as Fallback

For edge cases where names might have slight variations:

```python
# After exact match check fails, try fuzzy matching
if not exact_match:
    # Calculate similarity (simple approach)
    # Only match if names are very similar (to avoid false positives)
    if clean_game_name in clean_entry_name or clean_entry_name in clean_game_name:
        # Additional check: length difference must be small
        len_diff = abs(len(clean_game_name) - len(clean_entry_name))
        if len_diff <= 3:  # Allow max 3 character difference
            logger.info(f"✅ Found '{riot_id}' (fuzzy match: '{entry.get('summonerName')}') in {tier_display} {division or ''}: {lp} LP")
            return { ... }
```

### Step 4: Add Debug Logging

Add more logging to understand what's being compared:

```python
logger.debug(f"Comparing: '{clean_game_name}' vs '{clean_entry_name}'")

# At end of tier search:
if not found:
    logger.debug(f"Checked {len(entries)} entries in {tier} {division}, no match for '{game_name}'")
```

## Expected API Call Flow

### For "HYPExMon5ter#NA1" in NA:

1. **Extract name**: `game_name = "hypexmon5ter"` (no tag)
2. **Search Gold I**: Compare against `"hypexmon5ter"` ✅ MATCH
3. **Return rank**: Gold I with actual stats

### For "Baceha#0000" in EUW:

1. **Extract name**: `game_name = "baceha"` (no tag)
2. **Search EUW tiers**: Compare against `"baceha"` ✅ MATCH
3. **Return rank**: Actual EUW rank

### For "LaurenTheCorgi#NA1" in NA:

1. **Extract name**: `game_name = "laurenthecorgi"` (no tag)
2. **Search NA tiers**: Compare against `"laurenthecorgi"` ✅ MATCH
3. **Return rank**: Actual NA rank

## Code Changes

**File**: `integrations/riot_api.py`

```python
async def find_summoner_in_league_entries(
    self, 
    region: str, 
    riot_id: str,
    max_tier: str = None
) -> Optional[Dict[str, Any]]:
    """
    Search TFT league entries to find a summoner's rank.
    
    Workaround for Riot API bug where Summoner API doesn't return 'id' field.
    Searches through tier/division entries to match by summoner name.
    
    Args:
        region: Region to search (e.g., 'na', 'euw')
        riot_id: Full Riot ID (e.g., 'HYPExMon5ter#NA1')
        max_tier: Stop searching if we find this tier or higher
        
    Returns:
        Dict with tier, rank, LP, wins, losses, or None if not found
    """
    platform = self._get_platform_endpoint(region)
    
    # FIXED: Extract ONLY the game name, completely ignore the tag
    if "#" in riot_id:
        game_name = riot_id.split("#")[0]  # Get name before #
    else:
        game_name = riot_id
    
    game_name = game_name.lower()  # Lowercase for comparison
    
    logger.info(f"🔍 Searching league entries for '{riot_id}' (searching for: '{game_name}') in {region.upper()}")
    
    # Optimized tier search order: Most common ranks first
    tier_search_order = [
        # Most common tiers (check first for speed)
        ("GOLD", "I"), ("GOLD", "II"), ("GOLD", "III"), ("GOLD", "IV"),
        ("PLATINUM", "I"), ("PLATINUM", "II"), ("PLATINUM", "III"), ("PLATINUM", "IV"),
        ("SILVER", "I"), ("SILVER", "II"), ("SILVER", "III"), ("SILVER", "IV"),
        
        # Higher tiers
        ("DIAMOND", "I"), ("DIAMOND", "II"), ("DIAMOND", "III"), ("DIAMOND", "IV"),
        
        # Lower tiers
        ("BRONZE", "I"), ("BRONZE", "II"), ("BRONZE", "III"), ("BRONZE", "IV"),
        ("IRON", "I"), ("IRON", "II"), ("IRON", "III"), ("IRON", "IV"),
        
        # Apex tiers (least common, check last)
        ("master", None),
        ("grandmaster", None),
        ("challenger", None),
    ]
    
    for tier, division in tier_search_order:
        try:
            # Build endpoint URL
            if tier in ["challenger", "grandmaster", "master"]:
                url = f"https://{platform}.api.riotgames.com/tft/league/v1/{tier}"
                response = await self._make_request(url)
                entries = response.get("entries", []) if isinstance(response, dict) else []
            else:
                url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/{tier}/{division}"
                entries = await self._make_request(url)
                if not isinstance(entries, list):
                    entries = []
            
            # Search entries for matching summoner
            for entry in entries:
                entry_name = entry.get("summonerName", "").lower()
                
                # Clean both names (remove spaces, underscores, special chars)
                clean_game_name = game_name.replace(" ", "").replace("_", "")
                clean_entry_name = entry_name.replace(" ", "").replace("_", "")
                
                # Exact match check (most reliable)
                is_exact_match = clean_game_name == clean_entry_name
                
                # Fuzzy match check (only if names are very similar)
                is_fuzzy_match = False
                if not is_exact_match:
                    # Check if one name contains the other
                    if clean_game_name in clean_entry_name or clean_entry_name in clean_game_name:
                        # Additional validation: length difference must be small
                        len_diff = abs(len(clean_game_name) - len(clean_entry_name))
                        if len_diff <= 3:  # Max 3 character difference
                            is_fuzzy_match = True
                
                if is_exact_match or is_fuzzy_match:
                    tier_display = tier.upper() if tier not in ["challenger", "grandmaster", "master"] else tier.capitalize()
                    lp = entry.get("leaguePoints", 0)
                    wins = entry.get("wins", 0)
                    losses = entry.get("losses", 0)
                    
                    match_type = "exact" if is_exact_match else "fuzzy"
                    logger.info(f"✅ Found '{riot_id}' ({match_type} match: '{entry.get('summonerName')}') in {tier_display} {division or ''}: {lp} LP ({wins}W/{losses}L)")
                    
                    return {
                        "tier": tier_display,
                        "rank": division or "I",
                        "leaguePoints": lp,
                        "wins": wins,
                        "losses": losses,
                        "summonerId": entry.get("summonerId"),
                        "queueType": "RANKED_TFT",
                        "source": "league_entries_search",
                        "matched_name": entry.get("summonerName")  # For debugging
                    }
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.06)  # ~16 requests/sec to be safe
            
        except RiotAPIError as e:
            if "404" in str(e) or "Data not found" in str(e):
                logger.debug(f"No data for {tier} {division or ''} in {region.upper()}")
            else:
                logger.warning(f"Error searching {tier} {division or ''}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error searching {tier} {division or ''}: {e}")
            continue
    
    logger.info(f"⚠️ No rank found for '{riot_id}' (searched for: '{game_name}') in {region.upper()}")
    return None
```

## Testing Expectations

After this fix:

✅ **HYPExMon5ter#NA1**: Should find rank as "HYPExMon5ter" in NA  
✅ **Baceha#0000**: Should find rank as "Baceha" in EUW  
✅ **LaurenTheCorgi#NA1**: Should find rank as "LaurenTheCorgi" in NA  
✅ **Fast Performance**: Should find ranks quickly (first few tiers)  
✅ **Accurate Matching**: No more false positives from tag confusion  

## Risk Assessment

**Low Risk**: Simple fix to name extraction logic  
**High Reward**: Makes the entire workaround functional  

## Files to Modify

1. **`integrations/riot_api.py`**: Fix name extraction in `find_summoner_in_league_entries()` method