---
id: system.frontend_components
version: 2.0
last_updated: 2025-10-13
tags: [system, frontend, components, react, dashboard]
---

# Frontend Components Documentation

## Overview
This document provides comprehensive documentation for all React components within the Live Graphics Dashboard 2.0 frontend application, including component hierarchies, props interfaces, and usage patterns.

## Component Architecture

### Directory Structure
```
dashboard/components/
├── auth/           # Authentication-related components
├── graphics/       # Graphic management components
├── archive/        # Archive and history components
├── canvas/         # Canvas editing and display components
├── locks/          # Lock management components
├── layout/         # Layout and navigation components
└── ui/            # Reusable UI components
```

### Technology Stack
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript 5.0
- **Styling**: Tailwind CSS 3.4
- **State Management**: React Context + Zustand
- **Forms**: React Hook Form + Zod validation
- **UI Library**: shadcn/ui components
- **Icons**: Lucide React

## Authentication Components (`components/auth/`)

### LoginForm Component
**Purpose**: User authentication and login interface

```typescript
interface LoginFormProps {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  redirectTo?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onError,
  redirectTo = '/dashboard'
}) => {
  // Component implementation
};
```

**Features**:
- Email and password authentication
- Multi-factor authentication support
- Remember me functionality
- Password reset integration
- Form validation with error handling

**Usage Example**:
```jsx
<LoginForm 
  onSuccess={() => router.push('/dashboard')}
  onError={(error) => toast.error(error.message)}
/>
```

### MFAVerification Component
**Purpose**: Multi-factor authentication verification

```typescript
interface MFAVerificationProps {
  userId: string;
  onVerified: () => void;
  onBackupCode: () => void;
}
```

**Features**:
- TOTP code input
- Backup code option
- Resend code functionality
- QR code display for setup

### UserProfile Component
**Purpose**: User profile display and management

```typescript
interface UserProfileProps {
  user: User;
  editable?: boolean;
  onUpdate?: (user: Partial<User>) => void;
}
```

## Graphics Components (`components/graphics/`)

### GraphicsList Component
**Purpose**: Display and manage graphics library

```typescript
interface GraphicsListProps {
  graphics: Graphic[];
  onEdit: (graphic: Graphic) => void;
  onDelete: (graphicId: string) => void;
  onDuplicate: (graphic: Graphic) => void;
  filter?: GraphicFilter;
  sortable?: boolean;
}
```

**Features**:
- Grid and list view modes
- Search and filtering
- Sorting options
- Batch operations
- Real-time updates

### GraphicEditor Component
**Purpose**: Graphic creation and editing interface

```typescript
interface GraphicEditorProps {
  graphic?: Graphic;
  template: Template;
  onSave: (graphic: Graphic) => void;
  onCancel: () => void;
  preview?: boolean;
}
```

**Features**:
- Visual template editor
- Real-time preview
- Data source binding
- Asset management
- Validation and testing

### TemplateSelector Component
**Purpose**: Template selection and preview

```typescript
interface TemplateSelectorProps {
  templates: Template[];
  selectedTemplate?: Template;
  onSelect: (template: Template) => void;
  category?: string;
}
```

**Features**:
- Template categorization
- Visual previews
- Search functionality
- Custom template creation

### GraphicsTab Component
**Purpose**: Main graphics management interface with table-based navigation

```typescript
interface GraphicsTabProps {
  tournamentId?: string;
  filters?: GraphicFilter;
  defaultView?: 'active' | 'archived';
}

interface GraphicFilter {
  search?: string;
  event_name?: string;
  created_by?: string;
  date_range?: [Date, Date];
}
```

**Features**:
- Tab-based navigation (Active/Archived)
- Table-based graphics display with sorting
- Real-time search and filtering
- Batch operations support
- Integration with CopyGraphicDialog
- Responsive design for mobile/desktop

**Usage Example**:
```jsx
<GraphicsTab 
  tournamentId="123"
  filters={{
    search: "template name",
    event_name: "Tournament Name"
  }}
/>
```

### CreateGraphicDialog Component
**Purpose**: Graphic creation with required event name field

```typescript
interface CreateGraphicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: CreateGraphicData) => Promise<boolean>;
  tournamentId?: string;
  templateId?: string;
}

interface CreateGraphicData {
  title: string;
  event_name: string;
  template_id: string;
  tournament_id?: string;
}
```

