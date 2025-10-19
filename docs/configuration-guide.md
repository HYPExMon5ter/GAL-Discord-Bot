# Configuration Guide

This guide provides comprehensive documentation for configuring the Guardian Angel League Discord Bot and Live Graphics Dashboard system.

## Overview

The GAL system uses multiple configuration mechanisms to manage different aspects of the application:

- **config.yaml**: Main bot configuration (channels, roles, tournament settings)
- **Environment Variables**: API and dashboard configuration
- **Google Sheets Integration**: Tournament data management
- **Database Configuration**: Data persistence settings
- **Security Configuration**: Authentication and access control

## Configuration File Structure

### Main Configuration (config.yaml)

The primary configuration file contains settings for bot behavior, channels, roles, and tournament management.

#### Channels Configuration
```yaml
# Discord channel configuration
channels:
  # Tournament-related channels
  unified_channel: 🎫tourney-registration  # Main tournament registration channel
  log_channel: bot-log                     # Bot logging channel
```

**Options:**
- `unified_channel`: Channel name for tournament registration
- `log_channel`: Channel for bot logging messages

#### Onboarding System Configuration
```yaml
onboard:
  # Channel settings
  main_channel: welcome                    # Welcome channel for new users
  review_channel: onboard-review           # Staff review channel for applications
  
  # Role settings
  role_on_approve: Angels                  # Role granted after approval
  
  # Embed configurations for onboarding flow
  embeds:
    main:
      title: 🌸 Welcome to Guardian Angel League!
      description: We're an inclusive community focused on creating a safe space for everyone.
      footer: Thank you for being here 💜
      color: '#f8c8dc'
    review:
      title: 📝 New Onboarding Submission
      footer: Staff Review Required
      color: '#3498db'
```

**Configuration Options:**
- `main_channel`: Channel for welcome messages
- `review_channel`: Staff review channel
- `role_on_approve`: Role assigned upon approval
- `embeds`: Customizable message templates

#### Discord Role Configuration
```yaml
roles:
  # Roles allowed to use bot commands
  allowed_roles:
    - Admin
    - Moderator  
    - GAL Helper
  
  # Tournament-specific roles
  registered_role: Registered              # Users who have registered for tournament
  checked_in_role: Checked In              # Users who have checked in for tournament
  angel_role: Angels                       # Approved community members
  
  # Notification settings
  ping_on_registration_open: true          # Ping when registration opens
  ping_on_checkin_open: true               # Ping when check-in opens
```

**Configuration Options:**
- `allowed_roles`: List of roles with bot access
- `registered_role`: Role for registered users
- `checked_in_role`: Role for checked-in users
- `angel_role`: Community member role
- `ping_*`: Enable/disable automatic notifications

#### Tournament Settings
```yaml
# Tournament settings
tournament:
  current_name: Curse of the Carousel      # Current tournament name
```

#### Google Sheets Configuration
See `config.yaml` for sheet configuration. Each mode (normal, doubleup) requires:
- `sheet_url_prod`: Production Google Sheet URL
- `sheet_url_dev`: Development Google Sheet URL  
- `header_line_num`: Row number for headers
- `max_players`: Maximum participants

See `integrations/sheets.py` for sheet integration implementation.

**Configuration Options:**
- `sheet_url_prod`: Production Google Sheet URL
- `sheet_url_dev`: Development Google Sheet URL
- `header_line_num`: Row number for headers
- `max_players`: Maximum participants per tournament type

#### Bot Presence Settings
```yaml
# Bot presence settings
rich_presence:
  type: PLAYING                            # Discord activity type
  message: 🛡️ TFT                          # Status message displayed on Discord
```

**Configuration Options:**
- `type`: Discord activity type (PLAYING, WATCHING, LISTENING, etc.)
- `message`: Status message to display

#### Bot Performance Settings
```yaml
# Bot performance settings
cache_refresh_seconds: 600                 # Cache refresh interval in seconds (10 minutes)
```

**Configuration Options:**
- `cache_refresh_seconds`: Interval for data refresh

### Live Graphics Dashboard Configuration

#### Environment Variables (.env.local)
See `.env.local` for local development overrides. Key variables:
- `DEV_GUILD_ID`: Development Discord server ID (see `config.py`)
- `DATABASE_URL`: Override database for testing (see `api/dependencies.py`)
- `NEXT_PUBLIC_API_URL`: Frontend API URL (see `dashboard/lib/api.ts`)

See `config.py` for environment variable loading logic.

