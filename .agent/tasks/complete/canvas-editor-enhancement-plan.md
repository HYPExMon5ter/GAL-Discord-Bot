---
id: tasks.canvas-editor-enhancement-plan
version: 1.0
created: 2025-01-13
status: active
tags: [canvas, editor, enhancement, refactor, ui-improvements]
title: Canvas Editor Enhancement Plan
priority: high
estimated_days: 3-5
---

# Canvas Editor Enhancement Plan

## Overview
This document outlines a comprehensive enhancement plan for the Canvas Editor to improve usability, functionality, and workflow efficiency. The plan focuses on replacing the current text/shape system with a data-driven property system and implementing various UI/UX improvements.

## Current State Analysis

### Existing Functionality
- Text elements with basic styling (font, color, size)
- Shape elements (rectangle, circle) with fill/border properties
- Grid system with 20px snap functionality
- Background image upload
- Basic element positioning and sizing
- Tab-based sidebar (Design, Elements, Data)

### Identified Issues
1. **Limited Property System**: Only supports generic text and shapes
2. **No Element Snapping**: Elements don't snap to each other
3. **Event Name Management**: No dropdown or event name persistence
4. **Inline Editing Issues**: Text content reverts when trying to delete
5. **UI Layout Problems**: Controls not optimally positioned
6. **Missing Undo/Redo**: Functions not visible in current interface
7. **Scrolling Issues**: Properties section scrolls independently

## Enhancement Requirements

### 1. New Property System
**Current**: Generic text and shape elements  
**Target**: Data-driven property elements

#### New Element Types:
- **Player Property**: Icon/placeholder for player data
- **Score Property**: Icon/placeholder for score data  
- **Placement Property**: Icon/placeholder for placement/rank data

#### Element Properties:
```typescript
interface PropertyElement {
  id: string;
  type: 'player' | 'score' | 'placement' | 'text'; // Keep text tool
  x: number;
  y: number;
  width: number;
  height: number;
  // Visual customization
  backgroundColor: string;
  borderColor: string;
  borderWidth: number;
  borderRadius: number;
  fontSize?: number; // For text elements
  // Data binding
  dataBinding: {
    source: 'api' | 'manual';
    field: 'player_name' | 'player_score' | 'player_placement' | 'custom';
    apiEndpoint?: string;
    manualValue?: string;
  };
  // Visual state
  isPlaceholder: boolean; // Shows icon when no data bound
  placeholderText: string;
}
```

### 2. Element Snapping System
**Feature**: Elements snap to each other when close enough  
**Sensitivity**: Same as grid snap (20px)  
**Implementation**:
```typescript
interface SnapSettings {
  snapToGrid: boolean;
  snapToElements: boolean;
  snapThreshold: number; // 20px
}

// Snap calculation logic
function calculateSnapPosition(
  element: PropertyElement,
  otherElements: PropertyElement[],
  threshold: number
): { x: number; y: number } {
  // Check proximity to other elements
  // Snap to edges, centers, and corners
  // Return adjusted position
}
```

### 3. Event Name Management System
**Current**: Manual text input  
**Target**: Dropdown with create new option

#### Features:
- Dropdown of existing event names
- "Create new event" option
- Event name persistence across graphics
- Auto-complete suggestions
- Event name editing inline

#### Implementation:
```typescript
interface EventManager {
  events: string[];
  addEvent(name: string): Promise<void>;
  getEvents(): Promise<string[]>;
  updateEvent(oldName: string, newName: string): Promise<void>;
}
```

### 4. UI Layout Reorganization

#### Header Changes:
- **Left**: Back button
- **Center**: Editable title and event name (inline text inputs)
- **Right**: Undo, Redo, Cancel, Save buttons

#### Sidebar Changes:
- **Single scrollable area**: Entire sidebar scrolls as one unit
- **Footer awareness**: Account for footer height in scroll calculations
- **Properties section**: No independent scrolling

#### Canvas Footer Changes:
- **Left side**: Grid and Snap buttons (under canvas edge)
- **Right side**: Zoom controls (zoom in/out/percentage), Fit, Reset buttons
- **Remove**: Current centered layout

