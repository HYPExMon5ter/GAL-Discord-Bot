# GAL Live Graphics Dashboard — Branding Update Plan  
**Author:** HYPExMon5ter  
**Target Model:** z.ai (GLM-4.6)  
**Objective:** Restyle the entire Live Graphics Dashboard frontend to fully align with the **Guardian Angel League (GAL) Brand Identity**, using the detailed color palette, typography, and design tone described below.

---

## 🧭 Context
This dashboard powers **live graphics overlays** for the *Guardian Angel League (GAL)* — a Teamfight Tactics community and tournament system.  
It generates OBS-ready graphics, scoreboard visuals, and dynamic canvas scenes.  
**Only** update styling and presentation; all functional logic, database integrations, and APIs must stay untouched.

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
1. **Updated global theme**
   - Update `tailwind.config.js`, `theme.css`, or equivalent with above palette & fonts.  
2. **Component restyling**
   - Modernize buttons, modals, sliders, sidebars using the GAL style system.  
3. **Brand assets**
   - Place GAL logo (light & dark variants) in `/public/assets/`.  
4. **Accessibility**
   - Ensure text contrast ratios meet WCAG AA.  
5. **Preview build**
   - Produce screenshots or build output verifying applied branding.

---

## 🧠 z.ai Action Plan
1. Scan the Live Graphics Dashboard repo.  
2. Locate all style-defining files and component libraries.  
3. Replace old theme values with the GAL palette and typography above.  
4. Apply consistent styling across global and per-component files.  
5. Output updated code plus a summary list of modified files.

---

## ✅ Acceptance Criteria
- UI matches GAL brand tone (dark-neon, purple/cyan glow, clean typography).  
- All components remain fully functional.  
- No unstyled legacy colors or mismatched fonts remain.  
- Readability and accessibility are preserved.

---

### ⚡ Prompt for z.ai
> You are updating the **GAL Live Graphics Dashboard** to match the **Guardian Angel League Brand Identity** described in this document.  
> Use the specified palette, typography, and component styling.  
> Preserve all logic and functionality while restyling every visible UI element, layout, and control to align with the GAL dark-neon aesthetic.  
> Deliver updated files and a concise changelog summarizing what was updated.

---