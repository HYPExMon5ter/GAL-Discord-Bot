## Implementation Strategy

**Confirmed:** Using **ShadCN/UI components with Tailwind CSS** (already in use throughout the project).

**Dependencies:** Project already has most Radix UI primitives. Will need to install:
- `@radix-ui/react-popover` (for Combobox dropdown)
- `cmdk` (optional - for better command palette UX, but can use simpler approach)

## Workflow

1. **Create task plan markdown file**
2. **Commit current changes** (scrollable properties, event name editing, unified buttons)
3. **Install required dependencies**: `npm install @radix-ui/react-popover`
4. **Create ShadCN-style Popover component** (if not exists)
5. **Create ShadCN-style Combobox component** (searchable dropdown with create)
6. **Create EventSelector wrapper component**
7. **Add backend API endpoint** (`/api/v1/events`)
8. **Update CreateGraphicDialog** to use EventSelector
9. **Update CopyGraphicDialog** to use EventSelector
10. **Update Canvas TopBar** to use EventSelector + align buttons
11. **Test complete workflow**

## Component Architecture (ShadCN + Tailwind)

### 1. Popover Component (`dashboard/components/ui/popover.tsx`)
Standard ShadCN Popover using `@radix-ui/react-popover` + Tailwind:
- Clean, accessible dropdown positioning
- Supports trigger + content pattern
- Consistent with existing UI components

### 2. Combobox Component (`dashboard/components/ui/combobox.tsx`)
**Pure ShadCN/Tailwind implementation** - no external command libraries needed:
```tsx
Features:
- Popover-based dropdown
- Input field for search/filter
- List of filtered options
- "Create new" button when typing non-existent value
- Keyboard navigation (Arrow keys, Enter, Escape)
- Fully accessible (ARIA attributes)
- Tailwind styling matching existing components
```

**Styling approach:**
- Use existing Tailwind utilities
- Match `select.tsx` component visual style
- Integrate with `gal-scrollbar` for dropdown list
- Hover states using `hover:bg-accent`
- Selected state using `bg-accent`
- Icons from `lucide-react` (Check, ChevronsUpDown, Plus)

### 3. EventSelector Component (`dashboard/components/graphics/EventSelector.tsx`)
Business logic wrapper:
- Fetches events from API (`/api/v1/events`)
- Manages loading/error states
- Provides Combobox with event data
- Handles event creation flow
- Toast notifications for errors

## Backend Implementation

### API Endpoint (`api/routers/graphics.py`)
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

### Service Method (`api/services/graphics_service.py`)
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

## Frontend Updates

### CreateGraphicDialog & CopyGraphicDialog
Replace this:
```tsx
<Input
  value={eventName}
  onChange={(e) => setEventName(e.target.value)}
  placeholder="Enter event name..."
/>
```

With this:
```tsx
<EventSelector
  value={eventName}
  onValueChange={setEventName}
  disabled={loading}
  className="w-full"
/>
```

### Canvas TopBar Button Alignment
```tsx
<div className="border-b bg-card p-4 flex items-center justify-between gap-4">
  <Button variant="outline" onClick={onClose} disabled={saving}>
    <ArrowLeft className="h-4 w-4 mr-2" />
    Back
  </Button>

  <div className="flex-1 flex gap-3">
    {/* Graphic Title */}
    <div className="flex-1 space-y-1">
      <label className="text-xs text-muted-foreground">Graphic Title</label>
      <Input value={title} onChange={...} />
    </div>
    
    {/* Event Name - using EventSelector */}
    <div className="flex-1 space-y-1">
      <label className="text-xs text-muted-foreground">Event Name</label>
      <EventSelector value={eventName} onValueChange={onEventNameChange} />
    </div>
  </div>

  {/* Buttons aligned to bottom of fields */}
  <div className="flex items-end gap-2 pb-[1px]">
    <Button variant="outline" onClick={onClose}>Cancel</Button>
    <Button onClick={onSave}>
      <Save className="h-4 w-4 mr-2" />
      {saving ? 'Saving...' : 'Save'}
    </Button>
  </div>
</div>
```

## Tailwind Styling Patterns

Following existing component patterns:
- `border` - standard borders
- `rounded-gal` or `rounded-lg` - consistent border radius
- `bg-card` / `bg-muted` - background colors
- `text-foreground` / `text-muted-foreground` - text colors
- `hover:bg-accent` - hover states
- `gal-scrollbar` - custom scrollbar styling
- `transition-colors` - smooth color transitions
- `focus-visible:ring-2` - focus states

## Files to Create
1. `dashboard/components/ui/popover.tsx` - ShadCN Popover (if not exists)
2. `dashboard/components/ui/combobox.tsx` - ShadCN Combobox with create
3. `dashboard/components/graphics/EventSelector.tsx` - Event business logic wrapper
4. `.agent/tasks/active/2025-10-28-add-event-dropdown-with-creation-capability.md` - Task documentation

## Files to Modify
1. `api/routers/graphics.py` - Add `/events` endpoint
2. `api/services/graphics_service.py` - Add `get_event_names()` method
3. `dashboard/components/graphics/CreateGraphicDialog.tsx` - Use EventSelector
4. `dashboard/components/graphics/CopyGraphicDialog.tsx` - Use EventSelector
5. `dashboard/components/canvas/TopBar.tsx` - Use EventSelector + align buttons
6. `dashboard/package.json` - Add `@radix-ui/react-popover`

## Commit Message for Current Changes
```
feat: improve canvas properties panel and add event name editing

- Make Properties Panel dynamically fill available space with proper scrolling
- Add event name field to Canvas TopBar alongside graphic title
- Implement event name change handler and validation in CanvasEditor
- Remove size="sm" from all dialog buttons for visual consistency
- Update save validation to require both title and event name
- Improve TopBar layout with labeled input fields
- Remove Quick Tips section from ToolsTab for cleaner interface
```

## Benefits of This Approach

✅ **Pure ShadCN/Tailwind** - No heavy dependencies, consistent styling
✅ **Matches existing design system** - Uses same patterns as other components
✅ **Accessible** - Full keyboard navigation and ARIA support
✅ **Performant** - Lightweight, no command palette library overhead
✅ **Maintainable** - Standard React patterns, easy to understand
✅ **Flexible** - Can easily add more features later (sorting, grouping, etc.)

## Alternative: Enhanced Version with CMDK

If you want **even better UX** (fuzzy search, command palette feel), can optionally install `cmdk`:
- Better keyboard shortcuts
- Fuzzy matching
- Command palette aesthetics
- Slightly heavier (~5KB gzipped)

**Recommendation:** Start with pure ShadCN/Tailwind approach (lighter, simpler). Can enhance with cmdk later if needed.