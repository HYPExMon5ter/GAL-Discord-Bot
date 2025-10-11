---
id: system.helper-modules
version: 1.3
last_updated: 2025-06-17
tags: [system, helpers, modules, documentation]
---

# Helper Modules Documentation

## Overview
The `helpers/` and `utils/` directories contain utility modules that provide specialized functionality for the GAL Discord Bot, including error handling, validation, configuration management, and security features.

## Utils Modules

### `utils/utils.py`
- **Purpose**: General utility functions and Discord member resolution (8,509 lines)
- **Key Functions**:
  - `resolve_member()` - Find Discord members by tag, name, or display name
  - `hyperlink_lolchess_profile()` - Create League of Legends profile hyperlinks
  - Member resolution with multiple fallback strategies
- **Dependencies**: discord.py, aiohttp, config system
- **Used By**: Core modules for member resolution and external profile linking

### `utils/logging_utils.py`
- **Purpose**: Secure logging with automatic token masking and sanitization (4,030 lines)
- **Key Functions**:
  - `mask_token()` - Mask sensitive tokens with configurable preview
  - `mask_discord_tokens()` - Detect and mask Discord bot tokens specifically
  - `mask_api_keys()` - Mask various API keys (Riot, Google, etc.)
  - `sanitize_log_message()` - Comprehensive log sanitization
  - `SecureLogger` - Logger wrapper with automatic sanitization
- **Security Features**:
  - Automatic Discord token pattern detection
  - Environment variable value masking
  - Configurable preview length for debugging
  - Protection against credential exposure in logs
- **Dependencies**: re, typing (no external dependencies)
- **Used By**: All modules for secure logging practices

## Helper Modules (helpers/)

### `helpers/error_handler.py`
- **Purpose**: Centralized error handling for Discord interactions (6,556 lines)
- **Key Functions**:
  - `handle_interaction_error()` - Handle command errors with logging and user feedback
  - Error ID tracking for debugging
  - Structured error reporting to Discord channels
  - Traceback logging with user-friendly messages
- **Dependencies**: discord.py, config system
- **Used By**: Core commands and interaction handlers

### `helpers/config_manager.py`
- **Purpose**: Configuration loading, reloading, and management (3,642 lines)
- **Key Functions**:
  - `reload_config()` - Hot-reload configuration from YAML files
  - `get_rich_presence()` - Rich presence configuration management
  - In-place configuration updates without restart
  - Configuration validation and error handling
- **Dependencies**: discord.py, yaml
- **Used By**: Bot initialization and runtime configuration

### `helpers/validation_helpers.py`
- **Purpose**: Data validation and permission checking (7,015 lines)
- **Key Functions**:
  - `validate_registration_capacity()` - Check tournament capacity limits
  - `validate_staff_permission()` - Staff role validation
  - `validate_and_respond()` - Async validation with Discord responses
- **Dependencies**: discord.py, persistence layer
- **Used By**: Registration commands and permission checks

### `helpers/role_helpers.py`
- **Purpose**: Discord role management and assignment (8,453 lines)
- **Key Functions**:
  - Role assignment based on registration status
  - Role cleanup and management
  - Role hierarchy validation
- **Dependencies**: discord.py, persistence layer
- **Used By**: Registration and tournament management

### `helpers/schedule_helpers.py`
- **Purpose**: Schedule management and time validation (4,354 lines)
- **Key Functions**:
  - `validate_schedule_times()` - Registration and check-in time validation
  - Schedule conflict detection
  - Time-based access control
- **Dependencies**: datetime, timezone handling
- **Used By**: Tournament scheduling commands

### `helpers/embed_helpers.py`
- **Purpose**: Discord embed creation and formatting (5,199 lines)
- **Key Functions**:
  - Standardized embed creation
  - Embed template management
  - Rich message formatting
- **Dependencies**: discord.py, config system
- **Used By**: All Discord message formatting

