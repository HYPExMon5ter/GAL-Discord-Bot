---
id: system.api_backend_system
version: 1.0
last_updated: 2025-10-13
tags: [api, backend, fastapi, authentication, documentation]
---

# API Backend System

**Purpose**: Complete FastAPI application providing RESTful endpoints and WebSocket connections for the Guardian Angel League Live Graphics Dashboard with secure master password authentication.

## Overview

The API backend system (`api/`) is a comprehensive FastAPI application that serves as the central data access point for the Live Graphics Dashboard. It implements secure authentication, real-time WebSocket updates, and provides complete CRUD operations for tournaments, users, and configuration management.

**Location**: `api/` directory  
**Primary Dependencies**: FastAPI, SQLAlchemy, JWT, Pydantic, WebSockets  

## Architecture

### Directory Structure
```
api/
├── main.py                  # FastAPI application setup and authentication
├── dependencies.py          # Common dependency injection patterns
├── middleware.py            # Custom middleware for security and logging
├── routers/                 # API route definitions
│   ├── tournaments.py       # Tournament management endpoints
│   ├── users.py             # User management endpoints  
│   ├── configuration.py     # Configuration management endpoints
│   └── websocket.py         # Real-time WebSocket endpoints
├── schemas/                 # Pydantic models for request/response validation
│   ├── auth.py              # Authentication models
│   ├── tournament.py        # Tournament data models
│   ├── user.py              # User data models
│   └── configuration.py     # Configuration data models
└── services/                # Business logic layer
    ├── tournament_service.py    # Tournament business logic
    ├── user_service.py          # User business logic
    └── configuration_service.py # Configuration business logic
```

## Core Components

### 1. FastAPI Application (`main.py`)
**Purpose**: Main application setup with authentication and CORS

**Key Features**:
- **JWT Authentication**: Master password-based authentication with configurable token expiration
- **CORS Middleware**: Cross-origin resource sharing configuration
- **API Documentation**: Auto-generated OpenAPI/Swagger docs at `/docs`
- **Security**: HTTP Bearer token authentication scheme
- **Environment Configuration**: `.env.local` based configuration

**For Implementation Details**: See `api/main.py` for:
- Authentication flow implementation
- Middleware setup and configuration
- Environment variable handling
- Application initialization

### 2. Dependencies System (`dependencies.py`)
**Purpose**: Common dependency injection for database sessions and authentication

**Key Features**:
- **Database Session Management**: SQLAlchemy session lifecycle management
- **Authentication Dependency**: JWT token verification for protected routes
- **Session Cleanup**: Automatic session cleanup to prevent connection leaks

**For Implementation Details**: See `api/dependencies.py` for:
- Database session factory patterns
- Authentication middleware implementation
- Error handling for dependency injection

### 3. Custom Middleware (`middleware.py`)
**Purpose**: Security and logging middleware for request/response handling

**Key Features**:
- **Request Logging**: Comprehensive request/response logging
- **Security Headers**: Custom security headers injection
- **Rate Limiting**: Basic rate limiting protection
- **Error Handling**: Centralized error response formatting
- **Performance Monitoring**: Request timing and metrics

**For Implementation Details**: See `api/middleware.py` for:
- Request/response logging implementation
- Security header configuration
- Rate limiting strategies
- Error handling patterns

## API Routes

### 1. Tournament Management (`api/routers/tournaments.py`)
**Purpose**: Complete CRUD operations for tournament data

**Endpoints**: Standard REST operations for tournament lifecycle management

**For Implementation Details**: See `api/routers/tournaments.py` for:
- Tournament CRUD operations
- Validation rules and business logic
- Error handling and response formatting

### 2. User Management (`api/routers/users.py`)
**Purpose**: User data management and authentication

**Key Features**:
- User CRUD operations
- Authentication and authorization
- Profile management

**For Implementation Details**: See `api/routers/users.py` for:
- User data models and validation
- Authentication endpoint implementations
- Authorization patterns

### 3. Configuration Management (`api/routers/configuration.py`)
**Purpose**: Dynamic configuration management

**Key Features**:
- Configuration CRUD operations
- Hot-reload capabilities
- Environment-specific settings

**For Implementation Details**: See `api/routers/configuration.py` for:
- Configuration validation schemas
- Dynamic update mechanisms
- Environment handling