**Environment Variables:**
- `DEV_GUILD_ID`: Development Discord server ID
- `DATABASE_URL`: Database connection string
- `NEXT_PUBLIC_API_URL`: Frontend API URL

#### Dashboard Configuration (config)
```yaml
# Live Graphics Dashboard configuration
dashboard:
  auto_start: true                         # Automatically start dashboard with bot
  api_port: 8000                          # Backend API port
  frontend_port: 3000                      # Frontend development server port
  health_check_interval: 30                # Health check interval in seconds
  max_startup_attempts: 3                  # Maximum attempts to start services
```

**Configuration Options:**
- `auto_start`: Start dashboard automatically
- `api_port`: Backend API service port
- `frontend_port`: Frontend development server port
- `health_check_interval`: Service health check interval
- `max_startup_attempts`: Maximum startup retry attempts

#### IGN Verification Configuration
```yaml
# IGN Verification configuration
ign_verification:
  enabled: true                            # Enable IGN verification during registration
  rate_limit: 100                          # Requests per minute
  cache_ttl: 3600                          # Cache time-to-live in seconds (1 hour)
  timeout: 10                              # Request timeout in seconds
```

**Configuration Options:**
- `enabled`: Enable/disable IGN verification
- `rate_limit`: API rate limit (requests per minute)
- `cache_ttl`: Cache expiration time
- `timeout`: API request timeout

## API Backend Configuration

### FastAPI Configuration
```python
# api/main.py
app = FastAPI(
    title="GAL Dashboard API",
    description="API for Guardian Angel League Dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Database Configuration
```python
# Dependencies - Standardized dashboard directory database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard/dashboard.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database models
Base = declarative_base()

# Database Standardization Notes:
# - All operations use dashboard/dashboard.db for consistency
# - Automatic creation if database file doesn't exist
# - Unified storage service with PostgreSQL primary + SQLite fallback
# - Thread-safe concurrent access with connection pooling
```

### Authentication Configuration
Authentication settings are configured via environment variables:
- `SECRET_KEY`: JWT secret key (see `api/auth.py`)
- `DASHBOARD_MASTER_PASSWORD`: Dashboard access password (see `api/auth.py`)
- Token expiration and algorithm settings in `api/auth.py`

See `api/auth.py` for complete authentication implementation.

## Database Configuration

### Database Location Standardization

The GAL system implements standardized database location management to ensure consistency across all components:

#### Standard Location
- **Path**: `dashboard/dashboard.db` (relative to project root)
- **Purpose**: Single database file for all bot, dashboard, and API operations
- **Benefits**: Simplified backups, debugging, and data management

#### Automatic Resolution
The system automatically resolves database paths to ensure all components use the same location:

```python
# In api/dependencies.py - automatic dashboard directory resolution
if not os.getenv("DATABASE_URL"):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dashboard_db_path = os.path.join(project_root, "dashboard", "dashboard.db")
    DATABASE_URL = f"sqlite:///{dashboard_db_path}"
```

### SQLite Configuration (Development)
```python
# Development SQLite database - standardized to dashboard directory
DATABASE_URL = "sqlite:///./dashboard/dashboard.db"

# Features:
# - Automatic creation if file doesn't exist
# - Thread-safe operations with connection pooling
# - WAL mode for better concurrent access
# - Regular vacuum operations for optimization
```

### PostgreSQL Configuration (Production)
Production PostgreSQL database configuration should be set via `DATABASE_URL` environment variable. The system supports:
- Connection pooling for performance (see `api/dependencies.py`)
- Automatic failover to SQLite fallback (see `core/storage_service.py`)
- Health monitoring and recovery (see `core/data_access/connection_manager.py`)
- Backup and replication support (see `core/storage_service.py`)

### Unified Storage Service

The system includes a unified storage service (`core/storage_service.py`) that provides:

#### Primary/Backup Architecture
```python
from core.storage_service import get_storage_service

storage = get_storage_service()

# Check storage status
status = storage.get_storage_status()
# Returns: {
#   "postgres_available": True,
#   "sqlite_fallback": True,
#   "persisted_views_count": 42,
#   "waitlist_data_count": 8
# }
```

#### Automatic Failover
- **Primary**: PostgreSQL (if configured and available)
- **Fallback**: SQLite (always available)
- **Seamless Transition**: No service interruption during failover
- **Data Recovery**: Automatic sync when primary service restored

#### Thread Safety
- **Connection Pooling**: Efficient database connection management
- **Lock Management**: Thread-safe concurrent operations
- **Transaction Safety**: ACID compliance with proper rollback
- **Performance Optimization**: Connection reuse and caching

### Connection Pool Configuration
```python
# Connection pool settings
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

