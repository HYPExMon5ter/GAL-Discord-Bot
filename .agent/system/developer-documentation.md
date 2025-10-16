---
id: system.developer_documentation
version: 2.0
last_updated: 2025-10-11
tags: [system, development, guidelines, testing, procedures]
---

# Developer Documentation

## Overview
This document provides comprehensive guidelines and procedures for developers working on the Live Graphics Dashboard 2.0, including development workflows, coding standards, testing procedures, and best practices.

## Development Environment Setup

### Prerequisites
- **Node.js**: 18.x or higher
- **npm**: 9.x or higher
- **Python**: 3.11 or higher
- **Git**: 2.30 or higher
- **Docker**: 20.x or higher
- **VS Code**: Recommended IDE

### Local Development Setup

#### 1. Repository Setup
```bash
# Clone the repository
git clone https://github.com/guardian-angel-league/dashboard.git
cd dashboard

# Install frontend dependencies
npm install

# Install backend dependencies (Python)
cd ../api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Setup environment files
cp .env.example .env.local
cp ../api/.env.example ../api/.env
```

#### 2. Environment Configuration
```bash
# .env.local (Frontend)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
NEXT_PUBLIC_ENVIRONMENT=development

# .env (Backend)
DATABASE_URL=sqlite:///./dashboard.db
SECRET_KEY=your-secret-key
DEBUG=true
CORS_ORIGINS=http://localhost:3000
```

#### 3. Development Scripts
```bash
# Frontend development
npm run dev              # Start development server
npm run build            # Build for production
npm run start            # Start production server
npm run lint             # Run ESLint
npm run type-check       # Run TypeScript checks
npm run test             # Run tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage

# Backend development
cd ../api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
python -m pytest        # Run tests
python -m pytest --cov  # Run tests with coverage
python -m alembic upgrade head  # Database migrations
```

#### Unified Quality Checks
Use `python scripts/run_quality_checks.py` from the repository root to execute the complete quality gate. The script sequentially runs Ruff, Black, pytest, and the dashboard lint/type-check commands to reproduce CI locally. Tooling configuration is centralised in `pyproject.toml`.

## Project Structure

### Frontend Structure
```
dashboard/
├── app/                  # Next.js app router
│   ├── (auth)/          # Auth routes
│   ├── (dashboard)/     # Dashboard routes
│   ├── api/            # API routes
│   └── globals.css     # Global styles
├── components/          # React components
│   ├── auth/           # Authentication components
│   ├── graphics/       # Graphics management
│   ├── canvas/         # Canvas editing
│   ├── locks/          # Lock management
│   ├── layout/         # Layout components
│   └── ui/             # Reusable UI components
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries
│   ├── api/           # API client
│   ├── utils/         # Helper functions
│   └── websocket/     # WebSocket client
├── store/              # State management
├── types/              # TypeScript definitions
├── public/             # Static assets
└── tests/              # Test files
```

### Backend Structure
```
api/
├── app/                # FastAPI application
│   ├── api/           # API routers
│   ├── core/          # Core functionality
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── utils/         # Utility functions
├── alembic/           # Database migrations
├── tests/             # Test files
└── requirements.txt   # Python dependencies
```

## Coding Standards

### TypeScript Guidelines

#### 1. Type Definitions
```typescript
// Use interfaces for object shapes
interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  createdAt: Date;
}

// Use types for unions or computed types
type UserRole = 'admin' | 'operator' | 'viewer';
type ApiResponse<T> = {
  data: T;
  message?: string;
  success: boolean;
};

// Use generics for reusable components
interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  onRowClick?: (row: T) => void;
}
```

#### 2. Component Patterns
```typescript
// Functional components with TypeScript
interface ButtonProps {
  variant: 'primary' | 'secondary';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  variant,
  size,
  disabled = false,
  onClick,
  children,
}) => {
  const baseClasses = 'btn';
  const variantClasses = `btn-${variant}`;
  const sizeClasses = `btn-${size}`;
  
  return (
    <button
      className={`${baseClasses} ${variantClasses} ${sizeClasses}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
};
```

#### 3. Error Handling
```typescript
// Custom error classes
class ApiError extends Error {
  constructor(
    public status: number,
    public data: any,
    message?: string
  ) {
    super(message || `API Error: ${status}`);
    this.name = 'ApiError';
  }
}