**Features**:
- Required event name validation
- Template selection interface
- Form validation with error handling
- Loading states during creation
- Success/error feedback

### CopyGraphicDialog Component
**Purpose**: Duplicate existing graphics with custom naming and event name

```typescript
interface CopyGraphicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCopy: (title: string, eventName?: string) => Promise<boolean>;
  sourceGraphic: Graphic | null;
}
```

**Features**:
- Pre-populated title with "(Copy)" suffix
- Editable event name field
- Required field validation
- Loading states during duplication
- Success/error feedback
- Automatic form reset on close

**Usage Example**:
```jsx
<CopyGraphicDialog
  open={copyDialogOpen}
  onOpenChange={setCopyDialogOpen}
  onCopy={handleCopyGraphic}
  sourceGraphic={selectedGraphic}
/>
```

## Archive Components (`components/archive/`)

### ArchiveBrowser Component
**Purpose**: Browse and search archived graphics

```typescript
interface ArchiveBrowserProps {
  archives: Archive[];
  onRestore: (archive: Archive) => void;
  onDelete: (archiveId: string) => void;
  onExport: (archive: Archive) => void;
}
```

**Features**:
- Date-based browsing
- Advanced search filters
- Bulk operations
- Export functionality
- Metadata display

### ArchiveDetails Component
**Purpose**: Display detailed archive information

```typescript
interface ArchiveDetailsProps {
  archive: Archive;
  onEdit: (archive: Partial<Archive>) => void;
  onRestore: () => void;
}
```

## Canvas Components (`components/canvas/`)

### CanvasEditor Component (Route-Based)
**Purpose**: Route-based canvas editing interface with metadata editing capabilities
**Route**: `/canvas/edit/{id}` (replaces legacy modal-based editor)

```typescript
interface CanvasEditorProps {
  graphic: Graphic;
  onSave: (title: string, eventName: string, canvasData: any) => Promise<boolean>;
  onCancel: () => void;
  locked?: boolean;
  lockInfo?: LockInfo;
}

// State management for metadata editing
const [title, setTitle] = useState(graphic.title);
const [eventName, setEventName] = useState(graphic.event_name);
```

**Features**:
- **Metadata Editing**: Editable title and event name fields in header
- **Route-Based Navigation**: Full-screen editing experience
- **Required Field Validation**: Prevents saving without event name
- **Canvas Locking**: Automatic lock acquisition and management
- **Real-time Collaboration**: WebSocket-based live updates
- **Drag and Drop Editing**: Visual canvas manipulation
- **Layer Management**: Comprehensive layer controls
- **Zoom and Pan Controls**: Canvas navigation features
- **Undo/Redo Functionality**: Edit history management
- **Auto-save**: Periodic saving of canvas state
- **Responsive Design**: Mobile and desktop optimization

**Metadata Editing Workflow**:
1. Load graphic with current title and event name
2. Display editable input fields in component header
3. Validate required fields before save operations
4. Include metadata in canvas save API calls
5. Update UI state after successful save

**Usage Example** (Route Implementation):
```jsx
// app/canvas/edit/[id]/page.tsx
export default function EditCanvasPage({ params }: { params: { id: string } }) {
  return (
    <CanvasEditor
      graphic={graphic}
      onSave={handleSave}
      onCancel={() => router.back()}
      locked={isLocked}
      lockInfo={lockInfo}
    />
  );
}
```

**Integration with Lock System**:
- Automatic lock acquisition on page load
- Lock status display in component header
- Lock refresh mechanism for extended editing sessions
- Conflict resolution for simultaneous editing attempts

### CanvasPreview Component
**Purpose**: Live canvas preview

```typescript
interface CanvasPreviewProps {
  canvas: Canvas;
  scale?: number;
  showGrid?: boolean;
  interactive?: boolean;
}
```

**Features**:
- Responsive scaling
- Grid overlay
- Interactive elements
- Performance optimization

### LayerPanel Component
**Purpose**: Layer management interface

```typescript
interface LayerPanelProps {
  layers: Layer[];
  selectedLayer?: Layer;
  onSelect: (layer: Layer) => void;
  onUpdate: (layer: Partial<Layer>) => void;
  onReorder: (layers: Layer[]) => void;
}
```

## Lock Components (`components/locks/`)