### 4. WebSocket Events (`api/routers/websocket.py`)
**Purpose**: Real-time event streaming to connected clients

**Key Features**:
- Real-time updates via WebSocket
- Event broadcasting
- Connection management

**For Implementation Details**: See `api/routers/websocket.py` for:
- WebSocket connection handling
- Event serialization and broadcasting
- Connection lifecycle management

## Data Models

### 1. Authentication Models (`api/schemas/auth.py`)
**Purpose**: JWT authentication request/response models

**For Implementation Details**: See `api/schemas/auth.py` for:
- Login request/response schemas
- Token validation models
- User authentication data structures

### 2. Tournament Models (`api/schemas/tournament.py`)
**Purpose**: Tournament data validation and serialization

**For Implementation Details**: See `api/schemas/tournament.py` for:
- Tournament creation/update schemas
- Response serialization models
- Validation rules and constraints

### 3. User Models (`api/schemas/user.py`)
**Purpose**: User data validation and serialization

**For Implementation Details**: See `api/schemas/user.py` for:
- User profile schemas
- Authentication data models
- Permission and role structures

### 4. Configuration Models (`api/schemas/configuration.py`)
**Purpose**: Configuration data validation and serialization

**For Implementation Details**: See `api/schemas/configuration.py` for:
- Configuration schema definitions
- Validation rules
- Environment-specific configurations

## Business Logic Services

### 1. Tournament Service (`api/services/tournament_service.py`)
**Purpose**: Tournament business logic and data operations

**For Implementation Details**: See `api/services/tournament_service.py` for:
- Business rule implementations
- Data validation logic
- Integration with data access layer

### 2. User Service (`api/services/user_service.py`)
**Purpose**: User management business logic

**For Implementation Details**: See `api/services/user_service.py` for:
- User lifecycle management
- Authentication workflows
- Permission handling

### 3. Configuration Service (`api/services/configuration_service.py`)
**Purpose**: Configuration management business logic

**For Implementation Details**: See `api/services/configuration_service.py` for:
- Configuration validation and processing
- Dynamic update handling
- Environment management

## Security Implementation

### Authentication Flow
1. Client sends master password to `/auth/login`
2. Server validates credentials and generates JWT token
3. Client includes JWT token in `Authorization: Bearer <token>` header
4. Server validates token for protected endpoints

**For Implementation Details**: See `api/main.py` for login endpoint and `api/dependencies.py` for token validation

### Security Best Practices
- Environment-based configuration with `.env.local`
- JWT token expiration and refresh mechanisms
- Request validation and sanitization
- Rate limiting and abuse prevention
- Comprehensive logging and monitoring

**For Implementation Details**: See `api/middleware.py` for security middleware and `api/main.py` for authentication setup

## Performance Considerations

### Optimization Strategies
- Async/await patterns for high concurrency
- Connection pooling for database operations
- Efficient serialization with Pydantic
- Proper error handling and resource cleanup
- Request/response caching where appropriate

**For Implementation Details**: See individual router files and service implementations for specific optimization patterns

## Testing Strategy

### Test Coverage Areas
- Unit tests for business logic services
- Integration tests for API endpoints
- Authentication and authorization testing
- WebSocket connection testing
- Performance and load testing

**For Implementation Details**: Refer to the project's test directory for specific test implementations

## Deployment Configuration

### Environment Setup
- Environment variables loaded from `.env` and `.env.local` (parent directory)
- Database connection configuration (SQLite for local, PostgreSQL for production)
- In-memory caching configuration (Redis removed as of v2.0)
- CORS and security settings
- Dashboard control via environment variables
- Logging and monitoring configuration

### Environment Variables

#### Required Variables
```bash
# Database Configuration
DATABASE_URL=sqlite:///./dashboard/dashboard.db  # Local development
DATABASE_URL=postgresql://...              # Production (Railway PostgreSQL)

# Dashboard Control
ENABLE_DASHBOARD=true                        # Enable/disable dashboard services

# API Configuration
RIOT_API_KEY=your_riot_api_key             # League of Legends IGN verification
```

#### Optional Variables
```bash
# Dashboard Authentication
DASHBOARD_MASTER_PASSWORD=secure_password    # Dashboard login password

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_TITLE="GAL Live Graphics Dashboard"
NODE_ENV=development                          # Node.js environment
API_BASE_URL=http://localhost:8000
```