// Error handling in async functions
const fetchData = async <T>(url: string): Promise<T> => {
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new ApiError(response.status, await response.json());
    }
    
    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      // Handle API errors
      throw error;
    }
    
    // Handle network errors
    throw new Error('Network error occurred');
  }
};
```

### React Best Practices

#### 1. Component Design
```typescript
// Single Responsibility Principle
const UserProfile: React.FC<{ userId: string }> = ({ userId }) => {
  const { user, loading, error } = useUser(userId);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div>
      <UserAvatar user={user} />
      <UserInfo user={user} />
      <UserActions user={user} />
    </div>
  );
};

// Composition over inheritance
const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className={`card ${className || ''}`}>
    {children}
  </div>
);

const CardHeader: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="card-header">{children}</div>
);

const CardContent: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="card-content">{children}</div>
);
```

#### 2. State Management
```typescript
// Use local state for UI-specific state
const [isOpen, setIsOpen] = useState(false);

// Use context for global state
const ThemeContext = createContext<Theme>('light');

const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>('light');
  
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
};

// Use Zustand for complex state
interface UserStore {
  user: User | null;
  setUser: (user: User | null) => void;
  updateUser: (updates: Partial<User>) => void;
}

const useUserStore = create<UserStore>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  updateUser: (updates) => set((state) => ({
    user: state.user ? { ...state.user, ...updates } : null
  })),
}));
```

#### 3. Performance Optimization
```typescript
// Memoization for expensive computations
const ExpensiveComponent: React.FC<{ data: ComplexData[] }> = React.memo(({ data }) => {
  const processedData = useMemo(() => {
    return data.map(item => expensiveProcessing(item));
  }, [data]);

  return <div>{/* Render processed data */}</div>;
});

// Callback memoization
const ParentComponent: React.FC = () => {
  const [count, setCount] = useState(0);
  
  const handleClick = useCallback(() => {
    setCount(prev => prev + 1);
  }, []);

  return <ChildComponent onClick={handleClick} />;
};

// Code splitting
const HeavyComponent = lazy(() => import('./HeavyComponent'));

const App: React.FC = () => (
  <Suspense fallback={<LoadingSpinner />}>
    <HeavyComponent />
  </Suspense>
);
```

### CSS and Styling Guidelines

#### 1. Tailwind CSS Best Practices
```typescript
// Component-specific styles
const Button: React.FC<ButtonProps> = ({ variant, size, children }) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors';
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    destructive: 'bg-red-600 text-white hover:bg-red-700',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const classes = cn(
    baseClasses,
    variantClasses[variant],
    sizeClasses[size]
  );

  return <button className={classes}>{children}</button>;
};
```

#### 2. CSS-in-JS (when needed)
```typescript
import { css } from '@emotion/react';

const dynamicStyles = (theme: Theme) => css`
  background-color: ${theme.primary};
  color: ${theme.text};
  padding: ${theme.spacing.md};
  border-radius: ${theme.borderRadius.md};
`;

const StyledComponent: React.FC<{ theme: Theme }> = ({ theme }) => (
  <div css={dynamicStyles(theme)}>
    Styled content
  </div>
);
```

## Testing Guidelines

### Testing Strategy
1. **Unit Tests**: Test individual functions and components
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test complete user workflows
4. **Visual Tests**: Ensure UI consistency

### Unit Testing with Jest and React Testing Library

#### 1. Component Testing
```typescript
// __tests__/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  test('renders with correct text', () => {
    render(<Button variant="primary" onClick={jest.fn()}>
      Click me
    </Button>);
    
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  test('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button variant="primary" onClick={handleClick}>
      Click me
    </Button>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('applies correct variant classes', () => {
    render(<Button variant="primary" onClick={jest.fn()}>
      Button
    </Button>);
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-blue-600', 'text-white');
  });
});
```

#### 2. Hook Testing
```typescript
// __tests__/hooks/useAuth.test.ts
import { renderHook, act } from '@testing-library/react';
import { useAuth } from '@/hooks/use-auth';

