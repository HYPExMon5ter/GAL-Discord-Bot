## Overview
Fix the Properties Panel to properly fill available space and scroll when needed, add event name editing capability throughout the application, and ensure consistent button sizing across all dialogs.

## Current Issues Identified

### 1. Properties Panel Scrolling
- The Properties Panel is set to `max-h-[400px]` which is arbitrary
- Should fill remaining vertical space dynamically and scroll only when content exceeds viewport
- Currently doesn't expand to use all available space after Quick Tips removal

### 2. Event Name Editing Missing
- Event name is required during graphic creation (already implemented)
- Event name is NOT editable in canvas editor TopBar (only title is shown)
- Event name cannot be updated after creation in the dashboard

### 3. Button Size Inconsistency
- Dialog footers have mismatched button sizes (Cancel vs Save/Submit)
- Need to ensure all action buttons use consistent sizing

## Implementation Plan

### Part 1: Fix Properties Panel Dynamic Height
**File:** `dashboard/components/canvas/Sidebar.tsx`

**Current Issue:** Properties Panel has fixed `max-h-[400px]`

**Solution:** Remove max-height constraint and use flex layout to fill remaining space

**Changes:**
```tsx
// OLD
<div className="border-t bg-card max-h-[400px] overflow-y-auto gal-scrollbar flex-shrink-0">

// NEW
<div className="border-t bg-card flex-1 min-h-0 overflow-y-auto gal-scrollbar">
```

This allows Properties Panel to:
- Take all remaining vertical space after tabs
- Automatically scroll when properties exceed available height
- Dynamically adjust when window resizes

### Part 2: Add Event Name to Canvas Editor
**Files:**
- `dashboard/components/canvas/TopBar.tsx` (add event name field)
- `dashboard/components/canvas/CanvasEditor.tsx` (manage event name state and saving)

**Current State:**
- TopBar only shows title as editable field
- CanvasEditor saves `event_name` but uses the original graphic's value

**Solution:**
Add event name input field next to title in TopBar with proper layout

**TopBar.tsx Changes:**
```tsx
interface TopBarProps {
  title: string;
  eventName: string; // ADD
  onTitleChange: (title: string) => void;
  onEventNameChange: (eventName: string) => void; // ADD
  // ... rest
}

// Layout: Two input fields side by side
<div className="flex-1 flex gap-3">
  <div className="flex-1">
    <label className="text-xs text-muted-foreground">Graphic Title</label>
    <Input value={title} onChange={(e) => onTitleChange(e.target.value)} ... />
  </div>
  <div className="flex-1">
    <label className="text-xs text-muted-foreground">Event Name</label>
    <Input value={eventName} onChange={(e) => onEventNameChange(e.target.value)} ... />
  </div>
</div>
```

**CanvasEditor.tsx Changes:**
```tsx
// Add event name state
const [eventName, setEventName] = useState(graphic.event_name || '');

// Add event name change handler
const handleEventNameChange = useCallback((newEventName: string) => {
  setEventName(newEventName);
}, []);

// Update save to include event name
const success = await onSave({
  title: title.trim(),
  event_name: eventName.trim(), // Use state instead of original
  data_json: getSerializedData(),
});

// Update validation
if (!title.trim() || !eventName.trim()) {
  toast.error('Missing fields', {
    description: 'Please enter both title and event name.',
  });
  return;
}

// Pass to TopBar
<TopBar
  eventName={eventName}
  onEventNameChange={handleEventNameChange}
  ...
/>
```

### Part 3: Unify Button Sizes Across Dialogs
**Files to Update:**
- `dashboard/components/graphics/CreateGraphicDialog.tsx`
- `dashboard/components/graphics/CopyGraphicDialog.tsx`
- `dashboard/components/graphics/DeleteConfirmDialog.tsx` (if exists)
- `dashboard/components/canvas/TopBar.tsx`

**Issue:** Cancel and Save buttons have inconsistent sizes

**Current State in Dialogs:**
```tsx
<Button variant="outline" size="sm" ...>Cancel</Button>
<Button size="sm" ...>Create & Start Editing</Button>
```

**Current State in TopBar:**
```tsx
<Button variant="outline" size="sm" ...>Cancel</Button>
<Button size="sm" ...>Save</Button>
```

**Solution:** Ensure all buttons use `size="default"` or consistent explicit sizing

**Apply to all DialogFooter sections:**
```tsx
<DialogFooter>
  <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
    Cancel
  </Button>
  <Button type="submit" disabled={...}>
    {loading ? '...' : 'Action'}
  </Button>
</DialogFooter>
```

**Apply to TopBar:**
```tsx
<Button variant="outline" onClick={onClose} disabled={saving}>
  Cancel
</Button>
<Button onClick={onSave} disabled={...}>
  <Save className="h-4 w-4 mr-2" />
  {saving ? 'Saving...' : 'Save'}
</Button>
```

Remove `size="sm"` from all action buttons to use default sizing consistently.

### Part 4: Ensure Event Name is Required
**Validation Points:**
1. ✅ Already required in CreateGraphicDialog (has `required` attribute)
2. ✅ Already required in CopyGraphicDialog (has `required` attribute)
3. ✅ Backend schema validates event_name as required (`min_length=1`)
4. ❌ Need validation in CanvasEditor save function (add in Part 2)

## Expected Results

### Properties Panel
- Fills all available vertical space in sidebar
- Scrolls smoothly when content (properties) exceeds viewport height
- Dynamically adjusts with window resize
- No fixed height constraint

### Event Name Editing
- TopBar shows two input fields: Graphic Title and Event Name
- Both fields are editable inline
- Both fields are required for saving
- Event name persists on save and appears in dashboard listings

### Button Consistency
- All Cancel and action buttons are the same size
- Consistent visual hierarchy across all dialogs and toolbars
- Professional, unified appearance

## Files to Modify
1. `dashboard/components/canvas/Sidebar.tsx` - Fix Properties Panel height
2. `dashboard/components/canvas/TopBar.tsx` - Add event name field and remove size="sm"
3. `dashboard/components/canvas/CanvasEditor.tsx` - Add event name state and validation
4. `dashboard/components/graphics/CreateGraphicDialog.tsx` - Remove size="sm" from buttons
5. `dashboard/components/graphics/CopyGraphicDialog.tsx` - Remove size="sm" from buttons

## Database/API Changes
No backend changes needed - event_name already supported in update endpoint.