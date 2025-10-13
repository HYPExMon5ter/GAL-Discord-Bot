---
id: sops.dark-mode-management
name: Dark Mode Management SOP
version: 1.0
last_updated: 2025-01-13
tags: [sops, ui, dark-mode, theme, frontend]
status: active
---

# Dark Mode Management SOP

## Overview
This SOP covers the management and maintenance of the dark mode theme implementation across the GAL Live Graphics Dashboard.

## System Components

### CSS Variables
- **Location**: `dashboard/app/globals.css`
- **Primary Colors**: `#1a1a1a` (background), `#2a2a2a` (cards)
- **Implementation**: Tailwind CSS with dark mode variables

### Layout Configuration
- **Location**: `dashboard/app/layout.tsx`
- **Implementation**: `<html className="dark">` applied by default

### Affected Components
- DashboardLayout.tsx (header, tabs)
- GraphicsTab.tsx (empty states, buttons)
- ArchiveTab.tsx (headers, badges)
- LoginForm.tsx (login form)
- CanvasEditor.tsx (canvas backgrounds)

## Management Procedures

### 1. Color Scheme Updates
```css
/* Primary dark theme colors */
--background: 0 0% 10%;  /* #1a1a1a */
--card: 0 0% 15%;        /* Slightly lighter than background */
--muted: 0 0% 25%;      /* Dark muted backgrounds */
```

### 2. Component Dark Mode Guidelines
- **Input Fields**: Use `border-slate-700` for dark backgrounds
- **Cards**: Use `bg-card` and `border-slate-700`
- **Text**: Ensure contrast ratio meets accessibility standards
- **Gradients**: Use dark-to-darker gradients, not light colors

### 3. Troubleshooting Common Issues

#### Light Backgrounds in Dark Mode
1. Check for hardcoded `bg-white` or `bg-gray-50` classes
2. Replace with semantic classes like `bg-background` or `bg-card`
3. Test across all components

#### Text Visibility Issues
1. Verify text colors use semantic classes
2. Check contrast ratios using accessibility tools
3. Ensure hover states maintain visibility

#### Component Inconsistencies
1. Audit all components for light theme remnants
2. Update CSS imports to include dark mode variables
3. Test in both development and production builds

## Quality Assurance

### Testing Checklist
- [ ] Login form displays correctly in dark mode
- [ ] Dashboard header and navigation are dark themed
- [ ] All cards and panels use dark backgrounds
- [ ] Text remains readable with proper contrast
- [ ] Buttons and interactive elements are visible
- [ ] Canvas editor uses dark theme
- [ ] Search and input fields work correctly
- [ ] Empty states display properly

### Browser Compatibility
- Test across Chrome, Firefox, Safari, and Edge
- Verify CSS custom properties are supported
- Check for any theme switching issues

## Maintenance

### Regular Tasks
1. **Weekly**: Audit for any new light theme elements
2. **Monthly**: Review accessibility compliance
3. **Quarterly**: Update color scheme if needed

### Emergency Procedures
1. **Critical UI Issues**: Immediately revert to known working state
2. **Accessibility Violations**: Prioritize fixes for contrast and readability
3. **Build Failures**: Check CSS syntax and variable definitions

## Implementation History
- **2025-01-13**: Initial dark mode implementation
- **Components Updated**: DashboardLayout, GraphicsTab, ArchiveTab, LoginForm, CanvasEditor
- **Color Scheme**: Dark gray (#1a1a1a) primary background

## Related Documentation
- `frontend-components.md`
- `architecture.md`
- `dashboard-deployment.md`

## Support Contacts
- **Frontend Issues**: Contact UI/UX team
- **Build Problems**: Contact development team
- **Accessibility**: Review accessibility guidelines
