## Spec: Fix Duplicate Separator Between Tournament Format and Check-In

### Issue
When check-in is open but registration is not, there are two separators appearing between the Tournament Format section and the Check-In section:
- **Separator 1**: Added at the end of `_get_header_components()` (line 222)
- **Separator 2**: Added in `_build_all_components()` before check-in (line 155)

### Root Cause
The logic at line 154-155 adds a separator before check-in if either `show_registration` OR `show_tournament_info` is true. However, `_get_header_components()` already adds a separator at its end (line 222). 

When registration is closed but check-in is open:
1. Header components are added (includes separator at end)
2. Registration components are NOT added
3. Another separator is added before check-in
4. Check-in components are added

Result: Two separators between Tournament Format and Check-In.

### Solution
Change the condition at line 154 to only add a separator if `show_registration` is true:

**Current (line 154-155):**
```python
if show_checkin and (show_registration or show_tournament_info):
    components.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
```

**Fixed:**
```python
if show_checkin and show_registration:
    components.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
```

### Logic Explanation
- If registration is shown: separator is needed between registration and check-in
- If registration is NOT shown: header already has separator at end, so check-in follows naturally without needing another separator

### Result
Clean visual layout with only one separator between sections, regardless of which sections are visible.