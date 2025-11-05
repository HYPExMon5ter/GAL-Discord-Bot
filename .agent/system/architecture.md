---
id: system.architecture
version: 2.1
last_updated: 2025-01-24
tags: [system, architecture, unified-data-flow, api-backend, event-system]
---

# Architecture Overview

## System Philosophy
- **Bot**: Python (`discord.py`) with slash commands, embeds, and Discord Scheduled Events
- **API**: FastAPI backend with JWT authentication providing RESTful endpoints and WebSocket connections
- **Data**: Unified data flow architecture with database-first (SQLite for dev, Postgres-ready). Google Sheets serves as a **view**
- **Events**: Event-driven architecture with prioritized handling and real-time updates
- **Security**: Comprehensive token masking, secure logging, and JWT-based API authentication
- **Documentation**: `.agent` auto-maintained via scripts/documentation_manager.py script

## Unified Data Flow Architecture

The Guardian Angel League system now implements a unified data flow architecture that centralizes data management through a comprehensive Data Access Layer (DAL), Event System, and API Backend. This architecture eliminates data fragmentation and provides real-time synchronization across all components.

### Architecture Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord Bot   │    │   Dashboard     │    │  External APIs  │
│                 │    │   Frontend      │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Event System   │◄──►│   API Layer     │◄──►│  Data Sources   │
│                 │    │   (FastAPI)     │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Data Access     │◄──►│  Cache Manager  │◄──►│  Google Sheets  │
│ Layer (DAL)     │    │                 │    │                 │
└─────────┬───────┘    └─────────────────┘    └─────────┬───────┘
          │                                              │
          ▼                                              ▼
