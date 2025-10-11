---
id: system.dependencies
version: 1.3
last_updated: 2025-06-17
tags: [dependencies, security-enhanced, current]
---

# Dependencies and System Requirements

## Python Requirements
- **Python Version**: 3.11+ (required for modern discord.py features)
- **Platform**: Cross-platform (Windows, Linux, macOS)
- **Architecture**: x64 recommended for production

## Core Dependencies

### Discord Framework
- **discord.py** (2.4+) - Modern Discord bot framework with slash commands
  - Required for: Bot functionality, slash commands, components
  - Features: Async/await support, view persistence, application commands

### Configuration & Environment
- **python-dotenv** - Environment variable management
  - Required for: Loading .env files securely
  - Security: Supports token masking and secure config loading

### YAML Configuration
- **pyyaml** - YAML parsing and configuration management
- **ruamel.yaml** - Advanced YAML with comments preservation
  - Required for: config.yaml parsing and hot-reload functionality
  - Features: Round-trip preservation, schema validation

## Database & Storage Layer

### ORM & Migrations (Retained for Future Use)
- **sqlalchemy** - Object-relational mapping (PostgreSQL-ready)
- **alembic** - Database migration management
  - Status: Configured but not actively used (currently SQLite)
  - Purpose: Future migration to PostgreSQL

### Database Drivers
- **psycopg2-binary** - PostgreSQL adapter
  - Status: Available for production PostgreSQL deployment
  - Purpose: High-performance database connectivity

## External Integrations

### Google Sheets Integration
- **gspread** - Google Sheets API client
  - Required for: Tournament data synchronization
  - Features: Async support, batch operations, caching

- **oauth2client** - Google OAuth2 authentication
  - Required for: Google API authentication
  - Security: Multi-source authentication (file + environment)

### Riot Games API
- **aiohttp** - Async HTTP client for API calls
  - Required for: Riot API integration, player verification
  - Features: Rate limiting, connection pooling, async support

## Data Processing & Utilities

### Text Processing
- **rapidfuzz** - Fast fuzzy string matching
  - Required for: Team name similarity matching
  - Performance: Optimized for real-time matching

### Time & Timezone
- **tzdata** - IANA timezone database
  - Required for: Discord scheduled events, timezone handling
  - Features: Comprehensive timezone support

### Terminal & Logging
- **colorama** - Cross-platform colored terminal text
  - Required for: Enhanced console logging
  - Features: Windows compatibility, colored output

## Web & API Framework (Retained)

### FastAPI Stack
- **fastapi** - Modern web framework (retained for future use)
- **uvicorn[standard]** - ASGI server with WebSocket support
- **websockets** - WebSocket protocol implementation
- **jinja2** - Template engine for web interfaces
  - Status: Available but not actively used
  - Purpose: Potential future dashboard reintegration

### HTTP Client
- **requests** - Synchronous HTTP client
  - Required for: Legacy API calls, external integrations
  - Features: Session management, retry logic

## Optional Components

### Caching
- **redis** - In-memory data structure store
  - Status: Configured but optional
  - Purpose: Enhanced caching for high-load scenarios
  - Current: File-based caching primarily used

## Security & Performance

### Security Features
- **All dependencies**: From trusted PyPI sources
- **Token masking**: Implemented via custom logging utilities
- **Environment isolation**: Proper .env file handling
- **API authentication**: Secure OAuth2 and token management

### Performance Optimizations
- **Async/await**: Comprehensive async implementation
- **Caching**: Google Sheets 10-minute cache with thread safety
- **Batch operations**: Optimized sheet API calls
- **Connection pooling**: HTTP client optimization

## Dependency Management

### Version Pinning Strategy
- **Production**: Pin specific versions for stability
- **Development**: Allow patch updates for security
- **Security updates**: Regular audit and update cycle

### Removed Dependencies (2025-10-10)
- **obs-websocket-client**: Moved to development requirements
- **playwright**: Browser automation (unused)
- **Pillow**: Image processing (not required for bot-only operation)
- **ML/AI packages**: chromadb, langchain, and related bloat removed

## Installation Requirements

### Development Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Production Deployment
- **Environment variables**: Securely configured
- **Database**: PostgreSQL recommended for production
- **Monitoring**: Application logging and health checks
- **Security**: Regular dependency scanning

## System Resources

### Minimum Requirements
- **RAM**: 512MB (1GB recommended)
- **Storage**: 100MB for dependencies + logs
- **CPU**: Single core sufficient (async I/O bound)

### Recommended Production
- **RAM**: 2GB for larger tournaments
- **Storage**: 1GB for logs and cache
- **CPU**: 2+ cores for concurrent operations
- **Network**: Stable internet connection for API calls

## Security Auditing

### Regular Checks
- **Dependency scanning**: Use safety or similar tools
- **Vulnerability monitoring**: GitHub Dependabot or similar
- **Version updates**: Monthly security patch cycle
- **Code review**: Regular security audit of integration points

### Best Practices
- **Pin versions**: Exact versions for production
- **Review updates**: Check changelogs before updates
- **Test thoroughly**: Full integration testing for updates
- **Monitor security**: Subscribe to security advisories

---
**Total Dependencies**: 18 active dependencies  
**Security Status**: Enhanced with comprehensive token masking  
**Last Updated**: 2025-06-17  
**Next Audit**: Recommended monthly
