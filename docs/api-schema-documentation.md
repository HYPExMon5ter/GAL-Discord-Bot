# API Schema Documentation

This document provides detailed schema documentation for all API endpoints including request/response examples and validation rules.

## Authentication Schemas

### Login Request
```json
{
  "master_password": "DASHBOARD_MASTER_PASSWORD_PLACEHOLDER"
}
```

**Fields:**
- `master_password` (string, required): Master password for authentication
- **Validation**: Must be exactly 32 characters (system default)
- **Rate Limit**: 5 attempts per minute

### Login Response
```json
{
  "access_token": "JWT_ACCESS_TOKEN_PLACEHOLDER",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Fields:**
- `access_token` (string): JWT token for API authentication
- `token_type` (string): Always "bearer"
- `expires_in` (number): Token expiration time in seconds (24 hours)

## Graphics Management

### Create Graphic Request
```json
{
  "title": "Tournament Championship",
  "event_name": "Curse of the Carousel Finals",
  "data_json": {
    "elements": [
      {
        "type": "text",
        "content": "Championship Match",
        "position": {"x": 100, "y": 50},
        "style": {"fontSize": 24, "color": "#ffffff"}
      }
    ]
  }
}
```

**Validation Rules:**
- `title`: Required, 1-255 characters
- `event_name`: Required, 1-255 characters  
- `data_json`: Optional, valid JSON object (max 10MB)

### Create Graphic Response
```json
{
  "id": 13,
  "title": "Tournament Championship",
  "event_name": "Curse of the Carousel Finals",
  "data_json": {
    "elements": [
      {
        "type": "text",
        "content": "Championship Match",
        "position": {"x": 100, "y": 50},
        "style": {"fontSize": 24, "color": "#ffffff"}
      }
    ]
  },
  "created_by": "admin_user",
  "created_at": "2025-01-18T10:30:00Z",
  "updated_at": "2025-01-18T10:30:00Z",
  "archived": false
}
```

### Update Graphic Request
```json
{
  "title": "Updated Title",
  "event_name": "Updated Event Name",
  "data_json": {
    "elements": [
      {
        "type": "text",
        "content": "Updated Content",
        "position": {"x": 150, "y": 75},
        "style": {"fontSize": 28, "color": "#ffff00"}
      }
    ]
  }
}
```

**Validation Rules:**
- All fields are optional, but at least one must be provided
- `title`: 1-255 characters if provided
- `event_name`: 1-255 characters if provided  
- `data_json`: Valid JSON string if provided

### Update Graphic Response
```json
{
  "id": 13,
  "title": "Updated Title",
  "event_name": "Updated Event Name",
  "data_json": {
    "elements": [
      {
        "type": "text",
        "content": "Updated Content",
        "position": {"x": 150, "y": 75},
        "style": {"fontSize": 28, "color": "#ffff00"}
      }
    ]
  },
  "created_by": "admin_user",
  "created_at": "2025-01-18T10:30:00Z",
  "updated_at": "2025-01-18T10:35:00Z",
  "archived": false
}
```

### List Graphics Request
```http
GET /api/v1/graphics/?include_archived=false&skip=0&limit=100
Authorization: Bearer <token>
```

**Query Parameters:**
- `include_archived` (boolean): Include archived graphics (default: false)
- `skip` (number): Number of items to skip (default: 0, max: 10000)
- `limit` (number): Items per page (default: 100, max: 1000)

### List Graphics Response
```json
{
  "graphics": [
    {
      "id": 13,
      "title": "Tournament Championship",
      "event_name": "Curse of the Carousel Finals",
      "data_json": {
        "elements": [
          {
            "type": "text",
            "content": "Championship Match",
            "position": {"x": 100, "y": 50},
            "style": {"fontSize": 24, "color": "#ffffff"}
          }
        ]
      },
      "created_by": "admin_user",
      "created_at": "2025-01-18T10:30:00Z",
      "updated_at": "2025-01-18T10:35:00Z",
      "archived": false
    }
  ],
  "total": 1
}
```

### Get Graphic by ID Response
```json
{
  "id": 13,
  "title": "Tournament Championship",
  "event_name": "Curse of the Carousel Finals",
  "data_json": {
    "elements": [
      {
        "type": "text",
        "content": "Championship Match",
        "position": {"x": 100, "y": 50},
        "style": {"fontSize": 24, "color": "#ffffff"}
      }
    ]
  },
  "created_by": "admin_user",
  "created_at": "2025-01-18T10:30:00Z",
  "updated_at": "2025-01-18T10:35:00Z",
  "archived": false
}
```

## Lock Management

### Acquire Lock Request
```json
{
  "graphic_id": 13,
  "user_name": "admin_user"
}
```

**Validation Rules:**
- `graphic_id`: Must exist and be unlocked or expired
- `user_name`: Must match authenticated user

### Acquire Lock Response
```json
{
  "id": 5,
  "graphic_id": 13,
  "locked: true,
  "locked_at": "2025-01-18T10:30:00Z",
  "expires_at": "2025-01-18T10:35:00Z"
}
```

### Get Lock Status Response
```json
{
  "locked": true,
  "lock_info": {
    "id": 5,
    "graphic_id": 13,
    "locked: true,
    "locked_at": "2025-01-18T10:30:00Z",
    "expires_at": "2025-01-18T10:35:00Z"
  },
  "can_edit": true
}
```

### Release Lock Response
```json
{
  "success": true,
  "message": "Lock released successfully"
}
```

**Status Codes:**
- `200`: Success
- `404`: Graphic not found
- `409`: Lock already released or expired
- `403`: User does not own the lock

## Archive Management

### Archive Graphic Request
```json
{}
```

**Body:** Empty object required for this endpoint

### Archive Graphic Response
```json
{
  "success": true,
  "message": "Graphic archived successfully",
  "graphic_id": 13,
  "archived_at": "2025-01-18T10:35:00Z"
}
```

### Restore Graphic Request
```json
{}
```

**Body:** Empty object required for this endpoint

### Restore Graphic Response
```json
{
  "success": true,
  "message": "Graphic restored successfully",
  "graphic_id": 13,
  "restored_at": "2025-01-18T10:40:00Z"
}
```

### List Archives Request
```http
GET /api/v1/archive/?skip=0&limit=100
Authorization: Bearer <token>
```

### List Archives Response
```json
{
  "archives": [
    {
      "id": 13,
      "title": "Tournament Championship",
      "event_name": "Curse of the Carousel Finals",
      "data_json": { ... },
      "created_by": "admin_user",
      "created_at": "2025-01-18T10:30:00Z",
      "updated_at": "2025-01-18T10:35:00Z",
      "archived": true
    }
  ],
  "total": 1,
  "can_delete": true
}
```

### Permanent Delete Response
```json
{
  "success": true,
  "message": "Graphic permanently deleted"
}
```

## Error Responses

### Authentication Errors
```json
{
  "detail": "Invalid authentication credentials"
}
```

**Status:** 401 Unauthorized

### Validation Errors
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

**Status:** 422 Unprocessable Entity

### Not Found Errors
```json
{
  "detail": "Graphic with id 999 not found"
}
```

**Status:** 404 Not Found

### Permission Errors
```json
{
  "detail": "You don't have permission to perform this action"
}
```

**Status:** 403 Forbidden

### Server Errors
```json
{
  "detail": "Internal server error"
}
```

**Status:** 500 Internal Server Error

## Data Types

### Canvas Data Format
```json
{
  "elements": [
    {
      "type": "text",
      "content": "Hello World",
      "position": {
        "x": 100,
        "y": 50
      },
      "style": {
        "fontSize": 24,
        "color": "#ffffff",
        "fontWeight": "bold"
      }
    },
    {
      "type": "rectangle",
      "position": {
        "x": 50,
        "y": 100
      },
      "size": {
        "width": 200,
        "height": 100
      },
      "style": {
        "fillColor": "#3498db",
        "strokeColor": "#2980b9",
        "strokeWidth": 2
      }
    }
  ],
  "canvas": {
    "width": 1920,
    "height": 1080,
    "background": "#000000"
  }
}
```

### Supported Element Types
1. **Text**: Text elements with content, position, and styling
2. **Rectangle**: Rectangular shapes with position, size, and styling
3. **Circle**: Circular shapes with position, radius, and styling
4. **Image**: Image elements with position, size, and source
5. **Line**: Line elements with start/end points and styling

### Style Properties
```json
{
  "fontSize": 24,
  "color": "#ffffff",
  "fontWeight": "bold",
  "fontFamily": "Arial",
  "textAlign": "left",
  "backgroundColor": "#3498db",
  "borderRadius": 5,
  "opacity": 1.0
}
```

## Rate Limiting

### General API Limits
- **Requests per minute**: 100 per authenticated user
- **WebSocket connections**: 5 per user
- **Burst requests**: 20 per minute
- **File uploads**: 10MB per request

### Specific Endpoint Limits
- **Login**: 5 attempts per minute
- **Graphics operations**: 50 per minute
- **Archive operations**: 20 per minute
- **Lock operations**: 100 per minute

## Pagination

### Query Parameters
- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items per page (default: 100, max: 1000)

### Response Format
```json
{
  "items": [...],
  "total": 1000,
  "page": 1,
  "per_page": 100,
  "has_next": true,
  "has_previous": false
}
```

## IGN Verification API

### Health Check
**Endpoint**: `GET /api/v1/ign-verification/health`

**Response**:
```json
{
  "status": "healthy",
  "service": "ign-verification",
  "timestamp": "2025-01-19T10:30:00Z",
  "version": "1.0.0"
}
```

### IGN Verification
**Endpoint**: `POST /api/v1/ign-verification/verify`

**Request**:
```json
{
  "ign": "PlayerName123",
  "region": "na"
}
```

**Fields:**
- `ign` (string, required): In-Game Name to verify
- `region` (string, required): Riot API region (na, euw, kr, etc.)

**Response (Success - User Exists)**:
```json
{
  "exists": true,
  "verified": true,
  "ign": "PlayerName123",
  "region": "na",
  "riot_data": {
    "puuid": "riot-puuid-example",
    "summoner_id": "summoner-id-example",
    "account_id": "account-id-example",
    "level": 150,
    "profile_icon_id": 1234
  },
  "verification_timestamp": "2025-01-19T10:30:00Z"
}
```

**Response (Success - User Doesn't Exist)**:
```json
{
  "exists": false,
  "verified": true,
  "ign": "PlayerName123",
  "region": "na",
  "riot_data": null,
  "verification_timestamp": "2025-01-19T10:30:00Z",
  "message": "IGN is available for registration"
}
```

**Response (API Failure - Fallback Mode)**:
```json
{
  "exists": null,
  "verified": false,
  "ign": "PlayerName123",
  "region": "na",
  "riot_data": null,
  "error": "API_UNAVAILABLE",
  "message": "IGN verification temporarily unavailable - registration allowed via fallback",
  "fallback_activated": true,
  "verification_timestamp": "2025-01-19T10:30:00Z"
}
```

**Error Responses**:
```json
{
  "detail": "Invalid request format",
  "error_code": "INVALID_REQUEST"
}
```

```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMITED",
  "retry_after": 60
}
```

**Fallback Behavior Documentation**:

The IGN verification API implements resilient fallback logic to ensure tournament registration can continue even when external services are unavailable.

#### Fallback Scenarios
1. **Riot API Unavailable**: Service timeouts or rate limiting
2. **Network Issues**: Connection failures or DNS resolution problems
3. **Service Maintenance**: API endpoints temporarily unavailable
4. **Authentication Failures**: Invalid API credentials or token expiration

#### Fallback Logic
```python
# Pseudocode for fallback behavior
try:
    # Try Riot API verification
    result = await verify_with_riot_api(ign, region)
    return result
