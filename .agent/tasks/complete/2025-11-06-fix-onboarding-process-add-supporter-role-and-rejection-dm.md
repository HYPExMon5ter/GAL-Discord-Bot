# Fix Onboarding Process Spec

## Current State Analysis

### ✅ What's Working:
1. **Acceptance Flow**: Correctly assigns "Angels" role and sends DM using `onboard_embed_from_cfg("approved")`
2. **Main Message**: Already customizable in `config.yaml` under `onboard.embeds.main`
3. **Approval DM**: Already customizable in `config.yaml` under `onboard.embeds.approved`

### ❌ What's Missing:

1. **Rejection Flow Issues**:
   - Currently does NOT send a DM to the user (line 446-472 in `core/onboard.py`)
   - Does NOT assign "Supporter" role
   - Only logs to bot-log channel (silent denial)
   - Comment says: `# Log to bot log (silent denial - no DM to user)` (line 455)

2. **Config Missing**:
   - No `role_on_deny` setting in `config.yaml` to specify "Supporter" role
   - The `denied` embed exists but is never used in the code

## Required Changes

### 1. Update `config.yaml` - Add Supporter Role Configuration

**Location**: `config.yaml` onboard section

**Add**:
```yaml
onboard:
  # Channel settings
  main_channel: welcome
  review_channel: onboard-review

  # Role settings
  role_on_approve: Angels          # Role granted after approval
  role_on_deny: Supporter          # NEW: Role granted after denial

  # ... rest stays the same
```

The `denied` embed is already present and will work as-is:
```yaml
denied:
  title: ❌ Onboarding Not Approved
  description: Your submission was reviewed but not approved at this time.
  color: '#e74c3c'
```

### 2. Update `config.py` - Add Denial Role Helper Function

**Location**: `config.py` after the `get_onboard_approval_role()` function (around line 122)

**Add new function**:
```python
def get_onboard_denial_role() -> str:
    """Get role to assign on onboard denial from config."""
    return get_onboard_config().get("role_on_deny", "Supporter")
```

### 3. Update `core/onboard.py` - Fix DenyButton Callback

**Location**: `core/onboard.py` in the `DenyButton.callback` method (lines 410-472)

**Changes needed**:

1. Import the new config function at the top:
```python
from config import (
    onboard_embed_from_cfg, get_onboard_main_channel,
    get_onboard_review_channel, get_onboard_approval_role,
    get_onboard_denial_role,  # ADD THIS
    get_log_channel_name
)
```

2. Replace the current denial logic (lines 428-463) with:
```python
# Get the member
member = interaction.guild.get_member(user_id)
if not member:
    await interaction.response.send_message(
        "Error: User is no longer in the server.",
        ephemeral=True
    )
    return

member_mention = member.mention

# Remove from pending submissions
submission_data = OnboardManager.remove_pending_submission(user_id)

# Assign denial role (Supporter)
denial_role = get_onboard_denial_role()
success = await RoleManager.add_role(member, denial_role)

if success:
    # Update embed to show denied
    embed = interaction.message.embeds[0]
    embed.color = discord.Color.red()
    embed.add_field(
        name="❌ Status",
        value=f"Denied by {interaction.user.mention}",
        inline=False
    )

    # Disable buttons
    for item in view.children:
        item.disabled = True

    await interaction.response.edit_message(embed=embed, view=view)

    # Send DM to user with customizable embed
    try:
        dm_embed = onboard_embed_from_cfg("denied")
        await member.send(embed=dm_embed)
        logging.info(f"Sent denial DM to {member}")
    except discord.Forbidden:
        logging.warning(f"Could not DM denial to {member}")

    # Log to bot log
    log_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=get_log_channel_name()
    )
    if log_channel:
        log_embed = discord.Embed(
            title="❌ Onboarding Denied",
            description=f"{member_mention} was denied onboarding by {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await log_channel.send(embed=log_embed)

    logging.info(f"Denied onboarding for {member} by {interaction.user}")

else:
    await interaction.response.send_message(
        f"Error: Could not assign '{denial_role}' role to {member.mention}.",
        ephemeral=True
    )
```

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `config.yaml` | Add Setting | Add `role_on_deny: Supporter` to onboard section |
| `config.py` | Add Function | Add `get_onboard_denial_role()` helper function |
| `core/onboard.py` | Update Import | Import `get_onboard_denial_role` |
| `core/onboard.py` | Rewrite Logic | Replace silent denial with role assignment + DM |

## Expected Behavior After Fix

### Acceptance Flow:
✅ Assign "Angels" role  
✅ Send DM using `approved` embed (customizable)  
✅ Log to bot-log  

### Rejection Flow:
✅ Assign "Supporter" role (NEW)  
✅ Send DM using `denied` embed (NEW - already configured)  
✅ Log to bot-log  

## Testing Plan

1. **Test Approval**: Submit onboard request → Staff approves → Verify Angels role + DM received
2. **Test Denial**: Submit onboard request → Staff denies → Verify Supporter role + DM received
3. **Test Config**: Modify `denied` embed in config.yaml → Deny user → Verify custom message shows
4. **Test Missing Role**: Temporarily rename "Supporter" role → Deny user → Verify error message
5. **Test DM Disabled**: User with DMs disabled → Deny → Verify graceful handling (logs warning)

---

**All changes are minimal and leverage existing infrastructure. The `denied` embed already exists and just needs to be used.**