### LockStatus Component
**Purpose**: Display current lock status

```typescript
interface LockStatusProps {
  lock?: Lock;
  canvasId: string;
  onRequestLock: () => void;
  onReleaseLock: () => void;
}
```

**Features**:
- Visual lock indicators
- Lock timer display
- User information
- Request/release actions

### LockConflictModal Component
**Purpose**: Handle lock conflicts

```typescript
interface LockConflictModalProps {
  conflict: LockConflict;
  onResolve: (resolution: ConflictResolution) => void;
  onCancel: () => void;
}
```

## Layout Components (`components/layout/`)

### DashboardLayout Component
**Purpose**: Main application layout

```typescript
interface DashboardLayoutProps {
  children: React.ReactNode;
  title?: string;
  breadcrumbs?: Breadcrumb[];
  actions?: React.ReactNode;
}
```

**Features**:
- Responsive navigation
- Sidebar with collapsible sections
- Breadcrumb navigation
- Header with user menu
- Footer with system status

### NavigationSidebar Component
**Purpose**: Main navigation interface

```typescript
interface NavigationSidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  collapsed?: boolean;
  onToggleCollapse: () => void;
}
```

### BreadcrumbNav Component
**Purpose**: Breadcrumb navigation

```typescript
interface BreadcrumbNavProps {
  items: Breadcrumb[];
  separator?: React.ReactNode;
}
```

## UI Components (`components/ui/`)

### Button Component
**Purpose**: Consistent button styling across the application

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
```

### Input Component
**Purpose**: Form input with validation

```typescript
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
```

### Modal Component
**Purpose**: Modal dialog system

```typescript
interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}
```

### DataTable Component
**Purpose**: Data display with sorting and pagination

```typescript
interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  search?: string;
  onSearch?: (search: string) => void;
  pagination?: PaginationConfig;
  sorting?: SortingState;
  onSorting?: (sorting: SortingState) => void;
}
```

## Custom Hooks (`hooks/`)

### useAuth Hook
**Purpose**: Authentication state management

```typescript
interface UseAuthReturn {
  user: User | null;
  session: Session | null;
  status: 'loading' | 'authenticated' | 'unauthenticated';
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (profile: Partial<User>) => Promise<void>;
}

const useAuth = (): UseAuthReturn => {
  // Hook implementation
};
```

**Features**:
- Session management
- Token refresh
- User profile updates
- Role-based access control

### useGraphics Hook
**Purpose**: Graphics data management

```typescript
interface UseGraphicsReturn {
  graphics: Graphic[];
  templates: Template[];
  loading: boolean;
  error: Error | null;
  createGraphic: (graphic: CreateGraphicInput) => Promise<Graphic>;
  updateGraphic: (id: string, updates: Partial<Graphic>) => Promise<Graphic>;
  deleteGraphic: (id: string) => Promise<void>;
  duplicateGraphic: (id: string) => Promise<Graphic>;
}

const useGraphics = (tournamentId?: string): UseGraphicsReturn => {
  // Hook implementation
};
```

**Features**:
- CRUD operations for graphics
- Template management
- Real-time updates via WebSocket
- Error handling and retry logic

### useArchive Hook
**Purpose**: Archive management

```typescript
interface UseArchiveReturn {
  archives: Archive[];
  loading: boolean;
  error: Error | null;
  addToArchive: (graphicIds: string[]) => Promise<void>;
  restoreFromArchive: (archiveId: string) => Promise<void>;
  deleteArchive: (archiveId: string) => Promise<void>;
  searchArchives: (query: string) => Promise<Archive[]>;
}

const useArchive = (): UseArchiveReturn => {
  // Hook implementation
};
```

## State Management

### Global State Structure
```typescript
interface AppState {
  auth: AuthState;
  graphics: GraphicsState;
  canvas: CanvasState;
  locks: LocksState;
  ui: UIState;
}

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: string | null;
}

interface GraphicsState {
  graphics: Graphic[];
  templates: Template[];
  selectedGraphic: Graphic | null;
  loading: boolean;
  error: string | null;
}
```

### Context Providers
```typescript
// Auth Provider
const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Authentication state management
};

// Graphics Provider
const GraphicsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Graphics state management
};

// WebSocket Provider
const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Real-time connection management
};
```

## Component Patterns

### Compound Components
```typescript
// Example: Card compound component
const Card = ({ children, className, ...props }: CardProps) => (
  <div className={cn('rounded-lg border bg-card text-card-foreground', className)} {...props}>
    {children}
  </div>
);

