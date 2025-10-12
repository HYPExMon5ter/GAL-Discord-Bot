---
id: sops.dashboard_security
version: 2.0
last_updated: 2025-10-11
tags: [sop, security, authentication, sessions, passwords]
---

# Dashboard Security SOP

## Overview
This Standard Operating Procedure (SOP) outlines the security protocols for accessing and operating the Live Graphics Dashboard 2.0, including password management, session security, and access control.

## Purpose
- Protect sensitive dashboard functionality and data
- Ensure secure authentication and authorization
- Maintain session integrity and prevent unauthorized access
- Provide clear security guidelines for all operators

## Scope
- User authentication and authorization
- Password management policies
- Session security procedures
- Access control and permissions
- Security incident response

## Prerequisites
- Completed security awareness training
- Understanding of basic security principles
- Appropriate security clearance level
- Knowledge of incident reporting procedures

## Authentication System Architecture

### Authentication Methods
1. **NextAuth.js Integration**
   - OAuth 2.0 compliant
   - Multi-provider support
   - Session management
   - Token-based authentication

2. **Multi-Factor Authentication (MFA)**
   - Time-based One-Time Password (TOTP)
   - SMS verification
   - Backup codes
   - Hardware token support

3. **Role-Based Access Control (RBAC)**
   - Operator roles
   - Administrative permissions
   - Granular access control
   - Temporary access grants

### Security Zones
```
Security Architecture:
├── Public Zone (No Authentication)
│   └── Marketing pages, public information
├── Authentication Zone (Login Required)
│   └── Dashboard access, basic features
├── Operations Zone (Operator Role)
│   └── Graphic management, canvas operations
├── Administrative Zone (Admin Role)
│   └── User management, system configuration
└── System Zone (Super Admin)
    └── Security settings, critical operations
```

## Security Procedures

### 1. Password Management

