# Archive and Deletion Process SOP

## Overview
This SOP defines the standard procedures for archiving and permanently deleting graphics in the Live Graphics Dashboard.

## Graphic Lifecycle

### 1. Active Graphics
- **Status**: `archived = false`
- **Visibility**: Main graphics tab
- **Operations**: Edit, Archive, Delete (soft delete)

### 2. Archived Graphics
- **Status**: `archived = true`
- **Visibility**: Archive tab
- **Operations**: Restore, Permanent Delete (admin only)

### 3. Permanent Deletion
- **Action**: Physical removal from database
- **Requirements**: Admin permissions
- **Warning**: Irreversible operation

## Archive Process

### Frontend Archive
1. **User Action**: Click "Archive" on active graphic
2. **API Call**: `POST /api/archive/{graphic_id}`
3. **Request Body**: `{}` (empty object)
4. **Response**: Archive confirmation with metadata

### API Archive Process
1. **Validate Lock**: Check if graphic is locked
2. **Create Archive Record**: Store metadata in archive table
3. **Update Graphic**: Set `archived = true`
4. **Release Lock**: Remove any active locks
5. **Return Success**: Archive response with details

### Archive Response Format
```json
{
  "success": true,
  "message": "Graphic archived successfully",
  "graphic_id": 123,
  "archived_at": "2025-01-09T10:30:00Z"
}
```

## Restore Process

### Frontend Restore
1. **User Action**: Click "Restore" on archived graphic
2. **API Call**: `POST /api/archive/{graphic_id}/restore`
3. **Response**: Restore confirmation

### API Restore Process
1. **Validate Archive**: Check archive record exists
2. **Update Graphic**: Set `archived = false`
3. **Update Archive**: Set restoration timestamp
4. **Return Success**: Restore response

## Deletion Process

### Soft Delete (Archive)
- **Endpoint**: `DELETE /api/graphics/{graphic_id}`
- **Action**: Archives the graphic (sets `archived = true`)
- **User Access**: All authenticated users
- **Reversible**: Yes (via restore)

### Permanent Delete
- **Endpoint**: `DELETE /api/archive/{graphic_id}/permanent`
- **Action**: Physical deletion from database
- **User Access**: Admin users only
- **Reversible**: No

## Archive Management

### Archive Statistics
- Total archived graphics
- Archive frequency by user
- Archive age distribution
- Restoration rates

### Archive Cleanup
- Review old archives periodically
- Identify candidates for permanent deletion
- Maintain archive retention policies

## Error Handling

### Archive Errors
- **400 Bad Request**: Graphic is locked
- **404 Not Found**: Graphic doesn't exist
- **409 Conflict**: Archive operation in progress

### Restore Errors
- **400 Bad Request**: Graphic not archived
- **404 Not Found**: Archive record doesn't exist

### Delete Errors
- **404 Not Found**: Graphic doesn't exist
- **403 Forbidden**: Insufficient permissions
- **409 Conflict**: Graphic is locked

## Troubleshooting

### Archive Issues
1. **Check lock status** before archiving
2. **Verify graphic exists** in database
3. **Check network connectivity** for API calls
4. **Review permissions** for user actions

### Restore Issues
1. **Verify archive record** exists
2. **Check graphic status** in database
3. **Validate user permissions**
4. **Check for conflicts** with active operations

### Deletion Issues
1. **Confirm admin permissions** for permanent delete
2. **Check graphic lock status**
3. **Verify archive record exists**
4. **Check database constraints**

## Best Practices

1. **Archive before deletion** to maintain recovery options
2. **Check lock status** before archive/delete operations
3. **Use descriptive archive reasons** when available
4. **Regular archive cleanup** to manage database size
5. **Test restore process** before permanent deletion

## Security Considerations

- Archive operations are logged with user attribution
- Permanent deletion requires admin permissions
- Archive metadata preserves audit trail
- Lock checks prevent concurrent modifications
- API authentication protects all operations

## Monitoring

### Key Metrics
- Archive success/failure rates
- Time to archive operations
- Archive size growth over time
- Permanent deletion frequency
- User archive patterns

### Alerts
- High archive failure rates
- Unusual permanent deletion patterns
- Archive size exceeding thresholds
- Lock-related archive failures

---

**Version**: 1.0  
**Created**: 2025-01-09  
**Owner**: Guardian Angel League Development Team
