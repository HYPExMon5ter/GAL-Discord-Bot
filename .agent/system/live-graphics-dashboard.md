---
id: system.live-graphics-dashboard
version: 2.0
last_updated: 2025-10-13
tags: [dashboard, frontend, backend, graphics, authentication, canvas-locking]
---

# Live Graphics Dashboard 2.0

## Overview
The Live Graphics Dashboard 2.0 is a comprehensive web-based platform for creating, managing, and archiving live broadcast graphics for the Guardian Angel League. The system features password-gated access, real-time collaborative editing, and robust archive management.

## Architecture

### Frontend Technology Stack
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript for type safety
- **Styling**: Tailwind CSS with custom design system
- **Components**: shadcn/ui component library
- **State Management**: React hooks with custom API integration
- **Authentication**: JWT token-based session management

### Backend Technology Stack
- **Framework**: FastAPI with Python
- **Database**: SQLite with PostgreSQL compatibility
- **Authentication**: JWT tokens with master password validation
- **Real-time**: WebSocket connections for live updates
- **ORM**: SQLAlchemy with relationship management

## Key Features

### 🔐 Authentication System
- **Master Password**: Single shared password for staff access
- **JWT Tokens**: 24-hour session tokens with automatic refresh
- **Session Management**: Secure cookie-based authentication
- **Login Tracking**: Comprehensive audit logging for all access attempts

### 🎨 Graphics Management
- **CRUD Operations**: Create, read, update, and delete graphics
- **Canvas Editor**: Full-screen route-based editing interface with advanced features
- **Table View**: Sortable table interface replacing card-based UI
- **Search Functionality**: Filter graphics by title or event name
- **Status Indicators**: Visual badges for locked and active graphics
- **Real-time Updates**: Live status updates via WebSocket connections

### 🔒 Canvas Locking System
- **Single-User Editing**: Only one user can edit a graphic at a time
- **Automatic Locking**: Lock acquisition when opening the canvas editor
- **5-Minute Expiry**: Automatic lock release after 5 minutes of inactivity
- **Visual Indicators**: Clear lock status with countdown timers
- **Conflict Prevention**: Users cannot edit locked graphics

### 📦 Archive Management
- **Safe Archiving**: Graphics can be archived without data loss
- **Metadata Tracking**: Archive records include timestamps and user information
- **Restore Functionality**: Archived graphics can be restored to active status
- **Admin Controls**: Permanent deletion available to administrators only
- **Archive Statistics**: Comprehensive archive metrics and contributor tracking

## API Endpoints

