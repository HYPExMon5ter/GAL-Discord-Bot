---
id: sops.canvas_locking_management
version: 2.0
last_updated: 2025-10-11
tags: [sop, canvas, locking, conflicts, emergency]
---

# Canvas Locking Management SOP

## Overview
This Standard Operating Procedure (SOP) details the management of canvas locking mechanisms within the Live Graphics Dashboard 2.0, including conflict resolution and emergency procedures.

## Purpose
- Prevent concurrent editing conflicts on graphics canvases
- Provide clear procedures for lock acquisition and release
- Establish conflict resolution protocols
- Enable emergency override capabilities when needed

## Scope
- Canvas lock acquisition and release
- Lock conflict resolution
- Emergency override procedures
- Lock timeout management
- Multi-user coordination

## Prerequisites
- Completed Dashboard Operations SOP training
- Understanding of multi-user systems
- Appropriate lock management permissions
- Knowledge of emergency procedures

## Lock System Architecture

### Lock Types
1. **Edit Locks** - Prevent concurrent modifications
2. **View Locks** - Ensure stable viewing during presentations
3. **System Locks** - Applied during maintenance or updates
4. **Emergency Locks** - Override all other locks for critical situations

### Lock States
```
Lock State Flow:
UNLOCKED → LOCKING → LOCKED → RELEASING → UNLOCKED
                ↓           ↓
          EXPIRED ← TIMEOUT ← AUTO_RELEASE
```

### Lock Hierarchy
1. **Emergency Locks** (Priority 1)
   - System administrator only
   - Override all other locks
   - Immediate effect

2. **System Locks** (Priority 2)
   - Automated system processes
   - Maintenance operations
   - Scheduled updates

3. **Edit Locks** (Priority 3)
   - User-initiated editing
   - Manual operation creation
   - Graphic modifications

4. **View Locks** (Priority 4)
   - Presentation mode
   - Live broadcasting
   - Demonstration purposes

## Standard Operating Procedures

### 1. Lock Acquisition

#### 1.1 Standard Lock Request
1. **Pre-Lock Checks**
   ```javascript
   // Check canvas status before requesting lock
   const canvasStatus = await getCanvasStatus(canvasId);
   
   if (canvasStatus.lock) {
     console.log('Canvas already locked by:', canvasStatus.lock.user);
     return false;
   }
   
   if (canvasStatus.activeUsers > 0) {
     notifyActiveUsers(canvasId, 'Lock request pending');
   }
   ```

2. **Lock Request Process**
   - Select desired canvas
   - Click "Lock Canvas" button
   - Specify lock duration (max 60 minutes)
   - Provide lock purpose/description
   - Confirm lock request

3. **Lock Confirmation**
   - System validates lock request
   - Lock assigned to requesting user
   - Lock timer starts
   - Other users notified of lock status

#### 1.2 Lock Duration Management
1. **Standard Duration Limits**
   - Quick edits: 5-15 minutes
   - Complex modifications: 30-60 minutes
   - Batch operations: 60-120 minutes (requires approval)
   - Emergency situations: Unlimited (manager approval)

2. **Lock Extension Process**
   - Request extension before expiration
   - Provide justification for extension
   - Get approval if exceeding standard limits
   - Update lock expiration time

### 2. Lock Release

#### 2.1 Standard Release Procedure
1. **Manual Release**
   - Complete all canvas modifications
   - Save all changes
   - Click "Release Lock" button
   - Confirm release action

2. **Automatic Release**
   - Lock expires after specified duration
   - System automatically releases lock
   - Users notified of lock availability
   - Changes auto-saved if configured

#### 2.2 Pre-Release Checklist
- [ ] All changes saved
- [ ] Graphic functionality tested
- [ ] No unsaved modifications
- [ ] Dependencies updated
- [ ] Documentation completed
- [ ] Team members notified

### 3. Lock Conflict Resolution

