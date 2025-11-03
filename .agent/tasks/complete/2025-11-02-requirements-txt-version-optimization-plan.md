## Requirements.txt Version Optimization Plan

Based on code analysis, I'll update requirements.txt to use the latest versions where safe, while keeping specific versions pinned where needed for compatibility.

### Analysis Summary

**Packages to Keep Pinned:**
1. **discord.py==2.6.3** - Core bot functionality uses Discord.py v2 features (modern intents, app_commands). Pin to ensure stability
2. **sqlalchemy==2.0.34** - Using SQLAlchemy 2.0 API patterns (create_engine, models). Keep pinned to 2.0.x range
3. **alembic==1.16.5** - Database migrations, should align with SQLAlchemy version
4. **fastapi==0.114.2** - API uses modern FastAPI patterns with Pydantic v2. Pin to 0.114.x range
5. **python-jose[cryptography]==3.5.0** - JWT auth, known compatibility issues with newer versions
6. **oauth2client==4.1.3** - Legacy Google library, deprecated (no updates expected)

**Packages to Update to Latest:**
- All utility libraries (colorama, tzdata, psutil, rapidfuzz)
- HTTP clients (aiohttp, requests, httpx)
- Testing tools (pytest, pytest-asyncio, coverage)
- Code quality tools (black, ruff, mypy)
- Google auth libraries (google-auth, google-auth-oauthlib, gspread)
- Configuration tools (pyyaml, ruamel.yaml, python-dotenv)
- Database drivers (psycopg2-binary)
- Security libraries (bcrypt, passlib, cryptography, PyJWT)
- Other dependencies (uvicorn, websockets, python-multipart, redis)

### Proposed requirements.txt Structure:
```python
# Discord Bot (pinned for stability)
discord.py==2.6.*
python-dotenv>=1.0

# Google Sheets Integration
gspread>=6.2
oauth2client==4.1.3  # Legacy, no updates
google-auth>=2.40
google-auth-oauthlib>=1.2

# Configuration
pyyaml>=6.0
ruamel.yaml>=0.18

# Database (pinned to 2.0.x for compatibility)
sqlalchemy~=2.0.34
alembic~=1.16.0
psycopg2-binary>=2.9

# API Framework (pinned for stability)
fastapi~=0.114.2
uvicorn[standard]>=0.30
websockets>=15.0
python-jose[cryptography]==3.5.0  # Known compatibility issues
python-multipart>=0.0.9
redis>=6.4

# HTTP Clients
aiohttp>=3.12
requests>=2.32
httpx>=0.27

# Authentication & Security
bcrypt>=4.3
passlib>=1.7
cryptography>=45.0
PyJWT>=2.10

# Utilities
rapidfuzz>=3.14
tzdata>=2025.2
colorama>=0.4
psutil>=7.1

# Testing
pytest>=8.4
pytest-asyncio>=0.25
coverage>=7.6

# Code Quality
black>=24.10
ruff>=0.8
mypy>=1.14
```

**Version Specifier Legend:**
- `==X.Y.Z` - Exact version pin (breaking changes expected)
- `==X.Y.*` - Pin minor version, allow patches
- `~=X.Y.Z` - Compatible release (~=2.0.34 allows 2.0.35+ but not 2.1.0)
- `>=X.Y` - Minimum version, allow all newer versions

This approach maximizes using latest versions while maintaining stability for critical dependencies.