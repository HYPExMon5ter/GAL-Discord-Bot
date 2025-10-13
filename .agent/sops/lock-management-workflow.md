# Lock Management Workflow SOP

## Overview
This SOP outlines the standard operating procedures for managing canvas locks in the Live Graphics Dashboard.

## Lock System Behavior

### Lock Acquisition
- **Endpoint**: `POST /api/lock/{graphic_id}`
- **Duration**: 5 minutes (300 seconds)
- **User**: Single user per graphic
- **Auto-cleanup**: Expired locks are automatically cleaned up

### Lock Release
- **Manual**: `DELETE /api/lock/{graphic_id}`
- **Auto**: Expire after 5 minutes of inactivity
- **Cleanup**: Use `POST /api/maintenance/cleanup-locks` for expired locks

## Lock Status Checking

### Frontend Status Polling
- **Frequency**: Every 30 seconds
- **Endpoint**: `GET /api/lock/{graphic_id}/status`
- **Response**: Lock status with countdown timer

### Visual Indicators
- **Unlocked**: Normal edit button
- **Locked by self**: "Edit" button with countdown
- **Locked by others**: "View" button with "In Use" badge

## Troubleshooting Lock Issues

### Stale Locks
**Symptoms**: Graphic shows as locked but no one is editing
**Solution**: 
1. Use maintenance endpoint: `POST /api/maintenance/cleanup-locks`
2. Manual database cleanup (admin only)

### Lock Not Releasing
**Symptoms**: User cannot release lock after editing
**Solution**:
1. Wait for automatic expiration (5 minutes)
2. Use manual cleanup endpoint
3. Check network connectivity

### Multiple Users on Same Graphic
**Symptoms**: Two users can edit simultaneously
**Solution**:
1. Check lock status endpoint response
2. Verify lock acquisition logic
3. Review frontend state management

## Lock Maintenance

### Daily Cleanup
Run lock cleanup to remove expired locks:
```bash
POST /api/maintenance/cleanup-locks
```

### Database Monitoring
Monitor for:
- Expired locks not cleaned up
- Orphaned locks (no associated graphic)
- Long-running locks (> 5 minutes)

## Best Practices

1. **Always release locks** when finished editing
2. **Save work frequently** during editing sessions
3. **Check lock status** before attempting to edit
4. **Use maintenance cleanup** for performance optimization
5. **Monitor lock metrics** for system health

## Error Handling

### Common Errors
- **404 Not Found**: Graphic doesn't exist
- **409 Conflict**: Lock already held by another user
- **400 Bad Request**: Invalid lock request

### Recovery Procedures
1. Refresh the page to clear stale state
2. Wait for lock expiration
3. Use maintenance cleanup tools
4. Contact admin for manual intervention

## Security Considerations

- Locks are tied to authenticated users
- Lock ownership cannot be transferred
- Admin users can override locks via maintenance endpoints
- Lock expiration prevents permanent locking

---

**Version**: 1.0  
**Created**: 2025-01-09  
**Owner**: Guardian Angel League Development Team
