# React Component Documentation

This document provides comprehensive documentation for all React components in the GAL Live Graphics Dashboard.

## Component Architecture

The dashboard follows a modular component architecture with clear separation of concerns:

- **Layout Components**: Page structure and navigation
- **UI Components**: Reusable base components from shadcn/ui
- **Feature Components**: Business logic and domain-specific functionality
- **Hook Components**: Custom React hooks for state management

## Component Index

### 📋 Layout Components

#### DashboardLayout
**Location**: `components/layout/DashboardLayout.tsx`

Main layout component for the dashboard application.

**Purpose**: Provides consistent page structure including header, navigation, and main content areas.

**Props**:
```typescript
interface DashboardLayoutProps {
  children: React.ReactNode;
  currentPage?: string;
}
```

**Usage**:
```tsx
<DashboardLayout currentPage="graphics">
  <GraphicsTable />
</DashboardLayout>
```

### 🔐 Authentication Components

#### LoginForm
**Location**: `components/auth/LoginForm.tsx`

Authentication form for dashboard access.

**Features**:
- Master password input with secure field
- Loading states and error handling
- Auto-navigation on successful login
- Responsive design with animated styling
- Accessible form with proper labels

**Props**: None (self-contained)

**Usage**:
```tsx
<LoginForm />
```

### 🎨 Canvas Components

#### CanvasEditor
**Location**: `components/canvas/CanvasEditor.tsx`

Comprehensive canvas editing interface for creating and managing graphics.

**Features**:
- Text and property element creation
- Drag-and-drop element positioning
- Data binding to tournament datasets
- Background image upload
- Grid snapping and alignment
- Zoom and pan controls
- Undo/redo operations
- Lock management for collaborative editing

**Props**:
```typescript
interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
}
```

**Usage**:
```tsx
<CanvasEditor 
  graphic={graphicData} 
  onClose={() => {}} 
  onSave={async (data) => { return true; }}
/>
```

### 📊 Graphics Management Components

#### GraphicsTable
**Location**: `components/graphics/GraphicsTable.tsx`

Table component for displaying and managing graphics.

**Features**:
- Paginated graphics list
- Search and filtering capabilities
- Bulk actions (delete, archive)
- Responsive design
- Loading states
- Error handling

**Props**:
```typescript
interface GraphicsTableProps {
  graphics: Graphic[];
  onEdit: (graphic: Graphic) => void;
  onDelete: (graphicId: number) => void;
  onArchive: (graphicId: number) => void;
  loading?: boolean;
}
```

**Usage**:
```tsx
<GraphicsTable 
  graphics={graphicsData}
  onEdit={handleEdit}
  onDelete={handleDelete}
  onArchive={handleArchive}
/>
```

#### GraphicCard
**Location**: `components/graphics/GraphicCard.tsx`

Card component for individual graphic display.

**Features**:
- Visual preview of graphics
- Metadata display (title, event, created date)
- Action buttons (edit, delete, archive)
- Lock status indicators
- Responsive design

**Props**:
```typescript
interface GraphicCardProps {
  graphic: Graphic;
  onEdit: () => void;
  onDelete: () => void;
  onArchive: () => void;
  locked?: boolean;
  lockedBy?: string;
}
```

**Usage**:
```tsx
<GraphicCard 
  graphic={graphicData}
  onEdit={handleEdit}
  onDelete={handleDelete}
  onArchive={handleArchive}
  locked={isLocked}
  lockedBy={lockedByUser}
/>
```

#### CreateGraphicDialog
**Location**: `components/graphics/CreateGraphicDialog.tsx`

Dialog for creating new graphics.

**Features**:
- Form validation
- Template selection
- Event configuration
- Preview generation
- Multi-step wizard interface

**Props**:
```typescript
interface CreateGraphicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: CreateGraphicData) => Promise<void>;
}
```

**Usage**:
```tsx
<CreateGraphicDialog 
  open={isDialogOpen}
  onOpenChange={setDialogOpen}
  onCreate={handleCreateGraphic}
/>
```

### 🗄️ Archive Components

#### ArchiveTab
**Location**: `components/archive/ArchiveTab.tsx`

Tab component for managing archived graphics.

**Features**:
- Filtered view of archived graphics
- Restore functionality
- Permanent deletion (admin only)
- Search and pagination
- Metadata display

**Props**:
```typescript
interface ArchiveTabProps {
  archives: Graphic[];
  onRestore: (graphicId: number) => void;
  onDelete: (graphicId: number) => void;
  canDelete: boolean;
}
```

**Usage**:
```tsx
<ArchiveTab 
  archives={archivedGraphics}
  onRestore={handleRestore}
  onDelete={handleDelete}
  canDelete={userIsAdmin}
/>
```

### 🔒 Lock Management Components

#### LockBanner
**Location**: `components/locks/LockBanner.tsx`

Banner component displaying lock status information.

**Features**:
- Visual lock indicators
- Countdown timer
- User information
- Action buttons (refresh, release)

**Props**:
```typescript
interface LockBannerProps {
  lock: CanvasLock | null;
  onRefresh: () => void;
  onRelease: () => void;
}
```

**Usage**:
```tsx
<LockBanner 
  lock={currentLock}
  onRefresh={refreshLock}
  onRelease={releaseLock}
/>
```

### 🔧 UI Components (shadcn/ui)