### 5. Text Element Editing Fix
**Issue**: Text content reverts to "Player Name" when deleted  
**Solution**: Proper handling of empty text state
```typescript
// Fix text element update logic
const updateTextElement = (elementId: string, content: string) => {
  if (content.trim() === '') {
    // Allow empty content, don't revert to default
    updateElement(elementId, { content: '' });
  } else {
    updateElement(elementId, { content });
  }
};
```

### 6. Visual Design for Property Elements
**Requirement**: Icons/placeholders instead of text labels  
**Design**: Clean, modern icons with customizable colors

#### Icon Designs:
- **Player**: User/person silhouette icon
- **Score**: Trophy or star icon  
- **Placement**: Ranking/podium icon
- **Custom**: Generic data icon

#### Customization Options:
- Background color
- Border color and width
- Border radius
- Size (width/height)
- Icon color (if applicable)

## Implementation Plan

### Phase 1: Core Property System (Day 1-2)
1. **Update Element Types**
   - Modify CanvasElement interface
   - Add new property element types
   - Update element creation functions

2. **Implement Property Element UI**
   - Create icon components for each property type
   - Add property element rendering logic
   - Implement placeholder state display

3. **Update Properties Panel**
   - Remove shape tools (rectangle, circle)
   - Add property element tools (player, score, placement)
   - Keep text tool
   - Update property editing interface

### Phase 2: Snapping System (Day 2-3)
1. **Element Proximity Detection**
   - Implement proximity calculation between elements
   - Add snap line visual feedback
   - Configure snap sensitivity

2. **Snap Logic Integration**
   - Integrate with existing drag system
   - Add snap settings to grid controls
   - Test and refine snap behavior

### Phase 3: Event Management (Day 3)
1. **Event Storage System**
   - Create event management service
   - Implement API endpoints for event CRUD
   - Add local storage fallback

2. **Dropdown UI Implementation**
   - Create dropdown component with create new option
   - Add inline editing capability
   - Implement auto-complete functionality

### Phase 4: UI Reorganization (Day 4)
1. **Header Redesign**
   - Move undo/redo to top right
   - Implement inline title/event name editing
   - Update button layout and styling

2. **Sidebar Scrolling Fix**
   - Remove nested scrolling
   - Implement single scroll container
   - Adjust for footer height

3. **Footer Controls Reorganization**
   - Move grid/snap to left under canvas
   - Move zoom controls to right
   - Update layout calculations

### Phase 5: Bug Fixes and Polish (Day 4-5)
1. **Text Element Fix**
   - Resolve text content reversion issue
   - Test empty content handling
   - Verify save/load functionality

2. **Testing and Refinement**
   - Comprehensive testing of all features
   - UI/UX refinements
   - Performance optimization
   - Documentation updates

## Technical Implementation Details

### File Structure Changes
```
dashboard/components/
├── canvas/
│   ├── CanvasEditor.tsx           # Main editor (major updates)
│   ├── elements/
│   │   ├── PropertyElement.tsx    # New property element component
│   │   ├── TextElement.tsx        # Updated text element
│   │   └── ElementSnapLines.tsx   # Visual snap feedback
│   ├── ui/
│   │   ├── EventDropdown.tsx      # Event name dropdown
│   │   └── InlineEditField.tsx    # Inline text editing
│   └── tools/
│       ├── PropertyTool.tsx       # Property element tools
│       └── ElementSnapService.ts  # Snap calculation service
```

### API Changes
```typescript
// New API endpoints
GET /api/events                    # Get all event names
POST /api/events                   # Create new event
PUT /api/events/{id}               # Update event name

// Updated graphic data structure
interface GraphicData {
  elements: PropertyElement[];
  settings: CanvasSettings;
  eventNames: string[];            // Persisted event names
  backgroundElement?: string;
}
```

### Database Schema Changes
```sql
-- Add events table
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add event_name column to graphics table if not exists
ALTER TABLE graphics ADD COLUMN event_name TEXT;
```

## Critical Issues Found (Post-Implementation)

