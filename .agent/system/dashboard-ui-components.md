---
id: system.dashboard_ui_components
version: 1.0
last_updated: 2025-01-24
tags: [dashboard, ui, components, shadcn, tailwind, react]
---

# Dashboard UI Components

## Overview

The Live Graphics Dashboard uses shadcn/ui components built with Radix UI primitives and Tailwind CSS for consistent, accessible UI elements throughout the application.

## Component Structure

### UI Components (`dashboard/components/ui/`)

#### Alert Dialog
**File**: `alert-dialog.tsx`  
**Purpose**: Confirmation dialogs and alerts  
**Features**: 
- Customizable title and description
- Action and cancel buttons
- Modal overlay with backdrop blur

#### Badge
**File**: `badge.tsx`  
**Purpose**: Status indicators and labels  
**Features**:
- Variant support (default, secondary, destructive, outline)
- Flexible sizing and styling
- Status indicators (e.g., "In Use", "Locked")

#### Button
**File**: `button.tsx`  
**Purpose**: Interactive buttons throughout the application  
**Features**:
- Multiple variants (default, destructive, outline, secondary, ghost, link)
- Size variations (default, sm, lg, icon)
- Loading states
- Disabled states

#### Card
**File**: `card.tsx`  
**Purpose**: Content containers with consistent styling  
**Features**:
- Header, content, and footer sections
- Consistent padding and shadows
- Hover effects

#### Collapsible
**File**: `collapsible.tsx`  
**Purpose**: Expandable/collapsible content sections  
**Features**:
- Smooth transitions
- Customizable trigger buttons
- Controlled and uncontrolled modes

#### Dialog
**File**: `dialog.tsx`  
**Purpose**: Modal dialogs for forms and interactions  
**Features**:
- Title, description, and footer sections
- Backdrop interaction handling
- Escape key support
- Customizable sizing

#### Input
**File**: `input.tsx`  
**Purpose**: Form input fields  
**Features**:
- Text, password, email, number types
- Validation states
- Placeholder text
- Disabled states

#### Label
**File**: `label.tsx`  
**Purpose**: Form field labels  
**Features**:
- Required field indicators
- Accessibility features
- Consistent spacing

#### Select
**File**: `select.tsx`  
**Purpose**: Dropdown selection fields  
**Features**:
- Single and multiple selection
- Search functionality
- Custom option rendering
- Keyboard navigation

#### Separator
**File**: `separator.tsx`  
**Purpose**: Visual content separators  
**Features**:
- Horizontal and vertical orientations
- Different styling options

#### Tabs
**File**: `tabs.tsx`  
**Purpose**: Tabbed content organization  
**Features**:
- Keyboard navigation
- Active tab indicators
- Customizable tab content

#### Toast Components
**Files**: `toast.tsx`, `toaster.tsx`  
**Purpose**: Notification system  
**Features**:
- Multiple toast variants (default, destructive)
- Auto-dismiss functionality
- Stack management
- Custom positioning

## Layout Components

### Dashboard Layout
**File**: `components/layout/DashboardLayout.tsx`  
**Purpose**: Main application layout structure  
**Features**:
- Responsive design
- Navigation sidebar
- Header with user info
- Main content area
- Footer with status information

### Authentication Layout
**Purpose**: Simple centered layout for login pages  
**Features**:
- Centered content
- Background styling
- Mobile responsive

## Feature-Specific Components

### Graphics Management

#### Graphics Card
**File**: `components/graphics/GraphicCard.tsx`  
**Purpose**: Display individual graphic items  
**Features**:
- Graphic preview
- Title and metadata
- Action buttons (Edit, Delete, Archive)
- Lock status indicators

#### Graphics Table
**File**: `components/graphics/GraphicsTable.tsx`  
**Purpose**: Tabular display of graphics data  
**Features**:
- Sortable columns
- Filter capabilities
- Pagination
- Row actions

#### Create Graphic Dialog
**File**: `components/graphics/CreateGraphicDialog.tsx`  
**Purpose**: Modal for creating new graphics  
**Features**:
- Form validation
- Template selection
- Name and description fields

#### Delete Confirmation Dialog
**File**: `components/graphics/DeleteConfirmDialog.tsx`  
**Purpose**: Confirmation dialog for destructive actions  
**Features**:
- Warning messages
- Confirmation text input
- Action logging

