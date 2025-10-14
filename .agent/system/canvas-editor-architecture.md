---
id: system.canvas-editor-architecture
version: 3.0
last_updated: 2025-01-13
tags: [canvas, editor, frontend, architecture, route-based, text-elements, property-system]
---

# Canvas Editor Architecture

## Overview
The Canvas Editor is a full-screen, route-based interface for creating and editing live broadcast graphics. It represents a complete architectural evolution from the previous modal-based design to a professional editing environment with advanced features.

## Architecture Transition

### Previous Architecture (v1.0 - Modal-Based)
```tsx
// Modal-based editing (DEPRECATED)
<Modal isOpen={isEditorOpen}>
  <CanvasEditor graphic={selectedGraphic} />
</Modal>
```

### Current Architecture (v2.1 - Route-Based with Visual Improvements)
```tsx
// Route-based editing (CURRENT)
/app/canvas/edit/[id]/page.tsx    # Full-screen editor with enhanced UI
/app/canvas/view/[id]/page.tsx    # OBS browser source
```

## Core Components

### 1. Canvas Edit Page (`/app/canvas/edit/[id]/page.tsx`)
**Purpose**: Full-screen canvas editing interface

**Key Features**:
- Responsive canvas area with zoom controls (25%-400%)
- 20px radial-gradient dotted grid system with snap-to-grid functionality
- Collapsible sidebar with tabbed interface featuring blue accent active states
- Element drag-and-drop with real-time positioning
- Properties panel for element editing
- Background image upload and management
- Enhanced visual interface with lock banner removal and repositioned controls

**Architecture**:
```tsx
┌─────────────────────────────────────────────────────────┐
│ [Header] Back | Title/Event | Undo/Redo | Save/Cancel    │
├─────────────────────────────────────────────────────────┤
│ ┌─────────┐                                       │         │
│ │ Sidebar │         Canvas Area (Zoomable)     │         │
│ │ (Collapse│                                       │         │
│  dible) │    • Elements (text, shapes)      │         │
│ │ Tabs    │    • Background image              │         │
│ │ (Blue   │    • Radial grid (20px dots)      │         │
│ │ accents)│    • Zoom 25%-400%                 │         │
│ └─────────┘                                       │         │
│                                                 │         │
│                                                 │         │
└─────────────────────────────────────────────────────────┘
                                                      │
          [Zoom] [Grid] [Snap] │ [Reset] [Fit] │ Controls
```

### 2. Canvas View Page (`/app/canvas/view/[id]/page.tsx`)
**Purpose**: OBS browser source rendering

**Key Features**:
- Minimal layout (no header, sidebar, controls)
- Responsive sizing for OBS browser sources
- Direct graphic data rendering
- Error handling for missing/archived graphics
- Performance optimized for live streaming

### 3. Enhanced GraphicsTable Component
**Purpose**: Table-based graphics management interface with visual improvements

**Key Features**:
- Sortable columns (Graphic Name, Event Name, Last Edited) with gradient headers
- Search functionality (title, event name)
- Contextual action buttons per graphic with improved alignment and hover effects
- Active/Archived view toggle
- Navigation-based editing workflow
- Enhanced visibility with proper text contrast for dark backgrounds
- Restored edit functionality for active graphics
- Color-coded action buttons (blue for edit, purple for copy, green for archive, red for delete)

## State Management Architecture

### Canvas State Structure
```typescript
interface CanvasState {
  elements: CanvasElement[];
  selectedElements: string[];
  zoom: number; // 0.25 to 4.0
  gridVisible: boolean;
  gridSnapEnabled: boolean;
  canvasSize: { width: number; height: number };
  backgroundImage?: string;
  history: HistoryEntry[];
  historyIndex: number;
  activeTab: 'design' | 'elements' | 'data';
  isDragging: boolean;
  dragStart: { x: number; y: number };
}
```

### Element Management System
```typescript
interface CanvasElement {
  id: string;
  type: 'text' | 'shape' | 'image';
  x: number;
  y: number;
  width?: number;
  height?: number;
  content?: string;
  style?: {
    color?: string;
    fontSize?: number;
    fontFamily?: string;
    backgroundColor?: string;
    borderRadius?: number;
    border?: string;
  };
  dataBinding?: string;
}
```

## Advanced Features Implementation

### 1. Zoom System
**Range**: 25% to 400% in 25% increments
**Implementation**: CSS transforms with coordinate transformation
```typescript
const screenToCanvas = (screenX: number, screenY: number) => ({
  x: screenX / zoom,
  y: screenY / zoom
});
```

