---
id: system.core-modules
version: 1.1
last_updated: 2025-10-10
tags: [system, core, modules, documentation]
---

# Core Modules Documentation

## Overview
The `core/` directory contains the primary bot functionality including command handling, Discord components, persistence, and core business logic.

## Module Details

### `core/__init__.py`
- **Purpose**: Core package initialization and exports
- **Key Functions**: Module imports and package setup
- **Dependencies**: discord.py, internal core modules

### `core/commands.py`
- **Purpose**: Slash command definitions and tournament management logic (2,147 lines)
- **Key Functions**: 
  - Tournament registration and check-in commands
  - Team management (normal/double-up modes)
  - Role management commands
  - Schedule and event commands
  - DM reminder system with error handling
  - Member resolution and validation
- **Dependencies**: discord.py, persistence layer, helpers, integrations
- **Integration Points**: All bot functionality flows through commands
- **Recent Changes**: Fixed syntax errors in send_reminder_dms function

### `core/components_traditional.py`
- **Purpose**: Traditional Discord components (buttons, modals, select menus)
- **Key Functions**:
  - Component state management
  - Traditional UI element handlers
  - Legacy component support
- **Dependencies**: discord.py components system

### `core/views.py`
- **Purpose**: View classes and persistent view management
- **Key Functions**:
  - Discord view definitions
  - Persistent view registration
  - View state management
- **Dependencies**: discord.py views, persistence layer

### `core/config_ui.py`
- **Purpose**: Configuration UI components and management
- **Key Functions**:
  - Configuration modals and forms
  - Settings validation
  - UI state management
- **Dependencies**: discord.py, config management

### `core/persistence.py`
- **Purpose**: Data persistence layer and database operations
- **Key Functions**:
  - Database connection management
  - Data CRUD operations
  - Caching layer
  - Migration support
- **Dependencies**: SQLite/PostgreSQL, database drivers
- **Integration Points**: All modules requiring data persistence

### `core/events.py`
- **Purpose**: Discord event handlers and bot lifecycle management (639 lines)
- **Key Functions**:
  - Bot startup and shutdown
  - Member join/leave events
  - Reaction and interaction events
  - Event scheduling system with fuzzy matching
  - Scheduled event automation
  - Error handling and logging
- **Dependencies**: discord.py event system, rapidfuzz, zoneinfo
- **Recent Changes**: Enhanced event scheduling with timezone support

### `core/onboard.py`
- **Purpose**: User onboarding system and approval workflow
- **Key Functions**:
  - New user registration process
  - Approval workflow management
  - Onboarding UI components
  - Role assignment for new users
- **Dependencies**: discord.py, persistence, helpers

### `core/migration.py`
- **Purpose**: Database migration and schema management
- **Key Functions**:
  - Schema versioning
  - Migration scripts execution
  - Data transformation
  - Rollback capabilities
- **Dependencies**: Database drivers, persistence layer

### `core/test_components.py`
- **Purpose**: Testing framework for core components
- **Key Functions**:
  - Component testing utilities
  - Mock data generation
  - Test scenario management
- **Dependencies**: Testing frameworks, core modules

## Data Flow
```
Discord Events → Events Handler → Commands → Business Logic → Persistence → Database
     ↓                ↓              ↓           ↓            ↓         ↓
User Interactions → Event Routing → Command Processing → Helper Functions → Data Storage → Response
```

## Key Integration Points
- **Commands ↔ Helpers**: Business logic delegation
- **Persistence ↔ Database**: Data layer abstraction
- **Views ↔ Components**: UI element coordination
- **Events ↔ All Modules**: Event distribution system

## Recent Updates (2025-10-10)
- **Fixed**: Syntax errors and import issues
- **Improved**: Error handling patterns
- **Updated**: Configuration management
- **Added**: Enhanced onboarding workflow

---
**Module Count**: 10 core modules  
**Documentation Status**: Complete  
**Last Reviewed**: 2025-10-10
