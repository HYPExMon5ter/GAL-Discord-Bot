# Canvas Delete & Unsaved Changes Protection

## Changes

### 1. Fix Delete Key Handler in Viewport.tsx
- Currently calls `onUpdateElement` with empty object (bug)
- Change to call `onDeleteElement` prop to properly delete selected elements
- Add prop: `onDeleteElement: (elementId: string) => void`

### 2. Add Unsaved Changes Tracking in CanvasEditor.tsx
- Track initial canvas JSON state on mount
- Add `hasUnsavedChanges` state that compares current vs initial state
- Reset to `false` after successful save
- Update whenever canvas state changes

### 3. Create UnsavedChangesDialog Component
- New file: `components/canvas/UnsavedChangesDialog.tsx`
- Use AlertDialog for prominent warning modal
- Actions: "Discard Changes" (destructive) and "Save Changes" (primary)
- Match styling of existing DeleteConfirmDialog

### 4. Implement Navigation Protection
- Add `beforeunload` event listener when `hasUnsavedChanges === true`
- Intercept close button click to show confirmation modal
- On confirm discard: allow close
- On confirm save: trigger save then close

## Files Modified
- `dashboard/components/canvas/Viewport.tsx` - Fix delete key handler
- `dashboard/components/canvas/CanvasEditor.tsx` - Add unsaved changes tracking and modal
- `dashboard/components/canvas/UnsavedChangesDialog.tsx` - New confirmation modal component