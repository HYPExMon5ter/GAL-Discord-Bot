---
id: system.access_control
version: 1.0
last_updated: 2025-01-18
tags: [security, authentication, authorization, access-control]
---

# Access Control

## Overview

The Guardian Angel League system implements a comprehensive access control system that secures both the Discord bot and the Live Graphics Dashboard. The system uses multiple authentication mechanisms and authorization patterns to ensure secure access to system resources.

## Authentication Methods

### Discord Bot Authentication
**Purpose**: Authenticate Discord bot with Discord API

**Implementation**:
- **Bot Token**: Secure token-based authentication with Discord
- **Token Management**: Secure storage and rotation of bot tokens
- **Connection Security**: Encrypted communication with Discord servers
- **Error Handling**: Graceful handling of authentication failures

```python
# Bot authentication pattern
import discord
from utils.logging_utils import mask_token, sanitize_log_message

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

try:
    bot = discord.Client(intents=discord.Intents.default())
    logger.info("Initializing Discord bot...")
    
except discord.LoginFailure as e:
    logger.error("Failed to authenticate with Discord - check your token configuration")
    if DISCORD_TOKEN:
        logger.debug(f"Token preview: {mask_token(DISCORD_TOKEN)}")
    raise
```

### Dashboard Authentication
**Purpose**: Secure authentication for Live Graphics Dashboard

**Authentication Flow**:
1. **Master Password**: Single password-based authentication for dashboard access
2. **JWT Tokens**: JSON Web Token generation for session management
3. **Token Expiration**: Configurable token lifetime with automatic refresh
4. **Secure Storage**: Token storage in browser localStorage with security headers

**Implementation Details**:
```python
# Dashboard authentication endpoint
@app.post("/auth/login")
async def login(request: LoginRequest):
    if request.password != MASTER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": "dashboard_user"})
    return {"access_token": token, "token_type": "bearer"}
```

### API Authentication
**Purpose**: Secure API endpoint access with JWT validation

**Features**:
- **Bearer Token Authentication**: HTTP Bearer token scheme
- **Token Validation**: Automatic JWT validation for protected routes
- **Role-Based Access**: Different access levels for different operations
- **Rate Limiting**: Protection against brute force attacks

```python
# API authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Authorization Patterns

### Discord Permissions
**Purpose**: Control Discord bot access based on user roles

**Permission Levels**:
- **Administrator**: Full access to all bot commands and settings
- **Moderator**: Access to tournament management and user moderation
- **Tournament Manager**: Access to tournament-specific operations
- **Registered User**: Basic access to registration and standings

**Implementation**:
```python
# Discord permission checking
@bot.command()
@commands.has_permissions(administrator=True)
async def configure_bot(ctx):
    """Configure bot settings (admin only)"""
    await ctx.send("Configuration options...")
```

### Dashboard Access Control
**Purpose**: Control dashboard feature access

**Access Levels**:
- **Full Access**: Complete dashboard functionality
- **Graphics Management**: Create, edit, and manage graphics
- **Read-Only**: View-only access to graphics and configurations
- **API Access**: Limited API endpoint access

### API Endpoint Protection
**Purpose**: Secure API endpoints based on operation sensitivity

**Protection Levels**:
- **Public**: Unprotected endpoints (health checks, public data)
- **Authenticated**: Requires valid JWT token
- **Admin**: Requires elevated permissions
- **Service**: Service-to-service authentication

## Security Measures

### Token Security
**Purpose**: Secure token handling and storage

**Measures**:
- **Token Masking**: Automatic masking of tokens in logs
- **Secure Storage**: Environment variable storage for sensitive tokens
- **Token Rotation**: Regular token rotation policies
- **Audit Logging**: Complete audit trail of authentication events

```python
# Token masking for logging
from utils.logging_utils import mask_token, sanitize_log_message

def log_authentication_attempt(token):
    masked_token = mask_token(token)
    logger.info(f"Authentication attempt with token: {masked_token}")
