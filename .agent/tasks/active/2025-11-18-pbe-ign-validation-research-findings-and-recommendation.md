## Spec: PBE IGN Validation - Technical Limitations

### Research Summary

After thorough research of Riot's account system and API documentation, I've discovered that **it is technically impossible to validate whether an account is "PBE-specific" vs "regular"** through the Riot API.

### Why PBE-Specific Validation Cannot Be Done

1. **Unified Account System**:
   - Riot uses a global account system where the same Riot Account (GameName#TAG) accesses both live and PBE servers
   - There is no separate "PBE account" vs "regular account" distinction at the API level

2. **No PBE Platform Code**:
   - The Riot API does not have a "PBE" region/platform routing value for account validation
   - Platform codes are: na1, euw1, kr, etc. (live servers only)
   - PBE is a server environment, not an API region

3. **Account API is Global**:
   - The Account API (`americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id`) validates ALL Riot Accounts
   - It cannot distinguish where a player intends to play (PBE vs live)
   - A valid account can access PBE if they meet eligibility (honor level 2+, no bans)

### Alternative Approaches

#### Option 1: Keep Current Validation (RECOMMENDED)
**Action**: Leave validation as-is (validates any valid Riot Account)

**Reasoning**:
- Players need valid Riot Accounts to play on PBE anyway
- The same account they use for live servers works on PBE
- Validates format (GameName#TAG) and account existence
- Prevents typos and invalid usernames

**Label Clarity**: The field is already labeled "PBE In-Game Name" which tells players the context

#### Option 2: No Validation
**Action**: Remove IGN validation entirely

**Reasoning**:
- Trust players to provide correct PBE IGNs
- Faster registration (no API calls)
- Risk: More typos and invalid entries

#### Option 3: Pattern Validation Only
**Action**: Validate format (GameName#TAG) without API calls

**Reasoning**:
- Ensures proper Riot ID format
- No API dependency
- Doesn't verify account exists

#### Option 4: Add Warning/Note (BEST COMPROMISE)
**Action**: Keep current validation + add clarifying text

**Changes**:
- Keep current Riot API validation
- Add help text: "Enter your Riot ID that you use to log into PBE"
- Update error messages to clarify that the account must exist

### Recommendation

**Keep current implementation** with minor text clarification:

```python
# Field label and placeholder
label="PBE In-Game Name"
placeholder="Enter your PBE Riot ID (Name#TAG)"

# Add help text to registration embed
help_text = "💡 **Note**: Use the same Riot ID you log into PBE with. This is your global Riot Account name."
```

### Why This is the Best Approach:

1. **Validates Real Accounts**: Ensures players provide valid, existing Riot Accounts
2. **Prevents Typos**: Catches misspellings before they cause tournament issues
3. **Already Implemented**: No code changes needed, just label improvements
4. **Technically Accurate**: PBE players DO use their Riot Accounts
5. **Flexible**: Works for both dedicated PBE accounts and players who play both

### What The Current System Does:

✅ **Validates**: Account exists in Riot's system  
✅ **Validates**: Proper format (GameName#TAG)  
✅ **Validates**: Account is not suspended/banned  
❌ **Cannot Validate**: Whether account has PBE access  
❌ **Cannot Validate**: Whether account is "PBE-only"  

### Implementation: No Changes Needed

The current validation already works correctly for PBE accounts. The only change would be clarifying the field description:

**Optional Enhancement**:
```python
# In core/views.py _setup_input_fields
self.ign_input = discord.ui.TextInput(
    label="PBE In-Game Name",
    placeholder="Enter your PBE Riot ID (Name#TAG)",
    required=True,
    default=default_ign or "",
    max_length=50
)
# Could add a note in the registration confirmation embed
```

### Conclusion

**The current implementation is already correct and optimal.** It validates that players provide real, existing Riot Accounts, which is exactly what's needed for PBE tournament registration. There is no technical way to further restrict validation to "PBE-only" accounts because such a distinction doesn't exist in Riot's account system.