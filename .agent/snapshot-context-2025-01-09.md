# Guardian Angel League - Live Graphics Dashboard
## Documentation Rebuild Snapshot Context
**Date**: 2025-01-09  
**Version**: 2.1.0  
**Branch**: live-graphics-dashboard

### 📋 Project Overview

The Guardian Angel League Live Graphics Dashboard is a modern web application for managing live broadcast graphics with real-time collaboration features.

### 🏗️ Architecture Overview

```
Guardian Angel League Discord Bot and Live Graphics Dashboard
├── api/                    # FastAPI backend service
│   ├── main.py            # FastAPI application entry point
│   ├── routers/           # API route definitions
│   │   └── graphics.py    # Graphics, archive, lock endpoints
│   ├── services/          # Business logic layer
│   │   └── graphics_service.py  # Graphics and lock management
│   ├── models.py          # SQLAlchemy database models
│   └── schemas/           # Pydantic request/response schemas
│       └── graphics.py    # Graphics, archive, lock schemas
├── dashboard/             # Next.js 14 frontend application
│   ├── components/        # React components
│   │   ├── graphics/      # Graphics management UI
│   │   ├── archive/       # Archive management UI  
│   │   ├── canvas/        # Canvas editor interface
│   │   └── ui/            # shadcn/ui components
│   ├── hooks/             # Custom React hooks
│   │   ├── use-graphics.ts # Graphics state management
│   │   └── use-archive.ts  # Archive state management
│   └── lib/               # Utility functions
│       └── api.ts         # API client configuration
├── .agent/                # Documentation and automation
│   └── sops/              # Standard Operating Procedures
└── scripts/               # Utility and maintenance scripts
```

### 🔧 Core Technologies

**Backend (API)**
- **Framework**: FastAPI with Python 3.12
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens with master password
- **Validation**: Pydantic schemas
- **CORS**: Cross-origin resource sharing enabled

**Frontend (Dashboard)**
- **Framework**: Next.js 14 with TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui components
- **State Management**: React Hooks + Context API
- **API Client**: Axios with interceptors
- **Authentication**: JWT token management

### 🚀 Key Features

#### Graphics Management
- **CRUD Operations**: Create, read, update, delete graphics
- **Canvas Editing**: Real-time collaborative canvas editing
- **Duplication**: Copy existing graphics with new titles
- **Search & Filter**: Find graphics by title and event

#### Lock Management System
- **Exclusive Editing**: Only one user can edit a graphic at a time
- **Auto-Expiration**: Locks automatically expire after 5 minutes
- **Visual Indicators**: Real-time lock status with countdown timers
- **Manual Release**: Users can release locks when finished editing
- **Maintenance**: Automated cleanup of expired locks

#### Archive System
- **Soft Delete**: Graphics are archived rather than permanently deleted
- **Restore Capability**: Archived graphics can be restored to active state
- **Permanent Delete**: Admin-only permanent deletion of archived items
- **Archive Metadata**: Tracks who archived and when

#### Authentication & Security
- **Master Password**: Single password system for dashboard access
- **JWT Tokens**: Secure token-based authentication with 24-hour expiration
- **Session Management**: Automatic session timeout and refresh
- **Activity Logging**: User actions are logged for audit trails

### 📡 API Architecture

#### Core Endpoints
```
POST   /api/v1/graphics/           # Create new graphic
GET    /api/v1/graphics/           # List graphics (paginated)
GET    /api/v1/graphics/{id}       # Get specific graphic
PUT    /api/v1/graphics/{id}       # Update graphic
DELETE /api/v1/graphics/{id}       # Soft delete (archive)
POST   /api/v1/graphics/{id}/duplicate # Duplicate graphic

POST   /api/v1/archive/{id}        # Archive graphic (requires {} body)
POST   /api/v1/archive/{id}/restore # Restore archived graphic
GET    /api/v1/archive/            # List archived graphics
DELETE /api/v1/archive/{id}/permanent # Permanent delete (admin)

POST   /api/v1/lock/{id}           # Acquire edit lock
DELETE /api/v1/lock/{id}           # Release edit lock
GET    /api/v1/lock/{id}/status    # Get lock status
POST   /api/v1/maintenance/cleanup-locks # Clean expired locks

POST   /api/v1/auth/login          # Authenticate with master password
POST   /api/v1/auth/refresh        # Refresh JWT token
GET    /api/v1/auth/verify         # Verify token validity
```

