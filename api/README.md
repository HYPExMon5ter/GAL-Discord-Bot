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

## Data Schemas

### Graphic Schema
```python
class GraphicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Graphic title")
    event_name: str = Field(..., min_length=1, max_length=255, description="Event name")
    data_json: Optional[Dict[str, Any]] = Field(default=None, description="Canvas data as JSON")

class GraphicCreate(GraphicBase):
    """Schema for creating a new graphic"""
    pass

class GraphicUpdate(BaseModel):
    """Schema for updating an existing graphic"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Graphic title")
    event_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Event name")
    data_json: Optional[str] = Field(None, description="Canvas data as JSON string")

class GraphicResponse(BaseModel):
    """Schema for graphic response"""
    id: int
    title: str
    event_name: Optional[str]
    data_json: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    archived: bool
```

### Lock Schema
```python
class CanvasLockCreate(BaseModel):
    """Schema for creating a canvas lock"""
    graphic_id: int
    user_name: str

class CanvasLockResponse(BaseModel):
    """Schema for canvas lock response"""
    id: int
    graphic_id: int
    user_name: str
    locked: bool
    locked_at: datetime
    expires_at: datetime
```

### Archive Schema
```python
class ArchiveActionRequest(BaseModel):
    """Schema for archive action requests"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for archiving")

class ArchiveResponse(BaseModel):
    """Schema for archive action response"""
    success: bool
    message: str
    graphic_id: int
    archived_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None
```

## Request/Response Examples

### Get Graphics
```http
GET /api/v1/graphics/?include_archived=false&skip=0&limit=10
Authorization: Bearer {token}
```

**Request Parameters:**
- `include_archived` (boolean, optional): Include archived graphics in results
- `skip` (integer, optional): Number of items to skip for pagination
- `limit` (integer, optional): Number of items per page (max: 100)

**Response:**
```json
{
  "graphics": [
    {
      "id": 13,
      "title": "Tournament Finals",
      "event_name": "Winter Championship 2025",
      "data_json": "{\"elements\": [...]}",
      "created_by": "admin_user",
      "created_at": "2025-01-09T10:00:00Z",
      "updated_at": "2025-01-09T10:30:00Z",
      "archived": false
    }
  ],
  "total": 1
}
```

### Create Graphic
```http
POST /api/v1/graphics/
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "New Tournament Bracket",
  "event_name": "Spring Tournament 2025",
  "data_json": {
    "tournament_type": "single_elimination",
    "participants": [],
    "rounds": []
  }
}
```

**Request Body:**
```json
{
  "title": "string (1-255 chars)",
  "event_name": "string (1-255 chars)", 
  "data_json": "object (optional)"
}
```

**Response (201 Created):**
```json
{
  "id": 14,
  "title": "New Tournament Bracket",
  "event_name": "Spring Tournament 2025",
  "data_json": "{\"tournament_type\": \"single_elimination\", \"participants\": [], \"rounds\": []}",
  "created_by": "admin_user",
  "created_at": "2025-01-09T11:00:00Z",
  "updated_at": "2025-01-09T11:00:00Z",
  "archived": false
}
```

### Update Graphic
```http
PUT /api/v1/graphics/14
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Tournament Bracket",
  "data_json": "{\"tournament_type\": \"double_elimination\", \"participants\": [...], \"rounds\": [...]}"
}
```

**Request Body:**
```json
{
  "title": "string (1-255 chars, optional)",
  "event_name": "string (1-255 chars, optional)",
  "data_json": "string (JSON, optional)"
}
```

**Response (200 OK):**
```json
{
  "id": 14,
  "title": "Updated Tournament Bracket",
  "event_name": "Spring Tournament 2025",
  "data_json": "{\"tournament_type\": \"double_elimination\", \"participants\": [...], \"rounds\": [...]}",
  "created_by": "admin_user",
  "created_at": "2025-01-09T11:00:00Z",
  "updated_at": "2025-01-09T11:15:00Z",
  "archived": false
}
```

### Delete Graphic
```http
DELETE /api/v1/graphics/14
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "message": "Graphic deleted successfully"
}
```

### Duplicate Graphic
```http
POST /api/v1/graphics/14/duplicate
Authorization: Bearer {token}
Content-Type: application/json

{
  "new_title": "Copy of Tournament Bracket",
  "new_event_name": "Spring Tournament 2025 (Copy)"
}
```

**Response (201 Created):**
```json
{
  "id": 15,
  "title": "Copy of Tournament Bracket",
  "event_name": "Spring Tournament 2025 (Copy)",
  "data_json": "{\"tournament_type\": \"double_elimination\", \"participants\": [...], \"rounds\": [...]}",
  "created_by": "admin_user",
  "created_at": "2025-01-09T11:20:00Z",
  "updated_at": "2025-01-09T11:20:00Z",
  "archived": false
}
```

### Lock Management

#### Acquire Lock
```http
POST /api/v1/lock/14
Authorization: Bearer {token}
Content-Type: application/json

{
  "graphic_id": 14
}
```

**Response (200 OK):**
```json
{
  "id": 6,
  "graphic_id": 14,
  "user_name": "admin_user",
  "locked": true,
  "locked_at": "2025-01-09T11:25:00Z",
  "expires_at": "2025-01-09T11:30:00Z"
}
```

#### Get Lock Status
```http
GET /api/v1/lock/14/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "locked": true,
  "lock_info": {
    "id": 6,
    "graphic_id": 14,
    "user_name": "admin_user",
    "locked": true,
    "locked_at": "2025-01-09T11:25:00Z",
    "expires_at": "2025-01-09T11:30:00Z"
  },
  "can_edit": true
}
```

#### Release Lock
```http
DELETE /api/v1/lock/14
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "message": "Lock released successfully"
}
```

#### Refresh Lock
```http
POST /api/v1/lock/14/refresh
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": 6,
  "graphic_id": 14,
  "user_name": "admin_user",
  "locked": true,
  "locked_at": "2025-01-09T11:25:00Z",
  "expires_at": "2025-01-09T11:35:00Z"
}
```

### Archive Operations

#### Archive Graphic
```http
POST /api/v1/archive/14
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "Season ended, preparing for next tournament"
}
```

**Request Body:**
```json
{
  "reason": "string (max 500 chars, optional)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Graphic archived successfully",
  "graphic_id": 14,
  "archived_at": "2025-01-09T11:40:00Z"
}
```

#### Restore Archived Graphic
```http
POST /api/v1/archive/14/restore
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Graphic restored successfully",
  "graphic_id": 14,
  "restored_at": "2025-01-09T11:45:00Z"
}
```

#### Get Archived Graphics
```http
GET /api/v1/archive/?skip=0&limit=10
Authorization: Bearer {token}
```

**Response:**
```json
{
  "archives": [
    {
      "id": 14,
      "title": "Updated Tournament Bracket",
      "event_name": "Spring Tournament 2025",
      "data_json": "{\"tournament_type\": \"double_elimination\", \"participants\": [...], \"rounds\": [...]}",
      "created_by": "admin_user",
      "created_at": "2025-01-09T11:00:00Z",
      "updated_at": "2025-01-09T11:15:00Z",
      "archived": true
    }
  ],
  "total": 1,
  "can_delete": true
}
```

#### Permanent Delete (Admin Only)
```http
DELETE /api/v1/archive/14/permanent
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "message": "Graphic permanently deleted successfully"
}
```

### Maintenance Operations

#### Cleanup Expired Locks (Admin Only)
```http
POST /api/v1/maintenance/cleanup-locks
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "message": "Cleaned up 3 expired locks",
  "cleaned_count": 3
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
