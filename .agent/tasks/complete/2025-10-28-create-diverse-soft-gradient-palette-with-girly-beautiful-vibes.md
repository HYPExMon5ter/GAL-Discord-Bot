
## Current State Analysis
All text elements currently use `.gal-text-gradient-primary` (purple #7A3FF2 → cyan #00E0FF), creating a uniform but monotonous look.

## New Gradient Palette Design
Using your GAL brand colors to create soft, beautiful, girly gradients with visual variety:

### **Gradient 1: Dreamy Pink-Purple** (Main Header)
- **Colors**: Soft Pink (#F082BE) → Lavender (#B3A8D4)
- **Vibe**: Gentle, elegant, feminine
- **Use**: "Live Graphics Dashboard" header

### **Gradient 2: Peach Blossom** (Active Graphics)
- **Colors**: Soft Peach/Pink (#FFDCF2) → Rose Pink (#F082BE)
- **Vibe**: Warm, soft, inviting
- **Use**: "Active Graphics" section header

### **Gradient 3: Twilight Blue-Purple** (Archive Graphics)
- **Colors**: Periwinkle (#DEE4FF) → Purple (#CA9ACC)
- **Vibe**: Cool, sophisticated, ethereal
- **Use**: "Archive Graphics" section header

### **Gradient 4: Cotton Candy** (Active Tabs)
- **Colors**: Baby Pink (#FFDCF2) → Lavender (#DEE4FF)
- **Vibe**: Sweet, playful, soft
- **Use**: Active navigation tab buttons

### **Gradient 5: Sunset Glow** (Alternative/Accents)
- **Colors**: Rose (#F082BE) → Purple-Pink (#CA9ACC)
- **Vibe**: Vibrant but soft, romantic
- **Use**: Special highlights or CTAs

## CSS Implementation

```css
/* Dreamy Pink-Purple - Main header */
.gal-text-gradient-primary {
  background: linear-gradient(135deg, #F082BE 0%, #B3A8D4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: bold;
}

/* Peach Blossom - Active Graphics */
.gal-text-gradient-peach {
  background: linear-gradient(135deg, #FFDCF2 0%, #F082BE 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: bold;
}

/* Twilight Blue-Purple - Archive Graphics */
.gal-text-gradient-twilight {
  background: linear-gradient(135deg, #DEE4FF 0%, #CA9ACC 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: bold;
}

/* Cotton Candy - Active tabs */
.gal-button-tab.active {
  background: linear-gradient(135deg, #FFDCF2 0%, #DEE4FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
}

/* Sunset Glow - Accents (kept as secondary) */
.gal-text-gradient-secondary {
  background: linear-gradient(135deg, #F082BE 0%, #CA9ACC 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
}

/* Keep soft blue for alternative use */
.gal-text-gradient-soft {
  background: linear-gradient(135deg, #9AB6DD 0%, #DEE4FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 500;
}
```

## Component Updates

1. **DashboardLayout.tsx**: Keep `.gal-text-gradient-primary` (now pink-purple)
2. **GraphicsTab.tsx**: Change to `.gal-text-gradient-peach`
3. **ArchiveTab.tsx**: Change to `.gal-text-gradient-twilight`
4. **Active tabs**: Automatically use new cotton candy gradient

## Visual Variety Achieved
- **Main Header**: Pink-purple dreamy gradient
- **Active Graphics**: Soft peach/pink warmth
- **Archive Graphics**: Cool blue-purple elegance
- **Active Tabs**: Sweet cotton candy tones

Each element gets its own beautiful, soft, girly gradient while maintaining brand cohesion with your GAL color palette.

## Files to Modify
1. `dashboard/app/globals.css` - Update gradient definitions
2. `dashboard/components/graphics/GraphicsTab.tsx` - Change to peach gradient
3. `dashboard/components/archive/ArchiveTab.tsx` - Change to twilight gradient
