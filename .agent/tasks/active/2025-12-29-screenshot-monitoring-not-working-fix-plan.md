## Screenshot Monitoring Not Working - Fix Plan

### Problem Analysis
1. **Screenshot monitoring is not active** - Uploads to "tournament-standings" channel produce no reaction or dashboard entries
2. **Root cause**: `screenshot_monitor.py` exists with `on_message()` method, but it's never called by the Discord bot
3. The screenshot monitor is not registered as a Discord event listener

### Current State
- ✅ `config.yaml` has `standings_screenshots.enabled: true` 
- ✅ `config.yaml` monitors "tournament-standings" channel
- ✅ `core/events/handlers/screenshot_monitor.py` exists with full implementation
- ❌ `screenshot_monitor` is NOT imported in `core/discord_events.py`
- ❌ No `@bot.event on_message` listener exists to call the screenshot monitor

### Solution Steps

1. **Import screenshot_monitor in discord_events.py**
   ```python
   from .events.handlers.screenshot_monitor import get_screenshot_monitor
   ```

2. **Register on_message listener in register_discord_events()**
   - Add `@bot.event async def on_message(message)` listener
   - Call `get_screenshot_monitor(bot).on_message(message)`
   - Handle errors gracefully

3. **Ensure proper event ordering**
   - Allow screenshot monitoring to proceed even if other events fail
   - Add appropriate error logging

4. **Test the fix**
   - Restart bot
   - Upload screenshot to "tournament-standings" channel
   - Verify ✅ reaction appears
   - Verify dashboard shows pending submission

### Files to Modify
- `core/discord_events.py` - Add on_message listener and screenshot_monitor import

### Expected Outcome
- ✅ Screenshot uploads trigger immediate confirmation reaction
- ✅ Screenshots are batched and processed (30s window)
- ✅ Dashboard shows pending submissions
- ✅ OCR/player matching extracts standings data
- ✅ Review UI displays side-by-side screenshot and extracted data

### Time Estimate
~5 minutes (code changes + bot restart)