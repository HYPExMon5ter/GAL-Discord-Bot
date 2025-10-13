---
id: sops.canvas-editor-workflow
version: 2.1
last_updated: 2025-10-12
tags: [sop, canvas, editor, workflow, graphics, broadcast]
---

# Canvas Editor Workflow SOP

## Overview
This Standard Operating Procedure (SOP) details the comprehensive workflow for creating, editing, and managing broadcast graphics using the Live Graphics Dashboard 2.0 full-screen canvas editor.

## Purpose
- Standardize canvas editor usage and best practices
- Ensure consistent graphic quality and branding
- Provide clear guidelines for advanced feature usage
- Maintain efficient graphic creation workflows

## Scope
- Full-screen canvas editor usage
- Advanced features (zoom, grid, snap-to-grid)
- Element management and properties editing
- Background upload and management
- Data binding implementation
- OBS browser source integration

## Prerequisites
- Completed Dashboard Operations SOP training
- Understanding of graphic design principles
- Familiarity with broadcast graphics requirements
- Access to Live Graphics Dashboard with editing permissions

## Canvas Editor Access

### 1. Navigation
1. **Route to Editor**: Navigate to `/canvas/edit/{id}` or create new graphic
2. **Authentication**: Ensure valid session is active
3. **Lock Status**: Verify graphic is not locked by another user
4. **Initial Setup**: Allow editor to load completely

### 2. Workspace Overview
```
┌─────────────────────────────────────────────────────────┐
│ [← Back] [Graphic Name]                    [Save] │ Header
├─────────────────────────────────────────────────────────┤
│ ┌─────────┐                                       │         │
│ │ Sidebar │         Canvas Area                │         │
│ │ (Collapse│                                       │         │
│  dible) │    • Tools & Settings              │         │
│         │    • Element Management            │         │
│         │    • Data Binding                  │         │
│ └─────────┘                                       │         │
│                                                 │         │
└─────────────────────────────────────────────────────────┘
                                                      │
                    [Grid][Snap][Zoom] │ Bottom Controls
```

## Canvas Setup Workflow

### 1. Canvas Configuration
#### 1.1 Basic Settings
1. **Canvas Size**: Set appropriate dimensions (default: 1920x1080)
   - Use preset sizes for standard broadcast formats
   - Custom size available for special requirements
2. **Background Color**: Set base canvas color
   - Use color picker for precise selection
   - Consider transparency requirements for OBS

#### 1.2 Background Image (Optional)
1. **Upload Background**: 
   - Click "Background Image" in Design tab
   - Select image file (JPG, PNG, GIF)
   - Wait for upload completion
2. **Background Management**:
   - Use "Remove Background" to clear image
   - Background covers entire canvas area
   - Optimize images for web use (< 2MB)

### 2. Grid and Snap Configuration
#### 2.1 Grid System
1. **Enable Grid**: Click "Grid" button or press 'G'
   - 20px dotted grid overlay
   - Visual aid for element alignment
   - Can be toggled on/off

#### 2.2 Snap-to-Grid
1. **Enable Snap**: Click "Snap" button or press 'S'
   - 5px tolerance for automatic alignment
   - Elements snap to grid when moved
   - Ensures consistent positioning

## Element Creation Workflow

### 1. Adding Elements
#### 1.1 Text Elements
1. **Access Tools**: Navigate to Design tab
2. **Add Text**: Click "Add Text Element"
3. **Initial Properties**:
   - Default text: "Player Name"
   - Default position: (100, 100)
   - Default style: White text, 48px font

#### 1.2 Shape Elements
1. **Rectangle**: Click "Rectangle" button
2. **Circle**: Click "Circle" button
3. **Initial Properties**:
   - Default size: 100x100 pixels
   - Default color: Red with white border
   - Default position: (200, 200)

### 2. Element Manipulation
#### 2.1 Selection
1. **Click to Select**: Click on any element to select it
2. **Visual Feedback**: Selected element shows blue border
3. **Properties Panel**: Right panel shows element properties
4. **Multiple Selection**: Shift+click for multiple elements (future feature)

