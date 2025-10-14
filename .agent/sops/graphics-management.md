---
id: sops.graphics_management
version: 2.0
last_updated: 2025-10-11
tags: [sop, graphics, templates, creation, management]
---

# Graphics Management SOP

## Overview
This Standard Operating Procedure (SOP) details the comprehensive workflow for creating, managing, and maintaining graphics templates and instances within the Live Graphics Dashboard 2.0.

## Purpose
- Standardize graphic creation and template management
- Ensure consistent branding and quality across all graphics
- Maintain efficient template reuse and customization
- Provide clear guidelines for graphic lifecycle management

## Scope
- Template creation and maintenance
- Graphic instance management
- Brand consistency enforcement
- Media asset organization
- Quality control procedures

## Prerequisites
- Completed Dashboard Operations SOP training
- Understanding of graphic design principles
- Familiarity with branding guidelines
- Access to template management tools

## Template Management Workflow

### 1. Template Creation

#### 1.1 Template Design Requirements
1. **Design Standards Compliance**
   - Follow GAL branding guidelines
   - Use approved color palettes and fonts
   - Maintain responsive design principles
   - Ensure accessibility standards met

2. **Technical Requirements**
   - Optimize for performance (max 2MB total assets)
   - Support multiple aspect ratios (16:9, 9:16, 1:1)
   - Implement smooth animations (60fps target)
   - Include proper data binding points

3. **Template Structure**
   ```
   template_name/
   ├── template.json          # Template configuration
   ├── styles/                # CSS/SCSS files
   ├── assets/               # Images, videos, fonts
   ├── scripts/              # JavaScript logic
   └── README.md             # Usage documentation
   ```

#### 1.2 Template Development Process
1. **Requirements Gathering**
   - Define graphic purpose and use cases
   - Identify required data sources
   - Determine interactive elements
   - Establish animation requirements

2. **Design Mockup**
   - Create visual design mockups
   - Review with stakeholders
   - Iterate on feedback
   - Finalize design specifications

3. **Template Implementation**
   - Set up template directory structure
   - Implement HTML structure
   - Apply styling and branding
   - Add JavaScript functionality
   - Configure data bindings

4. **Testing and Validation**
   - Test in various screen sizes
   - Validate data connections
   - Test animation performance
   - Verify accessibility compliance

### 2. Template Categories

#### 2.1 Lower Third Graphics
- **Purpose**: Display participant information and scores
- **Standard Elements**: Name, team, score, statistic
- **Variations**: Single player, team, tournament branding
- **Data Sources**: Tournament API, player database

#### 2.2 Score Bug Templates
- **Purpose**: Display current match scores and time
- **Standard Elements**: Team scores, match time, period/round
- **Variations**: Different sports, tournament formats
- **Data Sources**: Live scoring system, timer API

#### 2.3 Statistic Graphics
- **Purpose**: Display player/team statistics and comparisons
- **Standard Elements**: Stats labels, values, comparisons, trends
- **Variations**: Single stat, multiple stats, trend graphs
- **Data Sources**: Statistics database, analytics API

#### 2.4 Transition Graphics
- **Purpose**: Scene transitions and show segments
- **Standard Elements**: Logo, show title, transition effects
- **Variations**: Show open, segment transition, show close
- **Data Sources**: Show schedule, branding assets

#### 2.5 Information Graphics
- **Purpose**: Display informational content and announcements
- **Standard Elements**: Title, content, branding, call-to-action
- **Variations**: News ticker, announcement, schedule display
- **Data Sources**: Content management, schedule system

### 3. Template Configuration

#### 3.1 Template Schema
```json
{
  "template_id": "lower_third_v2",
  "name": "Lower Third v2.0",
  "category": "lower_third",
  "version": "2.0.0",
  "created_date": "2025-01-11",
  "description": "Standard lower third for player information",
  "dimensions": {
    "width": 1920,
    "height": 108,
    "safe_zones": {
      "title": {"x": 50, "y": 20, "width": 300, "height": 40},
      "content": {"x": 360, "y": 20, "width": 600, "height": 40}
    }
  },
  "data_bindings": [
    {
      "field": "player_name",
      "type": "text",
      "required": true,
      "max_length": 50
    },
    {
      "field": "team_name",
      "type": "text",
      "required": true,
      "max_length": 50
    },
    {
      "field": "player_score",
      "type": "number",
      "required": true,
      "default": 0
    }
  ],
  "styling": {
    "font_family": "GAL-Bold",
    "primary_color": "#FF6B35",
    "secondary_color": "#004E89",
    "background_color": "rgba(0,0,0,0.8)"
  },
  "animations": {
    "in": "slide_in_left",
    "out": "slide_out_right",
    "duration": 0.5
  },
  "assets": [
    {
      "type": "logo",
      "path": "assets/gal_logo.png",
      "required": true
    }
  ]
}
```

