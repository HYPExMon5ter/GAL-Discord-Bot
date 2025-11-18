## Spec: Update Registration Fields and Disable Rank Fetching

### Overview
Update registration modal field labels to reflect PBE vs Main server IGNs, disable rank fetching/writing, while maintaining IGN validation for the PBE IGN field only (which works for both regular and PBE accounts via existing Riot API integration).

---

### Part 1: Update Modal Field Labels

**File**: `core/views.py`  
**Location**: Lines 824-841 in `_setup_input_fields` method

#### Changes:
1. **Line 826**: Change `label="In-Game Name"` → `label="PBE In-Game Name"`
2. **Line 827**: Change placeholder from `"Enter your TFT IGN"` → `"Enter your PBE IGN (Name#TAG)"`
3. **Line 836**: Change `label="Alternative IGN(s)"` → `label="Main In-Game Name"`
4. **Line 837**: Change placeholder from `"Comma-separated alt IGNs (optional)"` → `"Enter your main server IGN (optional)"`

**Important Notes**:
- Keep variable names (`ign_input`, `alt_ign_input`) unchanged
- Sheet column mapping remains the same (ign_col, alt_ign_col)
- Data flow unchanged: `ign_input` → "IGN" column, `alt_ign_input` → "Alternative IGN" column

---

### Part 2: Update IGN Validation Logic

**File**: `core/views.py`  
**Location**: Lines 929-993 (IGN validation block)

#### Current Behavior:
```python
# Lines 929-930: Validates ALL IGNs (main + alternates)
all_igns_to_validate = [ign] + alt_igns_list
```

#### New Behavior:
**Validate ONLY the PBE IGN (primary ign field), skip Main IGN validation**:

```python
# Line 929-930: Only validate the PBE IGN (main field), skip alt IGNs
all_igns_to_validate = [ign]  # Only validate PBE IGN, not main server IGN
```

**Reasoning**: 
- **PBE IGN** (stored in `ign` field) → **NEEDS VALIDATION** - players will use this for tournament
- **Main IGN** (stored in `alt_igns` field) → **NO VALIDATION NEEDED** - optional reference only
- Existing validation already works for both regular accounts AND PBE accounts

#### How IGN Validation Works:
The current validation in `integrations/ign_verification.py`:
1. Uses global Riot Account API (`americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id`)
2. Accounts are **global** - works for all regions including PBE
3. Validates format: `GameName#TAG`
4. Returns success if account exists (even without TFT summoner data)
5. **Already supports both PBE and regular accounts** - they're in the same global Riot account system

**No changes needed to validation service** - it already handles both account types!

---

### Part 3: Disable Rank Fetching

**File**: `core/views.py`  
**Location**: Lines 298-340 (rank fetching block)

#### Changes:
**Comment out entire rank fetching block and set default**:

```python
# Lines 298-340: Comment out rank fetch logic
# # Parse comma-separated alternate IGNs for rank fetching
# alt_igns_list = []
# if alt_igns and alt_igns.strip():
#     alt_igns_list = [
#         name.strip() 
#         for name in re.split(r'\s*,\s*', alt_igns) 
#         if name.strip()
#     ]
# 
# # Collect all IGNs for rank fetching (main + alternates)
# all_igns_for_rank = [ign] + alt_igns_list
# 
# # 6.5) Fetch rank data for all IGNs
# rank_data = None
# try:
#     logging.info(f"🎖️ Fetching rank data for {discord_tag} with IGNs: {all_igns_for_rank}")
#     
#     from integrations.riot_api import RiotAPI
#     async with RiotAPI() as riot_client:
#         rank_data = await riot_client.get_highest_rank_across_accounts(
#             ign_list=all_igns_for_rank,
#             default_region="na"
#         )
#     
#     if rank_data and rank_data.get("success"):
#         logging.info(f"✅ Rank found for {discord_tag}: {rank_data['highest_rank']} "
#                   f"(IGN: {rank_data['found_ign']}, Region: {rank_data['region']})")
#         player_rank = rank_data["highest_rank"]
#     else:
#         player_rank = "Iron IV"
#         logging.warning(f"⚠️ No rank found for {discord_tag}, using default: {player_rank}")
#         
# except Exception as e:
#     logging.error(f"❌ Rank fetch error for {discord_tag}: {e}")
#     player_rank = "Iron IV"
#     logging.warning(f"⚠️ Rank fetch failed for {discord_tag}, using default: {player_rank}")

# Set default rank without fetching
player_rank = "Unranked"
logging.info(f"🔄 Registering {discord_tag} with default rank: {player_rank}")
```

**Keep**: Lines 341-356 (sheet registration logic - still passes rank parameter but with "Unranked" value)

---

### Part 4: Disable Rank Writing to Sheet

**File**: `integrations/sheets.py`  
**Locations**: Lines 690-695 and line 796

#### Changes:

**1. Existing user updates (lines 690-695)**:
```python
# Comment out rank update logic
# # Update rank if provided and different
# if rank is not None and rank != old_rank:
#     rank_col = await SheetIntegrationHelper.get_column_letter(gid, "rank_col")
#     if rank_col:
#         batch_updates.append((f"{rank_col}{row}", rank))
#         updates_needed.append("rank")
```

**2. New user registration (line 796)**:
```python
# Comment out rank writing
# # Add rank if column exists
# rank_col = await SheetIntegrationHelper.get_column_letter(gid, "rank_col")
# if rank_col:
#     rank_value = rank if rank is not None and rank.strip() != "" else "Iron IV"
#     writes[rank_col] = rank_value
#     logger.info(f"✍️ Writing rank to column {rank_col}: '{rank_value}'")
# else:
#     logger.error(f"❌ No rank column configured for guild {gid}!")
```

---

### Summary of Changes

| Component | Action | Result |
|-----------|--------|--------|
| **Field Labels** | Update display text | "PBE In-Game Name" / "Main In-Game Name" |
| **IGN Validation** | Validate only PBE IGN field (`ign`) | Main IGN field not validated |
| **Validation Service** | No changes | Already supports both regular and PBE accounts |
| **Rank Fetching** | Comment out API calls | No Riot API rank calls during registration |
| **Rank Writing** | Comment out sheet writes | Rank column remains empty/default |
| **Sheet Logic** | No changes | Column detection unchanged, data flow same |

### Data Flow Summary

**Registration Form → Sheet Columns:**
- `ign_input` (labeled "PBE In-Game Name") → `ign_col` → **VALIDATED**
- `alt_ign_input` (labeled "Main In-Game Name") → `alt_ign_col` → **NOT VALIDATED**
- `rank` → `rank_col` → **NOT WRITTEN** (commented out)

### Testing Checklist
- [ ] Registration modal shows "PBE In-Game Name" and "Main In-Game Name" labels
- [ ] PBE IGN field validates against Riot API (accepts both regular and PBE format accounts)
- [ ] Main IGN field accepts any input without validation
- [ ] Failed PBE IGN validation blocks registration with clear error message
- [ ] No Riot API rank calls during registration
- [ ] Registration completes successfully without rank data
- [ ] Sheet writes IGNs to correct columns (ign_col for PBE, alt_ign_col for Main)
- [ ] Rank column remains empty or shows "Unranked"