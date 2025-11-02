## Overview
Fix the canvas left sidebar scrolling issue where properties get cut off when an element is selected, and remove the Quick Tips section for a cleaner interface.

## Problem Analysis
The current `Sidebar.tsx` structure has:
1. A fixed-height container with tabs (Tools/Layers)
2. Tab content areas that should scroll but don't have proper overflow handling
3. Properties Panel fixed at the bottom that can overflow its container
4. Quick Tips section in ToolsTab taking up valuable space

## Implementation Plan

### 1. Update `Sidebar.tsx` (Main Structure)
- Add `overflow-hidden` to the main sidebar container to establish scroll context
- Make the tab content areas (`TabsContent`) scrollable with `overflow-y-auto` and `gal-scrollbar`
- Keep the Properties Panel fixed at bottom with its own scrollable container
- Ensure proper flex layout so content areas take available space

**Key Changes:**
```tsx
// Tab content areas become scrollable
<TabsContent value="tools" className="flex-1 m-0 overflow-y-auto gal-scrollbar">

// Properties Panel gets its own scroll container
<div className="border-t bg-card max-h-[400px] overflow-y-auto gal-scrollbar">
```

### 2. Update `ToolsTab.tsx` (Remove Quick Tips)
- Remove the entire Quick Tips section (lines 102-109)
- Keep only the Canvas Tools section with the action buttons
- This frees up vertical space for more important content

**Remove:**
```tsx
{/* Quick Tips */}
<div className="text-xs text-muted-foreground space-y-1">
  <p className="font-medium">Quick Tips:</p>
  ...
</div>
```

### 3. Update `PropertiesPanel.tsx` (No changes needed)
- Already has proper spacing with `space-y-4`
- Parent container will handle scrolling

### 4. Update `LayersTab.tsx` (No changes needed)
- Already has proper spacing
- Parent container will handle scrolling

## Expected Behavior
- **Tools tab**: Scrollable when content exceeds viewport, Quick Tips removed
- **Layers tab**: Scrollable element list when many elements exist
- **Properties Panel**: Independently scrollable when properties exceed 400px, won't cut off content
- All scroll areas use consistent `gal-scrollbar` styling for brand consistency

## Files to Modify
1. `dashboard/components/canvas/Sidebar.tsx` - Add scroll containers
2. `dashboard/components/canvas/ToolsTab.tsx` - Remove Quick Tips section