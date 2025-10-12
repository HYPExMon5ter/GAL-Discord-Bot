---
id: sops.route-based-canvas-operations
version: 1.0
last_updated: 2025-10-12
tags: [sop, canvas, route-based, operations, workflow, dashboard]
status: active
---

# Route-Based Canvas Operations SOP

## Overview
This Standard Operating Procedure (SOP) details the comprehensive workflow for route-based canvas operations in the Live Graphics Dashboard 2.0, covering both editing and viewing routes.

## Purpose
- Standardize route-based canvas editor usage
- Ensure proper navigation and state management
- Provide clear guidelines for OBS browser source integration
- Maintain efficient graphic creation and viewing workflows

## Scope
- Route-based canvas editor operations (`/canvas/edit/{id}`)
- OBS browser source viewing (`/canvas/view/{id}`)
- Navigation patterns and state management
- Authentication and lock management
- Error handling and recovery procedures

## Prerequisites
- Completed Dashboard Operations SOP training
- Understanding of route-based application architecture
- Familiarity with canvas editing workflows
- Access to Live Graphics Dashboard with appropriate permissions

## Route Structure Overview

### 1. Editor Route (`/canvas/edit/{id}`)
**Purpose**: Full-screen canvas editing interface
**Authentication**: Required (JWT token)
**Lock Management**: Automatic lock acquisition and management

### 2. Viewer Route (`/canvas/view/{id}`)
**Purpose**: OBS browser source rendering
**Authentication**: Not required (public access)
**Lock Management**: Not applicable (read-only)

## Editor Route Operations

### 1. Accessing the Editor

#### 1.1 From Graphics Table
1. **Navigate** to Dashboard → Graphics tab
2. **Locate** the desired graphic in the table
3. **Click** the "Edit" button for the target graphic
4. **System** automatically redirects to `/canvas/edit/{id}`

#### 1.2 Direct URL Access
1. **Enter** URL: `http://dashboard-domain.com/canvas/edit/{id}`
2. **Authentication** redirect if not logged in
3. **Verify** graphic exists and is accessible
4. **Proceed** to editor interface

#### 1.3 From Create Graphic Dialog
1. **Click** "Create New Graphic" in Graphics tab
2. **Fill** required fields (title, event name)
3. **Submit** form to create new graphic
4. **Redirect** to `/canvas/edit/{new-id}` for editing

### 2. Editor Interface Navigation

#### 2.1 Header Controls
```
┌─────────────────────────────────────────────────────────┐
│ [← Back] [Graphic Name]                    [Save] │ Header
└─────────────────────────────────────────────────────────┘
```

**Back Button**: Returns to Graphics tab dashboard
**Graphic Name**: Displays current graphic title (read-only)
**Save Button**: Commits changes to database

#### 2.2 Sidebar Navigation
```
┌─────────┐
│ Design  │ ← Active Tab
│ Elements│
│ Data    │
└─────────┘
```

**Design Tab**: Canvas properties, background, grid settings
**Elements Tab**: Layer management, element selection
**Data Tab**: Data binding and field connections

#### 2.3 Canvas Area Controls
```
                    [Grid][Snap][Zoom+/-] │ Bottom Controls
```

**Grid Toggle**: Enable/disable 20px grid overlay
**Snap Toggle**: Enable/disable snap-to-grid functionality
**Zoom Controls**: Adjust canvas zoom (25% - 400%)

### 3. Lock Management in Editor

#### 3.1 Automatic Lock Acquisition
1. **Load** editor route with graphic ID
2. **System** automatically checks lock status
3. **If available**: Acquire 5-minute lock for current user
4. **If locked**: Display lock conflict dialog with options

#### 3.2 Lock Maintenance
1. **Activity Detection**: User interactions refresh lock timer
2. **Automatic Refresh**: Lock extends with user activity
3. **Expiration Warning**: 30-second warning before lock expiry
4. **Graceful Release**: Lock releases on page exit or timeout

#### 3.3 Lock Conflict Resolution
1. **Detection**: System detects existing lock on graphic
2. **Display**: Lock conflict dialog with lock details
3. **Options**: Wait for release, force override (admin), or return to dashboard
4. **Resolution**: Appropriate action based on user choice

## Viewer Route Operations

