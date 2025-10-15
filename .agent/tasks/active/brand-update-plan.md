# GAL Live Graphics Dashboard — UI Enhancement & Canvas Improvement Plan  
**Author:** HYPExMon5ter  
**Target Model:** Refactor Coordinator  
**Objective:** Remove subtle shadows, fix canvas zoom behavior, and implement drag functionality while maintaining GAL branding consistency.

---

## 🧭 Context
This dashboard powers **live graphics overlays** for the *Guardian Angel League (GAL)* — a Teamfight Tactics community and tournament system.  
It generates OBS-ready graphics, scoreboard visuals, and dynamic canvas scenes.  

### 🔧 Current Issues to Address:
1. **Subtle Shadows**: Unwanted subtle shadows around tabs, buttons, and graphic table elements
2. **Canvas Zoom Behavior**: When zooming out, canvas becomes smaller instead of maintaining full screen coverage
3. **Canvas Interaction**: Missing drag functionality for empty canvas areas and inability to distinguish between element dragging and canvas panning

### 🎯 Key Objectives:
- Remove all subtle shadows while preserving hover glow effects
- Implement true infinite canvas zoom behavior (canvas always fills screen)
- Add canvas drag/pan functionality for empty areas
- Maintain existing GAL branding and color scheme

---

## 🎨 GAL Brand Identity (Text-Based Guidelines)

### 🔹 Color Palette
| Role | HEX | Description |
|------|------|-------------|
| **Primary Purple** | `#7A3FF2` | Main GAL color — energetic, slightly neon violet used for highlights, accents, and main buttons. |
| **Secondary Cyan** | `#00E0FF` | Cool glowing accent for hover effects, outlines, or complementary highlights. |
| **Deep Background** | `#0A0A0F` | Default background — near-black with a faint purple tint for immersive dark-mode visuals. |
| **Card / Surface Layer** | `#161626` | Slightly lighter background layer for cards, modals, and tool panels. |
| **Text Primary (Light)** | `#FFFFFF` | Main foreground text — crisp white for contrast on dark surfaces. |
| **Text Secondary** | `#C5C5D1` | Dimmed neutral text for secondary labels, captions, or tooltips. |
| **Error / Alert** | `#FF5F5F` | Used sparingly for warnings or invalid actions. |
| **Success / Confirm** | `#4EFFB0` | Green-cyan hybrid accent for confirmations, saves, or “ready” states. |

> Overall tone: **Dark, modern, and clean** — soft glows, neon gradients, and smooth hover transitions.  
> The purple should dominate, with cyan and white serving as accents. Never mix in harsh reds, yellows, or flat grayscale tones.

---

### 🔠 Typography
- **Primary Font:** `Poppins` (semibold and regular) — modern, rounded sans-serif.  
- **Secondary Font:** `Inter` or `Nunito` for body text if fallback needed.  
- Headings: uppercase or title-case with tight letter spacing (`font-weight: 600–700`).  
- Body text: `400–500`, high line-height for readability.  
- Avoid serif fonts entirely.  

> Keep typography crisp, consistent, and balanced — no more than two font weights per page.

---

### 🔳 UI/Component Style
- **Buttons:** Rounded corners (`border-radius: 12px`), subtle outer glow of primary purple; hover adds cyan edge or gradient.  
- **Cards/Containers:** Floating effect with faint inner shadow or border using semi-transparent cyan (`rgba(0, 224, 255, 0.15)`).  
- **Modals/Dialogs:** Blurred dark background (`backdrop-filter: blur(8px)`), white text, purple highlights.  
- **Inputs/Selectors:** Minimal outline with purple glow on focus.  
- **Sliders/Knobs:** Purple track with cyan thumb or indicator.  
- **Transitions:** Use smooth 200–300 ms cubic-bezier easing for hover/focus states.

---

### 💡 Lighting and Glow
- Prefer **soft gradients** over hard edges:
  - Example gradient: `linear-gradient(135deg, #7A3FF2 0%, #00E0FF 100%)`
- Add **subtle outer glows** for emphasis on active elements.
- Maintain overall **dark neon** tone — futuristic but clean.

---

