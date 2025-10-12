---
id: system.canvas-editor-architecture
version: 2.1
last_updated: 2025-10-12
tags: [canvas, editor, frontend, architecture, route-based]
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

### Current Architecture (v2.1 - Route-Based)
```tsx
// Route-based editing (CURRENT)
/app/canvas/edit/[id]/page.tsx    # Full-screen editor
/app/canvas/view/[id]/page.tsx    # OBS browser source
```

## Core Components

### 1. Canvas Edit Page (`/app/canvas/edit/[id]/page.tsx`)
**Purpose**: Full-screen canvas editing interface

**Key Features**:
- Responsive canvas area with zoom controls (25%-400%)
- 20px dotted grid system with snap-to-grid functionality
- Collapsible sidebar with tabbed interface
- Element drag-and-drop with real-time positioning
- Properties panel for element editing
- Background image upload and management

**Architecture**:
```tsx
┌─────────────────────────────────────────────────────────┐
│ [Header] Back Button | Graphic Name | Save Button        │
├─────────────────────────────────────────────────────────┤
│ ┌─────────┐                                       │         │
│ │ Sidebar │         Canvas Area (Zoomable)     │         │
│ │ (Collapse│                                       │         │
│  dible) │    • Elements (text, shapes)      │         │
│         │    • Background image              │         │
│         │    • Grid overlay (20px dots)      │         │
│         │    • Zoom 25%-400%                 │         │
│ └─────────┘                                       │         │
│                                                 │         │
│                                                 │         │
└─────────────────────────────────────────────────────────┘
                                                      │
                    [Grid][Snap][Zoom+/-] │ Bottom Controls
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
**Purpose**: Table-based graphics management interface

**Key Features**:
- Sortable columns (Graphic Name, Event Name, Last Edited)
- Search functionality (title, event name)
- Contextual action buttons per graphic
- Active/Archived view toggle
- Navigation-based editing workflow

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
**Grid Size**: 20px dotted grid
**Snap Tolerance**: 5px
**Implementation**: CSS background pattern with JavaScript snap calculation
```css
.canvas-grid {
  background-image: 
    radial-gradient(circle, #ccc 1px, transparent 1px);
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
- Active state indicators
- Smooth transitions

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

---

**Last Updated**: 2025-10-12  
**Next Review**: After next major feature release  
**Dependencies**: None (all components and APIs are stable)
