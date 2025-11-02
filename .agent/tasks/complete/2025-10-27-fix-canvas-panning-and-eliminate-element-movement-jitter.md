# Canvas Panning and Movement Fix Plan

## Problem 1: Canvas Panning - Enable Left-Click Drag on Empty Space

**Current Issue**: Only middle mouse button enables panning
**Goal**: Left-click on empty space = pan canvas, Left-click on element = select/drag element

### Solution:
1. **Track click target in Viewport**: Detect if click started on canvas background vs element
2. **Modify `usePanZoom.handlePanStart`**: Accept left-click (button === 0) when no element is clicked
3. **Add click target detection**: Check if mouse down happened on an element or background
4. **Prioritize element dragging**: If click is on element, prevent canvas panning

### Implementation:
- Add `isClickOnElement` state to track click target
- Modify `handleCanvasClick` to `handleCanvasMouseDown` for better control
- Update pan logic to allow left-click when `isClickOnElement === false`
- Ensure element `onMouseDown` sets flag to prevent canvas pan

## Problem 2: Element Movement Jitter

**Root Causes**:
1. Double debouncing (16ms + 8ms) causing delayed updates
2. Snap cache invalidation on every move
3. Multiple state update layers adding latency
4. Transition CSS briefly activating after drag

### Solution Approach:

#### A. Remove Excessive Debouncing
- **Remove** `debouncedUpdateElement` in Viewport.tsx
- **Remove** debounce from `handleElementDrag`
- Keep ONLY RAF throttling in `useElementDrag` for smooth 60fps updates
- Direct path: RAF → update position → React state

#### B. Optimize Snapping
- Remove snap result cache (overhead > benefit for single element drag)
- Keep dimension cache only
- Round snap positions BEFORE calculating to reduce micro-adjustments
- Reduce snap threshold from 8px to 5px for cleaner snapping

#### C. Simplify Update Chain
```
Mouse Move Event
  → RAF throttle (one frame delay max)
    → Calculate snap position
      → Update React state directly
```

#### D. Fix Transition CSS
- Remove `transition-all` completely during drag operations
- Use `will-change: transform` only during active drag
- Reset `will-change` immediately on mouse up

#### E. Direct Position Updates
- Move snapping calculation INSIDE the drag handler
- Apply snap before state update (not after)
- Use integer positions only (no fractional pixels)

## Problem 3: Movement Should Stop Immediately with Mouse

**Current Issue**: Element continues moving briefly after mouse stops
**Cause**: Debounced updates queued after mouse stops

### Solution:
- Remove all debouncing
- Use RAF throttling only (updates stop when frames stop)
- Flush any pending updates immediately on mouse up

## Implementation Order

### Phase 1: Fix Panning (usePanZoom.ts, Viewport.tsx)
1. Add click target tracking to Viewport
2. Detect empty space clicks vs element clicks
3. Enable left-click panning for empty space
4. Prevent panning when element is being dragged

### Phase 2: Remove Debouncing (Viewport.tsx, useElementDrag.ts)
1. Remove `debouncedUpdateElement` function
2. Remove debounce from `handleElementDrag`
3. Keep only RAF throttling in drag updates
4. Ensure updates flush on mouse up

### Phase 3: Optimize Snapping (snapping.ts)
1. Remove snap result cache
2. Round positions before snap calculation
3. Reduce snap threshold to 5px
4. Keep dimension cache only

### Phase 4: Fix Element CSS (TextElement.tsx, DynamicList.tsx)
1. Remove transition CSS entirely during drag
2. Use `will-change: transform` only during active drag
3. Apply integer positions only

### Phase 5: Simplify Update Flow (Viewport.tsx)
1. Direct path: drag event → snap → state update
2. Remove intermediate debounce layers
3. Round all positions to integers

## Expected Results

✅ Left-click empty space = pan canvas
✅ Left-click element = select/drag element  
✅ Smooth 60fps element movement
✅ Element follows mouse exactly with zero lag
✅ Movement stops immediately when mouse stops
✅ Clean snapping with no jitter
✅ No "drift" after releasing mouse