┌─────────────────┐                            ┌─────────────────┐
│   PostgreSQL    │                            │   Configuration │
│    Database     │                            │     System      │
└─────────────────┘                            └─────────────────┘
```

## Module Organization (2025-10-11)

### API Backend System (`api/`) - UPDATED
- `api/main.py` (211 lines) - FastAPI application with JWT authentication, CORS, and graphics endpoints
- `api/auth.py` (95 lines) - Authentication module with JWT token management and user verification
- `api/dependencies.py` (54 lines) - Database dependency injection and session management
- `api/middleware.py` (89 lines) - Custom middleware for security and logging
- `api/models.py` (156 lines) - SQLAlchemy models for graphics, canvas locks, archives, and authentication
- `api/routers/tournaments.py` (122 lines) - Tournament management endpoints
- `api/routers/users.py` (138 lines) - User management endpoints  
- `api/routers/configuration.py` (156 lines) - Configuration management endpoints
- `api/routers/websocket.py` (259 lines) - Real-time WebSocket connections and live updates
- `api/routers/graphics.py` (422 lines) - Graphics CRUD, canvas locking, and archive management endpoints
- `api/schemas/` (6 files, 1,048 lines) - Pydantic models for request/response validation including graphics
- `api/services/` (4 files, 4,321 lines) - Business logic layer including graphics service with lock management

### Data Access Layer (`core/data_access/`) - NEW
- `core/data_access/base_repository.py` (384 lines) - Abstract base repository interface
- `core/data_access/cache_manager.py` (657 lines) - Multi-level caching system (Redis + Memory)
- `core/data_access/connection_manager.py` (710 lines) - Database connection pooling and management
- `core/data_access/configuration_repository.py` (523 lines) - Configuration data operations
- `core/data_access/legacy_adapter.py` (412 lines) - Legacy system compatibility layer
- `core/data_access/persistence_repository.py` (587 lines) - Database persistence operations
- `core/data_access/sheets_repository.py` (493 lines) - Google Sheets integration

### Event System (`core/events/`) - NEW  
- `core/events/event_bus.py` (533 lines) - Central event dispatcher with prioritization
- `core/events/event_types.py` (372 lines) - Event type definitions and base classes
- `core/events/handlers/tournament_events.py` (217 lines) - Tournament event handlers
- `core/events/handlers/user_events.py` (164 lines) - User event handlers
- `core/events/handlers/guild_events.py` (189 lines) - Discord guild event handlers
- `core/events/handlers/configuration_events.py` (143 lines) - Configuration event handlers
- `core/events/subscribers/dashboard_subscribers.py` (127 lines) - Dashboard real-time updates
- `core/events/subscribers/discord_subscribers.py` (118 lines) - Discord bot integration

### Data Models (`core/models/`) - NEW
- `core/models/base_model.py` (157 lines) - Abstract base model with validation and audit trails
- `core/models/tournament.py` (213 lines) - Tournament entities with business logic
- `core/models/user.py` (254 lines) - User entities with permissions and statistics
- `core/models/guild.py` (189 lines) - Discord guild management entities
- `core/models/configuration.py` (201 lines) - Configuration entities with versioning

### Legacy Core Components (`core/`)
- `core/commands/` (86,573 lines) - Slash command definitions and tournament management logic
- `core/components_traditional.py` (73,408 lines) - Traditional Discord components and UI elements
- `core/views.py` (51,100 lines) - View classes and persistent view management
- `core/config_ui.py` (36,243 lines) - Configuration UI components and settings management
- `core/persistence.py` (16,544 lines) - Data persistence layer and database operations
- `core/events/event_bus.py` (29,619 lines) - Discord event handlers and bot lifecycle management
- `core/onboard.py` (23,126 lines) - User onboarding system and approval workflow
- `core/migration.py` (11,993 lines) - Database migration and schema management
- `core/test_components.py` (7,157 lines) - Testing framework for core components
- `core/__init__.py` (1,621 lines) - Core package initialization with new module exports

### Live Graphics Dashboard (`dashboard/`) - NEW
- `dashboard/app/` (8 files, 1,234 lines) - Next.js 14 app router with TypeScript pages and layouts
- `dashboard/components/` (12 files, 2,156 lines) - React components including UI, graphics, archive, auth, and canvas
- `dashboard/hooks/` (4 files, 567 lines) - Custom React hooks for API integration and state management
- `dashboard/lib/` (3 files, 234 lines) - API client, utilities, and configuration
- `dashboard/types/` (1 file, 89 lines) - TypeScript type definitions for the dashboard
- `dashboard/utils/` (1 file, 45 lines) - Helper functions for the dashboard frontend
- `dashboard/` (8 files, 234 lines) - Configuration files for Next.js, TypeScript, Tailwind, and shadcn/ui

### Integration Layer (`integrations/`)
- `integrations/sheets.py` (43,741 lines) - Google Sheets integration with caching and optimization
- `integrations/riot_api.py` (9,454 lines) - Riot Games API integration for player verification
- `integrations/sheet_integration.py` (18,846 lines) - Advanced sheet integration bridging systems
- `integrations/sheet_optimizer.py` (9,774 lines) - Performance optimization for sheet operations
- `integrations/sheet_detector.py` (12,627 lines) - Automatic sheet structure detection
- `integrations/sheet_base.py` (4,773 lines) - Base functionality for sheet operations
- `integrations/sheet_utils.py` (3,713 lines) - Utility functions for sheet operations
- `integrations/ign_verification.py` (4,522 lines) - IGN validation system
- `integrations/__init__.py` (764 lines) - Integration package initialization

### Helper System (`helpers/`)
- `helpers/error_handler.py` (6,556 lines) - Centralized error handling with structured reporting
- `helpers/waitlist_helpers.py` (31,520 lines) - Waitlist management and tournament overflow
- `helpers/role_helpers.py` (8,453 lines) - Discord role management and assignment
- `helpers/validation_helpers.py` (7,015 lines) - Data validation and permission checking
- `helpers/schedule_helpers.py` (4,354 lines) - Schedule management and time validation
- `helpers/embed_helpers.py` (5,199 lines) - Discord embed creation and formatting
- `helpers/sheet_helpers.py` (5,258 lines) - Google Sheets integration helpers
- `helpers/onboard_helpers.py` (12,827 lines) - User onboarding and approval workflow
- `helpers/config_manager.py` (3,642 lines) - Configuration loading and hot-reload
- `helpers/environment_helpers.py` (2,225 lines) - Environment-specific logic
- `helpers/__init__.py` (729 lines) - Helper package initialization

### Utilities (`utils/`)
- `utils/utils.py` (8,509 lines) - General utility functions and Discord member resolution
- `utils/logging_utils.py` (4,030 lines) - Secure logging with automatic token masking
- `utils/__init__.py` (609 lines) - Utility exports and imports

### Scripts (`scripts/`)
- `scripts/generate_snapshot.py` (9,208 lines) - Context snapshot generator for AI sessions
- `scripts/documentation_manager.py` (18,492 lines) - Unified documentation audit and fix tool

## Data Flow Architecture

### Unified Data Flow
```
Discord User/Dashboard → Event System → API Layer → Data Access Layer → Cache → Database → Response
         ↓                    ↓            ↓              ↓              ↓         ↓          ↓
    User Interaction → Event Bus → FastAPI → Repository Pattern → Multi-level → PostgreSQL → Real-time Update
