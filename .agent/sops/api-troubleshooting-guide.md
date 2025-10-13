# API Troubleshooting Guide

## Overview
This guide provides troubleshooting steps for common API errors encountered in the Live Graphics Dashboard.

## Common HTTP Error Codes

### 400 Bad Request
**Causes**:
- Missing required request body
- Invalid request parameters
- Locked resource preventing operation
- Validation errors in request data

**Troubleshooting Steps**:
1. **Check Request Body**: Ensure required body is present
   - Archive endpoint: Send `{}` as body
   - Other endpoints: Check required fields
   
2. **Verify Lock Status**: Check if graphic is locked
   ```bash
   GET /api/lock/{graphic_id}/status
   ```
   
3. **Validate Request Format**: Check JSON structure
   - Use browser dev tools to inspect request
   - Verify Content-Type header is `application/json`

**Example Fixes**:
```javascript
// ❌ Wrong - No body
await api.post(`/archive/${id}`);

// ✅ Correct - Empty object body
await api.post(`/archive/${id}`, {});
```

### 401 Unauthorized
**Causes**:
- Missing or invalid JWT token
- Token has expired
- Incorrect authentication credentials

**Troubleshooting Steps**:
1. **Check Token**: Verify JWT token is present in headers
2. **Token Expiration**: Check if token has expired (24-hour lifetime)
3. **Refresh Token**: Use refresh endpoint if available
4. **Re-authenticate**: Login again with valid credentials

**Debugging**:
```javascript
// Check token in localStorage
console.log('Token:', localStorage.getItem('token'));

// Check token expiration
const token = localStorage.getItem('token');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log('Token expires:', new Date(payload.exp * 1000));
```

### 403 Forbidden
**Causes**:
- Insufficient permissions for operation
- Admin-only endpoint access
- Resource access restrictions

**Troubleshooting Steps**:
1. **Check Permissions**: Verify user has required access level
2. **Admin Operations**: Confirm admin status for privileged endpoints
3. **Resource Ownership**: Check if user owns the resource

### 404 Not Found
**Causes**:
- Resource doesn't exist
- Incorrect endpoint URL
- Wrong resource ID

**Troubleshooting Steps**:
1. **Verify Resource Exists**: Check database for the resource
2. **Check Endpoint URL**: Ensure URL is correct
3. **Validate Resource ID**: Confirm ID is valid and exists

**Database Check**:
```python
# Check if graphic exists
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Graphic

DATABASE_URL = 'sqlite:///./dashboard.db'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

graphic = db.query(Graphic).filter(Graphic.id == graphic_id).first()
print(f"Graphic exists: {graphic is not None}")
if graphic:
    print(f"Title: {graphic.title}, Archived: {graphic.archived}")
```

### 405 Method Not Allowed
**Causes**:
- HTTP method not supported by endpoint
- Route registration issues
- Incorrect method in API call

**Troubleshooting Steps**:
1. **Check HTTP Method**: Verify correct method (GET, POST, PUT, DELETE)
2. **Route Registration**: Confirm API routes are properly registered
3. **Endpoint Documentation**: Check API docs for correct methods

**Example Fix**:
```javascript
// ❌ Wrong method
await api.get(`/archive/${id}/permanent`);

// ✅ Correct method
await api.delete(`/archive/${id}/permanent`);
```

### 409 Conflict
**Causes**:
- Resource already locked
- Concurrent modification conflicts
- State conflicts in operations

**Troubleshooting Steps**:
1. **Check Lock Status**: Verify resource is not locked
2. **Wait and Retry**: Wait for lock to expire
3. **Force Release**: Use maintenance endpoints if available

### 500 Internal Server Error
**Causes**:
- Database connection issues
- Server-side exceptions
- Configuration problems

**Troubleshooting Steps**:
1. **Check Server Logs**: Review API server error logs
2. **Database Connection**: Verify database is accessible
3. **Configuration**: Check environment variables and settings

## Network Issues

### CORS Errors
**Symptoms**: CORS policy errors in browser console
**Solutions**:
1. Check API CORS configuration
2. Verify allowed origins list
3. Ensure proper preflight handling

### Connection Refused
**Symptoms**: Network connection refused
**Solutions**:
1. Check if API server is running
2. Verify port accessibility
3. Check firewall settings

### Timeout Issues
**Symptoms**: Requests timing out
**Solutions**:
1. Increase timeout values
2. Check server performance
3. Verify database query efficiency

## Debugging Tools

### Browser DevTools
1. **Network Tab**: Inspect HTTP requests and responses
2. **Console Tab**: Check for JavaScript errors
3. **Application Tab**: Verify localStorage and cookies

### API Testing
1. **Postman/Insomnia**: Test API endpoints directly
2. **cURL**: Command-line API testing
3. **Swagger UI**: Interactive API documentation

### Server Logs
1. **API Server Logs**: Check for error messages
2. **Database Logs**: Monitor query performance
3. **Application Logs**: Review system events

## Common Scenarios

### Archive/Delete Not Working
**Symptoms**: 400 or 404 errors when archiving/deleting
**Root Causes**:
1. Graphic is locked
2. Wrong endpoint being called
3. Graphic already archived
4. Database inconsistencies

**Solution Flow**:
1. Check lock status: `GET /api/lock/{id}/status`
2. Verify graphic exists in database
3. Check correct endpoint usage
4. Clear browser cache and retry

### Lock Management Issues
**Symptoms**: Locks not releasing or acquiring
**Root Causes**:
1. Expired locks not cleaned up
2. Network connectivity issues
3. Server state inconsistencies

**Solution Flow**:
1. Run lock cleanup: `POST /api/maintenance/cleanup-locks`
2. Check server connectivity
3. Restart API server if needed

### Authentication Problems
**Symptoms**: 401 errors or login failures
**Root Causes**:
1. Invalid credentials
2. Token expiration
3. Configuration issues

**Solution Flow**:
1. Verify master password
2. Check token expiration
3. Re-authenticate with fresh credentials

## Prevention

### Code Reviews
- Validate API endpoint usage
- Check error handling implementation
- Verify request/response formats

### Testing
- Unit tests for API calls
- Integration tests for workflows
- Error scenario testing

### Monitoring
- API error rate monitoring
- Performance metrics tracking
- Log analysis for patterns

---

**Version**: 1.0  
**Created**: 2025-01-09  
**Owner**: Guardian Angel League Development Team