## Security Configuration

### Authentication Settings
Authentication is configured via environment variables:
- `SECRET_KEY`: JWT secret key (see `api/auth.py`)
- `DASHBOARD_MASTER_PASSWORD`: Dashboard access password (see `api/auth.py`)
- Token expiration and algorithm settings in `api/auth.py`

**Security Best Practices:**
1. Use strong, randomly generated secrets
2. Store secrets in environment variables, not in code
3. Rotate secrets regularly
4. Use separate secrets for development and production

### CORS Configuration
CORS is configured in `api/main.py` with:
- Allowed origins for development and production
- Credential support for authenticated requests
- HTTP methods and headers configuration
- See `api/main.py` for specific CORS settings

### Rate Limiting Configuration
Rate limiting is configured in the API middleware with:
- Requests per minute limits
- Time window configuration
- See `api/main.py` and `integrations/ign_verification.py` for implementation

## Environment Variable Configuration

### .env (Base Configuration)
See `.env` file for base configuration. Key variable categories:
- Discord configuration (bot token, client ID, guild ID)
- Google Sheets service account path
- Riot API key
- Database connection string
- Dashboard authentication settings
- API server configuration

See `config.py` for environment variable loading and validation.

### .env.local (Local Development Overrides)
See `.env.local` for development-specific overrides:
- Development Discord server ID
- Test database configuration
- Local API endpoints
- Debug flags

See `config.py` for how local overrides are applied.

### Production Environment Variables
Production environment variables should be set via your hosting platform:
- PostgreSQL database connection string
- Production dashboard password
- Production JWT secret
- Production API keys
- Production service account credentials

See `services/dashboard_manager.py` for production-specific configuration handling.

## Integration Configuration

### Google Sheets Integration
Google Sheets integration uses service account authentication. Configuration is handled via:
- Service account JSON file (see `integrations/sheets.py`)
- Environment variables for credentials (see `.env`)
- Sheet URL configuration in `config.yaml`

See `integrations/sheets.py` and `integrations/sheet_base.py` for implementation details.

### Riot API Configuration
Riot API integration is configured via:
- `RIOT_API_KEY`: API key from Riot Developer Portal (see `.env`)
- Rate limiting and timeout settings (see `integrations/ign_verification.py`)
- Regional endpoint configuration

See `integrations/ign_verification.py` for IGN verification implementation.

### WebSocket Configuration
WebSocket settings are configured for real-time features:
- Host and port configuration
- Connection limits
- Rate limiting for messages
- See API configuration files for WebSocket implementation details

## Configuration Validation

### Configuration Schema
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class BotConfig(BaseModel):
    channels: dict = Field(...)
    onboard: dict = Field(...)
    roles: dict = Field(...)
    tournament: dict = Field(...)
    sheet_configuration: dict = Field(...)
    rich_presence: dict = Field(...)
    cache_refresh_seconds: int = Field(default=600)

class DashboardConfig(BaseModel):
    auto_start: bool = Field(default=True)
    api_port: int = Field(default=8000)
    frontend_port: int = Field(default=3000)
    health_check_interval: int = Field(default=30)
    max_startup_attempts: int = Field(default=3)
```

### Configuration Validation Function
```python
def validate_config(config_path: str) -> bool:
    """Validate configuration file structure and values."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = ['channels', 'onboard', 'roles', 'tournament']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate channel names
        if 'unified_channel' not in config['channels']:
            raise ValueError("Missing unified_channel configuration")
        
        # Validate role names
        allowed_roles = config['roles'].get('allowed_roles', [])
        if not allowed_roles:
            raise ValueError("No allowed_roles configured")
        
        return True
    
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False
```

## Configuration Management

### Loading Configuration
```python
import yaml
from pathlib import Path

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")
```

### Configuration Reloading
```python
def reload_config():
    """Reload configuration and update running services."""
    global config
    config = load_config()
    
    # Update bot settings
    update_bot_settings()
    
    # Update database connections
    update_database_connections()
    
    # Update API settings
    update_api_settings()
```

### Configuration Backup
```python
import shutil
from datetime import datetime

def backup_config(config_path: str):
    """Create a backup of the current configuration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{config_path}.backup_{timestamp}"
    
    shutil.copy2(config_path, backup_path)
    print(f"Configuration backed up to: {backup_path}")
    
    return backup_path
