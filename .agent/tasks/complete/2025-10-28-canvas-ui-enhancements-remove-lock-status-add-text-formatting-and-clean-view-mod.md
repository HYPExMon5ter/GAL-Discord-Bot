# Canvas UI Enhancements Spec

## Overview
Enhance the canvas editor with text formatting capabilities, remove unnecessary UI elements, and clean up the view mode display.

## Changes Required

### 1. Remove Lock Status Display (CanvasEditor.tsx)
**Location:** `components/canvas/CanvasEditor.tsx` lines 315-325
- Remove the absolute positioned lock status badge at bottom-left
- Keeps lock functionality intact - only removes the visual indicator
- Users no longer see "Editing as..." and "Lock expires..." text

### 2. Add Text Formatting Toolbar (PropertiesPanel.tsx)
**Location:** `components/canvas/PropertiesPanel.tsx`
**Adds:** Bold, Italic, Underline toggle buttons for text styling

**New Type Additions:**
```typescript
// lib/canvas/types.ts - extend BaseElement
export interface BaseElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  fontSize: number;
  fontFamily: string;
  color: string;
  bold?: boolean;      // NEW
  italic?: boolean;    // NEW
  underline?: boolean; // NEW
}
```

**UI Changes:**
- Add formatting toolbar section in PropertiesPanel
- Three toggle buttons (Bold, Italic, Underline) with shadcn Button component
- Applies to ALL element types (text, players, scores, placements)
- Styling applies via CSS: `fontWeight`, `fontStyle`, `textDecoration`

### 3. Remove Top-Left Controls in View Mode (CanvasView.tsx)
**Location:** `components/canvas/CanvasView.tsx` lines 132-140
- Remove the development debug info overlay that shows:
  - Graphic ID
  - Element count
  - Player count
  - Canvas dimensions
- This cleanup applies to both development AND production modes

### 4. Smart "No Data" Overlay Logic (CanvasView.tsx)
**Location:** `components/canvas/CanvasView.tsx` lines 122-130
**Current:** Shows "No Tournament Data" overlay when `players.length === 0`
**New Behavior:**
- Completely remove the "No data available" overlay
- When no data exists, dynamic elements simply don't render
- Static text elements always render regardless of data availability
- Clean, professional display with no overlays

### 5. Apply Text Formatting in Rendering Components

**TextElement.tsx:**
- Apply `fontWeight: bold ? 'bold' : 'normal'`
- Apply `fontStyle: italic ? 'italic' : 'normal'`
- Apply `textDecoration: underline ? 'underline' : 'none'`

**DynamicList.tsx:**
- Same formatting applied to all list items
- Consistent styling across all dynamic elements

## Implementation Details

### Type Safety
- Update `DEFAULT_ELEMENT_CONFIGS` to include default formatting values
- Serializer handles new properties automatically (backward compatible)
- Existing graphics without formatting properties default to `false`

### UI/UX Considerations
- Formatting buttons use variant="outline" with active state highlighting
- Changes apply immediately with live preview
- Formatting persists in saved graphics
- No migration needed - old graphics work without changes

## Files to Modify
1. `lib/canvas/types.ts` - Add formatting properties to BaseElement
2. `components/canvas/PropertiesPanel.tsx` - Add formatting toolbar UI
3. `components/canvas/elements/TextElement.tsx` - Apply formatting styles
4. `components/canvas/elements/DynamicList.tsx` - Apply formatting to list items
5. `components/canvas/CanvasEditor.tsx` - Remove lock status display
6. `components/canvas/CanvasView.tsx` - Remove debug overlay and data overlay

## Testing Checklist
- [ ] Text formatting toggles work for text elements
- [ ] Text formatting applies to player names
- [ ] Text formatting applies to scores
- [ ] Text formatting applies to placements
- [ ] Lock status no longer visible in editor
- [ ] View mode has clean display (no overlays, no debug info)
- [ ] Empty data state shows only static elements
- [ ] Formatting persists after save/reload
- [ ] Existing graphics load without errors