#### 3.2 Data Source Configuration
```json
{
  "data_sources": [
    {
      "name": "tournament_api",
      "type": "rest_api",
      "endpoint": "/api/tournaments/{tournament_id}/players/{player_id}",
      "method": "GET",
      "refresh_interval": 30,
      "headers": {
        "Authorization": "Bearer {api_token}"
      }
    },
    {
      "name": "websocket_data",
      "type": "websocket",
      "endpoint": "/ws/live_scores",
      "auto_reconnect": true,
      "reconnect_interval": 5
    }
  ]
}
```

### 4. Graphic Instance Management

#### 4.1 Instance Creation
1. **Template Selection**
   - Browse available templates
   - Filter by category or use case
   - Preview template functionality
   - Select appropriate template

2. **Instance Configuration**
   - Enter instance name and description
   - Configure data source mappings
   - Set timing and triggers
   - Customize styling within brand guidelines

3. **Validation**
   - Test data connections
   - Preview graphic functionality
   - Verify responsive behavior
   - Check for configuration errors

#### 4.2 Graphic Deletion Management

##### Active Graphics Deletion
Active graphics require confirmation before permanent deletion:

1. **Delete Confirmation Workflow**
   - Click "Delete" button on target graphic
   - DeleteConfirmDialog appears with warning message
   - Review deletion details and impact
   - Confirm permanent deletion action

2. **Confirmation Dialog Features**
   - Clear warning about permanent nature
   - Graphic name and metadata display
   - Confirmation button with loading state
   - Cancellation option available

3. **Post-Deletion Actions**
   - Graphic immediately removed from database
   - Real-time UI updates via WebSocket
   - Success notification displayed
   - Archive not created (data permanently lost)

##### Archive Graphics Deletion
Archive graphics use direct deletion without confirmation:

1. **Direct Deletion Process**
   - Navigate to Archived tab
   - Click "Delete" button on target archive
   - Archive immediately removed from system
   - Success notification displayed

2. **Deletion Characteristics**
   - No confirmation required
   - Immediate permanent deletion
   - No recovery options available
   - Audit log entry created

##### Deletion Security and Permissions
1. **Permission Requirements**
   - Active Graphics: `graphics:delete` permission required
   - Archive Graphics: `archive:delete` permission required
   - Self-Deletion: Users can delete graphics they created
   - Admin Override: Administrators can delete any graphic

2. **Lock State Considerations**
   - Graphics with active locks cannot be deleted
   - Lock status displayed in delete confirmation
   - User must unlock graphic before deletion
   - Automatic lock release after deletion

3. **Audit and Compliance**
   - All deletions logged with user attribution
   - Deletion timestamp and reason recorded
   - Graphic metadata preserved in audit log
   - Compliance reports generated automatically

#### 4.3 Instance Deployment
1. **Tournament Assignment**
   - Select target tournament
   - Choose specific matches or events
   - Set activation schedule
   - Configure priority levels

2. **Quality Assurance**
   - Deploy to staging environment first
   - Test with sample data
   - Verify integration with other systems
   - Get stakeholder approval

3. **Production Deployment**
   - Schedule deployment during low-traffic periods
   - Monitor deployment process
   - Verify successful activation
   - Document deployment details

### 5. Media Asset Management

#### 5.1 Asset Organization
```
assets/
├── logos/                   # Team and sponsor logos
│   ├── teams/
│   └── sponsors/
├── backgrounds/             # Background images and videos
│   ├── animated/
│   └── static/
├── fonts/                   # Custom font files
├── sounds/                  # Audio effects
├── images/                  # Miscellaneous images
└── videos/                  # Video clips
```

#### 5.2 Asset Requirements
1. **Image Specifications**
   - Format: PNG, JPG, SVG preferred
   - Resolution: Minimum 1920x1080 for HD
   - File Size: Maximum 2MB per image
   - Compression: Optimize for web delivery

2. **Video Specifications**
   - Format: MP4, WebM preferred
   - Resolution: 1920x1080 or higher
   - Frame Rate: 30fps or 60fps
   - Duration: Maximum 30 seconds for loops

3. **Font Requirements**
   - Format: WOFF, WOFF2, TTF
   - Licensing: Verify commercial use rights
   - Performance: Optimize for web loading
   - Fallback: Provide system font alternatives

### 6. Quality Control Procedures

