## Problem Analysis

Two critical issues are preventing the event dropdown from working properly:

1. **Input Field Not Accepting Typing**: The Dialog component is using Radix UI's default modal behavior which traps focus and prevents interaction with elements inside the Dialog. The input field in the Popover can't receive keyboard events because the Dialog's focus trap is blocking them.

2. **Z-Index Conflict**: The Popover has `z-[100]` while the Dialog content has `z-50`, but because the Popover is rendered inside the Dialog's focus trap, it's still causing issues. The Cancel button underneath is still clickable through the dropdown.

## Root Causes

1. **Dialog Focus Trap**: Radix UI Dialog by default creates a focus scope that prevents keyboard events from reaching nested popovers
2. **Z-Index Hierarchy**: Dialog overlay (z-50) → Dialog content (z-50) → Popover (z-[60] default, z-[100] custom)
3. **Modal Behavior**: The Dialog's modal behavior is interfering with the Popover's event handling

## Solution

### File 1: `dashboard/components/ui/dialog.tsx`
Add support for `onOpenAutoFocus` prop to DialogContent to prevent automatic focus trapping on open.

### File 2: `dashboard/components/graphics/CreateGraphicDialog.tsx`
Add `onOpenAutoFocus` handler to DialogContent that prevents the dialog from immediately focusing elements, allowing the Popover to manage its own focus.

### File 3: `dashboard/components/ui/combobox.tsx`
1. Lower z-index from `z-[100]` to `z-[70]` (above Dialog z-50 but not excessive)
2. Add `onOpenAutoFocus` handler to prevent Radix from stealing focus
3. Improve the `onInteractOutside` handler to properly detect clicks inside the popover

### File 4: `dashboard/components/ui/popover.tsx`
Pass through `onOpenAutoFocus` prop to allow controlling focus behavior.

## Technical Details

**Focus Management Flow:**
1. Dialog opens → prevents auto-focus with `onOpenAutoFocus`
2. User clicks Event dropdown → Popover opens
3. Popover's `useEffect` focuses the input after 50ms delay
4. Input receives focus and keyboard events work normally
5. `onInteractOutside` prevents closing when interacting with input

**Z-Index Stack (lowest to highest):**
- Dialog overlay: z-50 (darkens background)
- Dialog content: z-50 (form content)
- Popover: z-[70] (dropdown above dialog content)
- Any future tooltips/toasts: z-[80+]