---
id: system.security_architecture
version: 1.0
last_updated: 2025-01-17
tags: [security, authentication, authorization, data-protection, compliance]
---

# Security Architecture

## Overview

The Guardian Angel League bot implements a comprehensive security architecture designed to protect user data, prevent unauthorized access, and ensure secure operation across all system components. This architecture follows defense-in-depth principles with multiple security layers.

## Security Layers

### Layer 1: Authentication and Authorization
**Purpose**: Verify user identity and control access to resources
**Components**:
- Discord OAuth2 integration
- JWT token management
- Role-based access control (RBAC)
- Session management

### Layer 2: Data Protection
**Purpose**: Protect data at rest and in transit
**Components**:
- Encryption for sensitive data
- SSL/TLS for network communications
- Token masking and sanitization
- Secure logging practices

### Layer 3: Infrastructure Security
**Purpose**: Secure the underlying infrastructure
**Components**:
- Network security
- Database security
- File system permissions
- Environment variable protection

### Layer 4: Application Security
**Purpose**: Secure the application code and runtime
**Components**:
- Input validation
- Error handling
- Dependency security
- Security testing

## Authentication System

### Discord OAuth2 Integration
```python
# Discord OAuth2 flow
1. User initiates login via Discord
2. Redirect to Discord authorization
3. Receive authorization code
4. Exchange code for access token
5. Verify user identity
6. Create session/token
7. Grant application access
```

### JWT Token Management
```python
# JWT Token Structure
{
    "sub": "user_id",
    "guild_id": "server_id",
    "roles": ["member", "admin"],
    "iat": 1234567890,
    "exp": 1234567990,
    "permissions": ["read:graphics", "write:graphics"]
}

# Token Security Features
- Short expiration times (1 hour)
- Secure signing with HMAC
- Audience validation
- Token rotation
```

### Role-Based Access Control (RBAC)
**Roles**:
- **Guest**: Read-only access to public graphics
- **Member**: Basic graphic editing and creation
- **Moderator**: Advanced editing and management
- **Admin**: Full system administration

**Permissions**:
```python
PERMISSIONS = {
    "read:graphics": ["guest", "member", "moderator", "admin"],
    "write:graphics": ["member", "moderator", "admin"],
    "delete:graphics": ["moderator", "admin"],
    "manage:users": ["admin"],
    "system:config": ["admin"]
}
```

## Data Protection

### Token Masking and Sanitization
```python
# Token masking utilities
def mask_token(token: str) -> str:
    """Mask sensitive tokens for logging"""
    if not token or len(token) < 8:
        return "***"
    return token[:4] + "*" * (len(token) - 8) + token[-4:]

def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive data from logs"""
    sensitive_keys = ['token', 'password', 'api_key', 'secret']
    return {k: v if k not in sensitive_keys else mask_token(str(v)) 
            for k, v in data.items()}
```

### Encryption Implementation
```python
# Sensitive data encryption
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive configuration data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive configuration data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### Secure Logging Practices
```python
# Secure logging configuration
import logging
from logging.handlers import RotatingFileHandler

