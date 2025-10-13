---
id: sops.table_alignment
version: 1.0
last_updated: 2025-10-13
tags: [sop, ui-alignment, table-formatting, user-experience]
---

# Table Alignment SOP

## Overview
This Standard Operating Procedure (SOP) outlines the standards and procedures for table alignment and formatting in the Guardian Angel League Live Graphics Dashboard, ensuring consistent and professional presentation across all table-based components.

## Purpose
- Establish consistent table alignment standards
- Ensure proper user experience across all table interfaces
- Maintain visual consistency in data presentation
- Provide guidelines for table formatting and styling

## Scope
- Graphics table alignment and formatting
- Archive table presentation standards
- User table formatting requirements
- System table consistency across components
- Responsive table behavior for different screen sizes

## Alignment Standards

### Default Table Alignment

#### Header Alignment
- **Primary Headers**: Center-aligned (`text-center`)
- **Action Column Headers**: Center-aligned
- **Status Indicators**: Center-aligned
- **Timestamp Columns**: Center-aligned
- **User Information**: Left-aligned for readability

#### Content Alignment
- **Text Content**: Center-aligned to match headers (`text-center`)
- **Numeric Data**: Center-aligned for consistency
- **Status Indicators**: Center-aligned
- **Action Buttons**: Center-aligned
- **User Names/IDs**: Left-aligned for readability
- **Timestamps**: Center-aligned

### Specific Table Types

#### Graphics Table
```css
/* Headers */
.table-header-title { text-align: center; }
.table-header-event-name { text-align: center; }
.table-header-created-by { text-align: left; }
.table-header-created-at { text-align: center; }
.table-header-actions { text-align: center; }

/* Content */
.table-content-title { text-align: center; }
.table-content-event-name { text-align: center; }
.table-content-created-by { text-align: left; }
.table-content-created-at { text-align: center; }
.table-content-actions { text-align: center; }
```

#### Archive Table
```css
/* Headers */
.archive-header-title { text-align: center; }
.archive-header-event-name { text-align: center; }
.archive-header-archived-by { text-align: left; }
.archive-header-archived-at { text-align: center; }
.archive-header-actions { text-align: center; }

/* Content */
.archive-content-title { text-align: center; }
.archive-content-event-name { text-align: center; }
.archive-content-archived-by { text-align: left; }
.archive-content-archived-at { text-align: center; }
.archive-content-actions { text-align: center; }
```

## Implementation Guidelines

### CSS Classes and Utilities

#### Tailwind CSS Alignment Classes
```css
/* Center alignment (default for most columns) */
.text-center { text-align: center; }

/* Left alignment (for user-readable text) */
.text-left { text-align: left; }

/* Right alignment (for numeric data if needed) */
.text-right { text-align: right; }
```

#### Custom Table Components
```jsx
// TableHeaderCell component
const TableHeaderCell = ({ children, align = "center", className = "" }) => (
  <th className={`px-4 py-3 ${align === "left" ? "text-left" : "text-center"} ${className}`}>
    {children}
  </th>
);

// TableDataCell component
const TableDataCell = ({ children, align = "center", className = "" }) => (
  <td className={`px-4 py-3 ${align === "left" ? "text-left" : "text-center"} ${className}`}>
    {children}
  </td>
);
```

### Component Implementation

#### Graphics Table Example
```jsx
// GraphicsTable.tsx implementation
const GraphicsTable = ({ graphics }) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHeaderCell>Title</TableHeaderCell>
          <TableHeaderCell>Event Name</TableHeaderCell>
          <TableHeaderCell align="left">Created By</TableHeaderCell>
          <TableHeaderCell>Created At</TableHeaderCell>
          <TableHeaderCell>Actions</TableHeaderCell>
        </TableRow>
      </TableHeader>
      <TableBody>
        {graphics.map((graphic) => (
          <TableRow key={graphic.id}>
            <TableDataCell>{graphic.title}</TableDataCell>
            <TableDataCell>{graphic.event_name}</TableDataCell>
            <TableDataCell align="left">{graphic.created_by}</TableDataCell>
            <TableDataCell>{formatDate(graphic.created_at)}</TableDataCell>
            <TableDataCell>
              <div className="flex justify-center space-x-2">
                <Button size="sm" variant="outline">Edit</Button>
                <Button size="sm" variant="outline">Copy</Button>
                <Button size="sm" variant="outline">Archive</Button>
              </div>
            </TableDataCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
```

## Responsive Behavior

### Mobile Adaptation
```css
/* Mobile table adjustments */
@media (max-width: 768px) {
  .table-mobile {
    /* Stack table rows on mobile */
    display: block;
  }
  
  .table-mobile thead {
    display: none;
  }
  
  .table-mobile tbody,
  .table-mobile tr,
  .table-mobile td {
    display: block;
    width: 100%;
  }
  
  .table-mobile tr {
    margin-bottom: 1rem;
    border: 1px solid #e2e8f0;
    border-radius: 0.375rem;
  }
  
  .table-mobile td {
    text-align: left !important; /* Force left alignment on mobile */
    padding: 0.5rem;
    border-bottom: 1px solid #e2e8f0;
  }
  
  .table-mobile td:before {
    content: attr(data-label) ": ";
    font-weight: 600;
    color: #475569;
  }
}
```