describe('useAuth', () => {
  test('initial state is correct', () => {
    const { result } = renderHook(() => useAuth());
    
    expect(result.current.user).toBeNull();
    expect(result.current.status).toBe('loading');
  });

  test('login updates user state', async () => {
    const { result } = renderHook(() => useAuth());
    
    await act(async () => {
      await result.current.login({
        email: 'test@example.com',
        password: 'password'
      });
    });
    
    expect(result.current.user).toBeTruthy();
    expect(result.current.status).toBe('authenticated');
  });
});
```

#### 3. API Testing
```typescript
// __tests__/lib/api/graphics.test.ts
import { GraphicsService } from '@/lib/api/graphics';
import { apiClient } from '@/lib/api/client';

// Mock API client
jest.mock('@/lib/api/client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('GraphicsService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('fetches graphics successfully', async () => {
    const mockGraphics = [
      { id: '1', name: 'Graphic 1' },
      { id: '2', name: 'Graphic 2' }
    ];

    mockedApiClient.get.mockResolvedValue({ graphics: mockGraphics });

    const service = new GraphicsService();
    const graphics = await service.getGraphics();

    expect(graphics).toEqual(mockGraphics);
    expect(mockedApiClient.get).toHaveBeenCalledWith('/graphics', undefined);
  });

  test('handles API errors', async () => {
    const error = new Error('Network error');
    mockedApiClient.get.mockRejectedValue(error);

    const service = new GraphicsService();
    
    await expect(service.getGraphics()).rejects.toThrow('Network error');
  });
});
```

### Integration Testing

#### 1. Component Integration
```typescript
// __tests__/integration/GraphicEditor.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GraphicEditor } from '@/components/graphics/GraphicEditor';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

describe('GraphicEditor Integration', () => {
  test('creates new graphic successfully', async () => {
    const queryClient = createTestQueryClient();
    
    render(
      <QueryClientProvider client={queryClient}>
        <GraphicEditor
          template={mockTemplate}
          onSave={jest.fn()}
          onCancel={jest.fn()}
        />
      </QueryClientProvider>
    );

    // Fill in form fields
    await userEvent.type(screen.getByLabelText(/name/i), 'Test Graphic');
    await userEvent.selectOptions(screen.getByLabelText(/template/i), 'template-1');
    
    // Save the graphic
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    
    // Wait for success message
    await waitFor(() => {
      expect(screen.getByText(/graphic created/i)).toBeInTheDocument();
    });
  });
});
```

### End-to-End Testing with Playwright

#### 1. E2E Test Setup
```typescript
// tests/e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Dashboard E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'password');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('can create and edit a graphic', async ({ page }) => {
    // Navigate to graphics page
    await page.click('[data-testid="graphics-nav"]');
    await expect(page).toHaveURL('/graphics');

    // Create new graphic
    await page.click('[data-testid="create-graphic-button"]');
    await page.fill('[data-testid="graphic-name"]', 'Test Graphic');
    await page.selectOption('[data-testid="template-select"]', 'lower-third');
    await page.click('[data-testid="save-button"]');

    // Verify graphic was created
    await expect(page.locator('[data-testid="graphic-list"]')).toContainText('Test Graphic');

    // Edit the graphic
    await page.click('[data-testid="edit-graphic-button"]');
    await page.fill('[data-testid="graphic-name"]', 'Updated Test Graphic');
    await page.click('[data-testid="save-button"]');

    // Verify update
    await expect(page.locator('[data-testid="graphic-list"]')).toContainText('Updated Test Graphic');
  });

  test('handles canvas locking correctly', async ({ page }) => {
    await page.goto('/canvas/123');
    
    // Try to lock canvas
    await page.click('[data-testid="lock-canvas-button"]');
    await expect(page.locator('[data-testid="lock-status"]')).toContainText('Locked by you');

    // Try to edit canvas (should work)
    await page.click('[data-testid="edit-mode-button"]');
    await expect(page.locator('[data-testid="canvas-editor"]')).toBeVisible();
  });
});
```

### Visual Testing

#### 1. Screenshot Testing
```typescript
// tests/visual/Button.visual.test.tsx
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button Visual Tests', () => {
  test('primary button matches snapshot', () => {
    const { container } = render(
      <Button variant="primary" onClick={jest.fn()}>
        Primary Button
      </Button>
    );
    
    expect(container).toMatchSnapshot();
  });

  test('secondary button matches snapshot', () => {
    const { container } = render(
      <Button variant="secondary" onClick={jest.fn()}>
        Secondary Button
      </Button>
    );
    
    expect(container).toMatchSnapshot();
  });
});
```

## Development Workflow

### Git Workflow

#### 1. Branch Naming Convention
```bash
# Feature branches
feature/dashboard-redesign
feature/canvas-locking-system

