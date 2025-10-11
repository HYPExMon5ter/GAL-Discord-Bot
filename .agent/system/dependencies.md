---
id: system.dependencies
version: 1.1
last_updated: 2025-10-10
tags: [dependencies, audit-updated]
---

# Dependencies

## Core Dependencies
- Python 3.11+
- discord.py (Discord bot framework)
- python-dotenv (Environment configuration)

## Database & Storage
- sqlalchemy (ORM - retained for future use)
- alembic (Database migrations - retained)
- psycopg2-binary (PostgreSQL adapter)

## External Integrations
- gspread (Google Sheets API)
- oauth2client (Google authentication)
- rapidfuzz (Team name similarity matching)

## Web & API
- fastapi (Retained for potential future dashboard integration)
- uvicorn[standard] (ASGI server)
- websockets (WebSocket support)
- aiohttp (HTTP client)

## Utilities
- requests (HTTP requests)
- pyyaml & ruamel.yaml (YAML configuration)
- colorama (Terminal colors)
- redis (Caching - configured but optional)
- jinja2 (Template engine)
- tzdata (Timezone data)

## Removed Dependencies (2025-10-10)
- obs-websocket-client (Moved to requirements-dev)
- playwright (Moved to requirements-dev)
- Pillow (Image processing - unused)
- Several ML/AI packages (Unused bloat)

## Security Notes
- All dependencies are from trusted sources
- Regular security audits recommended
- Consider using dependency scanning tools
- Pin versions for production deployments
