# Automated Rank Detection and Validation for Registration

## Overview
Implement automatic rank fetching and validation for all in-game names (IGNs) during registration, storing the highest rank across all game modes and regions in the Google Sheets database. Ranks are fetched once at registration time and stored for future use in lobby balancing.

## Key Components

### 1. Rank Column Detection (`integrations/sheet_detector.py`)
- **Add** "rank" pattern to `COLUMN_PATTERNS` dictionary
- Patterns: `["rank", "ranked", "tier", "rating", "elo", "current rank", "player rank", "current_rank"]`
- Enable auto-detection of rank column in Google Sheets
- Column will be detected alongside existing columns (Discord, IGN, Registered, etc.)

### 2. Multi-Region Rank Fetching (`integrations/riot_api.py`)
- **Create** new method: `async def get_highest_rank_across_accounts(self, ign_list: List[str], default_region: str = "na") -> Dict[str, Any]`
  
**Functionality**:
```python
# For each IGN:
#   1. Try default region first
#   2. If not found (404), try ALL regions: na, euw, eune, kr, br, lan, las, oce, jp, tr, ru
#   3. Fetch league entries for all TFT queues (RANKED_TFT, RANKED_TFT_DOUBLE_UP, RANKED_TFT_TURBO)
#   4. Track highest rank found

# Return format:
{
    "success": True,
    "highest_rank": "Diamond II 45 LP",
    "rank_tier": "DIAMOND",
    "rank_division": "II", 
    "lp": 45,
    "queue_type": "RANKED_TFT",
    "found_ign": "PlayerName#TAG",
    "region": "na",
    "raw_rank_value": 21  # For sorting: Challenger=28, GM=27, etc.
}
```

**Rank Priority** (for comparison):
- Challenger (28) > Grandmaster (27) > Master (26)
- Diamond I (25) > Diamond II (24) > Diamond III (23) > Diamond IV (22)
- Platinum I (21) > Platinum II (20) > Platinum III (19) > Platinum IV (18)
- Gold I-IV (17-14) > Silver I-IV (13-10) > Bronze I-IV (9-6) > Iron I-IV (5-2)
- Unranked (0)
- Within same rank: Higher LP wins

**Error Handling**:
- If ALL names fail across ALL regions: Return `{"success": False, "highest_rank": "Unranked"}`
- Log warnings for API failures but don't block registration
- Respect rate limits with proper delays between region attempts

### 3. IGN Validation Enhancement (`core/views.py` - RegistrationModal.on_submit)

**Parse Alternate IGNs**:
```python
# Split on comma with flexible whitespace
alt_igns_raw = self.alt_ign_input.value.strip() if self.alt_ign_input else ""
alt_igns_list = []

if alt_igns_raw:
    # Split by comma and clean each entry
    alt_igns_list = [
        name.strip() 
        for name in re.split(r'\s*,\s*', alt_igns_raw) 
        if name.strip()
    ]
```

**Validate ALL IGNs**:
```python
# Validate primary IGN (already done)
is_valid, msg, riot_data = await verify_ign_for_registration(ign, "na")

# NEW: Validate each alternate IGN
all_igns_to_validate = [ign] + alt_igns_list
validation_results = []

for ign_to_check in all_igns_to_validate:
    # Try verification with region auto-detection
    is_valid, msg, riot_data = await verify_ign_for_registration(ign_to_check, "na")
    validation_results.append({
        "ign": ign_to_check,
        "valid": is_valid,
        "message": msg
    })

# If any validation fails, show error
failed_igns = [r for r in validation_results if not r["valid"]]
if failed_igns:
    error_embed = discord.Embed(
        title="❌ IGN Verification Failed",
        description=f"The following IGNs could not be verified:\n" + 
                    "\n".join([f"• **{r['ign']}**: {r['message']}" for r in failed_igns])
    )
    await interaction.edit_original_response(embed=error_embed)
    return
```

### 4. Region Auto-Detection (`integrations/ign_verification.py`)
- **Enhance** `verify_ign_for_registration()` to try multiple regions
- **Strategy**:
  1. Parse Riot ID (handle `Name#TAG` or plain `Name`)
  2. Try default region (na) first
  3. On 404 error, iterate through all regions: `["na", "euw", "eune", "kr", "br", "lan", "las", "oce", "jp", "tr", "ru"]`
  4. Return first successful match with region info
  5. If all regions fail, return invalid

```python
async def verify_ign_for_registration(ign: str, default_region: str = "na") -> Tuple[bool, str, Optional[Dict]]:
    """Verify IGN with automatic region detection."""
    regions_to_try = [default_region] + [r for r in ALL_REGIONS if r != default_region]
    
    for region in regions_to_try:
        try:
            # Attempt verification
            result = await verify_in_region(ign, region)
            if result["success"]:
                return True, f"✅ Verified in {region.upper()}", result
        except NotFoundError:
            continue  # Try next region
        except RateLimitError:
            await asyncio.sleep(1)  # Brief pause
            continue
    
    return False, "❌ IGN not found in any region", None
```

### 5. Rank Fetching in Registration Flow (`core/views.py` - complete_registration)

**Add after validation, before sheet write**:
```python
# After successful IGN validation
logging.info(f"🎖️ Fetching rank data for {discord_tag} with IGNs: {all_igns_to_validate}")

rank_data = None
try:
    async with RiotAPI() as riot_client:
        rank_data = await riot_client.get_highest_rank_across_accounts(
            ign_list=all_igns_to_validate,
            default_region="na"
        )
    
    if rank_data and rank_data.get("success"):
        logging.info(f"✅ Rank found for {discord_tag}: {rank_data['highest_rank']} "
                    f"(IGN: {rank_data['found_ign']}, Region: {rank_data['region']})")
    else:
        logging.warning(f"⚠️ No rank found for {discord_tag}, defaulting to Unranked")
        rank_data = {"highest_rank": "Unranked"}
        
except Exception as e:
    logging.error(f"❌ Rank fetch error for {discord_tag}: {e}")
    rank_data = {"highest_rank": "Unranked"}  # Graceful fallback

# Extract rank string for storage
player_rank = rank_data.get("highest_rank", "Unranked")
```

