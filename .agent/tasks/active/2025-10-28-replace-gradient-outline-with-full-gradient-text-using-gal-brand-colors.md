
## Brand Color Analysis
From your GAL brand guidelines:
- **Primary Purple**: #7A3FF2 (main brand color)
- **Secondary Cyan/Blue**: #00E0FF (accent color)
- **Soft Pastels**: #FFDCF2, #DEE4FF, #9AB6DD, #B3A8D4, #CA9ACC, #F082BE

## Gradient Design Strategy

### Primary Gradient (Headers & Important Text)
**Purple to Cyan** - Your signature brand gradient
- Start: #7A3FF2 (Purple)
- End: #00E0FF (Cyan)
- Angle: 135deg for dynamic diagonal flow
- Use for: Main dashboard title, section headers

### Secondary Gradient (Active Tabs)
**Soft Purple to Pink** - Elegant and professional
- Start: #B3A8D4 (Soft Purple)
- End: #CA9ACC (Purple-Pink)
- Angle: 135deg
- Use for: Active tab buttons

### Alternative Options
**Light Blue to Cyan** - Clean and modern
- Start: #9AB6DD (Light Blue)
- End: #00E0FF (Cyan)
- Use for: Subtle emphasis elements

## Implementation Plan

### 1. Update CSS Classes in `globals.css`

Replace `.gal-text-gradient-outline` with gradient text classes:

```css
/* Primary gradient - Dashboard headers */
.gal-text-gradient-primary {
  background: linear-gradient(135deg, #7A3FF2 0%, #00E0FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: bold;
}

/* Secondary gradient - Active tabs */
.gal-text-gradient-secondary {
  background: linear-gradient(135deg, #B3A8D4 0%, #CA9ACC 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
}

/* Soft gradient - Subtle emphasis */
.gal-text-gradient-soft {
  background: linear-gradient(135deg, #9AB6DD 0%, #00E0FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

Update button active state:
```css
.gal-button-tab.active {
  background: linear-gradient(135deg, #7A3FF2 0%, #00E0FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
}
```

### 2. Update Components

**DashboardLayout.tsx** - Main header:
- Change class from `gal-text-gradient-outline` to `gal-text-gradient-primary`
- Remove `data-text` attribute (no longer needed)

**GraphicsTab.tsx** - Section header:
- Change to `gal-text-gradient-primary`
- Remove `data-text` attribute

**ArchiveTab.tsx** - Section header:
- Change to `gal-text-gradient-primary`
- Remove `data-text` attribute

**page.tsx** - Tab buttons:
- Active tabs will use updated `.gal-button-tab.active` class
- Keep existing structure, gradient applies automatically

### 3. Remove Old Code
- Delete `.gal-text-gradient-outline::before` pseudo-element CSS
- Clean up unused `data-text` attributes

## Visual Result
- **Dashboard Title**: Beautiful purple-to-cyan gradient (signature GAL colors)
- **Section Headers**: Same purple-to-cyan gradient for consistency
- **Active Tabs**: Matching gradient for visual coherence
- **Professional & Clean**: Soft gradients that align with your brand's elegant aesthetic

## Files to Modify
1. `dashboard/app/globals.css` - Replace outline CSS with gradient classes
2. `dashboard/components/layout/DashboardLayout.tsx` - Update header class
3. `dashboard/components/graphics/GraphicsTab.tsx` - Update header class
4. `dashboard/components/archive/ArchiveTab.tsx` - Update header class

This approach uses your exact brand colors in soft, professional gradients that will look polished and consistent across the entire dashboard.
