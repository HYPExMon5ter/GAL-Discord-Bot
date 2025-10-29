## Problem Analysis

The Combobox component has fundamental issues when used inside a Dialog:
1. **Focus Trap Conflicts**: Dialog's focus management conflicts with Popover's focus management
2. **Z-Index Issues**: Popover z-70 doesn't properly layer above Dialog z-50, allowing clicks through
3. **Aria-Hidden Blocking**: Modal Popover triggers aria-hidden which blocks keyboard input
4. **Overcomplicated Solution**: Using nested modal components (Dialog + Popover) creates multiple competing focus traps

## Root Cause

The issue is architectural - we're trying to layer two Radix UI modal primitives (Dialog and Popover), each with their own focus management, z-index stacking, and aria attributes. This creates conflicts that are difficult to resolve without breaking one component or the other.

## Proposed Solution: Simple Input with Dropdown Suggestions

Replace the Combobox with a simpler, native HTML-based approach that won't conflict with the Dialog:

### Option 1: Input + Datalist (Recommended - Simplest)
Use a native HTML `<input>` with a `<datalist>` for autocomplete suggestions. This is:
- **Simple**: No complex component layers
- **Native**: Browser handles all focus and keyboard events
- **Compatible**: Works perfectly inside Dialog
- **Intuitive**: Users can type freely or select from suggestions

**User Experience:**
- Click input field → start typing
- Dropdown shows matching events as you type
- Click suggestion to select
- Type new name to create new event
- No modal conflicts, works naturally

### Option 2: Custom Dropdown with Absolute Positioning
Build a custom dropdown that:
- Renders outside the Dialog using Portal
- Uses absolute positioning based on input coordinates
- Manages its own z-index hierarchy
- Doesn't use Radix Popover at all

**User Experience:**
- Similar to current Combobox
- More control over positioning and styling
- More code but more reliable

### Option 3: Two-Step Flow (Alternative UX)
Separate event selection from event creation:
- Show existing events as clickable chips/buttons
- Add "+ Create New Event" button that reveals an input field
- Clearer intent separation

**User Experience:**
- Click event chip to select existing
- Click "+ Create New" to show input for new event
- Less elegant but completely avoids dropdown issues

## Recommended Implementation: Option 1 (Input + Datalist)

### File: `dashboard/components/graphics/EventSelector.tsx`
**Changes:**
1. Remove Combobox import
2. Replace with native `<input>` element
3. Add `<datalist>` with event options
4. Style to match existing design
5. Keep fallback input for API errors

**Key Code:**
```tsx
<div>
  <input
    list="events-list"
    value={value}
    onChange={(e) => onValueChange(e.target.value)}
    placeholder="Type or select event name..."
    className="w-full h-10 px-3 rounded-md border"
  />
  <datalist id="events-list">
    {events.map(event => (
      <option key={event} value={event} />
    ))}
  </datalist>
</div>
```

### File: `dashboard/components/ui/combobox.tsx`
**Action:** Can be left as-is for potential future use outside of Dialogs, or removed if not needed elsewhere

## Benefits of Option 1

✅ **No Focus Conflicts**: Native input works seamlessly in Dialog  
✅ **No Z-Index Issues**: Browser handles layering natively  
✅ **Works Immediately**: No complex debugging needed  
✅ **Better UX**: Users can type freely without dropdown fighting them  
✅ **Accessible**: Native HTML datalist is screen-reader friendly  
✅ **Lightweight**: Much less code and complexity  
✅ **Mobile Friendly**: Native controls work better on mobile devices  

## Implementation Steps

1. Update EventSelector to use input + datalist
2. Add proper styling to match design system
3. Test typing and selection workflow
4. Remove debugging console.logs from Combobox
5. Verify event creation and selection both work

This approach completely sidesteps the Dialog/Popover conflict by using native HTML elements that the browser knows how to handle correctly.