#### 6.1 Template Review Checklist
- [ ] Design follows branding guidelines
- [ ] All required data bindings configured
- [ ] Responsive design tested on all devices
- [ ] Animations perform smoothly
- [ ] Accessibility standards met
- [ ] Documentation complete and accurate
- [ ] Asset optimization verified
- [ ] Cross-browser compatibility tested

#### 6.2 Instance Validation Checklist
- [ ] Data connections functioning properly
- [ ] All required fields populated
- [ ] Conditional logic working correctly
- [ ] Error handling implemented
- [ ] Performance within acceptable limits
- [ ] User testing completed
- [ ] Stakeholder approval obtained

#### 6.3 Deletion Workflow Validation Checklist

##### Active Graphics Deletion Validation
- [ ] Delete button displays correctly in graphics table
- [ ] DeleteConfirmDialog appears when delete is clicked
- [ ] Confirmation dialog shows correct graphic information
- [ ] Warning message about permanent deletion is clear
- [ ] Confirmation button requires user action
- [ ] Loading state displays during deletion process
- [ ] Success notification appears after deletion
- [ ] Graphic is immediately removed from table
- [ ] WebSocket event updates other connected clients
- [ ] Archive is not created (permanent deletion)

##### Archive Graphics Deletion Validation
- [ ] Delete button displays correctly in archive table
- [ ] No confirmation dialog appears for archive deletion
- [ ] Deletion occurs immediately upon button click
- [ ] Success notification appears after deletion
- [ ] Archive entry removed from archive table
- [ ] No recovery options available post-deletion
- [ ] Audit log entry created for compliance

##### Error Handling Validation
- [ ] Locked graphics cannot be deleted
- [ ] Permission denied errors handled gracefully
- [ ] Network errors during deletion handled appropriately
- [ ] Invalid graphic ID errors handled with user feedback
- [ ] Server errors during deletion show retry options
- [ ] Concurrent deletion conflicts resolved appropriately

##### User Experience Validation
- [ ] Clear visual distinction between delete actions
- [ ] Consistent button styling and placement
- [ ] Appropriate use of color for destructive actions
- [ ] Keyboard navigation support for delete actions
- [ ] Screen reader compatibility for delete workflows
- [ ] Mobile-responsive delete interface
- [ ] Loading states provide clear feedback
- [ ] Error messages are informative and actionable

### 7. Template Version Control

#### 7.1 Version Management
1. **Semantic Versioning**
   - Major: Breaking changes (2.0.0)
   - Minor: New features (1.1.0)
   - Patch: Bug fixes (1.0.1)

2. **Change Documentation**
   - Document all version changes
   - Maintain change log
   - Notify users of updates
   - Provide migration guides

#### 7.2 Template Updates
1. **Non-Breaking Updates**
   - Apply to new instances automatically
   - Offer update for existing instances
   - Test thoroughly before deployment
   - Monitor for issues post-deployment

2. **Breaking Changes**
   - Create new template version
   - Maintain old version for compatibility
   - Provide migration tools
   - Communicate timeline for deprecation

### 8. Performance Optimization

#### 8.1 Asset Optimization
- Compress images without quality loss
- Optimize video files for streaming
- Minify CSS and JavaScript files
- Implement lazy loading for large assets

#### 8.2 Template Performance
- Limit DOM complexity
- Optimize animation performance
- Implement efficient data updates
- Monitor memory usage

### 9. Troubleshooting

#### 9.1 Common Template Issues
1. **Data Not Loading**
   - Check API endpoint accessibility
   - Verify authentication credentials
   - Test data format compatibility
   - Review network connectivity

2. **Styling Problems**
   - Validate CSS syntax
   - Check for conflicting styles
   - Verify asset file paths
   - Test responsive behavior

3. **Animation Issues**
   - Check browser compatibility
   - Verify performance impact
   - Test on various devices
   - Optimize animation timing

#### 9.2 Performance Issues
1. **Slow Loading**
   - Optimize asset sizes
   - Implement caching strategies
   - Reduce HTTP requests
   - Monitor network performance

2. **High Memory Usage**
   - Limit concurrent animations
   - Optimize DOM operations
   - Implement cleanup procedures
   - Monitor memory leaks

## Training Requirements

### Template Creation Training
- Graphic design principles
- Brand guidelines application
- Technical implementation skills
- Quality assurance procedures

### Template Management Training
- Version control procedures
- Update management
- Performance optimization
- Troubleshooting techniques

## JSON Serialization and Data Management

### Overview
Due to SQLite database limitations, all graphic data must be properly serialized to JSON format before storage. This section outlines the procedures for handling JSON serialization in graphic creation and management.

### Serialization Requirements