#### 3.1 Conflict Detection
```javascript
// Real-time conflict detection
const lockConflict = {
  detected: true,
  canvasId: 'canvas_123',
  currentLock: {
    userId: 'user_456',
    userName: 'John Doe',
    lockType: 'edit',
    expiresAt: '2025-01-11T15:30:00Z',
    purpose: 'Updating lower third graphics'
  },
  requestingUser: 'user_789',
  requestingUserName: 'Jane Smith',
  conflictType: 'edit_lock_active'
};
```

#### 3.2 Conflict Resolution Strategies
1. **Wait for Release**
   - Monitor lock expiration
   - Notify current lock holder
   - Set up notification for lock availability
   - Plan work around lock schedule

2. **Negotiated Handoff**
   - Contact current lock holder
   - Coordinate transition timing
   - Transfer lock ownership
   - Ensure change continuity

3. **Force Release (Emergency Only)**
   - Escalate to manager
   - Document emergency situation
   - Obtain override approval
   - Execute force release

#### 3.3 Conflict Resolution Workflow
```
Conflict Detected → Assess Impact → Choose Resolution Strategy
                                   ↓                    ↓
                            Wait/Negotiate      Emergency Override
                                   ↓                    ↓
                            Resolution Complete    Documentation Required
```

### 4. Emergency Procedures

#### 4.1 Emergency Override Conditions
1. **System Critical Issues**
   - Graphics not displaying during live event
   - System-wide failures affecting broadcasts
   - Security vulnerabilities requiring immediate fix
   - Data corruption threatening operations

2. **Broadcast Emergency**
   - Live event technical difficulties
   - Breaking news requiring immediate graphic changes
   - Sponsor logo errors or compliance issues
   - Score/information accuracy problems

#### 4.2 Emergency Override Process
1. **Immediate Response**
   ```bash
   # Emergency lock override (admin only)
   POST /api/admin/locks/emergency-override
   {
     "canvasId": "canvas_123",
     "reason": "Live broadcast score error",
     "overrideUser": "admin_001",
     "justification": "Incorrect score being displayed to 50k+ viewers"
   }
   ```

2. **Override Actions**
   - Force release existing lock
   - Assign emergency lock to authorized user
   - Notify all affected users
   - Log override with detailed justification

3. **Post-Emergency Procedures**
   - Document emergency situation
   - Analyze root cause
   - Update procedures if needed
   - Conduct team debrief

#### 4.3 Emergency Lock Types
1. **Broadcast Emergency Lock**
   - Priority: Immediate
   - Duration: Until resolved
   - Authorization: Broadcast Manager
   - Notification: All users immediately

2. **System Emergency Lock**
   - Priority: High
   - Duration: System-dependent
   - Authorization: System Administrator
   - Notification: IT and operations teams

### 5. Lock Management Best Practices

#### 5.1 Proactive Lock Management
1. **Lock Planning**
   - Schedule lock usage in advance
   - Coordinate with team members
   - Plan for extended operations
   - Communicate lock schedules

2. **Lock Etiquette**
   - Release locks as soon as possible
   - Communicate lock status to team
   - Avoid unnecessary lock extensions
   - Respect others' lock schedules

#### 5.2 Lock Monitoring
```javascript
// Lock status monitoring dashboard
const lockMetrics = {
  totalLocks: 15,
  activeLocks: 8,
  expiredLocks: 2,
  conflictsToday: 3,
  averageLockDuration: 25, // minutes
  longestActiveLock: {
    user: 'John Doe',
    duration: 45,
    canvas: 'main_score_bug'
  }
};
```

#### 5.3 Performance Considerations
1. **System Load**
   - Monitor lock operation performance
   - Optimize database queries
   - Implement caching for frequent checks
   - Scale resources during peak usage

2. **Database Optimization**
   ```sql
   -- Optimize lock queries
   CREATE INDEX idx_locks_canvas_active ON locks(canvas_id, is_active);
   CREATE INDEX idx_locks_expires ON locks(expires_at);
   CREATE INDEX idx_locks_user ON locks(user_id, is_active);
   ```

### 6. Lock System Administration

#### 6.1 Lock Audit Procedures
1. **Daily Audit**
   - Review active locks
   - Identify expired locks not released
   - Check for unusual lock patterns
   - Verify lock compliance

