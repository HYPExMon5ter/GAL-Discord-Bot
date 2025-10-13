---
id: system.websocket_integration
version: 1.0
last_updated: 2025-10-13
tags: [websocket, real-time, live-updates, integration]
---

# WebSocket Integration System

## Overview
This document describes the WebSocket integration architecture for real-time communication in the Guardian Angel League Live Graphics Dashboard, enabling live updates and synchronized user experiences.

## Architecture Overview

### WebSocket Implementation
- **Technology**: FastAPI WebSocket endpoints
- **Protocol**: WebSocket with JSON message format
- **Authentication**: JWT token-based authentication
- **Connection Management**: Automatic reconnection and health monitoring

### Message Flow Architecture
```
Dashboard Client ←→ WebSocket Server ←→ Event System ←→ Data Sources
      ↓                      ↓                    ↓              ↓
   Real-time UI          Message Bus          Event Bus        Database
   Updates               Routing              Processing       Changes
```

## WebSocket Endpoints

### Primary WebSocket Endpoint
- **Endpoint**: `/ws/graphics`
- **Authentication**: JWT token required
- **Purpose**: Real-time graphics updates
- **Message Types**: Create, Update, Delete, Lock, Unlock

### Connection Management
- **Connection ID**: Unique identifier per client
- **User Association**: Links connections to user accounts
- **Session Tracking**: Active session monitoring
- **Cleanup**: Automatic cleanup of inactive connections

## Message Types and Formats

### Graphics Update Messages
```json
{
  "type": "graphic_update",
  "data": {
    "id": "graphic_id",
    "action": "created|updated|deleted",
    "payload": { ... },
    "timestamp": "2025-10-13T10:00:00Z",
    "user": "username"
  }
}
```

### Lock Status Messages
```json
{
  "type": "lock_status",
  "data": {
    "graphic_id": "graphic_id",
    "locked": true,
    "locked_by": "username",
    "lock_time": "2025-10-13T10:00:00Z"
  }
}
```

### User Activity Messages
```json
{
  "type": "user_activity",
  "data": {
    "user_id": "user_id",
    "username": "username",
    "action": "viewing|editing",
    "target": "graphic_id",
    "timestamp": "2025-10-13T10:00:00Z"
  }
}
```

## Client-Side Integration

### WebSocket Connection Management
```typescript
// Connection establishment
const ws = new WebSocket(`ws://localhost:8000/ws/graphics?token=${jwtToken}`);

