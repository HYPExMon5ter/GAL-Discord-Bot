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

### Tournament Management (`/api/v1/tournaments`)
- `GET /api/v1/tournaments/` - List tournaments with pagination
- `GET /api/v1/tournaments/{id}` - Get specific tournament
- `POST /api/v1/tournaments/` - Create new tournament
- `PUT /api/v1/tournaments/{id}` - Update tournament
- `DELETE /api/v1/tournaments/{id}` - Delete tournament
- `GET /api/v1/tournaments/{id}/statistics` - Tournament statistics

### User Management (`/api/v1/users`)
- `GET /api/v1/users/` - List users with pagination
- `GET /api/v1/users/{id}` - Get specific user
- `GET /api/v1/users/discord/{discord_id}` - Get user by Discord ID
- `POST /api/v1/users/` - Create new user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `GET /api/v1/users/statistics/overview` - User statistics

### Configuration Management (`/api/v1/configuration`)
- `GET /api/v1/configuration/` - List all configurations
- `GET /api/v1/configuration/{key}` - Get specific configuration
- `PUT /api/v1/configuration/{key}` - Update configuration
- `POST /api/v1/configuration/{key}` - Create new configuration
- `DELETE /api/v1/configuration/{key}` - Delete configuration
- `GET /api/v1/configuration/category/{category}` - Get configurations by category
- `POST /api/v1/configuration/bulk-update` - Bulk update configurations

### WebSocket (`/api/v1/ws`)
- `WebSocket /api/v1/ws/{token}` - Real-time updates
- `GET /api/v1/ws/status` - WebSocket connection status

## WebSocket Events

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/{jwt_token}');
```

### Message Types
- `ping` - Keep-alive ping
- `pong` - Keep-alive response
- `subscribe` - Subscribe to specific events
- `tournament_update` - Tournament data changes
- `user_update` - User data changes
- `configuration_update` - Configuration changes
- `system_notification` - System notifications

### Example Messages
```json
// Ping
{
  "type": "ping"
}

// Subscribe to tournaments
{
  "type": "subscribe",
  "event_type": "tournament_update"
}

// Tournament update (server → client)
{
  "type": "tournament_update",
  "data": {
    "id": 1,
    "name": "Tournament Name",
    "status": "active"
  },
  "timestamp": "2025-10-10T20:00:00Z"
}
```

## Request/Response Examples

### Get Tournaments
```http
GET /api/v1/tournaments/?skip=0&limit=10&status=active
Authorization: Bearer {token}
```

Response:
```json
{
  "tournaments": [
    {
      "id": 1,
      "name": "Summer Tournament",
      "description": "Annual summer competition",
      "status": "active",
      "max_participants": 100,
      "current_participants": 45,
      "start_date": "2025-06-01T18:00:00Z",
      "end_date": "2025-06-03T20:00:00Z",
      "created_at": "2025-05-01T10:00:00Z",
      "updated_at": "2025-06-01T18:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10
}
```

### Create Tournament
```http
POST /api/v1/tournaments/
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Tournament",
  "description": "A new exciting tournament",
  "max_participants": 50,
  "start_date": "2025-12-01T18:00:00Z",
  "end_date": "2025-12-03T20:00:00Z"
}
```

### Update Configuration
```http
PUT /api/v1/configuration/tournament_settings
Authorization: Bearer {token}
Content-Type: application/json

{
  "value": {
    "auto_checkin": true,
    "checkin_reminder_minutes": 30
  },
  "description": "Tournament check-in settings"
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