#### 2.2 Drag and Drop
1. **Initiate Drag**: Click and hold element
2. **Positioning**: Drag to desired location
3. **Snap Behavior**: Elements snap to grid when enabled
4. **Release**: Drop element at final position

#### 2.3 Keyboard Shortcuts
- **G**: Toggle grid visibility
- **S**: Toggle snap-to-grid
- **+/-**: Zoom in/out
- **0**: Reset zoom to 50%
- **Delete**: Remove selected element

## Element Properties Editing

### 1. Text Element Properties
#### 1.1 Content Editing
1. **Content Field**: Edit text directly in properties panel
2. **Font Size**: Set size in pixels (8-256px range)
3. **Color**: Use color picker for text color
4. **Position**: Precise X/Y coordinate control

#### 1.2 Advanced Text Features
1. **Data Binding**: Connect to live data sources (see Data Binding section)
2. **Font Styling**: Font family and weight (future feature)
3. **Text Effects**: Shadow, outline (future feature)

### 2. Shape Element Properties
#### 2.1 Size Control
1. **Width/Height**: Set dimensions in pixels
2. **Aspect Ratio**: Lock/unlock aspect ratio (future feature)
3. **Position**: Precise X/Y coordinate control

#### 2.2 Appearance
1. **Background Color**: Fill color for shapes
2. **Border Color**: Outline color
3. **Border Width**: 0-10px range
4. **Opacity**: Transparency control (future feature)

## Zoom and Navigation

### 1. Zoom Controls
#### 1.1 Zoom Range
- **Minimum**: 25% (quarter size)
- **Maximum**: 400% (4x size)
- **Default**: 50% (half size)

#### 1.2 Zoom Methods
1. **Button Controls**: Use +/- buttons in bottom controls
2. **Keyboard**: Press +/- keys for zoom control
3. **Reset**: Click "Reset" button or press '0'
4. **Visual Indicator**: Current zoom percentage displayed

### 2. Canvas Navigation
#### 2.1 Viewport Navigation
1. **Scroll**: Use browser scroll bars for large canvases
2. **Center Focus**: Canvas remains centered at all zoom levels
3. **Responsive**: Canvas scales to fit available space

## Data Binding Workflow

### 1. Data Sources
#### 1.1 Available Sources
- **Lobby-Specific**: Particular lobby and round data
- **Player Roster**: Current player information
- **Tournament Data**: Tournament-wide information
- **Custom Data**: Manual data entry

#### 1.2 Data Binding Process
1. **Access Data Tab**: Click "Data" tab in sidebar
2. **Select Element**: Choose text element to bind
3. **Choose Data Field**: Select appropriate field from dropdown
4. **Save Binding**: Changes automatically saved

### 2. Supported Data Fields
#### 2.1 Player Information
- `player_name`: Player display name
- `player_score`: Current player score
- `player_placement`: Current placement/ranking
- `player_rank`: Player rank/level
- `team_name`: Team or group name

#### 2.2 Tournament Information
- `tournament_name`: Tournament title
- `round_name`: Current round or stage
- `event_name`: Event or match name

## Element Management

### 1. Elements Tab
#### 1.1 Layer View
1. **Access Elements**: Click "Elements" tab
2. **Layer Display**: Shows all elements with layer numbers
3. **Element Types**: Visual indicators for element types
4. **Selection**: Click elements to select them

#### 1.2 Element Operations
1. **Delete**: Remove elements via delete button
2. **Properties**: Selected elements show expanded properties
3. **Reordering**: Drag to reorder layers (future feature)
4. **Visibility**: Toggle element visibility (future feature)

### 2. Best Practices
#### 2.1 Element Organization
1. **Logical Naming**: Use descriptive element names
2. **Layer Management**: Place background elements first
3. **Grouping**: Related elements should be nearby
4. **Consistency**: Maintain consistent styling across similar elements

## Saving and Exporting