**Changes in v2.0**: 
- **Redis Removed**: Redis caching replaced with in-memory caching for simpler deployment
- **ENABLE_DASHBOARD**: New variable to control dashboard service startup
- **Railway Support**: Optimized for Railway.com production deployment
- **Security Updates**: Environment variable precedence updated for better configuration management

**For Implementation Details**: See `api/dependencies.py` and `api/main.py` for environment variable handling and configuration patterns

## Graphics Service and JSON Serialization

### Graphics Service (`api/services/graphics_service.py`)
**Purpose**: Business logic layer for graphics management with proper JSON serialization

**Key Features**:
- **JSON Serialization**: Automatic serialization/deserialization for SQLite compatibility
- **Canvas Locking**: Real-time canvas editing lock management
- **Archive Management**: Graphic archiving and restoration procedures
- **Error Handling**: Robust error handling for serialization issues

**Implementation Details**:

#### JSON Serialization Pattern
```python
def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
    """Create a new graphic with proper JSON serialization"""
    from ..models import Graphic
    
    db_graphic = Graphic(
        title=graphic.title,
        # Serialize Python dict to JSON string for SQLite compatibility
        data_json=json.dumps(graphic.data_json or {}),
        created_by=created_by,
        archived=False
    )
    
    self.db.add(db_graphic)
    self.db.commit()
    self.db.refresh(db_graphic)
    
    return {
        "id": db_graphic.id,
        "title": db_graphic.title,
        # Deserialize JSON string back to Python dict for API response
        "data_json": json.loads(db_graphic.data_json) if db_graphic.data_json else {},
        "created_by": db_graphic.created_by,
        "created_at": db_graphic.created_at,
        "updated_at": db_graphic.updated_at,
        "archived": db_graphic.archived
    }
```

#### Canvas Locking System
```python
def acquire_lock(self, lock_request: CanvasLockCreate) -> Dict[str, Any]:
    """Acquire a canvas lock for editing"""
    from ..models import CanvasLock
    
    # Check if there's an existing active lock
    existing_lock = self.get_active_lock(lock_request.graphic_id)
    
    if existing_lock:
        # If lock belongs to the same user and is still valid, extend it
        if existing_lock.user_name == lock_request.user_name and existing_lock.expires_at > datetime.utcnow():
            existing_lock.expires_at = datetime.utcnow() + timedelta(minutes=5)
            self.db.commit()
            self.db.refresh(existing_lock)
            
            return {
                "id": existing_lock.id,
                "graphic_id": existing_lock.graphic_id,
                "user_name": existing_lock.user_name,
                "locked": True,
                "locked_at": existing_lock.locked_at,
                "expires_at": existing_lock.expires_at
            }
        
        # Lock is owned by someone else
        return {
            "locked": True,
            "locked_by": existing_lock.user_name,
            "expires_at": existing_lock.expires_at,
            "can_edit": False
        }
    
    # Create new lock
    new_lock = CanvasLock(
        graphic_id=lock_request.graphic_id,
        user_name=lock_request.user_name,
        locked=True,
        locked_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    
    self.db.add(new_lock)
    self.db.commit()
    self.db.refresh(new_lock)
    
    return {
        "id": new_lock.id,
        "graphic_id": new_lock.graphic_id,
        "user_name": new_lock.user_name,
        "locked": True,
        "locked_at": new_lock.locked_at,
        "expires_at": new_lock.expires_at,
        "can_edit": True
    }
```

#### Error Handling and Recovery
```python
def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
    """Create a new graphic with robust error handling"""
    try:
        from ..models import Graphic
        
        # Validate data_json before serialization
        data_to_serialize = graphic.data_json or {}
        
        # Ensure data is JSON serializable
        try:
            json_str = json.dumps(data_to_serialize)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error: {e}")
            json_str = json.dumps({})  # Fallback to empty object
        
        db_graphic = Graphic(
            title=graphic.title,
            data_json=json_str,
            created_by=created_by,
            archived=False
        )
        
        self.db.add(db_graphic)
        self.db.commit()
        self.db.refresh(db_graphic)
        
        return {
            "id": db_graphic.id,
            "title": db_graphic.title,
            "data_json": json.loads(db_graphic.data_json) if db_graphic.data_json else {},
            "created_by": db_graphic.created_by,
            "created_at": db_graphic.created_at,
            "updated_at": db_graphic.updated_at,
            "archived": db_graphic.archived
        }
        
    except Exception as e:
        logger.error(f"Error creating graphic: {e}")
        self.db.rollback()
        raise
```