def setup_secure_logging():
    """Configure secure logging with token masking"""
    
    # Custom filter for sensitive data
    class SensitiveDataFilter(logging.Filter):
        def filter(self, record):
            # Mask tokens and sensitive data
            if hasattr(record, 'msg'):
                record.msg = sanitize_log_message(record.msg)
            return True
    
    # Configure handler
    handler = RotatingFileHandler(
        'secure.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    handler.addFilter(SensitiveDataFilter())
    
    return handler
```

## Network Security

### SSL/TLS Configuration
```python
# SSL/TLS configuration for FastAPI
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Force HTTPS in production
if os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# SSL context configuration
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

### CORS Security
```python
# CORS configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.example.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting
```python
# Rate limiting implementation
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/graphics")
@limiter.limit("100/minute")
async def get_graphics(request: Request):
    # Rate limited endpoint
    pass
```

## Database Security

### Connection Security
```python
# Secure database connection
def create_secure_connection():
    """Create secure database connection"""
    
    connection_string = os.getenv("DATABASE_URL")
    
    # Ensure SSL for PostgreSQL
    if connection_string.startswith("postgresql://"):
        if "?sslmode=" not in connection_string:
            connection_string += "?sslmode=require"
    
    return connection_string
```

### Access Control
```python
# Database access control
class DatabaseAccessControl:
    """Control database access based on user roles"""
    
    def __init__(self, user_role: str):
        self.role = user_role
        self.permissions = self._get_role_permissions()
    
    def _get_role_permissions(self) -> dict:
        """Get permissions based on user role"""
        return {
            "admin": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "moderator": ["SELECT", "INSERT", "UPDATE"],
            "member": ["SELECT", "INSERT"],
            "guest": ["SELECT"]
        }
    
    def can_execute(self, operation: str) -> bool:
        """Check if user can execute database operation"""
        return operation in self.permissions.get(self.role, [])
```

### Query Parameterization
```python
# Secure database queries
async def get_user_graphics(user_id: str, guild_id: str):
    """Get user graphics with parameterized queries"""
    
    query = """
        SELECT id, title, event_name, created_at, updated_at
        FROM graphics 
        WHERE created_by = %s AND guild_id = %s
        ORDER BY created_at DESC
    """
    
    # Use parameterized queries to prevent SQL injection
    async with get_db_connection() as conn:
        result = await conn.fetch(query, user_id, guild_id)
        return [dict(row) for row in result]
```

## Application Security

### Input Validation
```python
# Input validation with Pydantic
from pydantic import BaseModel, validator
import re

class GraphicCreateRequest(BaseModel):
    title: str
    event_name: str
    data_json: dict
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        if len(v) > 200:
            raise ValueError('Title too long')
        # Sanitize title
        return re.sub(r'[<>"\']', '', v.strip())
    
    @validator('event_name')
    def validate_event_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Event name cannot be empty')
        return v.strip()
```

### Error Handling
```python
# Secure error handling
from fastapi import HTTPException
import logging

class SecureErrorHandler:
    """Handle errors without exposing sensitive information"""
    
    @staticmethod
    def handle_database_error(error: Exception):
        """Handle database errors securely"""
        logging.error(f"Database error: {str(error)}")
        
        # Don't expose database details to client
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred"
        )
    
    @staticmethod
    def handle_authentication_error(error: Exception):
        """Handle authentication errors"""
        logging.warning(f"Authentication error: {str(error)}")
        
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )
```

### Dependency Security
```python
# Security scanning for dependencies
import subprocess
import json

def scan_dependencies():
    """Scan for security vulnerabilities in dependencies"""
    
    try:
        # Run safety check
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            vulnerabilities = json.loads(result.stdout)
            logging.warning(f"Security vulnerabilities found: {vulnerabilities}")
            
            # Send alert for critical vulnerabilities
            for vuln in vulnerabilities:
                if vuln.get('vulnerability_severity') == 'high':
                    send_security_alert(vuln)
    
    except Exception as e:
        logging.error(f"Security scan failed: {e}")

def send_security_alert(vulnerability: dict):
    """Send security alert for critical vulnerabilities"""
    
    alert_message = f"""
    CRITICAL SECURITY VULNERABILITY DETECTED
    
    Package: {vulnerability.get('package')}
    Version: {vulnerability.get('installed_version')}
    Vulnerability: {vulnerability.get('vulnerability_id')}
    Severity: {vulnerability.get('vulnerability_severity')}
    
    Immediate action required!
    """
    
    # Send to security team
    logging.critical(alert_message)
