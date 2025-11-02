
## Gradient Text Outline Fix

### Problem Analysis
- Gradient outline is offset because the `::before` pseudo-element uses `transform: scale(1.06)` but positions from `left: 0; top: 0;`
- Hover states cause the outline to misbehave
- The outline doesn't stay centered on the text properly

### Solution
Fix the CSS for both `.gal-text-gradient-outline` and `.gal-button-tab.active` classes in `globals.css`:

1. **Center the outline properly**:
   - Use `left: 50%; top: 50%` positioning
   - Add `translate(-50%, -50%)` to the transform to center it
   - This ensures the scaled outline expands evenly around the text

2. **Fix hover behavior**:
   - Add `pointer-events: none` to the `::before` pseudo-element
   - Ensure the outline doesn't interfere with hover states

3. **Optimize the effect**:
   - Adjust `z-index` to ensure proper layering
   - Fine-tune blur and drop-shadow values for better visual appearance
   - Maintain consistent styling between header text and button tabs

### Files to Modify
- `dashboard/app/globals.css` - Update `.gal-text-gradient-outline::before` and `.gal-button-tab.active::before`

This will ensure white text with a properly centered gradient outline that doesn't shift or misbehave on hover.