### `helpers/sheet_helpers.py`
- **Purpose**: Google Sheets integration helpers (5,258 lines)
- **Key Functions**:
  - Sheet operation helpers
  - Data formatting for sheets
  - Sheet validation utilities
- **Dependencies**: gspread, sheet integration modules
- **Used By**: Sheet data operations

### `helpers/waitlist_helpers.py`
- **Purpose**: Waitlist management and tournament overflow handling (31,520 lines)
- **Key Classes**:
  - `WaitlistError` - Custom waitlist exceptions
  - `WaitlistManager` - Waitlist operations and management
- **Dependencies**: persistence layer, validation helpers
- **Used By**: Tournament registration overflow management

### `helpers/onboard_helpers.py`
- **Purpose**: User onboarding and approval workflow (12,827 lines)
- **Key Classes**:
  - `OnboardManager` - New user registration and approval
- **Dependencies**: discord.py, persistence, validation
- **Used By**: User onboarding system

### `helpers/environment_helpers.py`
- **Purpose**: Environment-specific logic and validation (2,225 lines)
- **Key Functions**:
  - `validate_environment()` - Environment configuration validation
- **Dependencies**: os, environment variables
- **Used By**: Bot initialization and environment setup

## Security Features

### Token Management
- **Automatic Masking**: All tokens masked in logs with configurable preview
- **Pattern Detection**: Discord tokens, API keys detected via regex
- **Environment Protection**: Environment variable values automatically masked
- **Debug Support**: Safe token previews (last 4 characters only)

### Error Handling
- **Structured Logging**: Consistent error format with unique IDs
- **User Feedback**: Friendly error messages without exposing internals
- **Traceback Protection**: Sensitive data filtered from tracebacks
- **Channel Integration**: Error reporting to Discord channels

### Data Validation
- **Input Sanitization**: User inputs validated before processing
- **Permission Checks**: Role-based access control
- **Capacity Limits**: Tournament size validation
- **Schedule Validation**: Time-based access control

## Integration Patterns

### Error Handling Flow
```
Discord Interaction → Command Handler → Error Catch → ErrorHandler → Log + User Response
     ↓                ↓              ↓            ↓              ↓
User Action → Business Logic → Exception → Structured Error → Sanitized Message
```

### Configuration Management
```
YAML File → ConfigManager → Validation → In-memory Cache → Module Access
     ↓              ↓            ↓           ↓              ↓
config.yaml → Load/Reload → Schema Check → _FULL_CFG → Bot Modules
```

### Security Flow
```
Log Message → sanitize_log_message() → Pattern Detection → Token Masking → Safe Output
      ↓               ↓                     ↓              ↓              ↓
Original Text → Discord/API Detection → Regex Matching → Partial Preview → Log File
```

## Recent Updates (2025-06-17)
- **Added**: Comprehensive logging sanitization with `SecureLogger`
- **Enhanced**: Error handling with structured reporting and unique IDs
- **Improved**: Configuration management with hot-reload capabilities
- **Updated**: All helper modules with consistent error handling patterns
- **Security**: Automatic token masking in all log outputs
- **Documentation**: Updated line counts and module descriptions to match current codebase

## Usage Examples

### Secure Logging
```python
from utils.logging_utils import SecureLogger, sanitize_log_message

logger = SecureLogger(__name__)
logger.info("Bot started with token: abcdef...")  # Automatically masked
```

### Error Handling
```python
from helpers.error_handler import ErrorHandler

try:
    # Command logic
    pass
except Exception as e:
    await ErrorHandler.handle_interaction_error(
        interaction, e, context="Registration"
    )
```

### Configuration Management
```python
from helpers.config_manager import ConfigManager

# Hot reload configuration
success = ConfigManager.reload_config()
if success:
    await interaction.response.send_message("Configuration reloaded!")
```

---
**Module Count**: 12 helper/utility modules  
**Documentation Status**: Complete  
**Last Reviewed**: 2025-06-17
