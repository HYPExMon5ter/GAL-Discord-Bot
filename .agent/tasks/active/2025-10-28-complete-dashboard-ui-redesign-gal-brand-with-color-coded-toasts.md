
## Complete Dashboard UI Redesign Plan

### Phase 1: Foundation & Typography
1. **Update Tailwind config** - Add brand fonts: Abrau Regular (headers), Montserrat (body), Bebas Neue Regular (accents)
2. **Update global CSS** - Implement deep dark mode (#0A0A0F background), brand colors (purple #7A3FF2, cyan #00E0FF, green #4EFFB0, red #FF5F5F), celestial decorative elements (outline stars/sparkles), proper high contrast for readability, toast color variants
3. **Update canvas fonts** - Add Abrau Regular, Montserrat, and Bebas Neue Regular to FONT_OPTIONS in PropertiesPanel.tsx

### Phase 2: Color-Coded Toast System
4. **Update Sonner.tsx** - Add color-coded toast variants:
   - **Success**: Green (#4EFFB0) background with green glow, white text
   - **Error/Delete**: Red (#FF5F5F) background with red glow, white text
   - **Info**: Purple (#7A3FF2) background with purple glow
   - **Warning**: Amber (#F59E0B) background with amber glow
   All with proper dark mode contrast and subtle glows matching brand style

### Phase 3: Login Screen Redesign
5. **Redesign LoginForm.tsx** - Remove ALL emojis, clean celestial aesthetic with subtle outline star decorations in corners, use Abrau Regular for "GUARDIAN ANGEL LEAGUE" title, angel wings logo with purple glow, brand pastel accents (#DEE4FF, #B3A8D4), deep dark background, high-contrast white text, professional appearance

### Phase 4: Dashboard Layout
6. **Redesign DashboardLayout header** - Remove emojis, angel wings icon with purple glow, "GUARDIAN ANGEL LEAGUE" in Abrau Regular, subtle celestial outline star accents (not emojis), clean spacing
7. **Update dashboard tabs** - Remove emojis, clean text-only tabs ("Active Graphics" / "Archived Graphics"), purple gradient for active state, smooth transitions

### Phase 5: Graphics Table Overhaul
8. **Redesign GraphicsTable.tsx** - Dark mode optimized, compact icon-only action buttons with color-coded tooltips and glows:
   - Edit: Cyan glow
   - Copy: Purple glow
   - Archive: Amber glow
   - Delete: Red glow
   - View: Green glow
   
   Alternating row backgrounds, purple hover tint, Montserrat typography, clean sort indicators

### Visual Design Principles:
- **NO emojis anywhere** - Clean, professional celestial aesthetic with outline stars/sparkles
- **Deep dark theme** - #0A0A0F background, #161626 cards
- **Brand typography** - Abrau (headers), Montserrat (body), Bebas Neue (accents)
- **High contrast** - White/light text (#FFFFFF) on dark backgrounds (WCAG AA compliant)
- **Color-coded feedback**:
  - Success/View: Green #4EFFB0
  - Error/Delete: Red #FF5F5F
  - Primary: Purple #7A3FF2
  - Warning/Archive: Amber #F59E0B
  - Info/Edit: Cyan #00E0FF
- **Subtle effects** - Glows, gradients, smooth transitions
- **Celestial decorations** - Outline stars, not emoji stars

### Files to Update:
- ✅ tailwind.config.ts (fonts)
- ✅ globals.css (dark mode, colors, toast variants, celestial styles)
- ✅ sonner.tsx (color-coded toast styles)
- ✅ LoginForm.tsx (complete redesign, no emojis)
- ✅ DashboardLayout.tsx (header redesign, no emojis)
- ✅ page.tsx (dashboard - clean tabs, no emojis)
- ✅ GraphicsTable.tsx (table overhaul, icon buttons)
- ✅ PropertiesPanel.tsx (add brand fonts)

All existing functionality preserved with dramatic visual improvement and better user feedback through color-coded notifications.