const CardHeader = ({ children, className, ...props }: CardHeaderProps) => (
  <div className={cn('flex flex-col space-y-1.5 p-6', className)} {...props}>
    {children}
  </div>
);

const CardContent = ({ children, className, ...props }: CardContentProps) => (
  <div className={cn('p-6 pt-0', className)} {...props}>
    {children}
  </div>
);
```

### Render Props Pattern
```typescript
interface DataFetcherProps<T> {
  url: string;
  children: (data: T | null, loading: boolean, error: Error | null) => React.ReactNode;
}

const DataFetcher = <T,>({ url, children }: DataFetcherProps<T>) => {
  // Fetch data and render children
};
```

### Higher-Order Components
```typescript
const withAuth = <P extends object>(Component: React.ComponentType<P>) => {
  return function AuthenticatedComponent(props: P) {
    const { status } = useAuth();
    
    if (status === 'loading') return <LoadingSpinner />;
    if (status === 'unauthenticated') return <LoginForm />;
    
    return <Component {...props} />;
  };
};
```

## Performance Optimization

### Component Memoization
```typescript
const ExpensiveComponent = React.memo(({ data }: { data: ComplexData }) => {
  // Expensive rendering logic
}, (prevProps, nextProps) => {
  // Custom comparison function
  return shallowEqual(prevProps.data, nextProps.data);
});
```

### Virtual Scrolling
```typescript
const VirtualizedList: React.FC<VirtualizedListProps> = ({ items, itemHeight, height }) => {
  // Virtual scrolling implementation for large lists
};
```

### Code Splitting
```typescript
const GraphicEditor = dynamic(() => import('./GraphicEditor'), {
  loading: () => <LoadingSpinner />,
  ssr: false
});
```

## Testing

### Component Testing Patterns
```typescript
// Example component test
describe('LoginForm', () => {
  it('should render login form', () => {
    render(<LoginForm />);
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('should submit login form with valid credentials', async () => {
    const mockLogin = jest.fn();
    render(<LoginForm onSuccess={mockLogin} />);
    
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled();
    });
  });
});
```

## Accessibility

### ARIA Implementation
```typescript
const AccessibleButton: React.FC<ButtonProps> = ({ children, ...props }) => (
  <button
    role="button"
    aria-label={props['aria-label']}
    aria-describedby={props['aria-describedby']}
    {...props}
  >
    {children}
  </button>
);
```

### Keyboard Navigation
```typescript
const KeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Handle keyboard navigation
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return <div>...</div>;
};
```

## Internationalization

### i18n Configuration
```typescript
const i18nConfig = {
  locales: ['en', 'es', 'fr'],
  defaultLocale: 'en',
  messages: {
    en: {
      'graphics.title': 'Graphics',
      'graphics.create': 'Create Graphic',
      'graphics.edit': 'Edit Graphic'
    },
    es: {
      'graphics.title': 'Gráficos',
      'graphics.create': 'Crear Gráfico',
      'graphics.edit': 'Editar Gráfico'
    }
  }
};
```

## Component Library Integration

### shadcn/ui Integration
```typescript
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { DataTable } from '@/components/ui/data-table';

// Usage in components
const MyComponent = () => (
  <div>
    <Button variant="default">Click me</Button>
    <Input placeholder="Enter text" />
    <Modal open={isOpen} onOpenChange={setOpen}>
      {/* Modal content */}
    </Modal>
  </div>
);
```

## Best Practices

### Component Design Principles
1. **Single Responsibility**: Each component should have one clear purpose
2. **Composition over Inheritance**: Prefer composition patterns
3. **Props Interface**: Define clear, typed props interfaces
4. **State Management**: Keep local state minimal, lift state when needed
5. **Error Boundaries**: Implement error boundaries for robust error handling

### Code Organization
1. **Barrel Exports**: Use index files for clean imports
2. **Component Co-location**: Keep related components together
3. **Utility Functions**: Extract reusable logic
4. **Type Definitions**: Centralize type definitions
5. **Styling Consistency**: Follow established styling patterns

## References
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [shadcn/ui Documentation](https://ui.shadcn.com)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: Frontend Lead
- **Classification**: Internal Use Only
