# Fix TopBar Spacing and Layout

## Problem Analysis

Looking at the screenshot and current code, the issues are:

1. **Excessive gaps**: `gap-3` (12px) between all sections creates too much space
2. **justify-between**: Forces elements to spread across the entire width
3. **max-w-md limitation**: Title/Event inputs are constrained to 28rem max, leaving empty space
4. **Large padding**: `p-3` on the main container adds extra space
5. **Dividers have equal gap**: Dividers are treated the same as content, adding 12px on both sides

## Solution

### Layout Strategy
Change from `justify-between` to `justify-start` and use strategic spacing:
- **Tight sections**: Dividers with minimal gap (2px) from adjacent elements
- **Flexible inputs**: Remove max-width constraint, let Title/Event expand to fill space
- **Compact action groups**: Keep buttons grouped tightly
- **Reduced padding**: Use smaller padding for tighter layout

### Specific Changes

**File**: `dashboard/components/canvas/TopBar.tsx`

#### Current Structure (PROBLEM):
```tsx
<div className="... gap-3 justify-between">
  <Button>Back</Button>
  <div className="h-8 w-px bg-border" />  {/* 12px gap on both sides */}
  <div className="flex-1 flex gap-2 max-w-md">  {/* Limited width! */}
    {/* Inputs */}
  </div>
  <div className="h-8 w-px bg-border" />
  {/* More sections */}
</div>
```

#### New Structure (SOLUTION):
```tsx
<div className="... gap-2 justify-start">
  {/* Back button */}
  <Button className="shrink-0">Back</Button>
  
  {/* Divider with tight spacing */}
  <div className="h-8 w-px bg-border mx-1" />
  
  {/* Title/Event - FILL AVAILABLE SPACE */}
  <div className="flex-1 flex gap-2 min-w-0">  {/* No max-w, use min-w-0 for proper flex */}
    <div className="flex-1 min-w-[150px]">
      <label>Graphic Title</label>
      <Input />
    </div>
    <div className="flex-1 min-w-[150px]">
      <label>Event Name</label>
      <EventSelector />
    </div>
  </div>
  
  {/* Divider */}
  <div className="h-8 w-px bg-border mx-1" />
  
  {/* Undo/Redo - compact group */}
  <div className="flex gap-0.5 shrink-0">
    <Button>Undo</Button>
    <Button>Redo</Button>
  </div>
  
  {/* Divider */}
  <div className="h-8 w-px bg-border mx-1" />
  
  {/* Cancel/Save - compact group */}
  <div className="flex gap-1.5 shrink-0">
    <Button>Cancel</Button>
    <Button>Save</Button>
  </div>
</div>
```

### Key CSS Changes

1. **Main container**:
   - `p-3` → `p-2.5` (slightly tighter)
   - `gap-3` → `gap-2` (reduce spacing between elements)
   - `justify-between` → `justify-start` (no forced spreading)

2. **Dividers**:
   - Add `mx-1` (4px margin on each side) for tight visual separation
   - Keeps dividers close to adjacent content

3. **Title/Event section**:
   - Remove `max-w-md` completely
   - Add `min-w-0` to allow proper flexbox shrinking
   - Add `min-w-[150px]` to each input to prevent over-shrinking
   - Keep `flex-1` to expand and fill available space

4. **Button groups**:
   - Add `shrink-0` to prevent compression
   - Undo/Redo: `gap-1` → `gap-0.5` (2px between buttons)
   - Cancel/Save: `gap-2` → `gap-1.5` (6px between buttons)

5. **Back button**:
   - Add `shrink-0` to prevent compression

## Expected Result

**Before**:
```
[Back]        |        [Title: 200px] [Event: 200px]        |        [Undo] [Redo]        |        [Cancel]  [Save]
^^^^^         ^^^^^^^^                                      ^^^^^^^^                     ^^^^^^^^
Too much space        Max-width limited                      Too much space              Too much space
```

**After**:
```
[Back] | [Title: --------EXPANDS-------] [Event: --------EXPANDS-------] | [Undo][Redo] | [Cancel] [Save]
       ^^                                                                 ^^             ^^
     Tight                                                              Tight          Tight
```

## Benefits

1. ✅ **Reduced spacing**: Dividers are visually closer to content (4px vs 12px)
2. ✅ **No wasted space**: Title/Event inputs expand to fill available width
3. ✅ **Compact layout**: Overall tighter appearance without losing readability
4. ✅ **Responsive**: Inputs scale with window size while maintaining minimum widths
5. ✅ **Visual hierarchy**: Dividers clearly separate functional groups

## File to Modify

- `dashboard/components/canvas/TopBar.tsx` - Complete layout restructure