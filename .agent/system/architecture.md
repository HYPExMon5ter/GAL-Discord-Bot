---
id: system.architecture
version: 1.3
last_updated: 2025-06-17
tags: [system, architecture, updated, documentation-refresh]
---

# Architecture Overview

## System Philosophy
- **Bot**: Python (`discord.py`) with slash commands, embeds, and Discord Scheduled Events
- **Data**: Database-first (SQLite for dev, Postgres-ready). Google Sheets serves as a **view**
- **Architecture**: Bot-only operation (dashboard removed), focused on Discord integration
- **Security**: Comprehensive token masking and secure logging implementation
- **Documentation**: `.agent` auto-maintained via Droid + Git hooks + CI audits

## Module Organization (2025-06-17)

### Core Components (`core/`)
- `commands.py` (86,573 lines) - Slash command definitions and tournament management logic
- `components_traditional.py` (73,408 lines) - Traditional Discord components and UI elements
- `views.py` (51,100 lines) - View classes and persistent view management
- `config_ui.py` (36,243 lines) - Configuration UI components and settings management
- `persistence.py` (16,544 lines) - Data persistence layer and database operations
- `events.py` (29,619 lines) - Discord event handlers and bot lifecycle management
- `onboard.py` (23,126 lines) - User onboarding system and approval workflow
- `migration.py` (11,993 lines) - Database migration and schema management
- `test_components.py` (7,157 lines) - Testing framework for core components
- `__init__.py` (591 lines) - Core package initialization

### Integration Layer (`integrations/`)
- `sheets.py` (43,741 lines) - Google Sheets integration with caching and optimization
- `riot_api.py` (9,454 lines) - Riot Games API integration for player verification
- `sheet_integration.py` (18,846 lines) - Advanced sheet integration bridging systems
- `sheet_optimizer.py` (9,774 lines) - Performance optimization for sheet operations
- `sheet_detector.py` (12,627 lines) - Automatic sheet structure detection
- `sheet_base.py` (4,773 lines) - Base functionality for sheet operations
- `sheet_utils.py` (3,713 lines) - Utility functions for sheet operations
- `ign_verification.py` (4,522 lines) - IGN validation system
- `__init__.py` (764 lines) - Integration package initialization

### Helper System (`helpers/`)
- `error_handler.py` (6,556 lines) - Centralized error handling with structured reporting
- `waitlist_helpers.py` (31,520 lines) - Waitlist management and tournament overflow
- `role_helpers.py` (8,453 lines) - Discord role management and assignment
- `validation_helpers.py` (7,015 lines) - Data validation and permission checking
- `schedule_helpers.py` (4,354 lines) - Schedule management and time validation
- `embed_helpers.py` (5,199 lines) - Discord embed creation and formatting
- `sheet_helpers.py` (5,258 lines) - Google Sheets integration helpers
- `onboard_helpers.py` (12,827 lines) - User onboarding and approval workflow
- `config_manager.py` (3,642 lines) - Configuration loading and hot-reload
- `environment_helpers.py` (2,225 lines) - Environment-specific logic
- `__init__.py` (729 lines) - Helper package initialization

### Utilities (`utils/`)
- `utils.py` (8,509 lines) - General utility functions and Discord member resolution
- `logging_utils.py` (4,030 lines) - Secure logging with automatic token masking
- `__init__.py` (609 lines) - Utility exports and imports

### Scripts (`scripts/`)
- `generate_snapshot.py` (9,208 lines) - Context snapshot generator for AI sessions
- `update_system_docs.py` (6,566 lines) - System documentation update utilities
- `migrate_columns.py` (2,905 lines) - Column migration and database schema updates

## Data Flow Architecture

### Primary Data Flow
```
Discord User Interaction → Slash Command → Business Logic → External APIs → Database → Discord Response
         ↓                      ↓               ↓              ↓            ↓              ↓
    User Input → Command Router → Helper Functions → API Calls → Persistence → Rich Embed/View
```

### Sheet Integration Flow
```
Config → Sheet Settings → Google Auth → Sheet Access → Cache Layer → Bot Operations
   ↓          ↓               ↓            ↓           ↓            ↓
YAML → Guild Config → OAuth2Client → gspread → asyncio Cache → Tournament Logic
```

### Security Flow
```
Log Message → sanitize_log_message() → Pattern Detection → Token Masking → Safe Output
      ↓               ↓                     ↓              ↓              ↓
Original Text → Discord/API Detection → Regex Matching → Partial Preview → Log File
```

## Recent Changes (2025-06-17)

### Major Updates
- **Security Enhancement**: Comprehensive token masking and secure logging system
- **Architecture**: Moved to bot-only operation (dashboard removed for focus)
- **Performance**: Enhanced sheet optimization with batch operations and caching
- **Error Handling**: Structured error reporting with unique IDs and user-friendly messages
- **Configuration**: Hot-reload capabilities with in-place updates

### Code Quality Improvements
- **Fixed**: Syntax errors in `send_reminder_dms` function and other critical issues
- **Enhanced**: Async support throughout the codebase with proper error handling
- **Updated**: Factory AI agents integration and documentation system
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
- `./data_flow.md` - Detailed data flow diagrams
- `./flows_registration_checkin.md` - Registration and check-in workflows
- `./scheduling_logic.md` - Tournament scheduling system
- `./core-modules.md` - Core component documentation
- `./helper-modules.md` - Helper module documentation  
- `./integration-modules.md` - Integration module documentation
- `../sops/` - Standard operating procedures and runbooks

## Performance Metrics
- **Total Lines**: ~350,000 lines of Python code across 35 modules
- **Async Support**: Comprehensive async/await implementation
- **Cache Performance**: 10-minute cache cycles with thread-safe operations
- **Error Recovery**: Graceful degradation with user-friendly error messages
- **Security**: Zero exposed credentials in logs or error messages

---
**Module Count**: 35 modules across 5 main directories  
**Documentation Status**: Complete and current  
**Security Status**: Enhanced with comprehensive token masking  
**Last Reviewed**: 2025-06-17


## Security & Logging

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
