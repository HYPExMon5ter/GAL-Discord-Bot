## Problem Analysis

The issue is a **z-index conflict** between the Dialog (z-50) and Popover (z-50), plus possible **modal focus trapping** by the Dialog component.

### Issues Identified:

1. **Z-Index Conflict**
   - Dialog overlay: `z-50`
   - Dialog content: `z-50`
   - Popover content: `z-50`
   - **Result**: Popover appears UNDER or at same level as Dialog, making it unclickable

2. **Modal Focus Trapping**
   - Dialog by default traps focus within itself
   - Radix Dialog's focus management prevents interaction with elements outside
   - Popover (inside Dialog) needs higher z-index to be above the Dialog's focus trap layer

3. **No Visible Cursor/Typing**
   - Input might be rendering but behind dialog overlay
   - Focus isn't reaching the input because dialog is capturing it
   - Auto-focus might be working but visually hidden

### Root Cause:
Both Dialog and Popover are at `z-50`, so when Popover opens inside Dialog:
- Popover renders at same level as Dialog
- Dialog's focus trap prevents interaction
- Clicking through to Cancel button behind confirms z-index issue

## Solution

### Part 1: Increase Popover Z-Index Above Dialog

**File:** `dashboard/components/ui/popover.tsx`

Change PopoverContent z-index from `z-50` to `z-[100]` or higher:

```tsx
className={cn(
  "z-[100] rounded-md border bg-popover p-4 ...",  // Changed from z-50
  className
)}
```

### Part 2: Add Modal={false} to Popover When Inside Dialog

**File:** `dashboard/components/ui/combobox.tsx`

Modify the Popover to not trap focus when inside a modal:

```tsx
<Popover open={open} onOpenChange={setOpen} modal={false}>
```

This prevents Popover from fighting with Dialog's focus management.

### Part 3: Ensure PopoverContent Uses Portal Correctly

The PopoverContent already uses Portal, but we should ensure it's rendering at document body level, not trapped inside Dialog.

**File:** `dashboard/components/ui/popover.tsx`

Verify PopoverPrimitive.Portal is being used (it already is, which is good).

### Part 4: Add Specific Z-Index for Combobox Popover

**File:** `dashboard/components/ui/combobox.tsx`

Override the z-index specifically in the Combobox PopoverContent:

```tsx
<PopoverContent 
  className="p-0 z-[100]"  // ADD z-[100] explicitly
  align="start"
  style={{ width: triggerWidth }}
  onInteractOutside={(e) => {
    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT';
    const isInsideContent = e.currentTarget.contains(target);
    
    if (isInput || isInsideContent) {
      e.preventDefault()
    }
  }}
>
```

### Part 5: Alternative - Use DropdownMenu Instead

If Popover continues to have issues, consider using Radix DropdownMenu which has better modal compatibility:

```tsx
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
```

But this requires more refactoring.

## Recommended Implementation Order

### Option A: Quick Fix (Try This First)

1. **Set `modal={false}` on Popover**
2. **Add `z-[100]` to PopoverContent in Combobox**

```tsx
// In combobox.tsx
<Popover open={open} onOpenChange={setOpen} modal={false}>
  <PopoverTrigger asChild>
    ...
  </PopoverTrigger>
  <PopoverContent 
    className="p-0 z-[100]"  // Changed from "p-0"
    align="start"
    style={{ width: triggerWidth }}
    ...
  >
```

### Option B: Global Fix (If Option A Works)

1. Update base Popover component z-index from `z-50` to `z-[60]`
2. Keep Combobox-specific override at `z-[100]`

## Expected Results

✅ **Popover appears above Dialog** - Visible and fully interactive  
✅ **Input is clickable** - Can click and focus the input field  
✅ **Cursor visible** - Blinking cursor shows in input  
✅ **Typing works** - Characters appear as you type  
✅ **No clicking through** - Can't accidentally click Dialog buttons behind  
✅ **Escape closes popover** - Then second Escape closes dialog  

## Files to Modify

### Primary Fix:
1. `dashboard/components/ui/combobox.tsx` - Add `modal={false}` and `z-[100]`

### Optional Enhancement:
2. `dashboard/components/ui/popover.tsx` - Increase base z-index to `z-[60]`

## Testing Checklist

- [ ] Open Create Graphic Dialog
- [ ] Click Event Name dropdown - should appear ABOVE dialog
- [ ] Click in search input - should get focus with visible cursor
- [ ] Type "Test Event" - should see characters appear
- [ ] See "Create event..." button
- [ ] Click outside dropdown (but inside dialog) - should close dropdown only
- [ ] Can't click Cancel button when dropdown is open
- [ ] Escape closes dropdown first, second Escape closes dialog
- [ ] Works in CreateGraphicDialog, CopyGraphicDialog, and Canvas TopBar

## Why This Fixes The Issue

**Z-Index Stacking Context:**
- Dialog: `z-50`
- Popover (new): `z-[100]`
- **Result**: Popover renders above Dialog

**Modal Focus Management:**
- `modal={false}` tells Popover not to trap focus
- Allows Dialog to manage overall focus
- Popover content remains accessible

**Portal Rendering:**
- PopoverPrimitive.Portal renders at document.body level
- With higher z-index, it appears above everything else
- No longer trapped under Dialog layers