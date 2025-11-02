# Dashboard Header Redesign Spec

## Overview
Reorganize the dashboard header to move navigation tabs to the top level, implement gradient outline text effects, and improve visual hierarchy.

## Core Changes

### 1. Header Layout Restructure (DashboardLayout.tsx)
**Current**: Logo + Title on left, toolbar + Sign Out on right
**New**: 
- **Top row**: Logo (no wings) + "Live Graphics Dashboard" with gradient outline | Buttons on right (Active Graphics, Archive Graphics, Sign Out)
- **Divider**: Horizontal line separator
- Remove: Angel wings from GAL logo box, sparkle dots from header

### 2. Navigation Architecture (page.tsx → DashboardLayout.tsx)
**Move tabs from page level to layout header**:
- Relocate "Active Graphics" and "Archive Graphics" buttons from Tabs component to header
- Convert to styled button links that control active state
- Position buttons left of Sign Out button in header toolbar

### 3. Gradient Outline Text Effect (new CSS utility)
**Implement dual-layer text styling**:
```css
.gal-text-gradient-outline {
  color: white;
  -webkit-text-stroke: 2px transparent;
  background: linear-gradient(135deg, #7A3FF2, #00E0FF);
  -webkit-background-clip: text;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(122, 63, 242, 0.5));
}
```

**Apply to**:
- "Live Graphics Dashboard" header text
- "Active Graphics" button (when active)
- "Archive Graphics" button (when active)

### 4. Button Styling Enhancement
**Active state**: White text with gradient outline + purple glow
**Inactive state**: Muted text (gray) with subtle hover effect
**All buttons**: Increased color vibrancy, rounded corners (12px)

### 5. Logo Simplification
- Remove angel wing SVG decorations from GAL logo box
- Keep gradient background and glow effect
- Maintain "GAL" text with Abrau font

### 6. Cleanup
- Remove sparkle animation dots from header
- Remove sparkle dots from footer
- Keep footer simple with "System Online" status only

## File Changes

### dashboard/app/globals.css
- Add `.gal-text-gradient-outline` utility
- Add `.gal-button-tab` for navigation buttons
- Update gradient definitions for outline effect

### dashboard/components/layout/DashboardLayout.tsx
- Add toolbar prop to accept navigation buttons
- Remove angel wing SVGs from logo
- Remove sparkle decorative elements
- Add horizontal divider after header section
- Apply gradient outline to "Live Graphics Dashboard" text

### dashboard/app/dashboard/page.tsx
- Remove Tabs/TabsList/TabsTrigger components
- Pass tab buttons as toolbar prop to DashboardLayout
- Implement active state tracking for button highlighting
- Style buttons with gradient outline when active

## Visual Specifications

**Color Palette**:
- Primary Purple: #7A3FF2
- Cyan: #00E0FF
- Success Green: #4EFFB0
- Error Red: #FF5F5F
- Text Primary: #FFFFFF
- Text Secondary: #C5C5D1

**Typography**:
- Headers: Abrau Regular
- Body/Buttons: Montserrat
- Accents: Bebas Neue Regular

**Effects**:
- Gradient: 135deg from Purple to Cyan
- Glow: 0 0 20px with color/0.3 opacity
- Border Radius: 12px (gal standard)

## Expected Outcome
A cleaner, more professional header with navigation buttons prominently displayed alongside system controls, featuring distinctive gradient outline text effects that maintain readability while adding visual interest.