```

## Common Configuration Issues and Solutions

### Issue 1: Channel Not Found
**Error**: `Channel not found: channel_name`

**Solution**: 
1. Verify channel exists in Discord server
2. Check channel name spelling in config.yaml
3. Ensure bot has proper permissions
4. Update channel name if it was renamed

### Issue 2: Authentication Failed
**Error**: `Authentication failed` or `Invalid credentials`

**Solution**:
1. Verify bot token is valid and not expired
2. Check bot has correct scopes in Discord Developer Portal
3. Ensure bot is invited to the server with proper permissions
4. Refresh token if needed

### Issue 3: Database Connection Issues
**Error**: `Unable to connect to database`

**Solution**:
1. Verify database URL is correct
2. Check database service is running
3. Verify credentials and permissions
4. Check network connectivity
5. Update connection pool settings

### Issue 4: Google Sheets Access Issues
**Error**: `Google Sheets authentication failed`

**Solution**:
1. Verify service account JSON file is valid
2. Check sharing permissions on Google Sheet
3. Ensure service account email has edit access
4. Verify API quotas haven't been exceeded

### Issue 5: Rate Limiting Issues
**Error**: `Rate limit exceeded`

**Solution**:
1. Monitor API usage and implement proper rate limiting
2. Configure appropriate timeout settings
3. Implement retry logic with exponential backoff
4. Monitor API quota usage

### Issue 6: Database Location Confusion
**Error**: `Database file not found` or `Wrong database file being used`

**Solution**:
1. **Verify Standardized Location**: Ensure database is in `dashboard/dashboard.db`
   ```bash
   # Check if database exists in correct location
   ls -la dashboard/dashboard.db
   ```
2. **Update Configuration**: Ensure DATABASE_URL points to standardized location
   ```bash
   # Check environment variable
   echo $DATABASE_URL
   # Should output: sqlite:///./dashboard/dashboard.db
   ```
3. **Migrate Existing Data**: If using old database location
   ```python
   # Check storage service status
   from core.storage_service import get_storage_service
   storage = get_storage_service()
   status = storage.get_storage_status()
   print(status)
   ```
4. **Verify All Components**: Ensure bot, dashboard, and API use same database
   - Check bot logs for database connection messages
   - Verify dashboard API can access database
   - Confirm all database operations use same file

### Issue 7: Discord Username Not Stored in Google Sheets
**Error**: `Discord username missing from registration data`

**Solution**:
1. **Check Configuration**: Verify Discord username storage is enabled
   ```yaml
   registration:
     discord_username_storage: true
     discord_username_column: B
   ```
2. **Verify Sheet Column Mapping**: Ensure column B exists and is properly formatted
   ```python
   # Test Discord username column detection
   from integrations.sheet_detector import detect_discord_column
   column = detect_discord_column()
   print(f"Discord username column: {column}")
   ```
3. **Check Sheet Permissions**: Ensure bot has write access to Google Sheets
4. **Validate Data Format**: Ensure Discord usernames are in correct format (user#discriminator)
5. **Review Registration Logs**: Check for errors during registration process
   ```bash
   # Search for Discord username related errors
   grep -i "discord.*username\|registration.*error" gal_bot.log
   ```

### Issue 8: Registration API Fallback Not Working
**Error**: `Registration fails when external APIs are unavailable`

**Solution**:
1. **Check Fallback Configuration**: Verify fallback logic is enabled
   ```yaml
   registration:
     api_fallback_enabled: true
     allow_registration_on_api_failure: true
     show_fallback_messages: true
   ```
2. **Test API Connectivity**: Check if external APIs are accessible
   ```bash
   # Test dashboard API health
   curl -f http://localhost:8000/api/v1/ign-verification/health || echo "API unavailable - fallback should activate"
   
   # Test IGN verification endpoint
   curl -X POST http://localhost:8000/api/v1/ign-verification/verify \
     -H "Content-Type: application/json" \
     -d '{"ign": "testign", "region": "na"}' || echo "Verification API unavailable"
   ```
3. **Verify Timeout Settings**: Ensure timeouts are configured appropriately
   ```bash
   # Check timeout configuration
   grep -A 3 "api_timeout\|timeout" config.yaml
   echo $IGN_VERIFICATION_TIMEOUT
   ```
4. **Monitor Fallback Activation**: Check logs for fallback activation
   ```bash
   # Search for fallback activation logs
   grep -i "fallback\|api.*fail\|registration.*fallback" gal_bot.log
   ```
5. **Test Registration Process**: Manually test registration with API disabled
   - Stop dashboard API service
   - Attempt registration via Discord
   - Verify registration succeeds with fallback message
   - Check Google Sheets for registration data

### Issue 9: Storage Service Failover Problems
**Error**: `Storage service unavailable` or `Database fallback not working`

**Solution**:
1. **Check Storage Service Status**: Verify service health and configuration
   ```python
   # Check storage service status
   from core.storage_service import get_storage_service
   storage = get_storage_service()
   status = storage.get_storage_status()
   print(f"PostgreSQL available: {status['postgres_available']}")
   print(f"SQLite fallback: {status['sqlite_fallback']}")
   ```
2. **Verify Database Connections**: Test both PostgreSQL and SQLite connections
   ```python
   # Test database operations
   try:
       data = storage.get_persisted_views()
       print(f"Successfully retrieved {len(data)} records")
   except Exception as e:
       print(f"Storage service error: {e}")
   ```
3. **Check Database Paths**: Ensure SQLite fallback database is accessible
   ```bash
   # Verify SQLite database exists and is writable
   ls -la storage/fallback.db
   sqlite3 storage/fallback.db ".tables"
   ```
4. **Monitor Failover Events**: Check logs for automatic failover
   ```bash
   # Search for failover related logs
   grep -i "failover\|fallback.*storage\|postgres.*unavailable" gal_bot.log
   ```

### Issue 10: Pending Registrations Not Processing
**Error**: `Pending registrations stuck in queue`

**Solution**:
1. **Check Pending Registrations**: Review queued registration data
   ```python
   # Check for pending registrations
   from core.storage_service import get_storage_service
   storage = get_storage_service()
   pending = storage.get_data("pending_registrations", "all")
   print(f"Pending registrations: {len(pending)}")
   ```
2. **Verify Automatic Retry Settings**: Ensure retry logic is configured
   ```yaml
   registration:
     automatic_retry_pending: true
     store_pending_registrations: true
     max_retries: 3
   ```
3. **Manual Retry Processing**: Manually process stuck registrations
   ```python
   # Trigger manual processing of pending registrations
   from integrations.registration_processor import process_pending_registrations
   results = process_pending_registrations()
   print(f"Processed {results['processed']} registrations")
   ```
4. **Check API Availability**: Verify required APIs are accessible for retry
   ```bash
   # Test all required API endpoints
   curl -f http://localhost:8000/api/v1/ign-verification/health
   curl -f http://localhost:8000/api/v1/tournaments/health
   ```

## Troubleshooting Tools and Commands

### Database Troubleshooting
```bash
# Check database location and size
ls -lh dashboard/dashboard.db
sqlite3 dashboard/dashboard.db ".schema"