### Mobile Table Implementation
```jsx
const ResponsiveTable = ({ data }) => {
  const isMobile = useMediaQuery("(max-width: 768px)");
  
  if (isMobile) {
    return (
      <div className="table-mobile">
        {data.map((item) => (
          <div key={item.id} className="p-4 border rounded-lg mb-4">
            <div className="font-semibold">{item.title}</div>
            <div className="text-sm text-gray-600 mt-1">
              <span data-label="Event Name">{item.event_name}</span>
            </div>
            <div className="text-sm text-gray-600">
              <span data-label="Created By">{item.created_by}</span>
            </div>
            <div className="text-sm text-gray-600">
              <span data-label="Created At">{formatDate(item.created_at)}</span>
            </div>
            <div className="mt-3 flex justify-center space-x-2">
              <Button size="sm" variant="outline">Edit</Button>
              <Button size="sm" variant="outline">Copy</Button>
              <Button size="sm" variant="outline">Archive</Button>
            </div>
          </div>
        ))}
      </div>
    );
  }
  
  return <DesktopTable data={data} />;
};
```

## Quality Assurance

### Visual Testing Checklist
- [ ] All table headers are center-aligned
- [ ] All table content cells are center-aligned
- [ ] User information columns are left-aligned
- [ ] Action buttons are center-aligned
- [ ] Consistent spacing between columns
- [ ] Proper vertical alignment in all cells
- [ ] Responsive behavior works correctly
- [ ] Mobile layout maintains readability

### Cross-Browser Testing
- [ ] Chrome (latest version)
- [ ] Firefox (latest version)
- [ ] Safari (latest version)
- [ ] Edge (latest version)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

### Performance Testing
- [ ] Large datasets render efficiently
- [ ] Scrolling performance remains smooth
- [ ] Sorting operations complete quickly
- [ ] Filtering functions perform well
- [ ] Mobile interactions are responsive

## Troubleshooting

### Common Alignment Issues

#### Misaligned Content
**Symptoms**: Table content appears misaligned or inconsistent
**Possible Causes**:
- Incorrect CSS class application
- Missing text alignment styles
- Inconsistent component implementation
- CSS specificity conflicts

**Resolution Steps**:
1. Verify correct Tailwind classes are applied
2. Check component implementation consistency
3. Inspect CSS specificity and conflicts
4. Test with different data content
5. Validate responsive behavior

#### Mobile Layout Issues
**Symptoms**: Table layout breaks on mobile devices
**Possible Causes**:
- Missing responsive CSS rules
- Incorrect mobile breakpoint usage
- Content overflow issues
- Touch interaction problems

**Resolution Steps**:
1. Verify mobile CSS is properly implemented
2. Test with actual mobile devices
3. Check content overflow and wrapping
4. Validate touch target sizes
5. Ensure mobile-specific styling is applied

#### Inconsistent Table Styling
**Symptoms**: Different tables show different alignment patterns
**Possible Causes**:
- Inconsistent component usage
- Multiple table implementations
- Missing shared styling components
- Override styles applied incorrectly

**Resolution Steps**:
1. Standardize on shared table components
2. Review component implementations for consistency
3. Remove duplicate styling definitions
4. Implement design system tokens for table styling
5. Update all table implementations to use standards

## Maintenance Procedures

### Regular Reviews
1. **Monthly Alignment Audits**
   - Review all table implementations
   - Check for consistency with standards
   - Test responsive behavior
   - Validate user experience

2. **Component Library Updates**
   - Update shared table components
   - Review and improve styling utilities
   - Document new alignment patterns
   - Update implementation guidelines

3. **User Feedback Integration**
   - Collect user feedback on table usability
   - Analyze user interaction patterns
   - Identify areas for improvement
   - Implement user-requested enhancements

### Code Review Guidelines
1. **Table Component Reviews**
   - Verify correct alignment classes usage
   - Check responsive implementation
   - Validate accessibility standards
   - Ensure consistent styling patterns

2. **CSS Review Standards**
   - Review alignment class usage
   - Check for CSS specificity issues
   - Validate responsive breakpoint usage
   - Ensure consistent naming conventions

## Documentation Updates

### When to Update This SOP
- New table components added to system
- Alignment standards change
- New responsive requirements identified
- User feedback indicates needed improvements
- Browser compatibility issues discovered

### Update Process
1. Document the change and rationale
2. Update implementation examples
3. Modify code review guidelines
4. Communicate changes to development team
5. Update component library if needed

## Related Documentation
- **[Frontend Components Documentation](../system/frontend-components.md)** - Component implementation details
- **[Branding Guidelines](../system/branding-guidelines.md)** - Visual design standards
- **[Dashboard Operations SOP](./dashboard-operations.md)** - General dashboard procedures
- **[UI/UX Standards](../system/ui-ux-standards.md)** - User interface guidelines

## Version History
- **v1.0** (2025-10-13): Initial SOP creation
  - Established table alignment standards
  - Defined responsive behavior requirements
  - Created implementation guidelines and examples

---

**Document Owner**: Frontend Development Team  
**Review Frequency**: Monthly  
**Next Review Date**: 2025-11-13  
**Approval**: UI/UX Lead
