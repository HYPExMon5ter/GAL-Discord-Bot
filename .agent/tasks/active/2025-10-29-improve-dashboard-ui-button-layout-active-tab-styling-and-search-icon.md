## Overview
Reorganize the GraphicsTab header layout, make active tabs more noticeable, ensure consistent button sizing, and add search icon to the search bar.

## Current State Analysis

### GraphicsTab Layout (Lines 311-360 in GraphicsTab.tsx):
```tsx
<div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
  <Button onClick={() => setCreateDialogOpen(true)} ...>
    <Plus /> Create New Graphic
  </Button>
  
  <div className="flex items-center gap-3">
    <Input placeholder="Search..." value={searchTerm} />
    <Button onClick={refetch}>
      <RefreshCw /> Refresh
    </Button>
  </div>
</div>
```

### ArchiveTab Layout (Lines 273-311 in ArchiveTab.tsx):
```tsx
<div className="flex flex-col sm:flex-row gap-4">
  <div className="relative flex-1">
    <Search className="absolute left-3..." />  // HAS SEARCH ICON
    <Input placeholder="..." className="pl-10" />
  </div>
  
  <Button onClick={refetch}>Refresh</Button>
</div>
```

### Active Tab Styling (dashboard/page.tsx):
```tsx
<Button className={`gal-button-tab ${activeTab === 'graphics' ? 'active' : ''}`}>
```

## Implementation Plan

### Part 1: Reorganize GraphicsTab Header Layout

**File:** `dashboard/components/graphics/GraphicsTab.tsx`

**Current Structure:**
```
[Create New Graphic Button] ...................... [Search Input] [Refresh Button]
```

**New Structure:**
```
[Search Input] [Create New Graphic Button] [Refresh Button]
```

**Changes:**
1. Move search input to the left (full width flex-1)
2. Add Search icon inside input (like ArchiveTab)
3. Move "Create New Graphic" button between search and refresh
4. Ensure all buttons are same size (remove size="sm", use default)

```tsx
{/* Search and Actions */}
<div className="flex flex-col sm:flex-row gap-4">
  {/* Search Input with Icon - Full width on mobile, flex-1 on desktop */}
  <div className="relative flex-1">
    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
    <Input
      placeholder="Search graphics by title or event..."
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      className="pl-10"
    />
  </div>
  
  {/* Action Buttons - Same size, aligned */}
  <div className="flex items-center gap-3">
    <Button
      onClick={() => setCreateDialogOpen(true)}
      disabled={loading}
      className="flex items-center gap-2"
    >
      <Plus className="h-4 w-4" />
      Create New Graphic
    </Button>
    
    <Button
      variant="outline"
      onClick={refetch}
      disabled={loading}
      className="flex items-center gap-2"
    >
      <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      Refresh
    </Button>
  </div>
</div>
```

### Part 2: Make Active Tab More Noticeable

**File:** `dashboard/app/globals.css`

Update the `.gal-button-tab.active` styles to be more prominent:

```css
.gal-button-tab.active {
  background: linear-gradient(135deg, #FFDCF2 0%, #DEE4FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
  border: none;
  position: relative;
  color: transparent;
  /* ADD THESE: */
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.2);  /* Border glow */
  transform: scale(1.02);  /* Slightly larger */
}

/* ADD ACTIVE INDICATOR LINE */
.gal-button-tab.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #F082BE 0%, #B3A8D4 100%);
  border-radius: 3px 3px 0 0;
}
```

**Alternative Simpler Approach (if gradient text causes issues):**
```css
.gal-button-tab.active {
  background: linear-gradient(135deg, rgba(240, 130, 190, 0.15) 0%, rgba(179, 168, 212, 0.15) 100%);
  color: hsl(var(--primary));
  font-weight: 700;  /* Bolder */
  border: 2px solid hsl(var(--primary) / 0.3);  /* Visible border */
  box-shadow: 0 2px 8px rgba(240, 130, 190, 0.2);  /* Shadow */
}
```

### Part 3: Unify Button Sizes Across Dashboard

**Files to Update:**
- `dashboard/components/graphics/GraphicsTab.tsx`
- `dashboard/components/archive/ArchiveTab.tsx`

**Current Issues:**
- Some buttons use `size="sm"` (smaller)
- Others use default size
- Inconsistent visual hierarchy

**Solution:**
Remove ALL `size="sm"` from action buttons and use default size consistently.

**Buttons to Update:**

**GraphicsTab.tsx:**
```tsx
// Remove size="sm" from:
- Create New Graphic button
- Refresh button  
- Clear Selection button
- Archive Selected button
- Delete Selected button
```

**ArchiveTab.tsx:**
```tsx
// Remove size="sm" from:
- Refresh button
- Clear Selection button
- Restore Selected button
- Delete Selected button
```

### Part 4: Update Dashboard Page Tab Buttons

**File:** `dashboard/app/dashboard/page.tsx`

Remove `size="sm"` from tab navigation buttons:

```tsx
const toolbar = (
  <>
    <Button
      variant="ghost"
      // Remove: size="sm"
      onClick={() => setActiveTab('graphics')}
      className={`gal-button-tab ${activeTab === 'graphics' ? 'active' : ''}`}
    >
      Active Graphics
    </Button>
    <Button
      variant="ghost"
      // Remove: size="sm"
      onClick={() => setActiveTab('archive')}
      className={`gal-button-tab ${activeTab === 'archive' ? 'active' : ''}`}
    >
      Archived Graphics
    </Button>
  </>
);
```

## Expected Results

### Header Layout (GraphicsTab):
```
┌─────────────────────────────────────────────────────────────────────┐
│ [🔍 Search graphics...]  [➕ Create New Graphic]  [🔄 Refresh]     │
└─────────────────────────────────────────────────────────────────────┘
```

### Active Tab Visual:
```
┌────────────────────────┐  ┌──────────────────┐
│  Active Graphics  ═══  │  │ Archived Graphic │
└────────────────────────┘  └──────────────────┘
   ↑ Highlighted with border, shadow, and underline
```

### Button Consistency:
✅ All action buttons (Create, Refresh, Archive, Delete, Restore) same size  
✅ All tab buttons same size  
✅ Consistent padding and spacing  
✅ Professional, unified appearance  

## Files to Modify

1. `dashboard/components/graphics/GraphicsTab.tsx` - Reorganize header, add search icon, remove size="sm"
2. `dashboard/components/archive/ArchiveTab.tsx` - Remove size="sm" from buttons
3. `dashboard/app/dashboard/page.tsx` - Remove size="sm" from tab buttons
4. `dashboard/app/globals.css` - Enhance `.gal-button-tab.active` styling
4. `dashboard/app/globals.css` - Enhance `.gal-button-tab.active` styling

## Visual Improvements

### Before:
- Create button on left, isolated
- Search input far from related buttons
- Active tab barely distinguishable
- Button sizes inconsistent
- No search icon in GraphicsTab

### After:
- Logical flow: Search → Create → Refresh
- All actions grouped together
- Active tab clearly highlighted with border + underline
- All buttons uniform size
- Search icon in both tabs for consistency

## Testing Checklist

- [ ] Search input appears first (left side) with magnifying glass icon
- [ ] Create New Graphic button appears between search and refresh
- [ ] Refresh button appears last (right side)
- [ ] All three buttons are same height
- [ ] Active tab has visible border/shadow/underline
- [ ] Active tab clearly distinguishable from inactive
- [ ] Layout responsive on mobile
- [ ] Search icon visible in both Active and Archive tabs
- [ ] Button spacing consistent
- [ ] Works in both Active Graphics and Archived Graphics tabs