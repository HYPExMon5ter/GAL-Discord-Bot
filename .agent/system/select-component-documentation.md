---
id: system.select_component_documentation
version: 1.0
last_updated: 2025-01-13
tags: [select, component, ui, dropdown, form, frontend]
---

# Select Component Documentation

## Overview
The Select component is a custom, fully-featured dropdown component built for the Live Graphics Dashboard. It provides a flexible, accessible, and visually consistent way to implement selection interfaces throughout the application.

## Component Architecture

### File Location
`dashboard/components/ui/select.tsx`

### Component Structure
```tsx
Select (Container)
├── SelectTrigger (Button component)
├── SelectContent (Dropdown container)
│   └── SelectItem (Individual options)
└── SelectValue (Display text for selected value)
```

### Implementation Pattern
The Select component follows the compound component pattern, allowing flexible composition while maintaining internal state management.

## API Reference

### Select (Container)
```typescript
interface SelectProps {
  children: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  disabled?: boolean;
  name?: string;
  required?: boolean;
}
```

**Props Description**:
- `children`: Select component children (Trigger, Content, Items)
- `value`: Controlled value for the select
- `defaultValue`: Initial uncontrolled value
- `onValueChange`: Callback when value changes
- `disabled`: Disables the select interaction
- `name`: Form field name for form submission
- `required`: Marks the field as required

### SelectTrigger
```typescript
interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  placeholder?: string;
  disabled?: boolean;
}
```

**Features**:
- Renders as a button with proper ARIA attributes
- Shows placeholder when no value is selected
- Displays selected value through SelectValue component
- Supports all standard button props

### SelectContent
```typescript
interface SelectContentProps {
  children: React.ReactNode;
  position?: 'popper' | 'item-aligned';
  side?: 'top' | 'right' | 'bottom' | 'left';
  sideOffset?: number;
  align?: 'start' | 'center' | 'end';
  alignOffset?: number;
  avoidCollisions?: boolean;
  collisionBoundary?: Element[];
  collisionPadding?: number;
  arrowPadding?: number;
  sticky?: 'partial' | 'always';
  hideWhenDetached?: boolean;
}
```

**Features**:
- Positions dropdown relative to trigger
- Handles collision detection and avoidance
- Supports arrow indicators
- Configurable positioning and alignment

### SelectItem
```typescript
interface SelectItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  value: string;
  disabled?: boolean;
  textValue?: string;
}
```

**Features**:
- Individual selectable options
- Custom value and display text
- Disabled state support
- Keyboard navigation compatibility

### SelectValue
```typescript
interface SelectValueProps {
  placeholder?: string;
}
```

**Features**:
- Displays the currently selected value
- Shows placeholder when no selection
- Automatically updates when value changes

## Usage Examples