// Connection event handlers
ws.onopen = () => {
  console.log('WebSocket connected');
  subscribeToUpdates();
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleWebSocketMessage(message);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
  scheduleReconnect();
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Message Handling
```typescript
function handleWebSocketMessage(message: WebSocketMessage) {
  switch (message.type) {
    case 'graphic_update':
      updateGraphicInCache(message.data);
      refreshUIComponents();
      break;
    case 'lock_status':
      updateLockStatus(message.data);
      break;
    case 'user_activity':
      updateActiveUsers(message.data);
      break;
  }
}
```

### Reconnection Strategy
- **Exponential Backoff**: Increasing delay between reconnection attempts
- **Maximum Attempts**: Limit reconnection attempts
- **Health Monitoring**: Monitor connection quality
- **Graceful Degradation**: Fallback to polling if WebSocket unavailable

## Server-Side Implementation

### WebSocket Endpoint Handler
```python
@app.websocket("/ws/graphics")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    # Authenticate user
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=4001)
        return
    
    # Accept connection
    await websocket.accept()
    
    # Register connection
    connection_id = register_connection(websocket, user)
    
    try:
        # Handle messages
        while True:
            data = await websocket.receive_text()
            await handle_websocket_message(data, user, connection_id)
    except WebSocketDisconnect:
        # Cleanup connection
        unregister_connection(connection_id)
```

### Broadcasting Mechanisms
```python
async def broadcast_to_all(message: dict):
    """Broadcast message to all connected clients"""
    for connection in active_connections:
        await connection.send_text(json.dumps(message))

async def broadcast_to_user(user_id: str, message: dict):
    """Broadcast message to specific user's connections"""
    user_connections = get_user_connections(user_id)
    for connection in user_connections:
        await connection.send_text(json.dumps(message))

async def broadcast_to_graphic_editors(graphic_id: str, message: dict):
    """Broadcast to users editing a specific graphic"""
    editors = get_graphic_editors(graphic_id)
    for editor in editors:
        await broadcast_to_user(editor.id, message)
```

## Real-Time Features

### Live Graphic Updates
- **Creation Notifications**: Real-time notification of new graphics
- **Edit Notifications**: Live updates when graphics are modified
- **Deletion Notifications**: Immediate updates when graphics are deleted
- **Archive Operations**: Real-time archive/restore status updates

### Canvas Locking System
- **Lock Acquisition**: Real-time lock status updates
- **Lock Release**: Immediate notification of lock releases
- **Lock Conflicts**: Real-time conflict resolution
- **Lock Overrides**: Administrative override notifications

### Collaborative Features
- **Multi-user Editing**: Real-time collaboration support
- **User Presence**: Show active users on graphics
- **Activity Tracking**: Track user interactions
- **Conflict Resolution**: Handle edit conflicts gracefully

## Performance and Scalability

### Connection Management
- **Connection Pooling**: Efficient connection management
- **Resource Limits**: Maximum connections per user
- **Memory Management**: Prevent memory leaks
- **Garbage Collection**: Regular cleanup of resources

### Message Optimization
- **Batch Processing**: Batch multiple updates together
- **Message Compression**: Compress large messages
- **Delta Updates**: Send only changed data
- **Priority Queuing**: Prioritize important messages

### Scalability Considerations
- **Horizontal Scaling**: Multiple WebSocket servers
- **Load Balancing**: Distribute connections across servers
- **Redis Integration**: Cross-server message broadcasting
- **Database Optimization**: Efficient data querying

## Security Considerations

### Authentication and Authorization
- **Token Validation**: Validate JWT tokens on connection
- **Permission Checking**: Verify user permissions for operations
- **Rate Limiting**: Prevent message flooding
- **IP Whitelisting**: Restrict connections by IP if needed

### Data Protection
- **Message Encryption**: Encrypt sensitive data in messages
- **Input Validation**: Validate all incoming messages
- **Output Sanitization**: Sanitize outgoing messages
- **Access Logging**: Log all WebSocket activities

### Security Headers
- **Origin Validation**: Validate WebSocket origins
- **CORS Configuration**: Proper CORS settings
- **Content Security Policy**: CSP headers for WebSocket URLs
- **XSS Prevention**: Prevent XSS through WebSocket messages

## Monitoring and Debugging

### Connection Monitoring
- **Active Connections**: Monitor number of active connections
- **Connection Quality**: Track latency and disconnection rates
- **Error Tracking**: Monitor WebSocket errors
- **Performance Metrics**: Track message processing times

### Debugging Tools
- **Message Logging**: Log all WebSocket messages
- **Connection Tracking**: Track connection lifecycle
- **Error Analysis**: Analyze connection failures
- **Performance Profiling**: Profile WebSocket performance

### Health Checks
- **Endpoint Health**: Monitor WebSocket endpoint health
- **Database Connectivity**: Check database connection status
- **Redis Connectivity**: Verify Redis connection for scaling
- **System Resources**: Monitor system resource usage

## Error Handling and Recovery

### Connection Errors
- **Network Failures**: Handle network interruptions gracefully
- **Server Errors**: Recover from server-side errors
- **Authentication Failures**: Handle authentication errors
- **Permission Errors**: Handle authorization errors

### Message Errors
- **Invalid Messages**: Handle malformed messages
- **Missing Data**: Handle incomplete message data
- **Type Errors**: Handle incorrect message types
- **Validation Errors**: Handle data validation failures

### Recovery Procedures
- **Automatic Reconnection**: Client-side reconnection logic
- **State Synchronization**: Resync client state on reconnection
- **Error Reporting**: Report errors to monitoring systems
- **Graceful Degradation**: Fallback to polling if needed

## Integration with Other Systems

### Event System Integration
- **Event Publishing**: Publish WebSocket messages as events
- **Event Subscriptions**: Subscribe to system events
- **Event Filtering**: Filter events for WebSocket clients
- **Event Transformation**: Transform events for WebSocket format

### API Integration
- **REST API Bridge**: Bridge between REST and WebSocket
- **Authentication Sync**: Sync authentication with REST API
- **Data Consistency**: Ensure data consistency across APIs
- **Rate Limiting**: Apply rate limits across all APIs

### Database Integration
- **Real-time Updates**: Monitor database changes
- **Change Data Capture**: Capture database change events
- **Data Validation**: Validate data before broadcasting
- **Transaction Safety**: Ensure transactional consistency

## Testing and Quality Assurance

### Unit Testing
- **WebSocket Handlers**: Test WebSocket endpoint handlers
- **Message Processing**: Test message processing logic
- **Authentication**: Test WebSocket authentication
- **Authorization**: Test permission checking

### Integration Testing
- **End-to-End**: Test complete WebSocket workflows
- **Multi-client**: Test multi-client scenarios
- **Performance**: Test WebSocket performance under load
- **Security**: Test WebSocket security measures

### Load Testing
- **Connection Limits**: Test maximum connection limits
- **Message Throughput**: Test message processing capacity
- **Memory Usage**: Test memory usage under load
- **Error Recovery**: Test error recovery under stress

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-13  
**Next Review**: 2025-11-13  
**Maintainers**: Development Team, Infrastructure Team