### Authentication
- `POST /auth/login` - Authenticate with master password
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/verify` - Verify current token validity

### Graphics Management
- `GET /api/v1/graphics` - List all active graphics
- `POST /api/v1/graphics` - Create new graphic
- `GET /api/v1/graphics/{id}` - Get specific graphic
- `GET /api/v1/graphics/{id}/view` - Public OBS browser source view (NEW)
- `PUT /api/v1/graphics/{id}` - Update graphic (requires unlock)
- `DELETE /api/v1/graphics/{id}` - Delete graphic (requires unlock, admin only)

### Canvas Locking
- `POST /api/v1/lock/{graphic_id}` - Acquire canvas lock
- `DELETE /api/v1/lock/{graphic_id}` - Release canvas lock
- `GET /api/v1/lock/{graphic_id}/status` - Check lock status
- `GET /api/v1/lock/status` - Get all active locks

### Archive Management
- `GET /api/v1/archive` - List archived graphics
- `POST /api/v1/archive/{id}` - Archive graphic
- `POST /api/v1/archive/{id}/restore` - Restore archived graphic
- `DELETE /api/v1/archive/{id}/permanent` - Permanent delete (admin only)

### Maintenance
- `POST /api/v1/maintenance/cleanup-locks` - Clean up expired locks

## Database Schema

### Graphics Table
```sql
CREATE TABLE graphics (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    event_name VARCHAR(255),                    -- NEW
    data_json TEXT DEFAULT '{}',
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE
);
```

### Canvas Locks Table
```sql
CREATE TABLE canvas_locks (
    id INTEGER PRIMARY KEY,
    graphic_id INTEGER NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    locked BOOLEAN DEFAULT TRUE,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (graphic_id) REFERENCES graphics(id)
);
```

### Archives Table
```sql
CREATE TABLE archives (
    id INTEGER PRIMARY KEY,
    graphic_id INTEGER NOT NULL,
    archived_by VARCHAR(255) NOT NULL,
    reason TEXT,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (graphic_id) REFERENCES graphics(id)
);
```

### Auth Logs Table
```sql
CREATE TABLE auth_logs (
    id INTEGER PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    success BOOLEAN NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT
);
```

### Active Sessions Table
```sql
CREATE TABLE active_sessions (
    id INTEGER PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Frontend Components

### Page Structure
- `app/page.tsx` - Root page with authentication redirect
- `app/login/page.tsx` - Login page with password authentication
- `app/dashboard/page.tsx` - Main dashboard with tabbed interface
- `app/layout.tsx` - Root layout with providers and global styles

### Component Hierarchy
```
DashboardLayout
├── Header
│   ├── UserStatus
│   └── SignOutButton
├── Tabs
│   ├── GraphicsTab
│   │   ├── CreateGraphicDialog
│   │   ├── GraphicCard
│   │   │   └── LockBanner
│   │   └── CanvasEditor
│   │       └── LockStatus
│   └── ArchiveTab
│       ├── ArchivedGraphicCard
│       └── RestoreDialog
└── Footer
```

### Custom Hooks
- `useAuth()` - Authentication state management
- `useGraphics()` - Graphics CRUD operations
- `useLocks()` - Canvas lock management
- `useArchive()` - Archive operations

## Security Features

### Authentication Security
- **Environment Variables**: Master password stored securely in environment
- **Token Expiration**: 24-hour token expiry with automatic refresh
- **Session Validation**: Token validation on every API request
- **Secure Headers**: CORS, XSS protection, and content security headers

### Data Security
- **Input Validation**: Comprehensive input sanitization and validation
- **SQL Injection Protection**: ORM-based database operations
- **XSS Prevention**: Proper data encoding and sanitization
- **CSRF Protection**: Same-site cookies and secure token handling

### Access Control
- **Role-Based Permissions**: Admin-only operations for permanent deletion
- **Lock Enforcement**: Automatic prevention of unauthorized edits
- **Audit Logging**: Comprehensive logging of all user actions
- **IP Tracking**: IP address logging for security monitoring

## Performance Optimization

### Frontend Optimization
- **Code Splitting**: Automatic code splitting with Next.js
- **Image Optimization**: Next.js Image component for optimized images
- **Caching Strategy**: Client-side caching for API responses
- **Lazy Loading**: Components loaded on demand

### Backend Optimization
- **Database Indexing**: Optimized indexes for frequent queries
- **Connection Pooling**: Efficient database connection management
- **Async Operations**: Full async/await support for non-blocking operations
- **Response Caching**: Intelligent caching for frequently accessed data

### Real-time Performance
- **WebSocket Efficiency**: Optimized WebSocket connection management
- **Lock Cleanup**: Automatic cleanup of expired locks
- **Session Management**: Efficient session storage and cleanup
- **Background Tasks**: Scheduled maintenance tasks for system health

## Development Workflow

### Local Development
```bash
# Start the FastAPI backend
cd api
python -m main

# Start the Next.js frontend
cd dashboard
npm run dev
```

### Environment Configuration
```bash
# Backend environment (.env.local)
DASHBOARD_MASTER_PASSWORD=your-secure-password
DATABASE_URL=sqlite:///./dashboard.db

# Frontend environment (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Database Setup
- SQLite database is automatically created on first run
- PostgreSQL support available with environment variable configuration
- Database migrations handled by SQLAlchemy models

## Integration Points

### Discord Bot Integration
- Real-time graphics updates via WebSocket connections
- Shared authentication system with the main bot
- Consistent data models across all systems

### Google Sheets Integration
- Archive data synchronization with Google Sheets
- Configuration management through existing sheet system
- Backup and restore functionality

### External API Integration
- Riot Games API for player verification (future enhancement)
- Third-party graphics library integration (planned)
- Cloud storage integration for graphics assets (planned)

## Monitoring and Maintenance

### System Health
- Health check endpoint at `/health`
- Comprehensive error logging and reporting
- Performance metrics and monitoring
- Database health checks

### Maintenance Tasks
- Automatic cleanup of expired locks (cron job)
- Session cleanup and token refresh
- Database optimization and indexing
- Log rotation and archival

### Troubleshooting
- Detailed error messages with context
- Debug logging for development
- Performance profiling tools
- Health monitoring dashboards

## Future Enhancements

### Phase 2 Features
- Discord OAuth integration for user authentication
- Role-based access control with granular permissions
- Multi-user collaboration with real-time editing
- Advanced graphics templates and components

### Performance Improvements
- Redis integration for enhanced caching
- CDN integration for static assets
- Database sharding for scalability
- Load balancing for high availability

### User Experience
- Drag-and-drop graphics editor
- Real-time collaboration features
- Advanced search and filtering
- Mobile-responsive design improvements

## Deployment Considerations

### Production Environment
- HTTPS enforcement for secure connections
- Environment-specific configuration management
- Database backup and disaster recovery
- Load balancing and scaling considerations

### Security Hardening
- Rate limiting for API endpoints
- Intrusion detection and prevention
- Regular security audits and updates
- Secure key management and rotation

### Monitoring and Alerting
- Application performance monitoring
- Error tracking and alerting
- Security event monitoring
- Resource usage monitoring

---
**Last Updated**: 2025-10-11  
**Version**: 2.0  
**Status**: Production Ready  
**Dependencies**: Node.js 18+, Python 3.8+, SQLite 3.x