```

## Security Monitoring

### Security Events Logging
```python
# Security event logging
class SecurityLogger:
    """Log security-related events"""
    
    def __init__(self):
        self.logger = logging.getLogger('security')
    
    def log_login_attempt(self, user_id: str, success: bool, ip: str):
        """Log login attempts"""
        event = {
            'event_type': 'login_attempt',
            'user_id': user_id,
            'success': success,
            'ip_address': ip,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"Successful login: {event}")
        else:
            self.logger.warning(f"Failed login attempt: {event}")
    
    def log_permission_denied(self, user_id: str, resource: str, action: str):
        """Log permission denied events"""
        event = {
            'event_type': 'permission_denied',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.logger.warning(f"Permission denied: {event}")
    
    def log_suspicious_activity(self, user_id: str, activity: str):
        """Log suspicious activities"""
        event = {
            'event_type': 'suspicious_activity',
            'user_id': user_id,
            'activity': activity,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.logger.critical(f"Suspicious activity detected: {event}")
```

### Intrusion Detection
```python
# Basic intrusion detection
class IntrusionDetector:
    """Detect suspicious patterns and potential attacks"""
    
    def __init__(self):
        self.failed_attempts = {}
        self.suspicious_ips = set()
    
    def check_brute_force(self, ip: str, user_id: str) -> bool:
        """Check for brute force attempts"""
        
        key = f"{ip}:{user_id}"
        self.failed_attempts[key] = self.failed_attempts.get(key, 0) + 1
        
        if self.failed_attempts[key] > 5:  # 5 failed attempts
            self.suspicious_ips.add(ip)
            return True
        
        return False
    
    def check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """Check for rate limit violations"""
        
        # Implementation would track requests per IP/endpoint
        # Return True if rate limit exceeded
        pass
    
    def is_ip_suspicious(self, ip: str) -> bool:
        """Check if IP is flagged as suspicious"""
        return ip in self.suspicious_ips
```

## Compliance and Auditing

### Audit Trail
```python
# Audit trail implementation
class AuditLogger:
    """Maintain audit trail of important actions"""
    
    def log_action(self, user_id: str, action: str, resource: str, details: dict):
        """Log user actions for audit"""
        
        audit_entry = {
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': self.get_session_id()
        }
        
        # Store in audit log
        self.save_audit_entry(audit_entry)
    
    def save_audit_entry(self, entry: dict):
        """Save audit entry to secure storage"""
        
        # Implementation would save to tamper-proof storage
        # Consider blockchain or append-only logs
        pass
```

### Data Retention
```python
# Data retention policies
class DataRetentionPolicy:
    """Manage data retention according to policies"""
    
    def __init__(self):
        self.retention_periods = {
            'audit_logs': 365,  # 1 year
            'user_sessions': 30,  # 30 days
            'graphics_data': 1825,  # 5 years
            'security_events': 2555  # 7 years
        }
    
    def cleanup_expired_data(self):
        """Remove expired data according to retention policies"""
        
        for data_type, retention_days in self.retention_periods.items():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            self.delete_data_before(data_type, cutoff_date)
    
    def delete_data_before(self, data_type: str, cutoff_date: datetime):
        """Delete data of specified type before cutoff date"""
        
        # Implementation would safely delete expired data
        # Ensure proper backup before deletion
        pass
```

## Security Testing

### Security Testing Framework
```python
# Security testing utilities
class SecurityTests:
    """Security testing utilities"""
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        
        malicious_inputs = [
            "'; DROP TABLE graphics; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]
        
        for input_data in malicious_inputs:
            # Test each endpoint with malicious input
            response = self.test_endpoint_with_input(input_data)
            assert response.status_code != 500, "SQL injection vulnerability detected"
    
    def test_xss(self):
        """Test for XSS vulnerabilities"""
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            response = self.test_endpoint_with_input(payload)
            assert payload not in response.text, "XSS vulnerability detected"
    
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        
        # Test accessing protected endpoints without authentication
        protected_endpoints = ['/api/admin', '/api/graphics/create']
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 401, "Authentication bypass detected"
```

## Security Best Practices

### Development Guidelines
1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Defense in Depth**: Multiple security layers
3. **Secure by Default**: Secure configurations out of the box
4. **Regular Updates**: Keep dependencies and systems updated
5. **Security Testing**: Regular security assessments

### Operational Guidelines
1. **Regular Audits**: Periodic security audits and assessments
2. **Incident Response**: Clear procedures for security incidents
3. **Monitoring**: Continuous security monitoring and alerting
4. **Training**: Regular security training for development team
5. **Documentation**: Maintain up-to-date security documentation

### Compliance Requirements
1. **Data Protection**: Compliance with data protection regulations
2. **Access Controls**: Proper access control implementation
3. **Audit Trails**: Comprehensive audit logging
4. **Data Retention**: Proper data retention and deletion policies
5. **Security Standards**: Adherence to security standards and frameworks

---

**Architecture Version**: 1.0  
**Last Updated**: 2025-01-17  
**Related Documentation**: [Dashboard Security SOP](../sops/dashboard-security.md), [Authentication System](./authentication-system.md)
