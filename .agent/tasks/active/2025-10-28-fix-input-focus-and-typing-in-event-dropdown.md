## Problem Analysis

The input field is not properly receiving focus when clicked, and keyboard input is not being captured. The issues are:

### Issue 1: stopPropagation Blocking Focus
The `e.stopPropagation()` on `onFocus` might be interfering with the input's ability to receive focus properly.

### Issue 2: No Auto-Focus on Open
When the dropdown opens, the input should automatically receive focus so the user can immediately start typing.

### Issue 3: Potential onInteractOutside Conflict
The `onInteractOutside` handler might be interfering with the input field's focus behavior.

## Solution

### Part 1: Auto-Focus Input When Dropdown Opens
**File:** `dashboard/components/ui/combobox.tsx`

Add a ref for the input field and auto-focus it when the popover opens:

```tsx
const inputRef = React.useRef<HTMLInputElement>(null)

React.useEffect(() => {
  if (open && inputRef.current) {
    // Small delay to ensure popover is fully rendered
    setTimeout(() => {
      inputRef.current?.focus()
    }, 0)
  }
}, [open])
```

### Part 2: Update Input Props
Remove `onFocus` stopPropagation (it's blocking focus) and add ref:

```tsx
<Input
  ref={inputRef}
  placeholder="Search or create..."
  value={search}
  onChange={(e) => setSearch(e.target.value)}
  onClick={(e) => e.stopPropagation()}
  // Remove: onFocus={(e) => e.stopPropagation()}
  className="h-9"
  autoFocus  // Also try this
/>
```

### Part 3: Improve onInteractOutside Handler
Make the handler more specific to avoid blocking input interactions:

```tsx
onInteractOutside={(e) => {
  // Only prevent closing if clicking on the input or dropdown items
  const target = e.target as HTMLElement;
  const isInput = target.tagName === 'INPUT';
  const isInsideContent = e.currentTarget.contains(target);
  
  if (isInput || isInsideContent) {
    e.preventDefault()
  }
}}
```

### Part 4: Add onKeyDown Handler for Enter Key
Allow users to create events by pressing Enter:

```tsx
<Input
  ref={inputRef}
  placeholder="Search or create..."
  value={search}
  onChange={(e) => setSearch(e.target.value)}
  onClick={(e) => e.stopPropagation()}
  onKeyDown={(e) => {
    if (e.key === 'Enter' && search.trim() && !options.includes(search.trim())) {
      e.preventDefault()
      handleCreateNew()
    }
  }}
  className="h-9"
/>
```

## Complete Updated Combobox Component

```tsx
export function Combobox({
  value,
  onValueChange,
  options,
  placeholder = "Select...",
  emptyText = "No results found.",
  createText = "Create",
  disabled = false,
  className,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const triggerRef = React.useRef<HTMLButtonElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)  // ADD THIS
  const [triggerWidth, setTriggerWidth] = React.useState<number>(0)

  React.useEffect(() => {
    if (triggerRef.current) {
      setTriggerWidth(triggerRef.current.offsetWidth)
    }
  }, [open])

  // AUTO-FOCUS INPUT WHEN DROPDOWN OPENS
  React.useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => {
        inputRef.current?.focus()
      }, 0)
    }
  }, [open])

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(search.toLowerCase())
  )

  const handleSelect = (selectedValue: string) => {
    onValueChange(selectedValue)
    setOpen(false)
    setSearch("")
  }

  const handleCreateNew = () => {
    if (search.trim()) {
      onValueChange(search.trim())
      setOpen(false)
      setSearch("")
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          ref={triggerRef}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between font-normal", className)}
        >
          {value || placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className="p-0" 
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
        <div className="p-2">
          <Input
            ref={inputRef}  // ADD THIS
            placeholder="Search or create..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {  // ADD THIS
              if (e.key === 'Enter' && search.trim() && !options.includes(search.trim())) {
                e.preventDefault()
                handleCreateNew()
              }
              // Allow Escape to close
              if (e.key === 'Escape') {
                setOpen(false)
              }
            }}
            className="h-9"
          />
        </div>
        {/* ... rest of component */}
      </PopoverContent>
    </Popover>
  )
}
```

## Expected Results

✅ **Auto-focus on open** - Input automatically receives focus when dropdown opens  
✅ **Cursor visible** - Input shows blinking cursor immediately  
✅ **Typing works** - Characters appear in input field as you type  
✅ **Enter to create** - Press Enter to create new event  
✅ **Escape to close** - Press Escape to close dropdown  
✅ **Click to focus** - Clicking input field works properly  

## Files to Modify

1. `dashboard/components/ui/combobox.tsx` - Add auto-focus and keyboard handling

## Testing Steps

1. **Open Create Graphic Dialog**
2. **Click Event Name dropdown** - Should open with cursor in input field
3. **Start typing** - Should see characters appear immediately
4. **Type "Test Event"** - Should see "Create event Test Event" button appear
5. **Press Enter** - Should create and select the event
6. **Try again** - Click dropdown, type, should work smoothly

## Root Cause Summary

The issue is that the input field needs:
1. **Auto-focus** when dropdown opens (currently manual click required)
2. **Proper event handling** (onFocus was blocking interactions)
3. **Keyboard support** (Enter key for quick creation)