### 2. Grid System
**Grid Size**: 20px radial-gradient dotted grid (updated from linear lines)
**Snap Tolerance**: 5px
**Implementation**: CSS radial-gradient background pattern with JavaScript snap calculation
```css
.canvas-grid {
  background-image: 
    radial-gradient(circle, rgba(200, 200, 200, 0.4) 1px, transparent 1px);
  background-size: 20px 20px;
  background-position: 0 0, 10px 10px;
}
```

### 3. Drag and Drop System
**Implementation**: Mouse event handlers with global listeners
**Features**:
- Real-time element positioning
- Snap-to-grid integration
- Visual feedback during drag
- Coordinate transformation with zoom compensation

### 4. Tab System Architecture
**Tabs**: Design, Elements, Data
**State Management**: React state with conditional rendering
**Features**:
- Context-sensitive content
- Enhanced active state indicators with blue accent colors (data-[state=active]:bg-blue-600)
- Smooth transitions
- Improved visual hierarchy with vibrant theme integration

## API Integration

### Canvas Data Persistence
```typescript
interface CreateGraphicRequest {
  title: string;
  event_name?: string;
  data_json?: any;
}

interface UpdateGraphicRequest {
  title?: string;
  event_name?: string;
  data_json?: string;
}
```

### Data Binding System
**Supported Fields**:
- Player Name, Score, Placement, Rank
- Team Name, Tournament Name, Round Name
- Custom data sources (lobby-specific, roster, tournament)

## Performance Optimizations

### 1. Canvas Rendering
- CSS transforms for zoom (GPU acceleration)
- Virtual scrolling for large element lists
- Debounced state updates
- Memory cleanup for unused resources

### 2. Data Management
- Lazy loading of graphics data
- Optimized API calls with caching
- Background image compression
- Efficient element state management

### 3. Browser Compatibility
- Standard web APIs for cross-browser support
- Progressive enhancement for older browsers
- Fallback options for advanced features

## Security Considerations

### 1. Authentication
- JWT token validation for all canvas operations
- Session management with automatic refresh
- Secure file upload handling

### 2. Data Validation
- Input sanitization for all user inputs
- File type restrictions for uploads
- XSS prevention in content rendering

### 3. Access Control
- Graphic-level permissions
- Session-based editing locks
- Audit logging for all modifications

## Browser Source Integration

### OBS Browser Source Configuration
**URL Format**: `http://localhost:3000/canvas/view/{id}`
**Recommended Settings**:
- Custom resolution: 1920x1080 or graphic-specific
- FPS: 60 (or as needed)
- Browser: Hardware acceleration enabled

### Performance Considerations
- Minimal DOM for OBS sources
- Efficient CSS animations
- Low resource usage
- No authentication required for public viewing

## Development Guidelines

### Component Structure
```
dashboard/app/canvas/
├── edit/
│   └── [id]/
│       └── page.tsx          # Main editor interface
└── view/
    └── [id]/
        └── page.tsx          # OBS browser source

dashboard/components/
├── graphics/
│   ├── GraphicsTable.tsx    # Table management
│   └── CreateGraphicDialog.tsx
└── canvas/                  # Legacy components (to be archived)
    └── CanvasEditor.tsx      # Modal-based (DEPRECATED)
```

### State Management Best Practices
- Use React hooks for local state
- Implement proper cleanup for global event listeners
- Optimize re-renders with useCallback and useMemo
- Maintain immutability for state updates

### TypeScript Type Safety
- Comprehensive interfaces for all data structures
- Type-safe API integration
- Proper error handling with typed responses
- Generic utility functions where appropriate

## Migration Notes

### From Modal to Route-Based
1. **URL Changes**: Navigation now uses `/canvas/edit/{id}` instead of modal
2. **State Management**: Canvas state is now page-scoped
3. **Authentication**: Same JWT-based system applies
4. **Data Persistence**: Enhanced with more comprehensive state saving

### Breaking Changes
- Component props structure completely changed
- Canvas data format enhanced with additional properties
- URL routing requires proper parameter handling
- Browser source URLs updated

## Recent Visual Improvements (2025-01-13)

### Lock Banner Removal
- **Implementation**: Complete removal of LockBanner component and containing div
- **Impact**: Cleaner interface with reduced visual clutter
- **Functionality Preserved**: All lock management functionality remains intact through status indicators

### Enhanced Grid System
- **Previous**: Linear gradient lines with full grid coverage
- **Current**: Radial-gradient dots with 20px spacing
- **Benefits**: Better visual hierarchy, reduced visual noise, improved readability
- **Implementation**: CSS radial-gradient with proper opacity for subtle appearance

### Control Repositioning
- **Header Area**: Undo/Redo buttons moved to top right near save/cancel actions
- **Left Side**: Zoom controls (zoom in/out/percentage display) repositioned
- **Right Side**: Reset and Fit buttons moved to opposite side for better workflow
- **Bottom Area**: Removed duplicate controls to reduce redundancy