### UI/UX Problems
1. **Dropdown Functionality Broken**
   - **Issue**: Dropdowns don't close properly, always stay open
   - **Impact**: Cannot select options, interface unusable
   - **Root Cause**: Select component styling conflicts

2. **Dropdown Styling Issues**
   - **Issue**: Light backgrounds with barely visible text
   - **Impact**: Poor contrast, accessibility issues
   - **Root Cause**: Dark theme not applied to dropdown components

3. **Inline Text Input Styling**
   - **Issue**: Text inputs look invisible, no visual feedback
   - **Impact**: Users don't know they can edit graphic/event names
   - **Root Cause**: Transparent styling conflicts with dark theme

4. **Layout Issues**
   - **Issue**: Title and event name stacked vertically instead of side-by-side
   - **Impact**: Poor use of header space
   - **Root Cause**: Incorrect flex layout implementation

### Immediate Fixes Required
1. **Fix Select Component Styling**: Apply proper dark theme to dropdowns
2. **Implement Dropdown Toggle**: Ensure dropdowns close properly
3. **Improve Text Input Visibility**: Add borders and background colors
4. **Reorganize Header Layout**: Side-by-side title and event editing
5. **Add Visual Indicators**: Show that fields are editable

## Risk Assessment and Mitigation

### High Risk Items
1. **Data Migration**: Existing graphics may need migration
   - **Mitigation**: Implement backward compatibility
   - **Testing**: Test with existing graphics data

2. **Performance**: Element snapping may impact performance
   - **Mitigation**: Optimize proximity calculations
   - **Testing**: Performance testing with many elements

3. **UI Component Conflicts**: Select component styling breaking dropdowns
   - **Mitigation**: Proper dark theme integration
   - **Testing**: Test all dropdown interactions

### Medium Risk Items
1. **UI Changes**: Layout reorganization may confuse users
   - **Mitigation**: Maintain familiar patterns where possible
   - **Testing**: User feedback sessions

2. **Event Storage**: New event management system
   - **Mitigation**: Implement robust error handling
   - **Testing**: Test event creation/editing/deletion

3. **Accessibility**: Poor text contrast in dropdowns
   - **Mitigation**: Ensure proper contrast ratios
   - **Testing**: Accessibility audit of all components

## Success Metrics

### Functional Metrics
- [ ] Property elements created and edited successfully
- [ ] Element snapping works within 20px threshold
- [ ] Event names persist across graphics
- [ ] Inline editing works for titles and event names
- [ ] Text editing bug resolved
- [ ] Undo/redo functionality restored
- [ ] Scilling issues resolved

### UX Metrics
- [ ] Improved workflow efficiency
- [ ] Reduced clicks for common operations
- [ ] Better visual feedback for interactions
- [ ] Cleaner, more intuitive interface

### Technical Metrics
- [ ] No performance regression
- [ ] Backward compatibility maintained
- [ ] All existing tests pass
- [ ] New test coverage for new features

## Testing Plan

### Unit Tests
- Property element creation and editing
- Element snapping calculations
- Event management functions
- Text editing bug fix verification

### Integration Tests
- Canvas editor full workflow
- Save/load functionality with new elements
- Event name dropdown integration
- API endpoint integration

### User Acceptance Tests
- Complete graphic creation workflow
- Property element usage scenarios
- Event name management scenarios
- UI layout and usability testing

## Timeline

**Week 1**: Core property system and UI updates
**Week 2**: Snapping system and event management
**Week 3**: Testing, refinement, and deployment

## Dependencies

### External Dependencies
- None (uses existing tech stack)

### Internal Dependencies
- Canvas Editor component (ready for enhancement)
- Graphics API (may need minor updates)
- Event management (new feature)

## Rollout Plan

### Phase 1: Feature Flag
- Implement new features behind feature flag
- Test with internal users
- Collect feedback and refine

### Phase 2: Gradual Rollout
- Enable features for subset of users
- Monitor performance and usage
- Address any issues

### Phase 3: Full Release
- Remove feature flags
- Update documentation
- User training and support

---

**Created**: 2025-01-13  
**Status**: Active  
**Next Review**: After Phase 1 completion  
**Implementation**: Ready to begin with Refactor Coordinator droid