### Basic Usage
```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

function BasicSelect() {
  return (
    <Select>
      <SelectTrigger>
        <SelectValue placeholder="Select an option" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="option1">Option 1</SelectItem>
        <SelectItem value="option2">Option 2</SelectItem>
        <SelectItem value="option3">Option 3</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

### Controlled Component
```tsx
function ControlledSelect() {
  const [value, setValue] = useState('');
  
  return (
    <Select value={value} onValueChange={setValue}>
      <SelectTrigger>
        <SelectValue placeholder="Choose a template" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="template1">Tournament Bracket</SelectItem>
        <SelectItem value="template2">Player Score</SelectItem>
        <SelectItem value="template3">Team Display</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

### With Disabled Items
```tsx
function SelectWithDisabledItems() {
  return (
    <Select>
      <SelectTrigger>
        <SelectValue placeholder="Select category" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="active">Active Graphics</SelectItem>
        <SelectItem value="archived">Archived Graphics</SelectItem>
        <SelectItem value="deleted" disabled>Deleted Graphics</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

### Form Integration
```tsx
function FormSelect() {
  return (
    <form>
      <Select name="graphicType" required>
        <SelectTrigger>
          <SelectValue placeholder="Select graphic type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="scoreboard">Scoreboard</SelectItem>
          <SelectItem value="bracket">Tournament Bracket</SelectItem>
          <SelectItem value="player">Player Card</SelectItem>
        </SelectContent>
      </Select>
      <button type="submit">Submit</button>
    </form>
  );
}
```

## Integration Points

### Canvas Editor Usage
**Location**: `dashboard/components/canvas/CanvasEditor.tsx`

**Use Cases**:
- Template selection for new graphics
- Tool selection in editing toolbar
- Layer property selection
- Data source configuration

**Example**:
```tsx
// Template selection in Canvas Editor
<Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
  <SelectTrigger>
    <SelectValue placeholder="Choose template" />
  </SelectTrigger>
  <SelectContent>
    {templates.map(template => (
      <SelectItem key={template.id} value={template.id}>
        {template.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

### Graphics Management Usage
**Location**: `dashboard/components/graphics/GraphicsTab.tsx`

**Use Cases**:
- Category filtering
- Status selection (active/archived)
- Sort order selection
- Bulk action selection

**Example**:
```tsx
// Status filter in GraphicsTab
<Select value={statusFilter} onValueChange={setStatusFilter}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Filter by status" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All Graphics</SelectItem>
    <SelectItem value="active">Active</SelectItem>
    <SelectItem value="archived">Archived</SelectItem>
  </SelectContent>
</Select>
```

### Copy Graphic Dialog Usage
**Location**: `dashboard/components/graphics/CopyGraphicDialog.tsx`

**Use Cases**:
- Template selection for duplication
- Event name selection from existing events
- Copy destination selection

**Example**:
```tsx
// Template selection in CopyGraphicDialog
<Select value={templateId} onValueChange={setTemplateId}>
  <SelectTrigger>
    <SelectValue placeholder="Select template" />
  </SelectTrigger>
  <SelectContent>
    {templates.map(template => (
      <SelectItem key={template.id} value={template.id}>
        {template.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

## Styling and Theming

### CSS Classes Structure
```css
/* Main select container */
.select-trigger {
  /* Trigger button styling */
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* ... other styles */
}

/* Dropdown content */
.select-content {
  /* Dropdown container styling */
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  /* ... other styles */
}

/* Individual items */
.select-item {
  /* Item styling */
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.select-item:hover {
  background-color: #f3f4f6;
}

.select-item[data-highlighted] {
  background-color: #e5e7eb;
}

.select-item[data-state="checked"] {
  background-color: #3b82f6;
  color: white;
}
```

### Dark Theme Support
The Select component includes comprehensive dark theme support:

```css
/* Dark theme variants */
.dark .select-content {
  background: #1f2937;
  border-color: #374151;
}

.dark .select-item:hover {
  background-color: #374151;
}

.dark .select-item[data-highlighted] {
  background-color: #4b5563;
}
```

## Accessibility Features

### ARIA Implementation
- `role="combobox"` on trigger button
- `aria-expanded` state management
- `aria-haspopup="listbox"` for screen readers
- `aria-labelledby` for proper labeling
- `aria-activedescendant` for keyboard navigation

### Keyboard Navigation
- **Space/Enter**: Open dropdown or select highlighted item
- **Arrow Up/Down**: Navigate through options
- **Escape**: Close dropdown without selection
- **Tab**: Focus navigation
- **Home/End**: Jump to first/last item

### Screen Reader Support
- Proper announcements for value changes
- Contextual descriptions for options
- State announcements for disabled items
- Form validation support

## Performance Considerations

### Virtual Scrolling
For large datasets, consider implementing virtual scrolling:
```tsx
// Example with virtual scrolling (future enhancement)
<Select>
  <SelectTrigger>
    <SelectValue placeholder="Select from thousands" />
  </SelectTrigger>
  <SelectContent>
    <VirtualizedList items={largeDataset} height={200}>
      {item => (
        <SelectItem value={item.id}>{item.name}</SelectItem>
      )}
    </VirtualizedList>
  </SelectContent>
</Select>
```

### Optimization Tips
- Use `value` prop for controlled components in forms
- Implement debouncing for remote data fetching
- Consider pagination for very large datasets
- Use memoization for expensive option rendering

## Testing Guidelines

### Unit Tests
```tsx
describe('Select Component', () => {
  it('should render trigger with placeholder', () => {
    render(<Select><SelectTrigger><SelectValue placeholder="Test" /></SelectTrigger></Select>);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('should open dropdown when trigger clicked', () => {
    const { getByRole } = render(<BasicSelect />);
    const trigger = getByRole('combobox');
    
    fireEvent.click(trigger);
    expect(getByRole('listbox')).toBeInTheDocument();
  });

  it('should call onValueChange when item selected', () => {
    const handleChange = jest.fn();
    render(<Select onValueChange={handleChange}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="test">Test</SelectItem></SelectContent></Select>);
    
    fireEvent.click(getByRole('combobox'));
    fireEvent.click(getByText('Test'));
    
    expect(handleChange).toHaveBeenCalledWith('test');
  });
});
```

### Accessibility Tests
- Verify ARIA attributes with testing-library
- Test keyboard navigation flow
- Validate screen reader announcements
- Check color contrast compliance

## Best Practices

### When to Use Select
- Choose from 3-15 options
- Single selection required
- Space-efficient display needed
- Predictable choice patterns

### When NOT to Use Select
- More than 15 options (consider search + select)
- Multiple selection needed (use checkbox group)
- Custom input required (use autocomplete)
- Visual preview needed (use custom component)

### Data Guidelines
- Keep option text concise and clear
- Use consistent value formats
- Provide meaningful placeholder text
- Include "None" or "All" options when appropriate

### Form Integration
- Always associate with a label
- Use appropriate validation attributes
- Provide clear error messages
- Consider required field indicators

## Migration Guide

### From Native Select
```tsx
// Before
<select value={value} onChange={e => setValue(e.target.value)}>
  <option value="">Choose...</option>
  <option value="1">Option 1</option>
</select>

// After
<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Choose..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="1">Option 1</SelectItem>
  </SelectContent>
</Select>
```

### From Third-Party Libraries
Most props and patterns are similar to popular libraries like React-Select or Downshift, making migration straightforward.

## Troubleshooting

### Common Issues
1. **Dropdown not opening**: Check for z-index conflicts
2. **Options not selectable**: Verify value prop types match
3. **Styling issues**: Ensure CSS imports are correct
4. **Form submission**: Include `name` prop for form integration

### Debugging Tips
- Use React DevTools to inspect component state
- Check browser console for JavaScript errors
- Validate HTML structure with browser inspector
- Test with different screen readers for accessibility

## Future Enhancements

### Planned Features
- Multi-select capability
- Search/filter functionality
- Custom option rendering
- Async option loading
- Grouped options support

### Contributing Guidelines
- Follow existing component patterns
- Maintain accessibility standards
- Include comprehensive tests
- Update documentation for new features

## Related Documentation

- [Frontend Components Documentation](./frontend-components.md) - Component overview
- [UI Customization Guidelines](../sops/ui-customization-guidelines.md) - Theme procedures
- [Canvas Editor Architecture](./canvas-editor-architecture.md) - Canvas integration
- [System Cross-References](./system-cross-references.md) - Integration mappings

---

**Document Control**:
- **Version**: 1.0
- **Created**: 2025-01-13
- **Last Updated**: 2025-01-13
- **Review Date**: 2025-04-13
- **Next Review**: 2025-07-13
- **Approved By**: Frontend Lead
- **Classification**: Internal Use Only
