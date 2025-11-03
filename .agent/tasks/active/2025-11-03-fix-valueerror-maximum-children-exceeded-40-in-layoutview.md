## Problem Analysis

The error occurs because **LayoutView has a hard limit of 40 children components**, and the current implementation is trying to add 4 separate containers, each counting all their nested children toward that limit.

**Current Structure:**
- `_header_container`: ~9 children (Section, TextDisplays, Separators)
- `_registration_container`: ~6 children
- `_checkin_container`: ~6 children  
- `_action_buttons_container`: ~2 ActionRows with buttons
- **Total: ~23+ children** (likely exceeding 40 when all components are counted)

## Root Cause

The issue is that we're calling `add_item()` on individual containers, which makes each container a child of the LayoutView. Discord counts **all nested components recursively** toward the 40-child limit.

## Solution: Build Single Container Dynamically

Instead of adding multiple containers to the LayoutView, we need to:
1. Keep a **single container** on the LayoutView
2. **Dynamically build the container's children list** based on boolean flags
3. Build the container in `__init__()` before adding it to the view

### Implementation Approach

**Method 1: Dynamic Component List Building (Recommended)**
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    
    # Build list of components based on flags
    components = []
    
    if self.SHOW_HEADER:
        components.extend(self._get_header_components())
    
    if self.SHOW_REGISTRATION:
        components.extend(self._get_registration_components())
    
    if self.SHOW_CHECKIN:
        components.extend(self._get_checkin_components())
    
    if self.SHOW_ACTION_BUTTONS:
        components.extend(self._get_action_button_components())
    
    # Create single container with all selected components
    container = discord.ui.Container(*components, accent_colour=discord.Colour(15762110))
    self.add_item(container)
```

**Method 2: Helper Methods for Component Groups**
- Create methods like `_get_header_components()` that return a list of components
- Each method returns the components for that section
- Conditionally extend the components list based on boolean flags
- Build one container with all enabled components

### Key Changes Needed

1. **Remove class-level container definitions** (`_header_container`, etc.)
2. **Create component builder methods** that return lists of components
3. **Build single container dynamically** in `__init__()` with only enabled sections
4. **Keep the boolean toggles** for easy enable/disable

### Benefits

- ✅ Stays within 40-child limit
- ✅ Maintains conditional rendering capability
- ✅ Clean, readable code structure
- ✅ Easy to extend with more conditions later
- ✅ Boolean flags can be replaced with runtime conditions (tournament state, permissions, etc.)

### Future Enhancement Path

Once working with booleans, replace with:
- Tournament registration/checkin status checks
- User permission checks
- Time-based logic
- Player registration state