# Fix Element Drag Glitches

## Problem 1: Post-Release Movement

**Issue**: RAF callback executes after mouse up, applying one more update

### Solution:
1. **Add drag state check in RAF callback**: Don't execute if not dragging
2. **Cancel pending RAF on endDrag**: Use `cancelAnimationFrame()` to clear queued updates
3. **Use ref for isDragging state**: Check current state, not stale closure state

## Problem 2: Element Teleporting

### Root Causes & Solutions:

#### A. Dual Calculation Paths (PRIMARY ISSUE)
**Problem**: Position calculated in two different places with different logic

**Solution**: 
- Remove calculation from `Viewport.handleElementDrag()`
- Use ONLY `useElementDrag.updateDrag()` for position calculation
- Pass calculated position directly, don't recalculate
- Apply snapping AFTER drag calculation, not during

#### B. Stale elementStart During Drag
**Problem**: When element position updates, `dragState.elementStart` doesn't update

**Solution**:
- Store initial position in a ref that doesn't change during drag
- OR use offset from current element position instead of start position
- Don't rely on React state for drag calculations

#### C. Pan/Zoom Interference
**Problem**: Pan state changes affect `screenToCanvas()` calculations

**Solution**:
- Calculate drag delta in screen space (pixels)
- Apply delta directly to element position
- Don't recalculate using `screenToCanvas()` on every move
- Store initial screen coordinates and apply accumulated delta

#### D. RAF Throttle Skipping Updates
**Problem**: RAF throttle can skip frames, causing jumps

**Solution**:
- Remove RAF throttling entirely for position updates
- Apply updates synchronously
- Let React's batching handle rendering optimization
- Browser already limits to 60fps via repaint

## Implementation Plan

### Phase 1: Fix useElementDrag (useElementDrag.ts)

1. **Remove RAF throttling from updatePosition**:
   - Apply position updates synchronously
   - Remove `rafThrottle()` wrapper
   - Let React handle batching

2. **Add RAF cancellation to endDrag**:
   - Track RAF ID in a ref
   - Cancel on mouse up
   
3. **Use refs instead of state for drag tracking**:
   - Store `dragStartRef` and `elementStartRef`
   - Prevents stale closure issues

4. **Simplify updateDrag**:
   - Calculate pure delta from start position
   - Don't depend on React state during calculations

### Phase 2: Simplify Viewport Drag Logic (Viewport.tsx)

1. **Remove redundant calculation in handleElementDrag**:
   - Don't call `screenToCanvas()` 
   - Don't recalculate position
   - Receive position from drag handler

2. **Apply snapping only once**:
   - Get raw position from drag calculation
   - Apply snapping as final step
   - Update element with snapped position

3. **Use simpler event flow**:
```
Mouse Move
  → useElementDrag calculates new position (screen space delta)
  → Apply snapping to position
  → Update element position
  → React renders (batched)
```

### Phase 3: Optimize Coordinate Handling

1. **Store initial positions in screen space**:
   - Convert element position to screen coordinates on drag start
   - Apply deltas in screen space
   - Convert back to canvas space only once per update

2. **Prevent pan during element drag**:
   - Ensure `isClickOnElementRef` prevents panning
   - Don't update pan state while dragging element

### Phase 4: Remove Unused Code

1. Remove unused `throttle()` function
2. Remove `lastUpdateRef` (not used effectively)
3. Simplify handlers

## Expected Results

✅ Element stops immediately when mouse stops (no post-release drift)
✅ Element follows mouse perfectly with zero teleporting
✅ Smooth movement without frame skips
✅ Snapping works cleanly without causing jumps
✅ No interference between panning and element dragging
✅ Simpler, more predictable code

## Key Principle

**Single Source of Truth**: Element position during drag should be calculated ONCE per mouse event, in ONE place, using consistent coordinates.