```

### Session Management
**Purpose**: Secure session handling

**Features**:
- **Session Expiration**: Automatic session timeout
- **Secure Cookies**: HttpOnly and Secure cookie flags
- **CSRF Protection**: Cross-site request forgery prevention
- **Session Revocation**: Ability to revoke active sessions

### Rate Limiting
**Purpose**: Prevent abuse and brute force attacks

**Implementation**:
- **IP-based Limits**: Rate limiting by IP address
- **User-based Limits**: Rate limiting by authenticated user
- **Endpoint-specific Limits**: Different limits for different endpoints
- **Progressive Delays**: Increasing delays for repeated failures

## Access Control Configuration

### Environment Variables
```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# Dashboard Authentication
MASTER_PASSWORD=your_secure_master_password_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Security Settings
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### Security Headers
```python
# Security middleware configuration
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## Audit and Monitoring

### Authentication Logging
**Purpose**: Track authentication events for security monitoring

**Logged Events**:
- Login attempts (success/failure)
- Token generation and validation
- Permission changes
- Access denied events

```python
# Authentication logging
def log_auth_event(event_type: str, user: str, success: bool, ip: str = None):
    log_data = {
        "event": event_type,
        "user": user,
        "success": success,
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if success:
        logger.info(f"Auth success: {event_type} for {user}", extra=log_data)
    else:
        logger.warning(f"Auth failure: {event_type} for {user}", extra=log_data)
```

### Security Monitoring
**Purpose**: Monitor for suspicious activity

**Monitoring Metrics**:
- Failed login attempts by IP
- Unusual access patterns
- Token usage anomalies
- Permission escalation attempts

## Best Practices

### Password Security
- **Strong Passwords**: Enforce strong password requirements
- **Password Hashing**: Use bcrypt for password storage
- **Password Rotation**: Regular password rotation policies
- **Password Recovery**: Secure password recovery mechanisms

### Token Management
- **Short-lived Tokens**: Use short expiration times for access tokens
- **Refresh Tokens**: Implement refresh token patterns
- **Token Storage**: Store tokens securely on client side
- **Token Revocation**: Implement token revocation mechanisms

### Network Security
- **HTTPS Only**: Enforce HTTPS for all communications
- **CORS Configuration**: Proper CORS configuration for APIs
- **Firewall Rules**: Network-level access controls
- **VPN Access**: Require VPN for administrative access

## Compliance Considerations

### Data Protection
- **GDPR Compliance**: User data protection and privacy
- **Data Minimization**: Collect only necessary data
- **Data Encryption**: Encrypt sensitive data at rest and in transit
- **Data Retention**: Appropriate data retention policies

### Audit Requirements
- **Access Logs**: Complete audit trail of access events
- **Change Logs**: Log all configuration changes
- **Incident Response**: Security incident response procedures
- **Regular Audits**: Regular security audits and assessments

## Troubleshooting

### Common Issues
1. **Token Expired**: Users getting logged out frequently
   - Check token expiration settings
   - Verify refresh token implementation

2. **Permission Denied**: Users unable to access resources
   - Verify user roles and permissions
   - Check permission configuration

3. **CORS Errors**: Frontend unable to access API
   - Verify CORS configuration
   - Check allowed origins list

4. **Rate Limiting**: Legitimate users being blocked
   - Review rate limiting settings
   - Check for bot activity

### Debug Authentication Issues
```python
# Debug authentication
import logging
from utils.logging_utils import sanitize_log_message

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_auth_flow(token):
    logger.debug(f"Authenticating with token: {sanitize_log_message(str(token))}")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token payload: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise
```

## Related Documentation

- [Security & Logging](./architecture.md#security--logging) - Security implementation details
- [API Backend System](./api-backend-system.md) - API authentication patterns
- [Frontend Components](./frontend-components.md) - Client-side authentication
- [System Architecture](./architecture.md) - Overall system security architecture

---

*Generated: 2025-01-18*
*Last Updated: Access control documentation with authentication methods*