### Graphics API Endpoints (`api/routers/graphics.py`)
**Purpose**: REST API endpoints for graphics management

**Key Endpoints**:
- `GET /graphics` - List all graphics (with optional archive filtering)
- `POST /graphics` - Create new graphic
- `GET /graphics/{id}` - Get specific graphic
- `PUT /graphics/{id}` - Update graphic
- `DELETE /graphics/{id}` - Delete graphic (soft delete via archive)
- `POST /lock/{id}` - Acquire canvas lock
- `DELETE /lock/{id}` - Release canvas lock
- `GET /lock/status` - Get lock status

**For Implementation Details**: See `api/routers/graphics.py` for:
- API endpoint implementations
- Request/response validation
- Error handling patterns
- Authentication requirements

### Graphics Schemas (`api/schemas/graphics.py`)
**Purpose**: Pydantic models for graphics data validation

**Key Models**:
- `GraphicCreate` - Request model for graphic creation
- `GraphicUpdate` - Request model for graphic updates
- `CanvasLockCreate` - Request model for lock acquisition
- `LockStatusResponse` - Response model for lock status

**For Implementation Details**: See `api/schemas/graphics.py` for:
- Data validation rules
- Type definitions
- Serialization patterns

## Related Documentation

- [Data Access Layer](./data-access-layer.md) - Database interaction layer
- [Event System](./event-system.md) - Real-time event handling
- [Data Models](./data-models.md) - Core data models and entities
- [Architecture Overview](./architecture.md) - System architecture details

## Dependencies

### Core Framework Dependencies
- **FastAPI**: Web framework and API routing
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: ORM and database operations
- **python-jose**: JWT token handling
- **python-multipart**: Multipart form data support

### Security Dependencies
- **passlib**: Password hashing utilities
- **python-bcrypt**: bcrypt password hashing
- **uvicorn**: ASGI server for production

### Database Dependencies
- **psycopg2-binary**: PostgreSQL database adapter
- **alembic**: Database migration tool
- **redis-py**: Redis client for caching


## Recent API Module Updates

### websocket

**Description**: WebSocket endpoints for real-time updates with backpressure handling.

**Key Functions**:

- `utcnow()`
  - Timezone-aware wrapper used throughout the WebSocket manager.
- `async websocket_endpoint(websocket, token)`
  - WebSocket endpoint for real-time updates.
- `async websocket_status()`
  - Get WebSocket connection status.
- `async send_tournament_update(tournament_data)`
- `async send_user_update(user_data)`
- `async send_configuration_update(config_data)`
- `async send_system_notification(notification)`
- `async send_placement_update(round_name, lobby_updates)`
  - Notify dashboard clients that placements were updated.
Dashboard should refresh standings data.

Args:
    round_name: Name of the round that was updated
    lobby_updates: List of placement updates with lobby, player, placement info

**Classes**:

- `ConnectionContext`
- `ConnectionManager`
  - Manages active WebSocket connections with bounded queues to avoid head-of-line
blocking and implements graceful teardown on errors or backpressure.
  - Methods: `get_connection_count()`, `get_user_count()`

**Dependencies**:
- __future__.annotations, contextlib.suppress, dataclasses.dataclass, dataclasses.field, datetime.UTC, datetime.datetime, datetime.timedelta, typing.Any, typing.Dict, typing.List, typing.Optional, typing.Set, fastapi.APIRouter, fastapi.WebSocket, fastapi.WebSocketDisconnect, jose.JWTError, jose.jwt, api.auth.ALGORITHM, api.auth.SECRET_KEY, api.auth.TokenData

### graphics_service

**Description**: Service layer for graphics management.

Acts as the orchestration layer between the FastAPI routers and the underlying
SQLAlchemy models, exposing operations as simple Python methods while raising
domain-specific `ServiceError`s when something goes wrong.

**Classes**:

- `GraphicsService`
  - Service for managing graphics and canvas locks.
  - Methods: `create_graphic()`, `get_graphics()`, `get_event_names()`, `get_graphic_by_id()`, `update_graphic()`, ...