```

### Legacy Bot Data Flow (Maintained)
```
Discord User Interaction → Slash Command → Business Logic → External APIs → Database → Discord Response
         ↓                      ↓               ↓              ↓            ↓              ↓
    User Input → Command Router → Helper Functions → API Calls → Persistence → Rich Embed/View
```

### Sheet Integration Flow
```
Config → Sheet Settings → Google Auth → Sheet Access → Cache Layer → DAL → Bot/API Operations
   ↓          ↓               ↓            ↓           ↓          ↓           ↓
YAML → Guild Config → OAuth2Client → gspread → asyncio Cache → Repository → Tournament Logic
```

### Event-Driven Updates
```
Data Change → Event Eission → Event Bus → Handlers → Subscribers → Dashboard Updates → Discord Notifications
     ↓             ↓              ↓           ↓           ↓              ↓                    ↓
  Database → Create Event → Prioritize → Business Logic → WebSocket → Real-time UI → Bot Messages
```

### Security Flow
```
Log Message → sanitize_log_message() → Pattern Detection → Token Masking → Safe Output
      ↓               ↓                     ↓              ↓              ↓
Original Text → Discord/API Detection → Regex Matching → Partial Preview → Log File
```

### API Authentication Flow
```
Dashboard Request → Master Password → JWT Token → API Validation → Database Access → Response
        ↓                ↓               ↓              ↓                ↓              ↓
   HTTP Request → Credentials Check → Token Generate → Bearer Verify → Permission Check → JSON Response
```

## Recent Changes (2025-10-11)

### Major Architecture Updates
- **Unified Data Flow**: Complete data flow architecture with centralized Data Access Layer
- **API Backend System**: FastAPI application with JWT authentication and WebSocket support
- **Event System**: Centralized event-driven architecture with prioritized handling
- **Data Models**: Comprehensive model layer with validation and business logic
- **Multi-level Caching**: Redis + Memory + Database caching for optimal performance
- **Real-time Updates**: WebSocket-based real-time dashboard updates

### Security Enhancements
- **JWT Authentication**: Master password-based API authentication with 24-hour tokens
- **Token Masking**: Comprehensive token masking and secure logging system
- **API Security**: Rate limiting, CORS configuration, and input validation
- **Access Control**: Role-based permissions and secure endpoint protection

### Performance Improvements
- **Connection Pooling**: Advanced database connection pooling with health checks
- **Caching Strategy**: Intelligent multi-level caching with automatic invalidation
- **Async Operations**: Full async/await support throughout the system
- **Batch Operations**: Optimized batch processing for database and sheet operations

### Legacy System Integration
- **Legacy Adapter**: Seamless integration with existing bot components
- **Backward Compatibility**: Full compatibility with existing commands and features
- **Gradual Migration**: Path for gradual migration from legacy systems
- **Data Consistency**: Maintained data consistency across old and new systems

### Code Quality Improvements
- **Fixed**: Syntax errors in `send_reminder_dms` function and other critical issues
- **Enhanced**: Async support throughout the codebase with proper error handling
- **Updated**: Factory AI agents integration and documentation system
- **Comprehensive Testing**: Unit tests, integration tests, and performance monitoring

### Live Graphics Dashboard 2.0 Implementation
- **Frontend Architecture**: Complete Next.js 14 + TypeScript + Tailwind + shadcn/ui implementation
- **Graphics Management**: Full CRUD operations for live broadcast graphics with canvas locking
- **Archive System**: Comprehensive archive and restore functionality with admin controls
- **Canvas Locking**: Real-time collaborative editing with 5-minute lock expiration and conflict prevention
- **Authentication Flow**: Master password-based authentication with JWT tokens and session management
- **Real-time Updates**: WebSocket integration for live dashboard updates and lock status
- **Database Schema**: SQLite database with models for graphics, canvas locks, archives, and authentication
- **API Integration**: Complete FastAPI backend with graphics CRUD, locking, and archive endpoints
- **UX Optimization**: Professional UI with clear action-oriented language and accessibility features

## Previous Changes (2025-06-17)

### Historical Updates
- **Security Enhancement**: Comprehensive token masking and secure logging system
- **Architecture**: Moved to bot-only operation (dashboard removed for focus)
- **Performance**: Enhanced sheet optimization with batch operations and caching
- **Error Handling**: Structured error reporting with unique IDs and user-friendly messages
- **Configuration**: Hot-reload capabilities with in-place updates
- **Improved**: Consistent error handling patterns across all modules

### Integration Enhancements
- **Added**: IGN verification system for player identity management
- **Enhanced**: Google Sheets integration with multi-source authentication
- **Optimized**: Sheet operations with batch processing and intelligent caching
- **Improved**: Riot API integration with proper rate limiting and error recovery

## Security Implementation

### Token Management System
```python
from utils.logging_utils import SecureLogger, mask_token

