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

---

**Note**: All timestamps are in ISO 8601 format (UTC).  
**Version**: 1.0.0  
**Last Updated**: 2025-01-18
