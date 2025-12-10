# Implementation Plan

## Overview
Update the onboarding system to:
1. Log to bot-log channel ONLY when DMs fail (not for all approvals/rejections)
2. Change "PBE In-Game Name" to "Tournament In-Game Name" across registration

## Changes Required

### 1. Onboarding DM Failure Logging (`core/onboard.py`)

**File**: `core/onboard.py`

**ApproveButton.callback()** (lines ~275-345):
- Remove the unconditional bot-log message after approval (lines ~320-330)
- Wrap the DM attempt in try/except for `discord.Forbidden`
- On DM failure: Log to bot-log channel with message: `"❌ Failed to DM approval to {member.mention}. Please reach out to them directly."`
- On DM success: No bot-log message

**DenyButton.callback()** (lines ~348-420):
- Remove the unconditional bot-log message after denial (lines ~395-405)
- Wrap the DM attempt in try/except for `discord.Forbidden`
- On DM failure: Log to bot-log channel with message: `"❌ Failed to DM rejection to {member.mention}. Please reach out to them directly."`
- On DM success: No bot-log message

**Code Pattern**:
```python
# Send DM to user
dm_sent = False
try:
    dm_embed = onboard_embed_from_cfg("approved")  # or "denied"
    await member.send(embed=dm_embed)
    dm_sent = True
    logging.info(f"Sent approval DM to {member}")
except discord.Forbidden:
    logging.warning(f"Could not DM approval to {member}")

# Log to bot-log ONLY if DM failed
if not dm_sent:
    log_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=get_log_channel_name()
    )
    if log_channel:
        log_embed = discord.Embed(
            title="❌ DM Delivery Failed",
            description=f"Failed to send {'approval' or 'rejection'} notification to {member.mention}. Please reach out to them directly.",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        await log_channel.send(embed=log_embed)
```

### 2. Tournament Username Label Updates (`core/views.py`)

**File**: `core/views.py`

**RegistrationModal._setup_input_fields()** (line ~1227):
- Change `label="PBE In-Game Name"` to `label="Tournament In-Game Name"`
- Update `placeholder="Enter your PBE IGN (Name#TAG)"` to `placeholder="Enter your Tournament IGN (Name#TAG)"`

**Line 1227**:
```python
# Before:
self.ign_input = discord.ui.TextInput(
    label="PBE In-Game Name",
    placeholder="Enter your PBE IGN (Name#TAG)",
    ...
)

# After:
self.ign_input = discord.ui.TextInput(
    label="Tournament In-Game Name",
    placeholder="Enter your Tournament IGN (Name#TAG)",
    ...
)
```

**Line 1413 (error message)**:
- Update the embed field name from `"💡 PBE IGN Tips"` to `"💡 Tournament IGN Tips"`

## Testing Considerations
1. Test approval flow with user who has DMs disabled
2. Test rejection flow with user who has DMs disabled
3. Verify bot-log messages appear ONLY on DM failures
4. Verify no bot-log messages on successful DMs
5. Check registration modal shows "Tournament In-Game Name"
6. Verify IGN validation error messages use correct terminology

## Files Modified
- `core/onboard.py` - Update ApproveButton and DenyButton callbacks
- `core/views.py` - Update RegistrationModal labels and error messages