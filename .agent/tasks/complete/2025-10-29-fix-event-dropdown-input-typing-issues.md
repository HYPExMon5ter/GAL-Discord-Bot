## Problem Analysis

The event dropdown input field is not accepting keyboard input due to the `onInteractOutside` handler in the Combobox component. This handler is calling `e.preventDefault()` when clicking on the input or inside the dropdown content, which is blocking normal input behavior.

## Root Cause

In `dashboard/components/ui/combobox.tsx` (lines 92-103), the `onInteractOutside` handler is:
1. Preventing default behavior for clicks inside the popover content
2. This prevents the input field from receiving focus and keyboard events properly
3. The Dialog modal in CreateGraphicDialog is also trapping focus, making it worse

## Solution

**File: `dashboard/components/ui/combobox.tsx`**

Remove the problematic `onInteractOutside` handler from the `PopoverContent` component. The `modal={false}` setting already handles proper interaction behavior.

**Changes:**
1. Remove the entire `onInteractOutside` prop from `PopoverContent`
2. Keep the `modal={false}` setting which already allows proper interaction
3. The input will automatically gain focus from the existing `useEffect` hook

This will allow:
- Normal text input in the search field
- Clicking on dropdown items to select them
- Creating new events by typing and pressing Enter
- Proper focus management without interference