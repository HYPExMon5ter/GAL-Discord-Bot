---
id: sops.ui-customization-guidelines
name: UI Customization Guidelines SOP
version: 1.0
last_updated: 2025-01-13
tags: [sops, ui, customization, emojis, themes, frontend]
status: active
---

# UI Customization Guidelines SOP

## Overview
This SOP provides guidelines for managing UI customization, including emojis, color schemes, and visual enhancements across the GAL Live Graphics Dashboard.

## Customization Categories

### 1. Emoji Usage Guidelines

#### Allowed Emojis
- **Headers**: Single emoji before text (e.g., "🎨 Active Graphics")
- **Actions**: Contextual emojis (e.g., "🔍 Search", "🚀 Create")
- **Status**: Status indicators (e.g., "🛡️ Security", "✨ New")

#### Emoji Placement Rules
- **Single Emojis Only**: No multiple emojis before/after text
- **Position**: Place emojis before text, not after
- **Consistency**: Use consistent emoji patterns across similar components

#### Prohibited Patterns
- ❌ Double emojis: "✨ Live Graphics Dashboard 🎯"
- ❌ Multiple emojis: "🎨 Active Graphics 📋 🎬"
- ❌ Emojis after text: "Active Graphics 🎨"

### 2. Color Scheme Management

#### Primary Color Palette
- **Background**: Dark gray (#1a1a1a)
- **Cards**: Slightly lighter (#2a2a2a)
- **Primary Blue**: #3b82f6 (for active states)
- **Success Green**: #10b981 (for positive actions)
- **Danger Red**: #ef4444 (for destructive actions)

#### Gradient Usage
- **Headers**: Blue to purple gradients for titles
- **Buttons**: Color-coded gradients based on action type
- **Cards**: Dark gradients for active/empty states

#### Dark Mode Compliance
- All components must work in dark mode
- Use semantic CSS classes over hardcoded colors
- Maintain accessibility contrast ratios

### 3. Component Customization

#### Header Customization
- **Main Title**: Gradient text with single emoji
- **Subtitles**: Clean text without emojis
- **User Info**: Minimal display (username, online status)

#### Tab Styling
- **Active State**: Blue background with white text
- **Inactive State**: Dark background matching theme
- **Icons**: Single emoji with text label

#### Button Styling
- **Primary Actions**: Gradient backgrounds with shadows
- **Secondary Actions**: Outline styling
- **Destructive Actions**: Red gradient backgrounds

## Implementation Procedures

### 1. Adding New Emojis
1. **Check Context**: Ensure emoji is relevant to component function
2. **Verify Placement**: Place emoji before text only
3. **Test Accessibility**: Ensure emoji doesn't interfere with screen readers
4. **Document**: Update component documentation

### 2. Color Updates
1. **Use CSS Variables**: Prefer semantic classes over hardcoded values
2. **Test Contrast**: Verify accessibility compliance
3. **Cross-Platform**: Test across different browsers
4. **Dark Mode**: Ensure compatibility with dark theme

### 3. Component Modifications
1. **Follow Patterns**: Use existing component styling patterns
2. **Maintain Consistency**: Keep similar components styled consistently
3. **Test Responsiveness**: Ensure changes work on all screen sizes
4. **Update Documentation**: Document any custom styling

## Quality Assurance

### Review Checklist
- [ ] Emojis follow placement guidelines (single, before text)
- [ ] Colors are accessible and meet contrast ratios
- [ ] Components work in dark mode
- [ ] No duplicate emojis or conflicting patterns
- [ ] Gradients are consistent with action types
- [ ] Responsive design maintained
- [ ] Browser compatibility verified

### Testing Procedures
1. **Visual Review**: Check all components for consistency
2. **Accessibility Test**: Verify screen reader compatibility
3. **Cross-Browser Test**: Test in Chrome, Firefox, Safari
4. **Responsive Test**: Test on mobile, tablet, desktop

## Customization Examples

### Correct Implementation
```tsx
// ✅ Good: Single emoji before text
<h2><span className="text-yellow-400">🎨</span> Active Graphics</h2>

// ✅ Good: Clean gradient button
<Button className="bg-gradient-to-r from-blue-500 to-blue-600">
  Create New Graphic
</Button>
```

### Incorrect Implementation
```tsx
// ❌ Bad: Double emojis
<h2>✨ Live Graphics Dashboard 🎯</h2>

// ❌ Bad: Emojis after text
<p>Active Graphics 🎨</p>

// ❌ Bad: Multiple emojis
<span>🎨 Create 📋 New 🚀 Graphic</span>
```

## Maintenance Schedule

### Regular Tasks
- **Weekly**: Audit for emoji placement consistency
- **Bi-weekly**: Review color scheme consistency
- **Monthly**: Test accessibility compliance
- **Quarterly**: Update emoji library if needed

### Emergency Procedures
1. **UI Breaking Changes**: Immediately revert to last working version
2. **Accessibility Issues**: Prioritize fixes for screen readers
3. **Browser Compatibility**: Address cross-browser issues promptly

## Version History
- **v1.0** (2025-01-13): Initial guidelines based on vibrant UI implementation

## Related Documentation
- `dark-mode-management.md`
- `frontend-components.md`
- `dashboard-operations.md`

## Support and Training
- **UI Training**: Provide developers with emoji and color guidelines
- **Design Review**: Regular design consistency reviews
- **Accessibility Training**: Ensure team understands accessibility requirements
