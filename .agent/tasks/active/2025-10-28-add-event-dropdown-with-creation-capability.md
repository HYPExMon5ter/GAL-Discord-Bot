# Add Event Dropdown with Creation and Align TopBar Buttons

**Status:** Active  
**Created:** 2025-10-28  
**Priority:** High  
**Type:** Feature Enhancement

## Overview
Replace all event name text inputs with a searchable dropdown (Combobox) that shows existing events, allows searching/filtering, and enables creating new events on-the-fly. Apply this to CreateGraphicDialog, CopyGraphicDialog, and Canvas TopBar. Also align buttons with input fields in TopBar.

## Current State Analysis

### Event Name Implementation
- Event names are stored in `graphics.event_name` column (string)
- No dedicated events table - event names are free-form strings
- No API endpoint to fetch distinct event names
- Currently implemented as plain text Input fields in 3 places:
  1. CreateGraphicDialog
  2. CopyGraphicDialog  
  3. Canvas TopBar

### UI Components Available
- `select.tsx` - Basic dropdown (not searchable, no create option)
- No Combobox component yet (need to create using shadcn/ui pattern)

## Implementation Plan

### Part 1: Create API Endpoint for Event Names
**File:** `api/routers/graphics.py`

Add new endpoint to fetch distinct event names from existing graphics:

```python
@router.get("/events", response_model=List[str])
async def get_event_names(
    _user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> List[str]:
    """Get list of unique event names from all graphics."""
    payload = await execute_service(service.get_event_names)
    return payload
```

**File:** `api/services/graphics_service.py`

Add service method:

```python
def get_event_names(self) -> List[str]:
    """Get list of distinct event names from all graphics."""
    result = (
        self.db.query(Graphic.event_name)
        .filter(Graphic.event_name.isnot(None))
        .filter(Graphic.event_name != '')
        .distinct()
        .order_by(Graphic.event_name)
        .all()
    )
    return [row[0] for row in result if row[0]]
```

### Part 2: Create Combobox UI Component
**File:** `dashboard/components/ui/combobox.tsx` (NEW)

Create a reusable Combobox component using shadcn/ui pattern with Popover + Command.

Key features:
- Search/filter functionality
- Select from existing options
- Create new option if not found
- Keyboard navigation support
- Accessible (ARIA attributes)

### Part 3: Create Popover Component (if needed)
**File:** `dashboard/components/ui/popover.tsx` (NEW - if not exists)

Standard shadcn/ui Popover component using @radix-ui/react-popover.

### Part 4: Create Event Selector Component
**File:** `dashboard/components/graphics/EventSelector.tsx` (NEW)

Wrapper component that:
- Fetches events from API on mount
- Uses Combobox for display
- Handles loading states
- Manages event creation

### Part 5: Update CreateGraphicDialog
**File:** `dashboard/components/graphics/CreateGraphicDialog.tsx`

Replace event name Input with EventSelector component.

### Part 6: Update CopyGraphicDialog
**File:** `dashboard/components/graphics/CopyGraphicDialog.tsx`

Replace event name Input with EventSelector component.

### Part 7: Update Canvas TopBar
**File:** `dashboard/components/canvas/TopBar.tsx`

1. Replace event name Input with EventSelector
2. Align buttons with input field bottom edges:
   - Wrap buttons in `flex items-end` container
   - Add `pb-[1px]` for precise alignment
   - Fields use `space-y-1` for label spacing

### Part 8: Update Frontend API Types
**File:** `dashboard/lib/api.ts`

Add events endpoint typing (optional).

## Expected Behavior

### Event Selection Flow
1. User opens CreateGraphicDialog/CopyGraphicDialog or edits in Canvas
2. Event Name shows as dropdown button
3. Click opens popover with search input
4. Shows list of existing events (fetched from API)
5. User can:
   - Select existing event from list
   - Type to filter events
   - Type new name and click "Create event {name}"
6. Selected/created event populates field
7. Form submits with event name

### Canvas TopBar Alignment
- Two input fields side-by-side with labels above
- Event field is combobox (looks like button but opens dropdown)
- Cancel and Save buttons aligned to bottom edge of input fields
- Clean, professional alignment with proper spacing

### API Integration
- `/api/v1/events` endpoint returns distinct event names
- Fast query with filtering and sorting
- Alphabetically sorted list
- Empty/null values filtered out

## Files to Create

1. `dashboard/components/ui/combobox.tsx` - Reusable combobox component
2. `dashboard/components/ui/popover.tsx` - Popover wrapper (if not exists)
3. `dashboard/components/graphics/EventSelector.tsx` - Event-specific combobox
4. `.agent/tasks/active/2025-10-28-add-event-dropdown-with-creation-capability.md` - This file

## Files to Modify

1. `api/routers/graphics.py` - Add `/events` endpoint
2. `api/services/graphics_service.py` - Add `get_event_names()` method
3. `dashboard/components/graphics/CreateGraphicDialog.tsx` - Replace Input with EventSelector
4. `dashboard/components/graphics/CopyGraphicDialog.tsx` - Replace Input with EventSelector
5. `dashboard/components/canvas/TopBar.tsx` - Replace Input with EventSelector + align buttons
6. `dashboard/lib/api.ts` - Add events fetch (optional typing)
7. `dashboard/package.json` - Add @radix-ui/react-popover if needed

## Dependencies to Check/Install

- `@radix-ui/react-popover` - May need installation
- Lucide icons: Check, ChevronsUpDown, Plus (already available)

## Testing Checklist

- [ ] Events API endpoint returns distinct event names
- [ ] Combobox opens and shows event list
- [ ] Search/filter works correctly
- [ ] Can select existing event
- [ ] Can create new event by typing + clicking create
- [ ] New event is immediately usable
- [ ] Event selector works in CreateGraphicDialog
- [ ] Event selector works in CopyGraphicDialog
- [ ] Event selector works in Canvas TopBar
- [ ] Buttons properly aligned with input fields in TopBar
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Loading states display correctly
- [ ] Empty states handled gracefully

## Benefits

✅ Consistent event naming across graphics  
✅ Easy event reuse and discovery  
✅ Prevents typos and duplicates  
✅ Clean UX for creating new events  
✅ Better alignment and visual hierarchy in TopBar  
✅ Improved user workflow efficiency  
✅ Professional, polished interface

## Notes

- Event names remain stored as strings in database (no schema changes)
- No migration required - backwards compatible
- Combobox component is reusable for other dropdowns in future
- Consider adding event management screen in future (rename, merge, delete events)

## Implementation Status

- [x] Create task plan file
- [x] Commit current changes
- [x] Install @radix-ui/react-popover
- [x] Create Popover component (if not exists)
- [x] Create Combobox component
- [x] Create EventSelector component
- [x] Add backend API endpoint and service method
- [x] Update CreateGraphicDialog
- [x] Update CopyGraphicDialog
- [x] Update Canvas TopBar
- [x] Commit event dropdown implementation
- [x] Fix dropdown interaction issues (input closing dropdown)
- [x] Fix dropdown width to match trigger button
- [x] Fix input focus and typing issues
- [x] Fix z-index conflicts between dialog and dropdown
- [ ] Test complete workflow