#### Data Flow
1. **Authentication**: Client authenticates with master password → JWT token
2. **Graphics Operations**: Client makes authenticated requests → API validates → Database operations
3. **Lock Management**: Real-time lock status polling → Visual UI updates
4. **Archive Workflow**: Archive → Metadata tracking → Restore/Permanent delete options

### 🔄 State Management Patterns

#### Frontend State
- **Graphics State**: Managed via `use-graphics.ts` hook
- **Archive State**: Managed via `use-archive.ts` hook  
- **Authentication**: JWT token stored in localStorage
- **Lock Status**: Real-time polling every 30 seconds
- **Error Handling**: Centralized error state with user feedback

#### Backend State
- **Database State**: SQLite with SQLAlchemy ORM
- **Lock State**: CanvasLock table with expiration tracking
- **Archive State**: Archive table with metadata tracking
- **Session State**: JWT token validation and refresh

### 🐛 Recent Bug Fixes & Improvements

#### Archive/Delete Issues (2025-01-09)
**Problem**: Archive and delete operations failing with HTTP errors
- **400 Bad Request** on archive operations
- **404 Not Found** on delete operations
- **405 Method Not Allowed** on permanent delete

**Root Cause**: Frontend API calls not matching backend expectations
- Archive endpoint required empty body `{}` but frontend sent none
- Permanent delete endpoint path mismatch between frontend/backend
- Expired locks preventing operations

**Solution**: 
- Fixed frontend API calls to send correct request bodies
- Updated permanent delete endpoint to use correct path
- Cleaned up 9 expired locks from database
- Added comprehensive error handling

#### Documentation Rebuild (2025-01-09)
**Problem**: Documentation was outdated and missing critical information
- API README showed non-existent endpoints
- Missing SOPs for lock management and archive workflows
- No troubleshooting guides for common errors

**Solution**: 
- Created comprehensive SOP documents in `.agent/sops/`
- Updated API README with current endpoints and examples
- Added troubleshooting guide for common HTTP errors
- Documented lock management and archive workflows

### 📊 Current System State

#### Database
- **Graphics**: 13 total graphics (12 archived, 1 active)
- **Locks**: 0 active locks (cleaned up 9 expired)
- **Archive Records**: Tracking all archived graphics with metadata

#### Active Features
- ✅ Graphics CRUD operations
- ✅ Lock management with auto-expiration
- ✅ Archive/restore functionality  
- ✅ Permanent deletion (admin only)
- ✅ Authentication with JWT tokens
- ✅ Real-time lock status updates
- ✅ Maintenance endpoints for cleanup

#### Known Limitations
- Canvas editor UI exists but needs full implementation
- No WebSocket support for real-time updates (polling only)
- Limited error recovery options for lock conflicts
- No bulk operations for graphics management

### 🎯 Development Priorities

#### Immediate (Next Sprint)
- Complete canvas editor implementation
- Add WebSocket support for real-time updates
- Implement bulk archive/delete operations
- Add comprehensive error recovery

#### Medium Term (Next Quarter)
- Advanced drawing tools and templates
- Multi-language support
- Dark mode toggle
- Export/import functionality
- Advanced analytics and reporting

#### Long Term (Next 6 Months)
- Multi-tenant support
- Advanced permission system
- Plugin architecture
- Mobile responsive design
- Integration with external design tools

### 🔐 Security Considerations

#### Current Security Measures
- **Authentication**: Master password with JWT tokens
- **Authorization**: Role-based access for admin operations
- **Input Validation**: Pydantic schemas for request validation
- **CORS Protection**: Configurable cross-origin access
- **SQL Injection Prevention**: SQLAlchemy ORM usage
- **Session Management**: Token expiration and refresh