### 1. Auto-Save Behavior
1. **Manual Save**: Click "Save" button to persist changes
2. **Auto-Lock**: Editing lock acquired on first edit
3. **Lock Duration**: 5-minute auto-renewal
4. **Collision Prevention**: Others cannot edit while locked

### 2. Save Process
1. **Validation**: Check for required fields
2. **Data Serialization**: Convert to JSON format
3. **API Update**: Send changes to backend
4. **Success Feedback**: Visual confirmation of save

## OBS Browser Source Setup

### 1. URL Configuration
1. **Access View URL**: Use `/canvas/view/{id}` for OBS
2. **Authentication**: Public access, no login required
3. **Performance**: Optimized for streaming applications

### 2. OBS Configuration
#### 2.1 Browser Source Settings
```
URL: http://localhost:3000/canvas/view/{id}
Width: 1920 (or canvas width)
Height: 1080 (or canvas height)
Custom CSS: None required
```

#### 2.2 Performance Settings
1. **Hardware Acceleration**: Enabled for better performance
2. **Frame Rate**: 60 FPS recommended
3. **Quality**: High quality rendering
4. **Refresh Rate**: Set to match stream frame rate

## Troubleshooting

### 1. Common Issues
#### 1.1 Canvas Not Loading
- Check authentication status
- Verify graphic ID is correct
- Ensure backend server is running
- Check browser console for errors

#### 1.2 Elements Not Responding
- Verify element is selected
- Check if canvas is locked by another user
- Refresh page and reattempt
- Check for JavaScript errors

#### 1.3 Save Not Working
- Verify internet connection
- Check authentication token validity
- Ensure required fields are filled
- Try manual save again

### 2. Performance Issues
#### 2.1 Slow Loading
- Check internet connection speed
- Reduce background image size
- Clear browser cache
- Close unused browser tabs

#### 2.2 Lag During Editing
- Reduce zoom level for large canvases
- Disable grid if not needed
- Close other applications
- Restart browser if needed

## Quality Assurance

### 1. Pre-Live Checklist
- [ ] All text elements properly aligned
- [ ] Colors meet broadcast standards
- [ ] No placeholder text remains
- [ ] Background images load correctly
- [ ] Data bindings tested and working
- [ ] Canvas saved successfully
- [ ] OBS source tested in preview

### 2. Live Monitoring
- Monitor OBS source quality
- Check for element positioning issues
- Verify data updates are reflecting
- Monitor system performance
- Watch for error messages

## Emergency Procedures

### 1. Editor Failure
1. **Save Current Work**: Attempt manual save
2. **Refresh Page**: Reload editor interface
3. **Clear Cache**: Clear browser cache and cookies
4. **Alternative Browser**: Try different browser
5. **Contact Support**: Report issue to development team

### 2. OBS Source Issues
1. **Check URL**: Verify correct view URL is used
2. **Refresh Source**: Reload browser source in OBS
3. **Check Network**: Verify localhost accessibility
4. **Alternative Method**: Use window capture as fallback

## Security Considerations

### 1. Access Control
- **Authentication Required**: Editor access requires valid login
- **Session Management**: Auto-logout after inactivity
- **Permission Levels**: Different access levels for different operations

### 2. Data Protection
- **Local Storage**: Sensitive data stored securely
- **Transmission**: HTTPS for all API calls
- **Validation**: Input sanitization and validation

## Performance Optimization

### 1. Best Practices
- **Image Optimization**: Use appropriate image formats and sizes
- **Element Management**: Remove unused elements
- **Regular Saves**: Save work frequently
- **Browser Choice**: Use modern browsers with good performance

### 2. Resource Management
- **Memory Usage**: Monitor browser memory usage
- **CPU Usage**: Be mindful of complex animations
- **Network Usage**: Optimize image file sizes
- **Storage**: Regular cleanup of unused graphics

---

**Last Updated**: 2025-10-12  
**Next Review**: After next major feature update  
**Dependencies**: Live Graphics Dashboard 2.1+