### 1. OBS Browser Source Configuration

#### 1.1 Basic Setup
1. **Open** OBS Studio
2. **Add** → Browser source
3. **Set URL**: `http://dashboard-domain.com/canvas/view/{id}`
4. **Set Dimensions**: Graphic-specific or 1920x1080 default
5. **Set FPS**: 60 or as required by content
6. **Enable** Hardware acceleration

#### 1.2 Advanced Configuration
1. **Custom CSS**: Add custom styles if needed
2. **Refresh Rate**: Set browser refresh rate
3. **Browser Path**: Use system default browser engine
4. **Shutdown Source**: Configure when not visible
5. **Refresh Browser**: Manual refresh option for testing

### 2. Viewer Route Features

#### 2.1 Minimal Layout
- **No Header**: Clean rendering without navigation
- **No Sidebar**: Full canvas space available
- **No Controls**: Optimized for display purposes
- **Responsive**: Adapts to browser source dimensions

#### 2.2 Data Handling
- **Live Updates**: Automatic refresh when graphic data changes
- **Error Handling**: Graceful error display for missing/archived graphics
- **Performance**: Optimized rendering for streaming applications
- **Compatibility**: Works with OBS, XSplit, and other browser sources

#### 2.3 Error States
1. **Missing Graphic**: Display "Graphic not found" message
2. **Archived Graphic**: Display "Graphic archived" message
3. **Database Error**: Display appropriate error message
4. **Network Error**: Display connection error message

## Navigation Patterns

### 1. Expected User Flows

#### 1.1 Edit Workflow
```
Graphics Table → Click Edit → Load Editor Route → Make Changes → Save → Return to Table
```

#### 1.2 Create Workflow
```
Graphics Table → Create New → Fill Form → Submit → Load Editor Route → Edit → Save
```

#### 1.3 View Workflow
```
Graphics Table → Click View → Load Viewer Route → OBS Integration → Live Display
```

#### 1.4 Error Recovery
```
Error State → Error Message → Action Buttons → Return to Previous State
```

### 2. Browser Navigation

#### 2.1 Back Button Behavior
- **Editor Route**: Returns to Graphics tab dashboard
- **Viewer Route**: Returns to previous page (if accessed directly)
- **Error Pages**: Returns to safe navigation point

#### 2.2 Browser Refresh
- **Editor Route**: Reloads graphic data, maintains lock if active
- **Viewer Route**: Reloads graphic data, displays latest version
- **Authentication**: Preserves session on refresh

#### 2.3 Tab Management
- **Multiple Editors**: Supported in separate browser tabs
- **Lock Conflicts**: Handled across multiple tabs
- **Session Sharing**: Authentication shared across tabs

## State Management

### 1. Editor State
- **Canvas Data**: Current element positions, styles, properties
- **UI State**: Sidebar collapsed, active tab, zoom level
- **Lock State**: Current lock status and expiration
- **Unsaved Changes**: Tracked for save prompts

### 2. Viewer State
- **Graphic Data**: Loaded from database on each request
- **Display Settings**: Optimized for browser source rendering
- **Error State**: Managed for graceful error display

### 3. Session Management
- **Authentication**: JWT token validation for editor routes
- **User Context**: Current user information and permissions
- **Activity Tracking**: User activity for lock maintenance

## Error Handling Procedures

### 1. Authentication Errors
1. **Detection**: JWT token expired or invalid
2. **Redirect**: Redirect to login page with return URL
3. **Recovery**: After login, return to intended editor route
4. **Message**: Display authentication success message

### 2. Lock Errors
1. **Conflict**: Graphic locked by another user
2. **Display**: Lock conflict dialog with details
3. **Options**: Wait, override (admin), or cancel
4. **Recovery**: Return to graphics table or wait for release

### 3. Network Errors
1. **Detection**: API call failures or timeout
2. **Display**: Network error message with retry option
3. **Recovery**: Retry mechanism with exponential backoff
4. **Fallback**: Local state management if available

### 4. Data Validation Errors
1. **Detection**: Invalid graphic data or structure
2. **Display**: Validation error with specific details
3. **Recovery**: Correct invalid data or reset to last valid state
4. **Prevention**: Client-side validation before submission

## Performance Optimization

