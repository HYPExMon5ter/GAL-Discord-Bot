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

#### 4.2 Instance Deployment
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

## Documentation Requirements

### Template Documentation
Each template must include:
- Purpose and use case description
- Data binding specifications
- Styling customization options
- Usage examples and screenshots

### Change Management
- Maintain change logs for all templates
- Document update procedures
- Track template usage statistics
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