### 🧭 Layout & Structure
- **Header / Top Bar:** Include GAL logo on left, right-aligned buttons with glowing hover.  
- **Sidebar (if any):** Gradient accent strip (purple→cyan) along active section indicator.  
- **Canvas / Main Editor:** Dark neutral background (`#0A0A0F`), grid lines or guides in translucent cyan.  
- **Footer:** Include zoom controls and text `© Guardian Angel League — Live Graphics Dashboard` styled in Text Secondary color.

---

## ⚙️ Technical Constraints
- Do **not** modify any backend logic, real-time data fetching, or OBS endpoints.  
- Maintain all current functionality for canvas manipulation, data sync, and rendering.  
- Ensure CSS/Tailwind/Styled-Components configuration remains valid and minimal.  

---

## 🧩 Required Deliverables

### Phase 1: Shadow Removal & UI Cleanup
1. **Remove subtle shadows from UI components**
   - Target: tabs, buttons, graphic tables
   - Preserve hover glow effects and interactivity
   - Update CSS/Tailwind classes to remove shadow utilities

### Phase 2: Canvas Zoom Enhancement
2. **Implement infinite canvas zoom behavior**
   - Canvas always fills available screen space
   - Zoom controls scale content, not canvas container
   - Maintain viewport coverage at all zoom levels

### Phase 3: Canvas Interaction
3. **Add canvas drag/pan functionality**
   - Empty area clicks should enable canvas panning
   - Element clicks should drag individual elements
   - Implement proper event delegation and hit detection

### Phase 4: Testing & Polish
4. **Functionality verification**
   - Test zoom behavior across all levels
   - Verify drag interactions work correctly
   - Ensure no regression in existing features

---

## 🧠 Technical Implementation Plan

### File Analysis Required:
- `dashboard/components/ui/button.tsx` - Remove shadow utilities, preserve hover effects
- `dashboard/components/ui/tabs.tsx` - Clean up tab styling 
- `dashboard/components/ui/select.tsx` - Remove subtle shadows
- `dashboard/app/globals.css` - Remove global shadow classes
- Canvas component files (locate these) - Implement zoom and drag functionality

### Implementation Steps:
1. **Shadow Removal Phase**
   - Audit all UI components for shadow classes (`shadow`, `shadow-sm`, `shadow-md`, etc.)
   - Remove unnecessary shadow utilities while preserving hover states
   - Update global CSS to remove default shadows

2. **Canvas Enhancement Phase**
   - Locate canvas rendering component
   - Implement viewport-based zoom (content scales, container fills screen)
   - Add pan/drag event handlers with hit detection
   - Ensure proper event delegation between canvas and element interactions

3. **Testing Phase**
   - Verify zoom maintains full screen coverage
   - Test drag interactions (canvas vs elements)
   - Confirm shadow removal doesn't break hover effects

---

## ✅ Acceptance Criteria
- **Shadow Removal**: All subtle shadows removed from tabs, buttons, and tables
- **Hover Effects**: Glow effects preserved and working on interactive elements
- **Canvas Zoom**: Canvas always fills screen at all zoom levels (infinite zoom behavior)
- **Canvas Drag**: Empty areas enable canvas panning, element areas drag individual elements
- **Functionality**: All existing features work without regression
- **Visual Polish**: Clean, professional appearance without unwanted shadows

---

### ⚡ Prompt for Refactor Coordinator
> You are implementing UI enhancements for the **GAL Live Graphics Dashboard** as described in this plan.  
> 
> **Primary Tasks:**
> 1. Remove subtle shadows from tabs, buttons, and tables while preserving hover glow effects
> 2. Fix canvas zoom behavior so canvas always fills screen at all zoom levels
> 3. Implement canvas drag/pan functionality for empty areas while maintaining element drag capability
> 
> **Technical Approach:**
> - Audit and remove shadow classes from UI components (`button.tsx`, `tabs.tsx`, `select.tsx`, `globals.css`)
> - Locate canvas component and implement viewport-based zoom (scale content, not container)
> - Add event handlers for canvas panning with proper hit detection
> - Maintain all existing GAL branding and functionality
> 
> **Deliverable:** Updated code files with a summary of changes made to address the shadow removal, canvas zoom, and drag functionality requirements.

---