### 6. Sheet Writing Integration (`integrations/sheets.py` - find_or_register_user)

**Add rank parameter**:
```python
async def find_or_register_user(
    discord_tag: str,
    ign: str,
    guild_id: str | None = None,
    team_name: str | None = None,
    alt_igns: str | None = None,
    pronouns: str | None = None,
    rank: str | None = None  # NEW
) -> int:
```

**Update column detection and writes**:
```python
# Get rank column letter
rank_col = await SheetIntegrationHelper.get_column_letter(gid, "rank_col")

# Add to writes dict
if rank_col and rank:
    writes[rank_col] = rank
    logging.info(f"✅ Writing rank to column {rank_col}: {rank}")

# Include in batch updates for both new and existing users
```

**Update cache structure**:
```python
# Update cache to include rank (8th element)
sheet_cache["users"][discord_tag] = (
    row, ign, True, False, team_name or "", 
    alt_igns or "", pronouns or "", rank or "Unranked"
)
```

### 7. Helper Function Updates (`helpers/sheet_helpers.py`)
- **Update** `get_user_data()` to return rank field
- **Update** cache unpacking to handle 8-element tuples (was 7, now 8 with rank)

```python
# Safely unpack with defaults (update from 7 to 8)
parts = list(cache_data) + [None] * (8 - len(cache_data))
row, ign, registered, checked_in, team, alt_ign, pronouns, rank = parts[:8]

return {
    "row": row,
    "ign": ign or "",
    "alt_ign": alt_ign or "",
    "pronouns": pronouns or "",
    "rank": rank or "Unranked",  # NEW
    "registered": str(registered).upper() == "TRUE",
    "checked_in": str(checked_in).upper() == "TRUE",
    "team": team if mode == "doubleup" else None,
    "discord_tag": discord_tag
}
```

### 8. Multiple Hyperlinks (Not Feasible)
**Research Conclusion**: Google Sheets does NOT support multiple clickable hyperlinks in a single cell via formulas.

**Options Considered**:
1. ❌ **Formula Method**: `HYPERLINK()` only supports one link per cell
2. ❌ **Apps Script**: Requires `setRichTextValue()` + manual script setup per sheet (too complex)
3. ✅ **Current Approach**: Keep single hyperlink for primary IGN (alternates as plain text)

**Recommendation**: Document this as a known limitation. If multiple hyperlinks are critical in future, consider:
- Separate column for each alt IGN with individual hyperlinks
- External dashboard/webpage with clickable links
- Manual rich text editing (not scalable)

## Implementation Order
1. ✅ Commit current changes (COMPLETED)
2. Add "rank" to sheet detector column patterns
3. Add rank column configuration support in config files
4. Create helper function for rank-to-numeric conversion (for sorting)
5. Implement `get_highest_rank_across_accounts()` in RiotAPI class
6. Enhance `verify_ign_for_registration()` with multi-region support
7. Update RegistrationModal to parse and validate all comma-separated IGNs
8. Modify `complete_registration()` to fetch rank data after validation
9. Update `find_or_register_user()` to accept and write rank column
10. Update cache structure and helper functions to handle rank field
11. Test full flow: registration → validation → rank fetch → sheet write
12. Run linting, type checking, and tests

## Testing Checklist
- [ ] Single IGN registration fetches correct rank
- [ ] Multiple comma-separated alts: all validated, highest rank found
- [ ] Cross-region detection: NA account + EUW account → highest rank detected
- [ ] Rank priority: Diamond beats Platinum, Diamond I beats Diamond II
- [ ] Different queue types: Standard, Double-Up, Hyper Roll all checked
- [ ] Rank writes to correct Google Sheets column
- [ ] Invalid alternate IGNs show proper error with specific failed names
- [ ] API failure gracefully defaults to "Unranked" without blocking registration
- [ ] Various comma formats: `"a,b"`, `"a, b"`, `"a , b"`, `"a  ,  b"` all parse correctly
- [ ] Existing users updating registration preserve/update rank data
- [ ] Cache properly stores 8-element tuples with rank field

## Configuration Updates Needed
Add to `config.yaml` sheet settings:
```yaml
sheets:
  normal:
    rank_col: "M"  # Or auto-detect
  doubleup:
    rank_col: "M"  # Or auto-detect
```

## Performance Considerations
- **Rate Limiting**: RiotAPI already has semaphore (max 4 concurrent)
- **Region Iteration**: Max 11 API calls per IGN if not found (unavoidable for accuracy)
- **Caching**: Store rank in sheet/cache, no need for re-fetching unless user updates
- **Registration Time**: May add 2-5 seconds for rank fetching (acceptable one-time cost)
- **Batch Operations**: Use existing batch update mechanisms in sheets.py

## Error Handling Strategy
- **API Timeout**: Log warning, default to "Unranked"
- **Rate Limit Hit**: Retry with exponential backoff (already implemented)
- **Invalid IGN**: Block registration with clear error message
- **Partial Validation**: If 1 of 3 IGNs invalid, block registration (all must be valid)
- **Rank Fetch Failure**: Allow registration, store "Unranked", log for admin review

## Future Enhancements (Out of Scope)
- Rank refresh command for admins
- Rank decay detection (warn if rank is old)
- Automatic rank updates on check-in
- Display rank badges in Discord embeds
- Rank-based lobby balancing algorithm