# Bugfix branches
fix/login-validation-error
fix/canvas-rendering-issue

# Hotfix branches
hotfix/security-vulnerability
hotfix/critical-bug

# Release branches
release/v2.1.0
```

#### 2. Commit Message Format
```
type(scope): description

feat(graphics): add template selection component
fix(auth): resolve login validation issue
docs(readme): update installation instructions
style(button): improve button styling
refactor(canvas): optimize canvas rendering logic
test(api): add integration tests for graphics API
build(deps): update react to v18
chore(deps): clean up unused dependencies
```

#### 3. Pull Request Template
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Ready for review
```

### Code Review Process

#### 1. Review Guidelines
- **Functionality**: Does the code work as intended?
- **Performance**: Are there any performance concerns?
- **Security**: Are there any security vulnerabilities?
- **Maintainability**: Is the code easy to understand and maintain?
- **Testing**: Are tests comprehensive and appropriate?
- **Documentation**: Is the code well documented?

#### 2. Review Checklist
```markdown
## Code Review Checklist

### General
- [ ] Code follows project conventions
- [ ] Variable and function names are descriptive
- [ ] Code is properly formatted
- [ ] Comments are clear and necessary

### Functionality
- [ ] Implementation matches requirements
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] No obvious bugs

### Performance
- [ ] No obvious performance issues
- [ ] Efficient algorithms used
- [ ] Proper memory management
- [ ] Optimized for scale

### Security
- [ ] No security vulnerabilities
- [ ] Input validation implemented
- [ ] Proper authentication/authorization
- [ ] Sensitive data protected

### Testing
- [ ] Tests cover functionality
- [ ] Tests handle edge cases
- [ ] Tests are maintainable
- [ ] Integration with existing tests
```

## Development Tools

### VS Code Configuration

#### 1. Recommended Extensions
```json
{
  "recommendations": [
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-json",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense",
    "ms-vscode.vscode-jest",
    "humao.rest-client"
  ]
}
```

#### 2. Settings
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "tailwindCSS.includeLanguages": {
    "typescript": "javascript",
    "typescriptreact": "javascript"
  }
}
```

### Linting and Formatting

#### 1. ESLint Configuration
```json
{
  "extends": [
    "next/core-web-vitals",
    "@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "prefer-const": "error",
    "no-var": "error"
  }
}
```

#### 2. Prettier Configuration
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}
```

### Debugging

#### 1. VS Code Debug Configuration
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Next.js: debug server-side",
      "type": "node-terminal",
      "request": "launch",
      "command": "npm run dev"
    },
    {
      "name": "Next.js: debug client-side",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000"
    },
    {
      "name": "Next.js: debug full stack",
      "type": "node-terminal",
      "request": "launch",
      "command": "npm run dev",
      "serverReadyAction": {
        "pattern": "started server on .+, url: (https?://.+)",
        "uriFormat": "%s",
        "action": "debugWithChrome"
      }
    }
  ]
}
```

## Performance Guidelines

### Frontend Performance

#### 1. Bundle Optimization
```typescript
// Dynamic imports for code splitting
const GraphicEditor = dynamic(() => import('@/components/graphics/GraphicEditor'), {
  loading: () => <LoadingSpinner />,
  ssr: false
});

// Route-based code splitting
const Dashboard = dynamic(() => import('@/app/dashboard/page'));
const Graphics = dynamic(() => import('@/app/graphics/page'));
```

#### 2. Image Optimization
```typescript
import Image from 'next/image';

// Use Next.js Image component for optimization
const OptimizedImage: React.FC<{ src: string; alt: string }> = ({ src, alt }) => (
  <Image
    src={src}
    alt={alt}
    width={800}
    height={600}
    placeholder="blur"
    blurDataURL="data:image/jpeg;base64,..."
    loading="lazy"
  />
);
```

#### 3. Memory Management
```typescript
// Cleanup functions in useEffect
const Component: React.FC = () => {
  useEffect(() => {
    const timer = setInterval(() => {
      // Some operation
    }, 1000);

    return () => {
      clearInterval(timer); // Cleanup
    };
  }, []);

  return <div>Component</div>;
};

