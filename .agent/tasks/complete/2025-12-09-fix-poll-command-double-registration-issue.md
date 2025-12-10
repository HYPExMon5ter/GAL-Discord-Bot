# Fix Plan: Poll Command Double Registration Issue

## Problem Identified
The poll command is being registered twice, causing the error:
```
discord.app_commands.errors.CommandAlreadyRegistered: Command 'poll' already registered.
```

**Root Cause:**
- The `poll_notify` function is decorated with `@gal.command()` at module level
- Then `register()` function tries to add it again with `gal_group.add_command(poll_notify)`
- This causes double registration

## Correct Pattern
Looking at `utility.py` and `registration.py`, the correct pattern is:
- Commands should be defined INSIDE the `register()` function
- Use `@gal.command()` decorator inside the function
- No manual `add_command()` call needed

## Solution

### Update `core/commands/poll.py`

**Change the structure from:**
```python
@gal.command(name="poll", ...)
@command_tracer("gal.poll")
async def poll_notify(...):
    ...

def register(gal_group) -> None:
    gal_group.add_command(poll_notify)  # ❌ This causes double registration
```

**To:**
```python
def register(gal: app_commands.Group) -> None:
    """Register poll commands with the GAL command group."""
    
    @gal.command(
        name="poll",
        description="Send poll notification to all Angels"
    )
    @app_commands.describe(
        link="Link to the Discord poll message",
        custom_message="Optional custom message override"
    )
    @command_tracer("gal.poll")
    async def poll_notify(
        interaction: discord.Interaction,
        link: str,
        custom_message: Optional[str] = None
    ) -> None:
        """Send poll notification to all users with the Angels role..."""
        # ... entire function body stays the same
```

## Changes Required

### File: `core/commands/poll.py`

1. **Remove the `@gal.command()` decorator** from module level
2. **Move the entire `poll_notify` function** inside the `register()` function
3. **Move the `@poll_notify.error` handler** inside the `register()` function as well
4. **Keep all imports** at the top
5. **Remove the manual `add_command()` call** from register function

### Structure:
```python
"""Poll notification commands for mass DM functionality."""

# Imports stay at top
import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands

from core.commands.common import ensure_staff, command_tracer
from helpers.poll_helpers import PollNotifier, validate_discord_link
from helpers import ErrorHandler

logger = logging.getLogger(__name__)


def register(gal: app_commands.Group) -> None:
    """Register poll commands with the GAL command group."""
    
    @gal.command(
        name="poll",
        description="Send poll notification to all Angels"
    )
    @app_commands.describe(
        link="Link to the Discord poll message",
        custom_message="Optional custom message override"
    )
    @command_tracer("gal.poll")
    async def poll_notify(
        interaction: discord.Interaction,
        link: str,
        custom_message: Optional[str] = None
    ) -> None:
        """Send poll notification to all users with the Angels role."""
        if not await ensure_staff(interaction, context="Poll Command"):
            return
            
        try:
            # ... rest of implementation stays exactly the same
            
    @poll_notify.error
    async def poll_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Handle errors for the poll command."""
        # ... error handler stays exactly the same


__all__ = ["register"]
```

## Why This Fixes The Issue

1. **Single Registration**: Command is only registered once when `register()` is called
2. **Follows Pattern**: Matches the pattern used by all other commands (utility.py, registration.py, etc.)
3. **No Double Decoration**: Command decorator is only applied once inside register()
4. **Proper Scoping**: Function is scoped to the register function, preventing module-level registration

## Testing

After fix:
1. Bot should start without `CommandAlreadyRegistered` error
2. `/gal poll` command should be available
3. Command should work as intended with all features

## Files Modified
- `core/commands/poll.py` - Restructure to match existing command pattern

## Expected Result
✅ Bot starts successfully
✅ No duplicate command registration errors
✅ `/gal poll` command works correctly
✅ All functionality preserved