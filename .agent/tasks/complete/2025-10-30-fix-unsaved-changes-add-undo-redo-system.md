# Fix Unsaved Changes Detection & Add Undo/Redo System

## Problem Analysis

### Why Unsaved Changes Detection Fails
The current implementation has a dependency issue:
- `useEffect` depends on `[canvas, getSerializedData]`
- `getSerializedData` is a `useCallback` that depends on `canvas`
- This creates a new function reference every time `canvas` changes
- The effect runs, but `initialCanvasStateRef.current` is also updated on mount via another effect with `[getSerializedData]` dependency
- **Root cause**: The initial state capture effect re-runs due to `getSerializedData` dependency, overwriting the baseline

## Solution Architecture

### 1. Fix Unsaved Changes Detection
**File**: `dashboard/components/canvas/CanvasEditor.tsx`
- Remove `getSerializedData` from the initial state capture effect dependencies
- Capture initial state only once on mount (empty deps array)
- Track title and eventName changes separately
- Compare serialized canvas state directly without function reference issues

### 2. Create Undo/Redo System
**New File**: `dashboard/hooks/canvas/useUndoRedo.ts`
- History stack with configurable max size (default 50)
- Current position pointer
- Actions: `pushState`, `undo`, `redo`, `canUndo`, `canRedo`, `clear`
- Debounced state pushing for drag operations (prevent history spam)
- Returns: `{ history, currentIndex, pushState, undo, redo, canUndo, canRedo, clear }`

### 3. Enhanced useCanvasState with Undo/Redo
**File**: `dashboard/hooks/canvas/useCanvasState.ts`
- Integrate `useUndoRedo` hook
- Push state to history after every mutation (updateBackground, addElement, updateElement, deleteElement)
- Add `undo()` and `redo()` methods that restore canvas state from history
- Add `canUndo`, `canRedo` boolean flags
- Debounce rapid position updates (element dragging) to avoid history spam

### 4. Redesigned TopBar Component
**File**: `dashboard/components/canvas/TopBar.tsx`

**New Layout**:
```
[Back Button] | [Graphic Title (smaller)] [Event Name (smaller)] | [Undo] [Redo] | [Cancel] [Save]
```

**Changes**:
- Reduce input sizes (more compact)
- Add vertical dividers (light gray `border-r`)
- Add Undo/Redo buttons with icons (RotateCcw, RotateCw from lucide-react)
- Disable undo/redo buttons when not available
- Add keyboard shortcuts (Ctrl+Z, Ctrl+Shift+Z or Ctrl+Y)
- Props: `onUndo`, `onRedo`, `canUndo`, `canRedo`

### 5. CanvasEditor Integration
**File**: `dashboard/components/canvas/CanvasEditor.tsx`
- Use enhanced `useCanvasState` with undo/redo
- Fix unsaved changes detection with corrected dependencies
- Add keyboard shortcut listener for Ctrl+Z (undo) and Ctrl+Y (redo)
- Pass undo/redo handlers to TopBar
- Track all changes: canvas state, title, eventName

## Implementation Details

### Undo/Redo Hook Structure
```typescript
interface HistoryState {
  canvas: CanvasState;
  timestamp: number;
}

function useUndoRedo(initialState: CanvasState, maxHistorySize = 50) {
  const [history, setHistory] = useState<HistoryState[]>([{ canvas: initialState, timestamp: Date.now() }]);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  const pushState = (state: CanvasState, debounce = false) => {
    // Add state to history, truncate future states if not at end
    // Limit history size
  };
  
  const undo = () => currentIndex > 0 ? history[currentIndex - 1].canvas : null;
  const redo = () => currentIndex < history.length - 1 ? history[currentIndex + 1].canvas : null;
  const canUndo = currentIndex > 0;
  const canRedo = currentIndex < history.length - 1;
  
  return { history, currentIndex, pushState, undo, redo, canUndo, canRedo, clear };
}
```

### Unsaved Changes Fix
```typescript
// BEFORE (BROKEN):
useEffect(() => {
  initialCanvasStateRef.current = getSerializedData();
}, [getSerializedData]); // Re-runs and overwrites baseline!

// AFTER (FIXED):
useEffect(() => {
  initialCanvasStateRef.current = serializeCanvasState(canvas);
  initialTitleRef.current = title;
  initialEventNameRef.current = eventName;
}, []); // Runs once on mount only

useEffect(() => {
  const currentState = serializeCanvasState(canvas);
  const hasChanges = 
    currentState !== initialCanvasStateRef.current ||
    title !== initialTitleRef.current ||
    eventName !== initialEventNameRef.current;
  setHasUnsavedChanges(hasChanges);
}, [canvas, title, eventName]); // Track all relevant changes
```

### TopBar Layout Structure
```tsx
<div className="border-b bg-card p-3 flex items-center justify-between gap-3">
  {/* Back Button */}
  <Button variant="outline" size="sm">Back</Button>
  
  {/* Divider */}
  <div className="h-8 w-px bg-border" />
  
  {/* Title & Event (Compact) */}
  <div className="flex-1 flex gap-2">
    <Input className="h-8 text-sm" />
    <EventSelector className="h-8 text-sm" />
  </div>
  
  {/* Divider */}
  <div className="h-8 w-px bg-border" />
  
  {/* Undo/Redo */}
  <div className="flex gap-1">
    <Button variant="ghost" size="sm">Undo</Button>
    <Button variant="ghost" size="sm">Redo</Button>
  </div>
  
  {/* Divider */}
  <div className="h-8 w-px bg-border" />
  
  {/* Cancel/Save */}
  <div className="flex gap-2">
    <Button variant="outline" size="sm">Cancel</Button>
    <Button size="sm">Save</Button>
  </div>
</div>
```

## Files to Modify/Create

### New Files
1. `dashboard/hooks/canvas/useUndoRedo.ts` - Core undo/redo state management

### Modified Files
1. `dashboard/hooks/canvas/useCanvasState.ts` - Integrate undo/redo
2. `dashboard/components/canvas/CanvasEditor.tsx` - Fix unsaved changes, add keyboard shortcuts
3. `dashboard/components/canvas/TopBar.tsx` - Redesign layout with undo/redo buttons

## Testing Scenarios
1. ✅ Move element → undo → redo
2. ✅ Add element → undo → element removed
3. ✅ Delete element → undo → element restored
4. ✅ Change element style → undo → style reverted
5. ✅ Rapid drag → history doesn't explode (debounced)
6. ✅ Undo to start → undo button disabled
7. ✅ Redo to end → redo button disabled
8. ✅ Make change after undo → future history cleared
9. ✅ Keyboard shortcuts work (Ctrl+Z, Ctrl+Y)
10. ✅ Unsaved changes detected for all scenarios
11. ✅ Title/event name changes trigger unsaved state

## Benefits
- **Robust Change Detection**: Works for all operations
- **Professional UX**: Standard undo/redo with keyboard shortcuts
- **Performance**: Debounced history for drag operations
- **Memory Efficient**: Configurable history limit
- **Cleaner UI**: Compact top bar with clear visual separation