#### 1. Data Structure Standards
All graphic data must follow a standardized JSON structure:
```json
{
  "elements": [
    {
      "id": "element_001",
      "type": "text",
      "content": "Player Name",
      "position": {"x": 100, "y": 200},
      "style": {"fontSize": 24, "color": "#FFFFFF"}
    }
  ],
  "settings": {
    "width": 1920,
    "height": 1080,
    "backgroundColor": "#000000",
    "duration": 5000
  },
  "metadata": {
    "template": "lower_third_v1",
    "created": "2025-01-11T10:00:00Z",
    "version": "1.0"
  }
}
```

#### 2. Backend Serialization Procedures
The graphics service automatically handles JSON serialization:
- **Storage**: Python objects are converted to JSON strings using `json.dumps()`
- **Retrieval**: JSON strings are converted back to objects using `json.loads()`
- **Validation**: Data structure is validated before serialization
- **Error Handling**: Fallback to empty object for invalid data

#### 3. Frontend Data Handling
Frontend components must properly handle JSON data:
- **Creation**: Send data as JavaScript objects
- **Editing**: Canvas editor provides structured data interface
- **Display**: Parse JSON strings for rendering
- **Validation**: Client-side validation before API calls

### Data Integrity Procedures

#### 1. Validation Before Serialization
```python
def validate_graphic_data(data: dict) -> bool:
    """Validate graphic data structure before serialization"""
    required_fields = ['elements', 'settings']
    
    for field in required_fields:
        if field not in data:
            return False
    
    # Validate elements array
    if not isinstance(data['elements'], list):
        return False
    
    # Validate each element
    for element in data['elements']:
        if not isinstance(element, dict) or 'id' not in element:
            return False
    
    return True
```

#### 2. Error Handling and Recovery
- **Serialization Errors**: Log error and use default empty object
- **Deserialization Errors**: Return empty object and log warning
- **Data Corruption**: Identify and flag corrupted records
- **Recovery Procedures**: Restore from backup or recreate from template

#### 3. Data Migration Procedures
When updating data structures:
1. **Backup**: Create backup of existing data
2. **Migration Script**: Write script to transform data
3. **Validation**: Test migration on sample data
4. **Rollback Plan**: Prepare rollback procedures
5. **Monitoring**: Monitor for issues after migration

### Troubleshooting JSON Serialization Issues

#### Common Issues and Solutions

1. **"Cannot store Python dictionary in SQLite" Error**
   - **Cause**: Attempting to store Python objects directly
   - **Solution**: Ensure `json.dumps()` is used before database storage
   - **Prevention**: Always validate serialization in development

2. **Malformed JSON Data**
   - **Cause**: Invalid JSON structure or encoding issues
   - **Solution**: Use `json.loads()` with error handling
   - **Prevention**: Implement schema validation

3. **Data Loss During Serialization**
   - **Cause**: Non-serializable data types
   - **Solution**: Convert all data to JSON-compatible types
   - **Prevention**: Define strict data type requirements

4. **Performance Issues with Large JSON**
   - **Cause**: Excessively large graphic data structures
   - **Solution**: Implement data compression and optimization
   - **Prevention**: Set size limits for graphic data

#### Diagnostic Procedures
1. **Check Application Logs**: Look for JSON serialization errors
2. **Database Inspection**: Verify data format in database
3. **API Testing**: Test create/update operations directly
4. **Frontend Debugging**: Monitor network requests and responses

### Best Practices

#### Development Guidelines
1. **Consistent Data Structure**: Use standardized JSON schema
2. **Validation**: Implement client and server-side validation
3. **Error Handling**: Provide meaningful error messages
4. **Testing**: Test with various data types and edge cases
5. **Documentation**: Document data structure requirements

#### Performance Optimization
1. **Data Compression**: Minimize JSON size where possible
2. **Caching**: Cache parsed JSON data on frontend
3. **Lazy Loading**: Load large graphics data on demand
4. **Monitoring**: Monitor JSON processing performance

## Documentation Requirements

### Template Documentation
Each template must include:
- Purpose and use case description
- Data binding specifications
- JSON structure requirements
- Styling customization options
- Usage examples and screenshots

### Change Management
- Maintain change logs for all templates
- Document update procedures
- Track template usage statistics
- Record data structure changes

### Technical Documentation
- JSON schema definitions
- API integration examples
- Error handling procedures
- Performance optimization guidelines
- Archive deprecated versions

## References
- [Dashboard Operations SOP](dashboard-operations.md)
- [Branding Guidelines](../system/branding-guidelines.md)
- [API Documentation](../system/api-backend-system.md)
- [Performance Monitoring SOP](performance-monitoring.md)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: Creative Director
- **Classification**: Internal Use Only