### Tab Styling Enhancement
- **Active State**: Blue accent colors (data-[state=active]:bg-blue-600 data-[state=active]:text-white)
- **Visual Feedback**: Clear distinction between active and inactive tabs
- **Theme Integration**: Consistent with overall vibrant UI theme

### Dark Theme Integration
- **Background**: Consistent with dashboard dark theme (#1a1a1a)
- **Text Colors**: Enhanced contrast for improved readability
- **UI Elements**: All components follow dark theme standards
- **Accessibility**: Maintained proper contrast ratios

### Graphics Table Integration
- **Enhanced Visibility**: Improved text contrast and table header styling
- **Action Buttons**: Color-coded with proper hover effects
- **Edit Functionality**: Restored for active graphics with proper workflow
- **Consistency**: Matches canvas editor visual improvements

## Property Element System (v3.0)

### Overview
The canvas editor has evolved from a shape-based system to a sophisticated text-driven property system that supports dynamic data binding and professional typography.

### Element Types
```typescript
type ElementType = 'text' | 'player' | 'score' | 'placement';

interface PropertyElement {
  id: string;
  type: ElementType;
  content: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  fontSize: number;
  fontFamily: string;
  color: string;
  backgroundColor: string;
  dataBinding?: {
    source: 'api' | 'manual';
    field: string;
    apiEndpoint?: string;
    manualValue?: string;
  };
  isPlaceholder: boolean;
}
```

### Property Element Configuration
- **Player Property**: Text element for player names with API data binding
- **Score Property**: Text element for scores with API data binding
- **Placement Property**: Text element for rankings/placements with API data binding
- **Text Property**: Generic text element for static content

### Data Binding System
```typescript
interface DataBinding {
  source: 'api' | 'manual';
  field: 'player_name' | 'player_score' | 'player_placement' | 'player_rank' | 'team_name';
  apiEndpoint?: string;
  manualValue?: string;
}
```

### Typography System
- **Font Options**: Arial, Times New Roman, Helvetica, Georgia, Verdana
- **Default Styling**: Black text on transparent background
- **Customization**: Full control over font size, color, and background
- **Persistence**: Font settings saved with graphic data

## Canvas Enhancements (v3.0)

### Size and Zoom System
- **Canvas Size**: 5000x5000 pixels (increased from 1920x1080)
- **Zoom Range**: 25% to 500% (increased from 400% maximum)
- **Zoom Controls**: Keyboard shortcuts (Ctrl/Cmd + scroll wheel) and button controls
- **Smart Scaling**: Automatic fit-to-screen functionality

### Element Snapping System
- **Grid Snapping**: 20px grid with toggle control
- **Element Snapping**: Elements snap to each other's edges and centers
- **Visual Feedback**: Blue snap lines during dragging
- **Snap Threshold**: 20px sensitivity matching grid system

### View Mode Implementation
- **Automatic Bounds Detection**: Smart canvas sizing based on content
- **Background Priority**: Uses background image dimensions if available
- **Element Bounds**: Calculates bounds from element positions if no background
- **OBS Integration**: Optimized browser source rendering for live streaming

### Event Management System
- **Dropdown Interface**: Event name selection with create new option
- **Event Persistence**: Event names saved across graphic sessions
- **Inline Creation**: Text input appears when creating new events
- **Event Storage**: Local storage with API persistence capability

### UI Layout Improvements (v3.0)
- **Header Design**: Side-by-side title and event editing with visual feedback
- **Inline Editing**: Clear text inputs with hover tooltips
- **Visual Indicators**: Editable field indicators with helpful tooltips
- **Professional Styling**: Dark theme compliant with proper contrast

### Text Editing Fixes (v3.0)
- **Content Persistence**: Fixed text element content reversion issues
- **Empty State Handling**: Proper support for empty text content
- **Input Validation**: Enhanced input sanitization and validation

## Future Enhancements

### Planned Features
- Undo/redo system with Command pattern
- Multi-selection capabilities
- Advanced alignment and distribution tools
- Template system for graphic reusability
- Real-time collaboration features

### Scalability Considerations
- Support for larger canvases (4K, 8K)
- Performance optimization for complex graphics
- Cloud-based storage for media assets
- Advanced animation capabilities

### Scalability Considerations
- Support for larger canvases (4K, 8K)
- Performance optimization for complex graphics
- Cloud-based storage for media assets
- Advanced animation capabilities

---

**Last Updated**: 2025-01-13  
**Next Review**: After next major feature release  
**Dependencies**: None (all components and APIs are stable)
**Visual Improvements**: Complete lock banner removal, enhanced grid system, control repositioning, blue accent tab styling