# Verify database connectivity
python -c "
from api.dependencies import SessionLocal
db = SessionLocal()
print('Database connection successful')
db.close()
"

# Check storage service status
python -c "
from core.storage_service import get_storage_service
storage = get_storage_service()
print(storage.get_storage_status())
"
```

### Registration System Troubleshooting
```bash
# Test Discord username detection
python -c "
from integrations.sheet_detector import detect_discord_column
print('Discord username column:', detect_discord_column())
"

# Test IGN verification with fallback
python -c "
import asyncio
from integrations.ign_verification import verify_ign_for_registration
async def test():
    result = await verify_ign_for_registration('testign')
    print('Verification result:', result)
asyncio.run(test())
"

# Check configuration
grep -A 10 "registration:" config.yaml
```

### API Integration Troubleshooting
```bash
# Test dashboard API health
curl -f http://localhost:8000/health || echo "Dashboard API unavailable"

# Test specific endpoints
curl -f http://localhost:8000/api/v1/ign-verification/health
curl -f http://localhost:8000/api/v1/tournaments/

# Check API logs
grep -i "api.*error\|timeout\|connection" gal_bot.log
```

### Monitoring and Logs
```bash
# Real-time log monitoring
tail -f gal_bot.log | grep -E "(registration|database|api|fallback)"

# Check recent errors
grep -i "error\|exception\|failed" gal_bot.log | tail -20

# Monitor storage service events
grep -i "storage.*service\|failover\|fallback" gal_bot.log

# Check registration events
grep -i "registration.*complete\|discord.*username\|api.*fallback" gal_bot.log
```
2. Add exponential backoff to retry logic
3. Consider implementing request queuing
4. Increase rate limits if possible

---

**Note**: Always back up your configuration before making changes.  
**Version**: 1.0.0  
**Last Updated**: 2025-01-18
