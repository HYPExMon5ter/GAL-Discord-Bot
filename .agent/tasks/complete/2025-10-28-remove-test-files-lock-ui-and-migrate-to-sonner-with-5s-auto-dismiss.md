# Spec: Remove Test Files, Lock UI, and Migrate to Sonner with 5s Auto-dismiss

## Overview
Clean up unnecessary test files, remove visual lock indicators (except for in-use error messages), and migrate from the deprecated shadcn toast component to Sonner with 5-second auto-dismiss.

## Part 1: Remove Test Files

**Files to delete:**
- `tests/e2e/smoke.spec.ts` - Playwright E2E test (unused)
- `test-results/.last-run.json` - Test artifacts
- `test-results/` directory (if empty after cleanup)
- Consider removing: `playwright.config.ts`, `localhost.har` if tests aren't being used

## Part 2: Remove Lock Visual Indicators

### Delete LockBanner Component
- Delete: `components/locks/LockBanner.tsx` (confirmed unused - no imports found)
- Delete: `components/locks/` directory if empty after removal

### Update GraphicCard.tsx
Remove all visual lock indicators from graphics cards:
- Remove "In Use" badge from card title (lines 73-78)
- Remove lock status card display (lines 72-102) showing "Currently being edited" with timer
- Keep the card functional, just remove lock UI
- Lock logic stays in backend, only show errors via toast

### Update CanvasEditor.tsx
- Keep lock acquisition/refresh/release logic intact
- Simplify lock failure toast (line 58) to: "This graphic is currently in use"
- Remove lock state from UI rendering (no visual indicators)

## Part 3: Migrate to Sonner Toast (Recommended by shadcn)

### Why Sonner?
- Shadcn has deprecated the old toast component
- Sonner is the recommended replacement
- Built-in auto-dismiss with configurable duration (default 4s, we'll set to 5s)
- Better animations and UX
- Maintained by Emil Kowalski

### Installation Steps

**1. Install Sonner component:**
```bash
npx shadcn@latest add sonner
```

**2. Update layout.tsx:**
Replace `<Toaster />` import and usage:
```tsx
// Remove old import
- import { Toaster } from '@/components/ui/toaster'

// Add new import
+ import { Toaster } from '@/components/ui/sonner'

// Toaster stays in same location in JSX
<Toaster />
```

**3. Update all toast usage across files:**

Files that need updates (4 files):
- `components/graphics/GraphicsTab.tsx`
- `components/canvas/CanvasEditor.tsx`
- `components/archive/ArchiveTab.tsx`

Change import:
```tsx
// Old
- import { useToast } from '@/components/ui/use-toast'
- const { toast } = useToast()

// New
+ import { toast } from 'sonner'
```

Change toast calls:
```tsx
// Old format
toast({
  title: 'Success',
  description: 'Operation completed',
  variant: 'destructive',
})

// New Sonner format
toast.success('Success', {
  description: 'Operation completed',
  duration: 5000, // 5 seconds
})

// For errors
toast.error('Error title', {
  description: 'Error message',
  duration: 5000,
})

// For info/default
toast('Info message', {
  description: 'Details',
  duration: 5000,
})
```

**4. Set default duration globally:**
In `app/layout.tsx`, configure Toaster:
```tsx
<Toaster duration={5000} />
```

**5. Remove old toast files (after migration):**
- `components/ui/toast.tsx`
- `components/ui/use-toast.ts`
- `components/ui/toaster.tsx` (will be replaced by sonner version)

## Part 4: Simplify Lock Error Messages

### CanvasEditor.tsx Toast Updates
Update lock error toasts to be concise:
```tsx
// Lock acquisition failure (line 55-59)
toast.error('Graphic in use', {
  description: 'This graphic is currently being edited.',
  duration: 5000,
})

// Lock acquisition error (line 83-87)
toast.error('Lock error', {
  description: 'Could not acquire editing lock.',
  duration: 5000,
})

// Lock expired (line 120-124)
toast.error('Lock expired', {
  description: 'Your editing session has expired. Please refresh.',
  duration: 5000,
})

// Lock refresh failed (line 128-132)
toast.error('Lock refresh failed', {
  description: 'Unable to extend editing lock. Save changes soon.',
  duration: 5000,
})

// Lock release error (line 142-146)
toast.error('Lock release error', {
  description: 'Unable to release editing lock.',
  duration: 5000,
})
```

## Implementation Order

1. ✅ **Install Sonner** - `npx shadcn@latest add sonner`
2. ✅ **Update layout.tsx** - Switch to Sonner Toaster
3. ✅ **Update GraphicsTab.tsx** - Migrate all toast calls
4. ✅ **Update CanvasEditor.tsx** - Migrate toasts + simplify lock messages
5. ✅ **Update ArchiveTab.tsx** - Migrate all toast calls
6. ✅ **Remove lock UI** - Update GraphicCard.tsx, delete LockBanner
7. ✅ **Delete test files** - Clean up test directories
8. ✅ **Delete old toast files** - Remove deprecated components

## Files Summary

**To Delete (7 files):**
- `components/locks/LockBanner.tsx`
- `components/ui/toast.tsx`
- `components/ui/use-toast.ts`
- `components/ui/toaster.tsx` (replaced by sonner)
- `tests/e2e/smoke.spec.ts`
- `test-results/.last-run.json`
- `test-results/` directory

**To Modify (4 files):**
- `app/layout.tsx` - Switch to Sonner
- `components/graphics/GraphicCard.tsx` - Remove lock UI
- `components/canvas/CanvasEditor.tsx` - Migrate toasts, simplify lock messages
- `components/graphics/GraphicsTab.tsx` - Migrate toasts
- `components/archive/ArchiveTab.tsx` - Migrate toasts

## Expected Result
- ✅ All toasts auto-dismiss after 5 seconds
- ✅ No visual lock indicators on graphics cards
- ✅ Simple toast notification when attempting to edit locked graphic
- ✅ Modern Sonner toast system with better UX
- ✅ Clean codebase with no test artifacts