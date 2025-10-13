---
id: sops.lock_refresh
version: 1.0
last_updated: 2025-10-13
tags: [sop, canvas-locking, lock-management, operations]
---

# Canvas Lock Refresh SOP

## Overview
This Standard Operating Procedure (SOP) outlines the processes for managing and refreshing canvas locks in the Guardian Angel League Live Graphics Dashboard, ensuring proper lock lifecycle management and preventing conflicts.

## Purpose
- Maintain proper canvas lock lifecycle
- Prevent lock expiration during extended editing sessions
- Handle lock conflicts and resolution
- Ensure data integrity during collaborative editing

## Scope
- Canvas lock acquisition and maintenance
- Lock refresh mechanisms and procedures
- Lock conflict resolution
- Lock timeout management
- User notification for lock operations

## Prerequisites

### Required Permissions
- **Administrator**: Full lock management access
- **Moderator**: Lock acquisition, refresh, and release
- **Operator**: Lock acquisition and refresh
- **Viewer**: No lock management access

### System Requirements
- Active Dashboard access with canvas editing permissions
- Stable WebSocket connection for real-time updates
- Valid user session
- Active canvas editing session

## Lock Lifecycle Management

### Lock Acquisition
1. **Automatic Lock Acquisition**
   - User navigates to `/canvas/edit/{id}` route
   - System checks for existing locks on graphic
   - If no lock exists, system automatically creates lock
   - Lock assigned to current user with expiration time

2. **Lock Acquisition Validation**
   - Verify user has editing permissions
   - Check graphic is not locked by another user
   - Validate lock acquisition prerequisites
   - Create lock record with metadata

3. **Lock Acquisition Response**
   - Display lock status to user
   - Start automatic lock refresh timer
   - Notify other users of lock status
   - Log lock acquisition event

### Lock Refresh Mechanisms

#### Automatic Lock Refresh
1. **Background Refresh Process**
   - System initiates refresh every 15 minutes
   - WebSocket connection sends refresh request
   - Server validates lock ownership and extends expiration
   - Client receives confirmation of refresh success

2. **Refresh Validation**
   - Verify lock belongs to current user
   - Check user session validity
   - Validate active editing state
   - Extend lock expiration time (typically +30 minutes)

3. **Refresh Failure Handling**
   - Log refresh failure events
   - Notify user of refresh issues
   - Implement retry mechanism (up to 3 attempts)
   - Fallback to manual refresh if automatic fails

#### Manual Lock Refresh
1. **Manual Refresh Trigger**
   - User clicks "Refresh Lock" button
   - System displays lock status with remaining time
   - Manual refresh available when < 5 minutes remaining
   - Refresh button disabled during automatic refresh

2. **Manual Refresh Process**
   - Send explicit lock refresh request
   - Server validates and extends lock
   - Update UI with new expiration time
   - Display success notification to user

### Lock Release Procedures

#### Automatic Lock Release
1. **Session-Based Release**
   - User navigates away from canvas editor
   - Browser tab or window closed
   - User session expires
   - WebSocket connection lost

2. **Automatic Release Conditions**
   - Lock expiration reached without refresh
   - User inactivity timeout (configurable, default 45 minutes)
   - System maintenance or shutdown
   - Administrative lock release

#### Manual Lock Release
1. **User-Initiated Release**
   - User clicks "Unlock" or "Release Lock" button
   - Confirmation dialog prevents accidental release
   - Lock immediately released and available to others
   - User redirected to graphics list

2. **Administrative Lock Release**
   - Administrators can release any lock
   - Requires administrative permissions
   - Must provide reason for lock override
   - Notifies original lock owner of override

## Lock Conflict Resolution

### Conflict Detection
1. **Lock Status Monitoring**
   - Real-time lock status updates via WebSocket
   - Polling fallback for WebSocket failures
   - Lock conflict detection on edit attempts
   - User presence indicators in canvas

2. **Conflict Scenarios**
   - Multiple users attempt to edit same graphic
   - Lock expiration during active editing
   - Network interruptions causing lock loss
   - Administrative lock overrides

### Conflict Resolution Procedures

#### Standard Conflict Resolution
1. **Conflict Notification**
   - Display lock status to attempting user
   - Show current lock owner and remaining time
   - Provide options to wait or request lock
   - Display estimated wait time if applicable

2. **Lock Request Queue**
   - Add user to lock request queue
   - Notify current lock owner of pending requests
   - Maintain queue order and priorities
   - Auto-notify when lock becomes available

#### Administrative Override
1. **Override Conditions**
   - Emergency situations requiring immediate access
   - Lock owner unresponsive for extended period
   - System maintenance or debugging requirements
   - Security incident response

2. **Override Process**
   - Administrator initiates lock override
   - System requests override reason
   - Lock immediately released and reassigned
   - Original owner notified of override

## Lock Configuration and Settings

