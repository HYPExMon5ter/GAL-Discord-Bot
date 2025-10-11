---
id: system.architecture
version: 1.1
last_updated: 2025-10-10
tags: [system, architecture, updated]
---

# Architecture Overview

- **Bot**: Python (`discord.py`) with slash commands, embeds, and Discord Scheduled Events.
- **Data**: Database-first (SQLite for dev, Postgres-ready). Google Sheets becomes a **view**.
- **Dashboard**: Next.js + TypeScript + shadcn/ui + Tailwind (future), reads DB via API.
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
- `utils/renderer.py` - Rendering utilities (removed)
- `utils/__init__.py` - Utility exports and imports

### Helper Modules
- `helpers/` - Various helper modules for roles, validation, error handling, etc.

## Recent Changes
- **Fixed**: Syntax error in `send_reminder_dms` function
- **Removed**: Unused integrations (obs_integration, live_graphics_api, renderer)
- **Updated**: Module imports and exports
- **Improved**: Exception handling patterns

See:
- `./data_flow.md`
- `./flows_registration_checkin.md`
- `./scheduling_logic.md`
- `../sops/` runbooks