### 1. Editor Performance
- **Lazy Loading**: Components loaded as needed
- **Debounced Updates**: Prevent excessive API calls
- **Memory Management**: Cleanup unused resources
- **Virtual Scrolling**: For large element lists

### 2. Viewer Performance
- **Minimal DOM**: Optimized for browser source rendering
- **Efficient CSS**: Hardware-accelerated animations
- **Resource Optimization**: Compressed assets and images
- **Caching**: Appropriate browser caching headers

### 3. Network Optimization
- **Request Batching**: Combine multiple API calls
- **Compression**: gzip compression for responses
- **CDN Integration**: Static asset delivery
- **Connection Pooling**: Efficient HTTP connection reuse

## Security Considerations

### 1. Editor Security
- **Authentication**: JWT token validation for all operations
- **Authorization**: Permission checks for graphic access
- **Input Validation**: Sanitization of all user inputs
- **XSS Prevention**: Proper data encoding and sanitization

### 2. Viewer Security
- **Public Access**: No authentication required
- **Data Exposure**: Only published graphic data exposed
- **CORS Headers**: Appropriate cross-origin settings
- **Rate Limiting**: Prevent abuse of viewer endpoints

### 3. Session Security
- **Token Refresh**: Automatic token refresh mechanism
- **Session Expiration**: Proper timeout handling
- **Secure Cookies**: HttpOnly and Secure cookie settings
- **CSRF Protection**: Same-site cookie attributes

## Troubleshooting

### 1. Common Issues

#### 1.1 Editor Won't Load
- **Check**: Authentication status
- **Verify**: Graphic ID is valid
- **Confirm**: Network connectivity
- **Solution**: Refresh page or re-authenticate

#### 1.2 Lock Not Acquired
- **Check**: Existing locks on graphic
- **Verify**: User permissions
- **Confirm**: Network connectivity
- **Solution**: Wait for lock release or contact admin

#### 1.3 OBS Source Not Displaying
- **Check**: URL format and graphic ID
- **Verify**: Network accessibility from OBS
- **Confirm**: Graphic is not archived
- **Solution**: Check firewall and network settings

### 2. Debugging Steps

#### 2.1 Enable Debug Mode
1. **Open** browser developer tools
2. **Check** console for JavaScript errors
3. **Monitor** network requests in Network tab
4. **Verify** authentication tokens in Application tab

#### 2.2 Check Logs
1. **Backend Logs**: Check server error logs
2. **Frontend Logs**: Check browser console
3. **Network Logs**: Monitor API responses
4. **Authentication Logs**: Verify login attempts

## Maintenance Procedures

### 1. Regular Maintenance
- **Log Review**: Daily error log review
- **Performance Monitoring**: Check response times
- **User Feedback**: Collect user experience feedback
- **Security Updates**: Apply security patches promptly

### 2. Performance Monitoring
- **Response Times**: Monitor API and page load times
- **Error Rates**: Track error frequency and types
- **User Activity**: Monitor usage patterns
- **Resource Usage**: Track server resource consumption

### 3. Update Procedures
- **Feature Deployment**: Coordinate feature releases
- **Backward Compatibility**: Ensure route stability
- **User Training**: Update documentation and training materials
- **Change Communication**: Notify users of changes

## Emergency Procedures

### 1. Service Outage
1. **Assessment**: Determine scope and impact
2. **Communication**: Notify users of service status
3. **Recovery**: Restore service as quickly as possible
4. **Post-mortem**: Document and analyze the incident

### 2. Data Corruption
1. **Detection**: Identify corrupted graphic data
2. **Isolation**: Prevent access to affected graphics
3. **Recovery**: Restore from backup if available
4. **Notification**: Inform affected users

### 3. Security Incident
1. **Identification**: Detect and confirm security breach
2. **Containment**: Prevent further damage
3. **Eradication**: Remove threat and vulnerabilities
4. **Recovery**: Restore normal operations

---

**Last Updated**: 2025-10-12  
**Version**: 1.0  
**Status**: Draft - Ready for Review  
**Dependencies**: Live Graphics Dashboard 2.0, Canvas Editor Architecture v2.1  
**Related SOPs**: Canvas Editor Workflow, Dashboard Operations, Graphics Management