#### 1.1 Password Requirements
- **Minimum Length**: 12 characters
- **Complexity Requirements**:
  - Uppercase letters (A-Z)
  - Lowercase letters (a-z)
  - Numbers (0-9)
  - Special characters (!@#$%^&*)
- **Prohibited**: Common patterns, dictionary words, personal information
- **Expiration**: 90 days maximum
- **History**: Cannot reuse last 5 passwords

#### 1.2 Password Creation Guidelines
```javascript
// Password validation function
function validatePassword(password) {
  const requirements = {
    minLength: 12,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumbers: /\d/.test(password),
    hasSpecial: /[!@#$%^&*]/.test(password),
    notCommon: !isCommonPassword(password),
    notPersonal: !containsPersonalInfo(password)
  };
  
  return requirements;
}
```

#### 1.3 Password Storage and Transmission
- **Storage**: Hashed with bcrypt (minimum 12 rounds)
- **Salt**: Unique per user
- **Transmission**: HTTPS/TLS 1.3 only
- **Memory**: Clear after authentication
- **Logs**: Never store or log passwords

#### 1.4 Password Reset Procedures
1. **Self-Service Reset**
   - User requests password reset
   - Email verification sent
   - Time-limited reset link (15 minutes)
   - Security question verification

2. **Administrative Reset**
   - Identity verification required
   - Manager approval needed
   - Temporary password generated
   - Forced change on first login

### 2. Multi-Factor Authentication

#### 2.1 MFA Configuration
```javascript
// TOTP setup for users
const setupMFA = async (userId) => {
  const secret = generateTOTPSecret();
  const qrCode = generateQRCode(secret, 'GAL Dashboard', user.email);
  
  await user.update({
    mfaSecret: encryptedSecret,
    mfaEnabled: false, // Pending verification
    backupCodes: generateBackupCodes()
  });
  
  return { secret, qrCode, backupCodes };
};
```

#### 2.2 MFA Enforcement
- **Required for**: All remote access
- **Exemptions**: Local network access (with approval)
- **Backup Options**: 10 single-use backup codes
- **Recovery**: Administrator verification required

#### 2.3 Session Management
```javascript
// Secure session configuration
const sessionConfig = {
  strategy: 'database',
  maxAge: 8 * 60 * 60, // 8 hours
  updateAge: 2 * 60 * 60, // 2 hours
  cookieSecurity: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'strict',
    name: '__Secure-gal-session'
  }
};
```

### 3. Access Control

#### 3.1 Role Definitions
1. **Viewer** (Level 1)
   - View-only access to graphics
   - No editing capabilities
   - Read-only API access

2. **Operator** (Level 2)
   - Create and edit graphics
   - Manage canvas operations
   - Access to operational features

3. **Manager** (Level 3)
   - User management
   - Configuration access
   - Report generation
   - Emergency procedures

4. **Administrator** (Level 4)
   - System configuration
   - Security settings
   - Backup and restore
   - Full system access

#### 3.2 Permission Matrix
```
Feature                 | Viewer | Operator | Manager | Admin
------------------------|--------|----------|---------|-------
View Graphics           |   ✓    |    ✓     |    ✓    |   ✓
Edit Graphics           |        |    ✓     |    ✓    |   ✓
Manage Canvases         |        |    ✓     |    ✓    |   ✓
User Management         |        |          |    ✓    |   ✓
System Configuration    |        |          |         |   ✓
Security Settings       |        |          |         |   ✓
Emergency Procedures    |        |          |    ✓    |   ✓
```

#### 3.3 Access Request Process
1. **Initial Access Request**
   - Complete access request form
   - Manager approval required
   - Security review for sensitive roles
   - Background check for admin access

2. **Access Provisioning**
   - Create user account
   - Assign appropriate role
   - Send temporary credentials
   - MFA enrollment required

3. **Access Review**
   - Quarterly access audits
   - Role appropriateness review
   - Inactive account cleanup
   - Permission adjustments

### 4. Session Security

#### 4.1 Session Management Best Practices
1. **Secure Session Configuration**
   ```javascript
   // NextAuth.js secure configuration
   export const authOptions = {
     session: {
       strategy: 'database',
       maxAge: 8 * 60 * 60, // 8 hours
       updateAge: 2 * 60 * 60, // 2 hours
     },
     useSecureCookies: process.env.NODE_ENV === 'production',
     cookies: {
       sessionToken: {
         name: '__Secure-next-auth.session-token',
         options: {
           httpOnly: true,
           sameSite: 'lax',
           path: '/',
           secure: true,
           domain: '.gal.gg'
         }
       }
     }
   };
   ```

2. **Session Monitoring**
   ```javascript
   // Active session monitoring
   const monitorSessions = async () => {
     const activeSessions = await db.session.findMany({
       where: {
         expires: { gte: new Date() }
       },
       include: {
         user: {
           select: { name: true, email: true, role: true }
         }
       }
     });
     
     // Alert on unusual patterns
     const suspiciousSessions = detectSuspiciousSessions(activeSessions);
     if (suspiciousSessions.length > 0) {
       await securityAlert(suspiciousSessions);
     }
   };
   ```

#### 4.2 Concurrent Session Management
- **Maximum Sessions**: 3 per user
- **Session Priority**: Most recent takes precedence
- **Old Session Handling**: Graceful notification and logout
- **Mobile Session Detection**: Different limits for mobile devices

#### 4.3 Idle Session Timeout
```javascript
// Idle timeout implementation
const IdleTimer = {
  timeout: 30 * 60 * 1000, // 30 minutes
  warning: 5 * 60 * 1000,  // 5 minute warning
  
  setup() {
    let timer;
    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(this.handleTimeout, this.timeout);
    };
    
    // Listen for user activity
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(
      event => document.addEventListener(event, resetTimer, true)
    );
  },
  
  handleTimeout() {
    showIdleWarning();
    setTimeout(forceLogout, 5 * 60 * 1000); // 5 minutes to respond
  }
};
```

### 5. Security Monitoring

#### 5.1 Login Monitoring
```javascript
// Security event tracking
const securityEvents = {
  login: {
    success: 'auth.login.success',
    failure: 'auth.login.failure',
    blocked: 'auth.login.blocked'
  },
  mfa: {
    success: 'auth.mfa.success',
    failure: 'auth.mfa.failure',
    bypass: 'auth.mfa.bypass'
  },
  session: {
    created: 'auth.session.created',
    expired: 'auth.session.expired',
    terminated: 'auth.session.terminated'
  }
};

// Track failed login attempts
const trackFailedLogin = async (email, ip, userAgent) => {
  await db.securityLog.create({
    data: {
      event: 'auth.login.failure',
      email,
      ip,
      userAgent,
      timestamp: new Date()
    }
  });
  
  const recentFailures = await getRecentFailures(email, ip);
  if (recentFailures.length >= 5) {
    await blockIPAddress(ip, 15 * 60); // 15 minutes
    await notifySecurityTeam(email, ip);
  }
};
```

#### 5.2 Anomaly Detection
1. **Unusual Login Patterns**
   - New geographic locations
   - Unusual time patterns
   - Multiple failed attempts
   - Rapid session creation

2. **Behavioral Anomalies**
   - Unusual feature access
   - Bulk data export
   - Configuration changes
   - Privilege escalation attempts

#### 5.3 Security Alerts
```javascript
// Alert configuration
const securityAlerts = {
  critical: {
    channels: ['email', 'sms', 'slack'],
    recipients: ['security-team@gal.gg', 'ops-manager@gal.gg'],
    escalation: 'immediate'
  },
  high: {
    channels: ['email', 'slack'],
    recipients: ['security-team@gal.gg'],
    escalation: '15 minutes'
  },
  medium: {
    channels: ['email'],
    recipients: ['security-team@gal.gg'],
    escalation: '1 hour'
  }
};
```

### 6. Incident Response

#### 6.1 Security Incident Classification
1. **Critical Incidents**
   - System compromise
   - Data breach
   - Unauthorized admin access
   - Widespread account compromise

2. **High Priority Incidents**
   - Single account compromise
   - Privilege escalation
   - Brute force attacks
   - Suspicious data access

3. **Medium Priority Incidents**
   - Failed login patterns
   - Policy violations
   - Access anomalies
   - Configuration security issues

#### 6.2 Incident Response Procedures
1. **Immediate Response**
   ```bash
   # Emergency lockdown procedure
   # Block affected accounts
   docker exec api python manage.py block_user --user-id <ID>
   
   # Force logout all sessions
   docker exec api python manage.py revoke_all_sessions
   
   # Enable enhanced monitoring
   docker exec api python manage.py enable_security_monitoring --level high
   ```

2. **Investigation**
   - Preserve forensic evidence
   - Analyze access logs
   - Identify compromised accounts
   - Determine impact scope

3. **Recovery**
   - Reset compromised credentials
   - Patch vulnerabilities
   - Review access controls
   - Update security procedures

#### 6.3 Communication Procedures
1. **Internal Communication**
   - Security team notification
   - Management briefing
   - Technical team coordination
   - All-staff announcements

2. **External Communication** (if required)
   - Legal notification
   - Regulatory reporting
   - Customer notification
   - Public statements

### 7. Security Configuration

#### 7.1 HTTPS Configuration
```nginx
# SSL/TLS configuration
server {
    listen 443 ssl http2;
    server_name dashboard.gal.gg;
    
    ssl_certificate /etc/ssl/certs/gal.gg.crt;
    ssl_certificate_key /etc/ssl/private/gal.gg.key;
    
    ssl_protocols TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Other security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

#### 7.2 Content Security Policy
```javascript
// CSP configuration
const contentSecurityPolicy = {
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'unsafe-eval'", "https://cdn.gal.gg"],
    styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
    fontSrc: ["'self'", "https://fonts.gstatic.com"],
    imgSrc: ["'self'", "data:", "https://assets.gal.gg"],
    connectSrc: ["'self'", "wss://api.gal.gg"],
    frameSrc: ["'none'"],
    objectSrc: ["'none'"],
    baseUri: ["'self'"],
    formAction: ["'self'"],
    frameAncestors: ["'none'"],
    upgradeInsecureRequests: []
  }
};
```

### 8. Backup and Recovery Security

#### 8.1 Secure Backup Procedures
1. **Encryption**
   - AES-256 encryption for all backups
   - Separate encryption keys management
   - Key rotation every 90 days
   - Secure key storage

2. **Access Control**
   - Backup access restricted to admins
   - Audit trail for backup operations
   - Multi-person approval for restores
   - Time-limited restore permissions

#### 8.2 Recovery Security
```bash
# Secure recovery procedures
# 1. Verify backup integrity
gpg --verify backup.sig backup.tar.gz

# 2. Decrypt backup
gpg --decrypt backup.tar.gz.gpg > backup.tar.gz

# 3. Extract in secure environment
mkdir /tmp/recovery
tar -xzf backup.tar.gz -C /tmp/recovery

# 4. Verify data before restore
python verify_backup_integrity.py /tmp/recovery

# 5. Execute restore with logging
python restore_database.py /tmp/recovery --log-file restore.log
```

## Training Requirements

### Security Awareness Training
- Password best practices
- Phishing recognition
- Social engineering awareness
- Incident reporting procedures

### Role-Specific Training
- Administrators: Security configuration, incident response
- Managers: Access control, security monitoring
- Operators: Session security, basic security practices

## Compliance and Auditing

### Security Audits
- Quarterly security assessments
- Annual penetration testing
- Compliance verification
- Security policy review

### Logging Requirements
All security events must log:
- Timestamp and user
- Event type and details
- IP address and user agent
- Outcome and response
- Investigation follow-up

## References
- [Security SOP](security.md)
- [Incident Response SOP](incident-response.md)
- [API Security Documentation](../system/api-backend-system.md)
- [Access Control Policies](../system/access-control.md)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: Security Manager
- **Classification**: Internal Use Only