#### Base Components
All UI components follow the shadcn/ui pattern with consistent styling and accessibility.

**Available Components**:
- `Button` - Interactive buttons with variants
- `Input` - Text input fields
- `Card` - Container with header/content/footer
- `Dialog` - Modal dialogs
- `Select` - Dropdown selection
- `Tabs` - Tabbed interface
- `Badge` - Status indicators
- `Alert` - Notification messages

## Hooks Documentation

### useAuth
**Location**: `hooks/use-auth.tsx`

Custom hook for authentication management.

**Features**:
- JWT token authentication
- Automatic token expiration handling
- Session persistence
- Centralized authentication state

**Usage**:
```typescript
const { isAuthenticated, login, logout, loading, username } = useAuth();
```

**Methods**:
- `login(masterPassword: string)`: Authenticate with master password
- `logout()`: End session and clear tokens
- `isAuthenticated`: Check if user is logged in
- `loading`: Check if authentication state is loading

### useLocks
**Location**: `hooks/use-locks.tsx`

Custom hook for managing canvas locks.

**Features**:
- Lock acquisition and release
- Lock status monitoring
- Auto-refresh functionality
- Conflict resolution

**Usage**:
```typescript
const { acquireLock, releaseLock, refreshLock, lockStatus } = useLocks();
```

**Methods**:
- `acquireLock(graphicId: number)`: Request editing lock
- `releaseLock(graphicId: number)`: Release current lock
- `refreshLock(graphicId: number)`: Extend lock duration
- `lockStatus`: Current lock information

### useDashboardData
**Location**: `hooks/use-dashboard-data.tsx`

Custom hook for dashboard data management.

**Features**:
- Graphics data fetching
- Error handling
- Loading states
- Data caching

**Usage**:
```typescript
const { graphics, loading, error, refetch } = useDashboardData();
```

## State Management

### Context Providers
- `AuthProvider`: Global authentication state
- `ThemeProvider`: UI theme management
- `DataProvider`: Application-wide data state

### Local State Patterns
Components follow consistent patterns for local state management:

```typescript
// Standard state pattern
const [state, setState] = useState(initialValue);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

// Async operation pattern
const handleAction = async () => {
  setLoading(true);
  setError(null);
  
  try {
    const result = await apiCall();
    setState(result);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

## Styling Guidelines

### CSS Architecture
- **Tailwind CSS**: Utility-first styling
- **CSS Variables**: Theme customization
- **Component-scoped**: Style encapsulation

### Theme Tokens
```css
:root {
  --primary: #6366f1;
  --primary-foreground: #ffffff;
  --secondary: #f1f5f9;
  --secondary-foreground: #1e293b;
  --accent: #0ea5e9;
  --accent-foreground: #ffffff;
  --destructive: #ef4444;
  --destructive-foreground: #ffffff;
}
```

### Responsive Design
- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Flexible layouts with Tailwind utilities

## Testing Components

### Component Testing Structure
```typescript
// Component test example
describe('LoginForm', () => {
  it('renders login form', () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/Master Password/i)).toBeInTheDocument();
  });

  it('handles login submission', async () => {
    render(<LoginForm />);
    userEvent.type(screen.getByLabelText(/Master Password/i), 'password');
    userEvent.click(screen.getByRole('button', { name: /access dashboard/i }));
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('password');
    });
  });
});
```

### Hook Testing
```typescript
// Hook test example
describe('useAuth', () => {
  it('provides authentication state', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.isAuthenticated).toBe(false);
  });
});
```

## Performance Considerations

### Optimization Techniques
1. **Memoization**: Use `useMemo` and `useCallback` for expensive computations
2. **Code Splitting**: Dynamic imports for large components
3. **Virtualization**: For large lists (future enhancement)
4. **Image Optimization**: Next.js automatic optimization

### Bundle Analysis
- Monitor component bundle sizes
- Tree-shaking unused imports
- Lazy load non-critical components

## Accessibility

### WCAG Compliance
- Semantic HTML structure
- ARIA labels and attributes
- Keyboard navigation support
- Screen reader compatibility

### Accessibility Checklist
- [ ] All interactive elements are keyboard accessible
- [ ] Proper heading hierarchy (H1, H2, H3...)
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators are visible
- [ ] Images have alt text
- [ ] Forms have proper labels

## Contributing to Components

### Adding New Components
1. **Create component file** in appropriate directory
2. **Add JSDoc documentation** with examples
3. **Include TypeScript types** for all props
4. **Add unit tests** for functionality
5. **Follow naming conventions** (PascalCase for components, camelCase for hooks)

### Code Style Guidelines
- Use TypeScript exclusively
- Follow ESLint configuration
- Consistent indentation (2 spaces)
- Meaningful variable and function names
- Proper error handling

### Component Template
```typescript
/**
 * ComponentName Component
 * 
 * Brief description of component purpose and features.
 * 
 * Features:
 * - Feature 1
 * - Feature 2
 * - Feature 3
 * 
 * @example
 * ```tsx
 * <ComponentName prop1="value1" prop2={value2} />
 * ```
 * 
 * @param {ComponentNameProps} props - Component props
 * @returns {JSX.Element} The component JSX
 */
export function ComponentName(props: ComponentNameProps) {
  // Implementation
}
```

---

**Last Updated**: 2025-01-18  
**Maintained by**: Guardian Angel League Development Team
