# Guardian Angel League - Live Graphics Dashboard API

## Overview

This API provides RESTful endpoints and WebSocket connections for the Guardian Angel League Live Graphics Dashboard. It uses FastAPI with master password authentication for secure access to tournament data, user information, and configuration settings.

## Authentication

The API uses master password authentication with JWT tokens. Follow these steps to authenticate:

### 1. Login
```http
POST /auth/login
Content-Type: application/json

{
  "master_password": "DASHBOARD_MASTER_PASSWORD"
}
```

### 2. Receive JWT Token
```json
{
  "access_token": "JWT_ACCESS_TOKEN",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Use Token in Requests
```http
Authorization: Bearer JWT_ACCESS_TOKEN
```

### Token Management
- **Login:** `POST /auth/login`
- **Refresh:** `POST /auth/refresh`
- **Verify:** `GET /auth/verify`
- **Expiration:** 24 hours (configurable)

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Health Check
- `GET /health` - API health status
- `GET /` - API information and endpoints

### Authentication Endpoints
- `POST /auth/login` - Authenticate with master password
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/verify` - Verify current token validity

### Graphics Management (`/api/v1/graphics`)
- `GET /api/v1/graphics/` - List all graphics (paginated)
- `GET /api/v1/graphics/{id}` - Get specific graphic by ID
- `POST /api/v1/graphics/` - Create new graphic
- `PUT /api/v1/graphics/{id}` - Update existing graphic
- `DELETE /api/v1/graphics/{id}` - Soft delete graphic (archives it)
- `POST /api/v1/graphics/{id}/duplicate` - Duplicate existing graphic

### Archive Management (`/api/v1/archive`)
- `POST /api/v1/archive/{graphic_id}` - Archive a graphic (requires empty body `{}`)
- `POST /api/v1/archive/{graphic_id}/restore` - Restore archived graphic
- `GET /api/v1/archive/` - List archived graphics (paginated)
- `DELETE /api/v1/archive/{graphic_id}/permanent` - Permanently delete archived graphic (admin only)

### Lock Management (`/api/v1/lock`)
- `POST /api/v1/lock/{graphic_id}` - Acquire edit lock for graphic
- `DELETE /api/v1/lock/{graphic_id}` - Release edit lock for graphic
- `GET /api/v1/lock/{graphic_id}/status` - Get lock status for specific graphic
- `GET /api/v1/lock/status` - Get status of all active locks

### Maintenance Endpoints (`/api/v1/maintenance`)
- `POST /api/v1/maintenance/cleanup-locks` - Clean up expired locks (maintenance)

## Lock Management

### Lock System
Graphics use a lock system to prevent concurrent editing:
- **Lock Duration**: 5 minutes (300 seconds)
- **Auto-Expiration**: Locks expire automatically
- **Single User**: Only one user can edit a graphic at a time
- **Visual Indicators**: Frontend shows lock status and countdown

### Lock Workflow
1. **Acquire Lock**: `POST /api/v1/lock/{graphic_id}`
2. **Check Status**: `GET /api/v1/lock/{graphic_id}/status`
3. **Release Lock**: `DELETE /api/v1/lock/{graphic_id}`
4. **Cleanup**: `POST /api/v1/maintenance/cleanup-locks`

## Archive System

### Archive Workflow
Graphics can be archived to preserve them while removing them from active view:
1. **Archive**: `POST /api/v1/archive/{graphic_id}` (requires empty body `{}`)
2. **Restore**: `POST /api/v1/archive/{graphic_id}/restore`
3. **Permanent Delete**: `DELETE /api/v1/archive/{graphic_id}/permanent` (admin only)

### Archive States
- **Active**: `archived = false` - Visible in main graphics list
- **Archived**: `archived = true` - Visible in archive tab only
- **Permanently Deleted**: Removed from database entirely

## Request/Response Examples

### Get Graphics
```http
GET /api/v1/graphics/?skip=0&limit=10
Authorization: Bearer {token}
```

Response:
```json
{
  "graphics": [
    {
      "id": 13,
      "title": "Title",
      "event_name": "Event Name",
      "data_json": {},
      "created_by": "username",
      "created_at": "2025-01-09T10:00:00Z",
      "updated_at": "2025-01-09T10:30:00Z",
      "archived": false
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10
}
```

### Create Graphic
```http
POST /api/v1/graphics/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "New Graphic",
  "event_name": "Event Name",
  "data_json": {}
}
```

### Archive Graphic
```http
POST /api/v1/archive/13
Authorization: Bearer {token}
Content-Type: application/json

{}
```

Response:
```json
{
  "success": true,
  "message": "Graphic archived successfully",
  "graphic_id": 13,
  "archived_at": "2025-01-09T10:30:00Z"
}
```

### Acquire Lock
```http
POST /api/v1/lock/13
Authorization: Bearer {token}
Content-Type: application/json

{
  "graphic_id": 13
}
```

Response:
```json
{
  "success": true,
  "lock_id": 5,
  "graphic_id": 13,
  "locked_by": "username",
  "expires_at": "2025-01-09T10:35:00Z",
  "can_edit": true
}
```

## Error Handling

The API returns standard HTTP status codes with detailed error messages:

### Common Error Responses
```json
{
  "detail": "Authentication failed"
}
```

### Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Pagination

List endpoints support pagination using `skip` and `limit` parameters:

```http
GET /api/v1/tournaments/?skip=20&limit=10
```

- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items per page (default: 100, max: 1000)

## Rate Limiting

The API includes rate limiting to prevent abuse:
- Requests per minute: 100 (per authenticated user)
- WebSocket connections: 5 per user
- Burst requests: 20

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **CORS Protection**: Configurable Cross-Origin Resource Sharing
- **Security Headers**: XSS protection, content type options, frame options
- **Request Logging**: All requests are logged with timing information
- **Token Expiration**: Automatic token expiration with refresh capability

## Development

### Running the API
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Run the API
python -m api.main
```

### Auto-reload Development
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Testing

The API includes comprehensive test coverage:
```bash
# Run tests
pytest tests/api/

# Run with coverage
pytest tests/api/ --cov=api --cov-report=html
```

## Deployment

### Docker
```dockerfile
FROM python:3.12

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
- `DASHBOARD_MASTER_PASSWORD`: Master password for authentication
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key
- `DEBUG`: Enable debug mode

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the error messages for detailed information
3. Contact the development team

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-10  
**Guardian Angel League Development Team**
