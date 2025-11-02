## Problem Analysis

Looking at the screenshot and code, there are two main issues:

### Issue 1: Dropdown Closes When Clicking Input
The popover is closing when you try to click or type in the search input. This is because Radix UI Popover has default behavior that closes when clicking outside, but it's also triggering when clicking *inside* the popover content.

**Root Cause:**
- Radix Popover's `onInteractOutside` handler is not being prevented
- Need to stop click events from bubbling up from the input field

### Issue 2: Dropdown Width Too Narrow
The PopoverContent has a fixed width of `w-72` (288px) in the Popover component, which doesn't match the trigger button width.

**Root Cause:**
- `PopoverContent` className has hardcoded `w-72` width
- Should match the trigger button width dynamically

## Solution Spec

### Part 1: Fix Dropdown Closing Issue

**File:** `dashboard/components/ui/combobox.tsx`

Add two fixes:

1. **Prevent input clicks from closing popover**:
```tsx
<Input
  placeholder="Search or create..."
  value={search}
  onChange={(e) => setSearch(e.target.value)}
  onClick={(e) => e.stopPropagation()}  // ADD THIS
  onFocus={(e) => e.stopPropagation()}   // ADD THIS
  className="h-9"
/>
```

2. **Add onInteractOutside handler to PopoverContent**:
```tsx
<PopoverContent 
  className="w-full p-0" 
  align="start"
  onInteractOutside={(e) => {
    // Prevent closing when clicking inside the popover
    if (e.currentTarget.contains(e.target as Node)) {
      e.preventDefault()
    }
  }}
>
```

### Part 2: Fix Dropdown Width

**File:** `dashboard/components/ui/popover.tsx`

Change PopoverContent default width from fixed to match trigger:

```tsx
// BEFORE
className={cn(
  "z-50 w-72 rounded-md border bg-popover p-4 ...",
  className
)}

// AFTER  
className={cn(
  "z-50 rounded-md border bg-popover p-4 ...",  // Remove w-72
  className
)}
```

**File:** `dashboard/components/ui/combobox.tsx`

Update PopoverContent to use trigger width:

```tsx
<PopoverContent 
  className="p-0" 
  align="start"
  style={{ width: 'var(--radix-popover-trigger-width)' }}  // ADD THIS
  onInteractOutside={(e) => {
    if (e.currentTarget.contains(e.target as Node)) {
      e.preventDefault()
    }
  }}
>
```

### Alternative Part 2 (Simpler Approach)

If CSS variable doesn't work, use ref-based approach:

```tsx
const [triggerWidth, setTriggerWidth] = React.useState<number>()
const triggerRef = React.useRef<HTMLButtonElement>(null)

React.useEffect(() => {
  if (triggerRef.current) {
    setTriggerWidth(triggerRef.current.offsetWidth)
  }
}, [open])

// Then in PopoverTrigger
<PopoverTrigger asChild>
  <Button
    ref={triggerRef}
    variant="outline"
    ...
  >
```

And in PopoverContent:
```tsx
<PopoverContent 
  className="p-0" 
  style={{ width: triggerWidth }}
>
```

## Implementation Steps

1. **Fix interaction closing** - Add click/focus event stopPropagation to Input
2. **Add onInteractOutside handler** - Prevent closing when interacting inside popover
3. **Remove fixed width** from PopoverContent base component
4. **Make dropdown match trigger width** - Use CSS variable or ref approach
5. **Test interaction** - Verify input is clickable and typeable
6. **Test width** - Verify dropdown spans full width of button

## Expected Results

✅ **Input is clickable** - Can click into the search field without dropdown closing
✅ **Typing works** - Can type in search field to filter or create events
✅ **Dropdown stays open** - Popover doesn't close when interacting with content
✅ **Full width dropdown** - Matches the trigger button width exactly
✅ **Create button visible** - When typing, "Create event..." button appears
✅ **Can create events** - Clicking create button adds the new event

## Files to Modify

1. `dashboard/components/ui/combobox.tsx` - Fix input interaction and width
2. `dashboard/components/ui/popover.tsx` - Remove fixed width constraint

## Testing Checklist

- [ ] Click into search input - dropdown stays open
- [ ] Type in search input - characters appear
- [ ] Dropdown width matches button width
- [ ] "No events found" message appears when empty
- [ ] "Create event..." button appears when typing
- [ ] Can click "Create event..." to add new event
- [ ] Dropdown closes after selecting or creating event
- [ ] Works in CreateGraphicDialog
- [ ] Works in CopyGraphicDialog  
- [ ] Works in Canvas TopBar