logger = SecureLogger(__name__)
logger.info("Bot started with token: abcdef...")  # Automatically masked

# Debug mode shows last 4 characters
logger.debug(f"Token preview: {mask_token(DISCORD_TOKEN, show_last=4)}")
```

### Error Handling with Security
```python
from helpers.error_handler import ErrorHandler

try:
    # Sensitive operations
    pass
except Exception as e:
    await ErrorHandler.handle_interaction_error(
        interaction, e, context="Registration", user_friendly=True
    )
```

## Cross-References
- `[API Integration](./api-integration.md)` - Data flow and API integration documentation
- `./flows_registration_checkin.md` - Registration and check-in workflows
- `./scheduling_logic.md` - Tournament scheduling system
- `./core-modules.md` - Core component documentation
- `./helper-modules.md` - Helper module documentation  
- `./integration-modules.md` - Integration module documentation
- `../sops/` - Standard operating procedures and runbooks

## Performance Metrics
- **Total Lines**: ~360,000 lines of code across 40+ modules (Python + TypeScript/React)
- **Dashboard Frontend**: 4,500+ lines of TypeScript/React code with Next.js 14
- **API Backend**: 2,500+ lines of Python with FastAPI and comprehensive graphics management
- **Database Models**: 8 SQLAlchemy models with relationships and indexing
- **Async Support**: Comprehensive async/await implementation across all systems
- **Cache Performance**: 10-minute cache cycles with thread-safe operations
- **Error Recovery**: Graceful degradation with user-friendly error messages
- **Security**: Zero exposed credentials in logs or error messages

---
**Module Count**: 40+ modules across 6 main directories (including dashboard/)  
**Documentation Status**: Complete and current with Live Graphics Dashboard 2.0  
**Security Status**: Enhanced with comprehensive token masking and JWT authentication  
**Last Reviewed**: 2025-10-11


## Security & Logging {#security--logging}

### Token Management
- **Secure Logging**: All tokens and API keys are automatically masked in logs
- **Environment Variables**: Sensitive variables are properly handled and not exposed
- **Error Handling**: Login failures provide useful information without exposing credentials
- **Debug Mode**: Token previews available in debug logs (last 4 characters only)

### Log Sanitization
- **Automatic Detection**: Discord tokens, API keys, and sensitive data patterns are detected
- **Pattern Matching**: Regular expression-based detection of token formats
- **Safe Logging**: All log messages are sanitized before output
- **Debug Support**: Masked information available for troubleshooting

### Implementation
```python
from utils.logging_utils import mask_token, sanitize_log_message

# Secure error handling
except discord.LoginFailure:
    logging.error("Failed to login - check your Discord token configuration")
    if DISCORD_TOKEN:
        logging.debug(f"Token preview: {mask_token(DISCORD_TOKEN)}")
```
