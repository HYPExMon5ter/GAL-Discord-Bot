## Problem Analysis

The onboarding welcome message says "a safe space for everyone" but should say "a safe space for marginalized genders". When you upload a modified `config.yaml`, the config reloads but the existing welcome embed in Discord is **not updated**.

**Root Cause**: In `core/onboard.py`, the `setup_onboard_channel()` function only **creates** the welcome embed if it doesn't exist. If it finds an existing embed, it skips posting a new one. There's no logic to **update** an existing embed when the config changes.

## Implementation Plan

### 1. Fix the wording in config.yaml
Change line 25:
```yaml
# Before
description: We're an inclusive community focused on creating a safe space for everyone.

# After  
description: We're an inclusive community focused on creating a safe space for marginalized genders.
```

### 2. Add embed update logic to `setup_onboard_channel()` in `core/onboard.py`
Modify the function to:
- Find the existing welcome embed message
- Compare its description with the current config
- **Update the message** if the content differs (using `message.edit()`)
- Keep the view (button) intact during the edit

### 3. Call onboard refresh during config reload
In `helpers/config_manager.py`, add a call to refresh/update the onboard channel when config is reloaded, similar to how `setup_unified_channel` is called.

### Key Code Changes

**core/onboard.py** - Modify `setup_onboard_channel()`:
```python
# Instead of just checking if embed exists, also compare content
if main_embed_exists:
    # Check if content matches current config
    current_embed = onboard_embed_from_cfg("main")
    if existing_message.embeds[0].description != current_embed.description:
        # Update the existing message
        view = OnboardView(guild.id)
        await existing_message.edit(embed=current_embed, view=view)
        logging.info("Updated main onboard embed with new config")
```

**helpers/config_manager.py** - Add to `reload_and_update_all()`:
```python
# After updating unified channel embeds, also update onboard channel
from core.onboard import setup_onboard_channel
await setup_onboard_channel(guild, bot)
```

This ensures that:
1. The config.yaml has the correct text
2. When config is uploaded/reloaded, the onboard embed automatically updates
3. Future config changes will properly reflect in the welcome channel