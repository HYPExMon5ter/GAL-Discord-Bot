## Spec: Clean Up Deprecated Code in components_traditional.py

### Issues Identified

1. **Duplicate methods outside class** (lines 557-605):
   - `_get_no_event_components()` - duplicate of method already in `UnifiedChannelLayoutView` class
   - `_get_action_button_components()` - duplicate of method already in `UnifiedChannelLayoutView` class
   - These are orphaned methods not attached to any class and preceded by a note saying they're placeholders

2. **Placeholder comment** (lines 557-558):
   - Comment stating "This section kept as a placeholder to show where the old async methods were"
   - This is unnecessary documentation clutter

3. **Missing invisible separator**:
   - In `_get_no_event_components()` method (inside the class, around line 316-331)
   - Need to add invisible separator between "# 🏆 Tournament Hub" and the no_event_text

### Changes to Make

1. **Remove lines 557-605**: Delete the placeholder comment and duplicate methods:
   - Remove the note about component builder methods
   - Remove duplicate `_get_no_event_components()` 
   - Remove duplicate `_get_action_button_components()`

2. **Add invisible separator in class method** (line ~320):
   - In `UnifiedChannelLayoutView._get_no_event_components()` 
   - Add `discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large)` between the header and Section

### Result

Clean, maintainable code with no duplicate/placeholder methods, and improved visual spacing in the no-event display.