2. **Weekly Analysis**
   - Analyze lock usage patterns
   - Identify bottlenecks
   - Review conflict resolution effectiveness
   - Generate performance reports

#### 6.2 Lock Cleanup Procedures
```bash
# Automated cleanup script
#!/bin/bash
# cleanup_expired_locks.sh

# Find expired locks
EXPIRED_LOCKS=$(psql -d gal_dashboard -c "
  SELECT id, user_id, canvas_id, expires_at 
  FROM locks 
  WHERE expires_at < NOW() AND is_active = true;
")

# Release expired locks
if [ ! -z "$EXPIRED_LOCKS" ]; then
  echo "Releasing expired locks:"
  echo "$EXPIRED_LOCKS"
  
  psql -d gal_dashboard -c "
    UPDATE locks 
    SET is_active = false, released_at = NOW() 
    WHERE expires_at < NOW() AND is_active = true;
  "
  
  # Notify users of expired lock release
  # ... notification logic
fi
```

### 7. Troubleshooting

#### 7.1 Common Lock Issues
1. **Lock Not Releasing**
   - Problem: Lock remains active after expiration
   - Solution: Manual database intervention, restart lock service
   - Prevention: Regular cleanup procedures, monitoring

2. **Lock Acquisition Failure**
   - Problem: Unable to acquire lock on available canvas
   - Solution: Check user permissions, clear browser cache, retry
   - Prevention: Regular permission audits, system maintenance

3. **Multiple Locks on Same Canvas**
   - Problem: System allows concurrent locks
   - Solution: Database constraint enforcement, code review
   - Prevention: Comprehensive testing, code reviews

#### 7.2 Performance Issues
1. **Slow Lock Operations**
   - Monitor database performance
   - Optimize lock queries
   - Implement connection pooling
   - Add caching layers

2. **High Memory Usage**
   - Review lock data structures
   - Implement lock cleanup
   - Optimize memory allocation
   - Monitor system resources

### 8. Integration with Other Systems

#### 8.1 WebSocket Integration
```javascript
// Real-time lock status updates
socket.on('lock_status_change', (data) => {
  const { canvasId, lockStatus, userId } = data;
  
  if (lockStatus === 'locked' && userId !== currentUserId) {
    showNotification(`Canvas ${canvasId} locked by ${getUserName(userId)}`);
    disableCanvasEditing(canvasId);
  } else if (lockStatus === 'unlocked') {
    hideNotification(`Canvas ${canvasId} is now available`);
    enableCanvasEditing(canvasId);
  }
});
```

#### 8.2 API Integration
```javascript
// REST API for lock management
const lockAPI = {
  async acquireLock(canvasId, duration, purpose) {
    return await fetch('/api/locks/acquire', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ canvasId, duration, purpose })
    });
  },
  
  async releaseLock(lockId) {
    return await fetch(`/api/locks/${lockId}/release`, {
      method: 'POST'
    });
  },
  
  async extendLock(lockId, additionalTime) {
    return await fetch(`/api/locks/${lockId}/extend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ additionalTime })
    });
  }
};
```

## Training Requirements

### Lock Management Training
- Lock system architecture understanding
- Conflict resolution procedures
- Emergency override protocols
- Performance monitoring

### Emergency Response Training
- Emergency identification criteria
- Override authorization process
- Post-emergency documentation
- Communication protocols

## Documentation Requirements

### Lock Logging
Every lock operation must log:
- Timestamp and user
- Canvas ID and lock type
- Operation type (acquire/release/extend)
- Lock duration and purpose
- Any conflicts or issues

### Incident Reporting
Emergency overrides require:
- Detailed situation description
- Justification for override
- Actions taken
- Resolution outcome
- Lessons learned

## References
- [Dashboard Operations SOP](dashboard-operations.md)
- [Emergency Rollback SOP](emergency-rollback.md)
- [API Documentation](../system/api-backend-system.md)
- [Security SOP](security.md)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: Operations Manager
- **Classification**: Internal Use Only