### Default Lock Settings
- **Lock Duration**: 30 minutes (configurable)
- **Refresh Interval**: 15 minutes
- **Inactivity Timeout**: 45 minutes
- **Max Queue Size**: 5 users
- **Override Notification**: Required for administrative overrides

### Configurable Parameters
```yaml
canvas_locking:
  default_duration_minutes: 30
  refresh_interval_minutes: 15
  inactivity_timeout_minutes: 45
  max_queue_size: 5
  require_admin_override_reason: true
  auto_refresh_enabled: true
  notification_types: ["websocket", "browser_notification"]
```

## Troubleshooting

### Common Lock Issues

#### Lock Acquisition Fails
**Symptoms**: Unable to acquire lock on canvas
**Possible Causes**:
- Another user currently holds the lock
- User lacks editing permissions
- Network connectivity issues
- Lock system temporarily unavailable

**Resolution Steps**:
1. Check current lock status and owner
2. Verify user has editing permissions
3. Test network connectivity
4. Wait for lock to become available
5. Contact lock owner if needed
6. Request administrative override if emergency

#### Lock Refresh Fails
**Symptoms**: Lock refresh notifications showing failures
**Possible Causes**:
- WebSocket connection issues
- Server-side lock validation failures
- Network interruptions
- User session expiration

**Resolution Steps**:
1. Check WebSocket connection status
2. Verify user session is active
3. Test network connectivity
4. Attempt manual lock refresh
5. Reload page and re-establish lock
6. Contact administrator if issue persists

#### Lock Not Released on Exit
**Symptoms**: Lock remains after user leaves canvas
**Possible Causes**:
- Browser closed unexpectedly
- Network connection lost during exit
- JavaScript errors preventing cleanup
- Server-side cleanup failures

**Resolution Steps**:
1. Verify user has actually left the canvas
2. Check user session status
3. Attempt administrative lock release
4. Restart canvas locking service if needed
5. Investigate client-side cleanup mechanisms

### Emergency Lock Procedures

#### Lock System Failure
1. **Immediate Actions**
   - Notify all active canvas users
   - Document current lock states
   - Prevent new lock acquisitions
   - Plan system restart if needed

2. **Recovery Procedures**
   - Restart canvas locking service
   - Validate existing lock states
   - Notify users of system recovery
   - Monitor for recurring issues

3. **Post-Incident Review**
   - Document root cause analysis
   - Review lock system performance
   - Update lock refresh procedures
   - Implement preventive measures

## Monitoring and Metrics

### Lock Performance Metrics
- **Lock Acquisition Rate**: Successful locks per hour
- **Lock Refresh Success Rate**: Percentage of successful refreshes
- **Lock Conflict Rate**: Lock conflicts per day
- **Average Lock Duration**: Typical lock holding time
- **Queue Wait Time**: Average time in lock request queue

### Lock System Health Monitoring
- **WebSocket Connection Health**: Real-time connection status
- **Lock Service Performance**: Response times and error rates
- **Database Lock Performance**: Lock table query performance
- **User Experience Metrics**: Lock-related user satisfaction

### Alert Thresholds
- **Lock Refresh Failure Rate** > 5%: Investigate immediately
- **Lock Conflict Rate** > 10%: Review lock duration settings
- **Average Queue Wait Time** > 10 minutes: Increase lock duration
- **Lock Service Downtime** > 1 minute: Emergency alert

## Quality Assurance

### Lock Validation Checklist
- [ ] Lock successfully acquired by authorized user
- [ ] Lock expiration time properly set
- [ ] Automatic refresh mechanism active
- [ ] User notifications working correctly
- [ ] Lock release on user exit functioning
- [ ] Conflict resolution procedures operational

### Refresh Validation Checklist
- [ ] Automatic refresh initiating every 15 minutes
- [ ] Refresh success rate > 95%
- [ ] Manual refresh option available
- [ ] Refresh failures properly logged
- [ ] User notifications for refresh status
- [ ] Fallback procedures for refresh failures

## Security Considerations

### Lock Access Control
- Verify user permissions before lock operations
- Implement lock ownership validation
- Log all lock operations and modifications
- Regular lock access pattern analysis

### Lock Data Protection
- Secure lock information transmission
- Validate lock ownership on each operation
- Prevent lock manipulation or spoofing
- Implement rate limiting for lock requests

## Related Documentation
- **[Canvas Editor Architecture](../system/canvas-editor-architecture.md)** - Canvas system architecture
- **[Dashboard Operations SOP](./dashboard-operations.md)** - General dashboard operations
- **[WebSocket Integration](../system/websocket-integration.md)** - Real-time communication
- **[Access Control System](../system/access-control.md)** - User permissions and security

## Version History
- **v1.0** (2025-10-13): Initial SOP creation
  - Established lock refresh procedures
  - Defined lock lifecycle management
  - Implemented conflict resolution strategies

---

**Document Owner**: Operations Team  
**Review Frequency**: Monthly  
**Next Review Date**: 2025-11-13  
**Approval**: Dashboard Operations Manager
