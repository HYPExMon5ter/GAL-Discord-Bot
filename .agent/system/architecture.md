---
id: system.architecture
version: 1.1
last_updated: 2025-10-10
tags: [system, architecture, updated]
---

# Architecture Overview

- **Bot**: Python (`discord.py`) with slash commands, embeds, and Discord Scheduled Events.
- **Data**: Database-first (SQLite for dev, Postgres-ready). Google Sheets becomes a **view**.
- **Architecture**: Bot-only operation (dashboard removed), focuses on Discord integration.
- **Docs**: `.agent` auto-maintained via Droid + Git hooks + CI audits.

## Module Organization (2025-10-10)

### Core Components
- `core/commands.py` - Slash command definitions and logic
- `core/components_traditional.py` - Traditional Discord components
- `core/views.py` - View classes and persistent views
- `core/config_ui.py` - Configuration UI components
- `core/persistence.py` - Data persistence layer
- `core/events.py` - Discord event handlers

### Integrations
- `integrations/sheets.py` - Google Sheets integration
- `integrations/riot_api.py` - Riot Games API integration
- `integrations/sheet_*.py` - Sheet optimization modules

### Utilities
- `utils/utils.py` - General utility functions
- `utils/__init__.py` - Utility exports and imports

### Helper Modules
- `helpers/` - Various helper modules for roles, validation, error handling, etc.

## Recent Changes (2025-10-10)
- **Architecture**: Moved to bot-only operation (dashboard removed)
- **Added**: IGN verification integration and comprehensive sheet optimization
- **Fixed**: Syntax errors, encoding issues, and import problems
- **Updated**: Factory AI agents integration and documentation system

See:
- `./data_flow.md`
- `./flows_registration_checkin.md`
- `./scheduling_logic.md`
- `./core-modules.md` - Core component documentation
- `./helper-modules.md` - Helper module documentation  
- `./integration-modules.md` - Integration module documentation
- `../sops/` runbooks


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