except Exception as e:
    # Any failure triggers fallback
    log_error("IGN verification failed", e)
    return {
        "exists": null,
        "verified": false,
        "fallback_activated": true,
        "message": "Registration allowed via fallback"
    }
```

#### Integration with Registration System
The registration system uses the API fallback as follows:

1. **Normal Operation**: API responds with explicit `exists: true/false`
2. **Fallback Activation**: API responds with `exists: null` and `fallback_activated: true`
3. **Registration Decision**: System allows registration when fallback is activated
4. **User Notification**: Clear message about verification status
5. **Monitoring**: Comprehensive logging for follow-up when services restore

#### Configuration for Fallback
```yaml
registration:
  api_fallback_enabled: true
  allow_registration_on_api_failure: true
  show_fallback_messages: true
  log_api_failures: true
  api_timeout_seconds: 10
  max_retries: 3
```

#### Monitoring Fallback Events
```bash
# Check for fallback activation in logs
grep -i "fallback.*activated\|api.*unavailable" gal_bot.log

# Monitor API health status
curl -f http://localhost:8000/api/v1/ign-verification/health

# Check verification API performance
grep "ign.*verification.*completed\|ign.*verification.*failed" gal_bot.log
```

### Registration Integration Example

```python
# Example of how registration system integrates with fallback API
async def process_registration(ign: str, discord_username: str, region: str = "na"):
    try:
        # Call IGN verification API
        response = await verify_ign_api(ign, region)
        
        if response["verified"]:
            if response["exists"] is False:
                # IGN is available - proceed with registration
                await complete_registration(ign, discord_username)
                return "Registration successful - IGN available"
            elif response["exists"] is True:
                # IGN already exists - block registration
                return "Registration failed - IGN already in use"
            elif response["fallback_activated"]:
                # API failed - allow registration via fallback
                await complete_registration(ign, discord_username)
                await log_fallback_event(ign, response)
                return "Registration successful via fallback - API temporarily unavailable"
        else:
            return "Registration failed - verification error"
            
    except Exception as e:
        # Complete system failure - allow registration
        await complete_registration(ign, discord_username)
        await log_system_failure(ign, e)
        return "Registration successful - system fallback activated"
```

---

**Note**: All timestamps are in ISO 8601 format (UTC).  
**Version**: 1.0.0  
**Last Updated**: 2025-01-19