#### Copy Graphic Dialog
**File**: `components/graphics/CopyGraphicDialog.tsx`  
**Purpose**: Duplicating existing graphics  
**Features**:
- Name customization
- Template copying
- Bulk operations

#### Graphics Tab
**File**: `components/graphics/GraphicsTab.tsx`  
**Purpose**: Main graphics management interface  
**Features**:
- Tab navigation
- Graphics listing
- Action buttons
- Status indicators

### Archive Management

#### Archive Tab
**File**: `components/archive/ArchiveTab.tsx`  
**Purpose**: Archive management interface  
**Features**:
- Archived graphics listing
- Restore functionality
- Admin deletion capabilities
- Archive statistics

#### Archived Graphic Card
**File**: `components/archive/ArchivedGraphicCard.tsx`  
**Purpose**: Display archived items  
**Features**:
- Archive date information
- Restore buttons
- Admin-only delete actions
- Archive metadata

### Canvas System

#### Canvas Editor
**File**: `components/canvas/CanvasEditor.tsx`  
**Purpose**: Full-screen graphics editing interface  
**Features**:
- Element manipulation
- Drag-and-drop positioning
- Property editing
- Data binding
- Zoom controls
- Grid snapping
- Undo/redo functionality

### Lock Management

#### Lock Banner
**File**: `components/locks/LockBanner.tsx`  
**Purpose**: Display lock status and countdown  
**Features**:
- Timer display
- Lock owner information
- Release actions
- Auto-refresh functionality

## Design System

### Color Palette
- **Primary**: Blue tones for primary actions
- **Secondary**: Gray tones for secondary elements
- **Success**: Green tones for success states
- **Warning**: Yellow/amber tones for warnings
- **Error**: Red tones for errors
- **Neutral**: Gray scale for text and borders

### Typography
- **Headings**: Consistent font sizes and weights
- **Body**: Readable base font size
- **Labels**: Form field labels
- **Captions**: Small supporting text

### Spacing
- **Base unit**: 4px spacing system
- **Consistent padding**: 4, 8, 12, 16, 20, 24px
- **Margins**: Consistent margin patterns
- **Gap spacing**: Flexbox and grid spacing

### Border Radius
- **Small**: 4px for buttons and inputs
- **Medium**: 8px for cards and containers
- **Large**: 12px for large containers

### Shadows
- **Subtle**: Light shadows for hover states
- **Medium**: Standard shadows for cards
- **Strong**: Prominent shadows for modals

## Accessibility Features

### Keyboard Navigation
- Tab order management
- Focus indicators
- Keyboard shortcuts
- Screen reader support

### ARIA Attributes
- Proper labels and descriptions
- Role definitions
- State announcements
- Live regions

### Visual Accessibility
- High contrast ratios
- Clear focus states
- Semantic HTML structure
- Alt text for images

## Responsive Design

### Breakpoints
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### Mobile Adaptations
- Collapsible navigation
- Touch-friendly buttons
- Responsive tables
- Mobile-optimized dialogs

### Desktop Enhancements
- Hover states
- Keyboard shortcuts
- Expanded layouts
- Multi-column views

## Performance Optimizations

### Component Optimization
- React.memo for expensive components
- useMemo for expensive calculations
- useCallback for event handlers
- Code splitting for large components

### Bundle Optimization
- Dynamic imports for heavy components
- Tree shaking for unused exports
- Component lazy loading
- Optimized asset loading

## Development Guidelines

### Component Creation
1. Use TypeScript interfaces for props
2. Implement proper error boundaries
3. Add accessibility attributes
4. Include loading states
5. Write unit tests

### Styling Practices
1. Use Tailwind utility classes
2. Avoid inline styles
3. Follow design system patterns
4. Ensure responsive behavior
5. Test in multiple screen sizes

### State Management
1. Lift state when necessary
2. Use custom hooks for complex logic
3. Implement proper prop types
4. Handle loading and error states
5. Optimize re-renders

## Related Documentation

- [Canvas Editor Architecture](./canvas-editor-architecture.md) - Canvas editing system details
- [Live Graphics Dashboard](./live-graphics-dashboard.md) - Complete dashboard overview
- [Authentication System](./authentication-system.md) - Auth component details
- [API Integration](./api-integration.md) - Backend integration patterns

---

*Generated: 2025-01-24*
*Last Updated: Complete UI components documentation*
