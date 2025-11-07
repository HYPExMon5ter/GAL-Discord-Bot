---
id: system.core-modules
version: 1.2
last_updated: 2025-11-07
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

### `core/commands/`
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

### `core/components_traditional.py` (Updated 2025-11-06)
- **Purpose**: Traditional Discord components (buttons, modals, select menus)
- **Key Functions**:
  - Component state management
  - Traditional UI element handlers
  - UI component registration and lifecycle management
  - **Deprecated**: Removed `build_unified_embed()` function - use `build_unified_view()` instead
- **Dependencies**: discord.py components system
- **Recent Changes**: Removed deprecated `build_unified_embed()` function as it was unused and marked as DEPRECATED

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

### `core/persistence.py` (Updated 2025-11-06)
- **Purpose**: Data persistence layer and database operations
- **Key Functions**:
  - Database connection management
  - Data CRUD operations
  - Event mode management per guild
  - Guild data persistence and retrieval
  - Message persistence for cross-session tracking
  - Async compatibility functions
- **Dependencies**: SQLite/PostgreSQL, database drivers, storage_service
- **Integration Points**: All modules requiring data persistence
- **Recent Changes**: 
  - Removed legacy adapter integration code
  - Simplified async functions without unnecessary DAL layer
  - Fixed asyncio import issue

### `core/events/event_bus.py`
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

### `core/onboard.py` (Updated 2025-11-05)
- **Purpose**: User onboarding system and approval workflow
- **Key Functions**:
  - New user registration process
  - Approval workflow management with supporter role
  - Onboarding UI components
  - Role assignment for new users
  - Rejection DM functionality
- **Dependencies**: discord.py, persistence, helpers
- **Recent Changes**: Added supporter role support and rejection DM functionality

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


## Recent Command Module Updates

### utility

**Description**: Utility, help, and information commands.

**Key Functions**:

- `register(gal)`
  - Register utility commands with the GAL command group.

**Dependencies**:
- __future__.annotations, typing.Optional, discord.app_commands, config.EMBEDS_CFG, config.GAL_COMMAND_IDS, helpers.ConfigManager, common.command_tracer, common.ensure_staff, common.handle_command_exception, core.test_components.TestComponents

### placement

**Description**: Placement update commands.

**Key Functions**:

- `register(gal)`
  - Register placement commands with the GAL command group.

**Dependencies**:
- __future__.annotations, discord.app_commands, discord.ext.commands, integrations.lobby_manager.LobbyManager, integrations.riot_api.RiotAPI, common.command_tracer, common.ensure_staff, common.handle_command_exception, api.routers.websocket.send_placement_update, integrations.lobby_manager.LobbyManager

### registration

**Description**: Registration and roster management commands.

**Key Functions**:

- `register(gal)`
  - Attach registration commands to the GAL command group.

**Dependencies**:
- __future__.annotations, typing.List, typing.Optional, typing.Sequence, typing.Tuple, discord.app_commands, config._FULL_CFG, config.embed_from_cfg, config.get_checked_in_role, config.get_registered_role, config.get_unified_channel_name, core.components_traditional.update_unified_channel, core.persistence.get_event_mode_for_guild, core.persistence.persisted, core.persistence.save_persisted, helpers.EmbedHelper, integrations.sheets.refresh_sheet_cache, utils.utils.send_reminder_dms, common.command_tracer, common.ensure_staff, common.handle_command_exception, common.localized_choice, common.logger, common.respond_with_message, core.discord_events.recent_pings, core.persistence.set_event_mode_for_guild, integrations.sheets.cache_lock, integrations.sheets.sheet_cache, helpers.sheet_helpers.SheetOperations, core.views.WaitlistRegistrationDMView