#### Security Best Practices
- Password stored in environment variables (not in code)
- JWT tokens with limited lifetime (24 hours)
- Admin-only access to destructive operations
- Lock system prevents concurrent modifications
- Audit logging for all user actions

### 📝 Development Workflow

#### Code Structure
- **API Routes**: RESTful design with proper HTTP methods
- **Service Layer**: Business logic separated from route handlers
- **Database Models**: SQLAlchemy with proper relationships
- **Frontend Components**: Modular design with TypeScript
- **State Management**: Hooks-based with proper error handling

#### Testing Strategy
- **API Testing**: pytest for backend endpoints
- **Frontend Testing**: React Testing Library for components
- **Integration Testing**: End-to-end workflow testing
- **Manual Testing**: User workflow validation

#### Documentation Standards
- **API Documentation**: OpenAPI/Swagger for endpoints
- **SOPs**: Standard operating procedures in `.agent/sops/`
- **Code Comments**: Inline documentation for complex logic
- **README Files**: Project setup and usage instructions

### 🌐 Deployment Architecture

#### Development Environment
- **API Server**: uvicorn running on localhost:8000
- **Dashboard**: Next.js dev server on localhost:3000
- **Database**: SQLite file at `api/dashboard.db`
- **Environment**: `.env.local` for configuration

#### Production Considerations
- **Load Balancing**: Multiple API server instances
- **Database**: PostgreSQL for production scale
- **Caching**: Redis for session and lock management
- **Monitoring**: Application and infrastructure metrics
- **Backup Strategy**: Regular database backups

### 📈 Performance Metrics

#### Current Performance
- **API Response Time**: <100ms for most operations
- **Lock Polling**: 30-second intervals for status updates
- **Database Size**: Lightweight SQLite with efficient queries
- **Memory Usage**: Optimized for single-server deployment

#### Optimization Opportunities
- Implement caching for frequently accessed graphics
- Add database indexes for performance queries
- Use WebSockets instead of polling for real-time updates
- Implement pagination for large graphics lists
- Add compression for API responses

### 🔧 Maintenance Procedures

#### Daily Tasks
- Monitor lock expiration and cleanup
- Check system error logs
- Verify API performance metrics

#### Weekly Tasks  
- Review archive growth and cleanup needs
- Update documentation for any changes
- Monitor user activity patterns

#### Monthly Tasks
- Database maintenance and optimization
- Security audit and updates
- Performance benchmarking
- Backup verification and testing

### 🚨 Incident Response

#### Common Issues
1. **Lock Conflicts**: Users can't edit locked graphics
   - Resolution: Wait for expiration or use maintenance cleanup
   
2. **Archive/Delete Failures**: HTTP errors on graphic operations
   - Resolution: Check lock status, verify API call format
   
3. **Authentication Issues**: Users can't login or access resources
   - Resolution: Verify master password, check JWT token validity

#### Escalation Procedures
1. **Level 1**: Basic troubleshooting with SOPs
2. **Level 2**: Server restart and database maintenance
3. **Level 3**: Code review and system architecture changes

### 📚 Documentation Resources

#### Technical Documentation
- **API README**: Complete endpoint documentation with examples
- **SOPs**: Standard operating procedures for all workflows
- **Troubleshooting Guide**: Common errors and solutions
- **Code Comments**: Inline documentation for complex logic

#### User Documentation
- **Dashboard README**: Frontend setup and usage instructions
- **Feature Guides**: How-to documentation for major features
- **Error Handling**: User-friendly error messages and recovery steps

---

**This snapshot context captures the current state of the Guardian Angel League Live Graphics Dashboard as of 2025-01-09, including all recent fixes, documentation improvements, and system architecture details.**

**Generated by**: Droid Documentation System  
**Version**: 2.1.0  
**Environment**: Development (live-graphics-dashboard branch)
