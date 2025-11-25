# UI Improvements: Green View Icon and Mobile Responsiveness

## Overview
Two changes requested:
1. Change the "View in OBS" eye icon to a dark green color (matching theme brightness)
2. Add mobile responsiveness to the Dashboard and Login pages

---

## 1. Green "View in OBS" Icon

### Current State
Both active and archived graphics have the eye icon styled with `text-gal-cyan` (cyan/blue).

### Changes Made:
- Added `gal-view: '#2D7D46'` color to Tailwind config
- Added `.gal-glow-view` style to globals.css
- Updated GraphicsTable.tsx to use new green color for both eye icons

---

## 2. Mobile Responsiveness

### Changes Made:
- Login Page: Reduced logo and text sizes on mobile
- Dashboard Layout: Stacked header layout on mobile, reduced logo size
- Dashboard Page: Made tab buttons responsive on mobile
- GraphicsTab/ArchiveTab: Already had good responsive classes