// Avoid memory leaks in event listeners
const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    setSocket(ws);

    return () => {
      ws.close(); // Cleanup WebSocket connection
    };
  }, [url]);

  return socket;
};
```

## Security Best Practices

### Frontend Security

#### 1. Input Validation
```typescript
// Sanitize user input
import DOMPurify from 'dompurify';

const SanitizedContent: React.FC<{ content: string }> = ({ content }) => {
  const sanitizedContent = useMemo(() => {
    return DOMPurify.sanitize(content);
  }, [content]);

  return <div dangerouslySetInnerHTML={{ __html: sanitizedContent }} />;
};
```

#### 2. XSS Prevention
```typescript
// Avoid dangerouslySetInnerHTML when possible
const SafeComponent: React.FC<{ text: string }> = ({ text }) => {
  return <div>{text}</div>; // Safe: text is automatically escaped
};

// If you must use dangerouslySetInnerHTML, always sanitize
const SafeHTML: React.FC<{ html: string }> = ({ html }) => {
  const sanitizedHtml = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong'],
    ALLOWED_ATTR: []
  });

  return <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />;
};
```

#### 3. CSRF Protection
```typescript
// Include CSRF token in API requests
const apiClient = {
  async post(url: string, data: any) {
    const csrfToken = getCsrfToken();
    
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify(data),
    });
  }
};
```

## Deployment Guidelines

### Build Process

#### 1. Production Build
```bash
# Build for production
npm run build

# Analyze bundle size
npm run analyze

# Test production build locally
npm run start
```

#### 2. Environment Variables
```bash
# Verify all required environment variables
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.gal.gg
NEXT_PUBLIC_WS_URL=wss://api.gal.gg/ws
NEXTAUTH_URL=https://dashboard.gal.gg
NEXTAUTH_SECRET=production-secret-key
```

#### 3. Performance Testing
```bash
# Run Lighthouse CI
npm run test:lighthouse

# Run performance tests
npm run test:performance

# Monitor bundle size
npm run test:bundle-size
```

## Documentation Standards

### Code Documentation

#### 1. JSDoc Comments
```typescript
/**
 * Creates a new graphic with the specified properties
 * @param graphic - The graphic data to create
 * @returns Promise that resolves to the created graphic
 * @throws {ApiError} When the API request fails
 * @example
 * ```typescript
 * const graphic = await createGraphic({
 *   name: 'Score Bug',
 *   templateId: 'score-bug-v2'
 * });
 * ```
 */
const createGraphic = async (graphic: CreateGraphicInput): Promise<Graphic> => {
  // Implementation
};
```

#### 2. Component Documentation
```typescript
interface GraphicEditorProps {
  /** The graphic being edited */
  graphic?: Graphic;
  /** The template to use for the graphic */
  template: Template;
  /** Callback when the graphic is saved */
  onSave: (graphic: Graphic) => void;
  /** Callback when editing is cancelled */
  onCancel: () => void;
  /** Whether to show the preview panel */
  showPreview?: boolean;
}

/**
 * A component for editing graphics with real-time preview
 * 
 * @example
 * ```tsx
 * <GraphicEditor
 *   template={selectedTemplate}
 *   onSave={handleSave}
 *   onCancel={handleCancel}
 *   showPreview
 * />
 * ```
 */
const GraphicEditor: React.FC<GraphicEditorProps> = ({
  graphic,
  template,
  onSave,
  onCancel,
  showPreview = false
}) => {
  // Component implementation
};
```

## Telemetry & Metrics
- Python services record counters and timings through `utils.metrics`.
- FastAPI middleware, Discord command tracers, and Sheets retry helpers emit metrics with thresholds for slow operations.
- The API exposes `GET /metrics` for diagnostics and local dashboards.
- Frontend hooks use `@/utils/logging` for consistent client-side telemetry output.

## References
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [Jest Documentation](https://jestjs.io)
- [Playwright Documentation](https://playwright.dev)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: Development Lead
- **Classification**: Internal Use Only