**Dependencies**:
- __future__.annotations, datetime.UTC, datetime.datetime, datetime.timedelta, typing.Any, typing.Dict, typing.List, typing.Optional, sqlalchemy.and_, sqlalchemy.or_, sqlalchemy.orm.Session, api.services.errors.ConflictError, api.services.errors.NotFoundError, models.Archive, models.CanvasLock, models.Graphic, schemas.graphics.CanvasLockCreate, schemas.graphics.GraphicCreate, schemas.graphics.GraphicUpdate, schemas.graphics.LockStatusResponse, api.services.StandingsService

### graphics

**Description**: Graphics API endpoints.

Routers delegate to the graphics service and keep controller logic minimal.

**Key Functions**:

- `async create_graphic(graphic, current_user, service)`
- `async get_graphics(include_archived, _user, service)`
- `async get_graphic(graphic_id, _user, service)`
- `async update_graphic(graphic_id, graphic_update, current_user, service)`
- `async duplicate_graphic(graphic_id, duplicate_request, new_title, new_event_name, current_user, service)`
- `async delete_graphic(graphic_id, current_user, service)`
- `async get_event_names(_user, service)`
  - Get list of unique event names from all graphics.
- `async permanent_delete_graphic(graphic_id, _admin, service)`
- `async acquire_lock(graphic_id, lock_request, current_user, service)`
- `async release_lock(graphic_id, session_request, current_user, service)`
- `async get_lock_status(graphic_id, session_id, current_user, service)`
- `async refresh_lock(graphic_id, session_request, current_user, service)`
- `async get_all_lock_status(_user)`
- `async archive_graphic(graphic_id, archive_request, current_user, service)`
- `async restore_graphic(graphic_id, current_user, service)`
- `async get_archived_graphics(current_user, service)`
- `async permanent_delete_archive(graphic_id, _admin, service)`
- `async cleanup_expired_locks(_admin, service)`
- `async get_ranked_players(tournament_id, guild_id, sort_by, sort_order, limit, service)`
  - Get ranked player data for simplified element system.
- `async view_graphic(graphic_id, service)`

**Dependencies**:
- __future__.annotations, typing.Any, typing.Dict, typing.Optional, fastapi.APIRouter, fastapi.Body, fastapi.Depends, fastapi.Query, fastapi.exceptions.HTTPException, sqlalchemy.exc.NoResultFound, api.auth.TokenData, api.dependencies.get_active_user, api.dependencies.get_graphics_service, api.dependencies.require_roles, api.dependencies.require_write_access, api.services.graphics_service.GraphicsService, api.utils.service_runner.execute_service, schemas.graphics.ArchiveActionRequest, schemas.graphics.ArchiveListResponse, schemas.graphics.ArchiveResponse, schemas.graphics.CanvasLockCreate, schemas.graphics.CanvasLockResponse, schemas.graphics.GraphicCreate, schemas.graphics.GraphicListResponse, schemas.graphics.GraphicResponse, schemas.graphics.GraphicUpdate, schemas.graphics.LockStatusResponse

### graphics

**Description**: Pydantic schemas for graphics management

**Classes**:

- `GraphicBase`
  - Base schema for graphics
  - Inherits from: BaseModel
- `GraphicCreate`
  - Schema for creating a new graphic
  - Inherits from: GraphicBase
- `GraphicUpdate`
  - Schema for updating an existing graphic
  - Inherits from: BaseModel
- `GraphicResponse`
  - Schema for graphic response
  - Inherits from: BaseModel
- `GraphicListResponse`
  - Schema for graphics list response
  - Inherits from: BaseModel
- `CanvasLockBase`
  - Base schema for canvas locks
  - Inherits from: BaseModel
- `CanvasLockCreate`
  - Schema for creating a canvas lock
  - Inherits from: CanvasLockBase
- `CanvasLockResponse`
  - Schema for canvas lock response
  - Inherits from: CanvasLockBase
- `LockStatusResponse`
  - Schema for lock status response
  - Inherits from: BaseModel
- `ArchiveActionRequest`
  - Schema for archive action requests
  - Inherits from: BaseModel
- `ArchiveResponse`
  - Schema for archive action response
  - Inherits from: BaseModel
- `ArchiveListResponse`
  - Schema for archive list response
  - Inherits from: BaseModel

**Dependencies**:
- datetime.datetime, typing.Dict, typing.Any, typing.Optional, pydantic.BaseModel, pydantic.ConfigDict, pydantic.Field
