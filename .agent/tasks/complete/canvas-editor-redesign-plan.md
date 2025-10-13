# Canvas Editor Redesign & Table View Implementation Plan

**Project**: Guardian Angel League Live Graphics Dashboard  
**Date**: 2025-10-12  
**Status**: In Progress  
**Priority**: High  

## 🎯 Overview
Complete redesign of the graphics management system from card-based UI to sortable table view, and transition from modal canvas editor to full-screen route-based editor with advanced features.

## ✅ Completed Work (As of 2025-10-12)

### Backend Updates
- [x] Added `event_name` field to Graphic model (database + API + schemas)
- [x] Created OBS view endpoint `/api/v1/graphics/{id}/view`
- [x] Updated all API endpoints to handle event_name
- [x] Database migration completed successfully

### Frontend Updates
- [x] Updated TypeScript interfaces (Graphic, CreateGraphicRequest, UpdateGraphicRequest)
- [x] Enhanced CreateGraphicDialog with event name field
- [x] Created sortable GraphicsTable component with all required actions
- [x] Updated GraphicsTab to use table instead of cards
- [x] Implemented navigation-based flow instead of modal

### Table Actions Implemented
- [x] **Active Graphics**: Edit, Duplicate, Archive, Delete, View
- [x] **Archived Graphics**: Duplicate, Unarchive, Restore, Delete, View
- [x] Sortable headers: Graphic Name, Event Name, Created, Actions
- [x] Search functionality includes title, event name, and creator

## 🔄 Immediate Changes Required

### Phase 1: Table View Refinements (Priority: High)
**Time Estimate**: 30 minutes

#### 1.1 Remove "Created By" Column
- [ ] Remove `created_by` from GraphicsTable columns
- [ ] Remove from search filtering logic
- [ ] Update table header styling

#### 1.2 Change "Created" to "Edited" 
- [ ] Update header text from "Created" to "Edited"
- [ ] Update data source from `created_at` to `updated_at`
- [ ] Add logic: show creation time if never edited, otherwise show last edit time
- [ ] Update sort field default to `updated_at`

#### 1.3 Backend Cleanup (Optional)
- [ ] Consider removing `created_by` field from API responses (frontend no longer uses it)
- [ ] Keep for audit trail purposes

### Phase 2: Route Structure Setup (Priority: High)
**Time Estimate**: 45 minutes

#### 2.1 Create Route Structure
```
app/
├── canvas/
│   ├── edit/
│   │   └── [id]/
│   │       └── page.tsx    # Full-screen canvas editor
│   └── view/
│       └── [id]/
│           └── page.tsx    # OBS browser source view
```

#### 2.2 OBS View Page (Quick Win)
- [ ] Create `/canvas/view/[id]/page.tsx`
- [ ] Minimal layout (no header, sidebar, etc.)
- [ ] Fetch graphic data from API
- [ ] Render canvas content exactly as designed
- [ ] Responsive sizing for OBS
- [ ] Error handling for missing/archived graphics

#### 2.3 Canvas Edit Page (Structure Only)
- [ ] Create `/canvas/edit/[id]/page.tsx` 
- [ ] Basic layout with header, sidebar, canvas area
- [ ] Import existing CanvasEditor component as starting point
- [ ] Set up route parameters and data fetching

### Phase 3: Full-Screen Canvas Editor (Priority: High)
**Time Estimate**: 3-4 hours

#### 3.1 Layout Structure
```
┌─────────────────────────────────────────────────────────┐
│ [Back] [Graphic Name]                    [Save Button] │ Header
├─────────────────────────────────────────────────────────┤
│ ┌─────────┐                                       │         │
│ │ Sidebar │                                       │         │
│ │ (Collap-│                                       │ Canvas  │
│ │  sible) │                                       │  Area   │
│ └─────────┘                                       │         │
│                                                 │         │
│                                                 │         │
└─────────────────────────────────────────────────────────┘
                                                      │
                                      [Grid][Snap][Zoom] │ Bottom Controls
```

#### 3.2 Component Architecture
- [ ] **FullscreenCanvasEditor**: Main wrapper component
- [ ] **CanvasHeader**: Back button, title, save
- [ ] **CollapsibleSidebar**: Design/Elements/Data Binding tabs
- [ ] **CanvasArea**: Main canvas with zoom/grid
- [ ] **CanvasControls**: Grid snap, toggle, zoom controls

#### 3.3 Sidebar Implementation
- [ ] Collapsible with smooth animations
- [ ] Design Tab: Tools, canvas properties, background upload
- [ ] Elements Tab: Layer management, selection
- [ ] Data Binding Tab: Player field connections

#### 3.4 Canvas Features Implementation
- [ ] **Zoom System**: 25%-400% with keyboard shortcuts (+/-)
- [ ] **Grid System**: 20px dotted grid (CSS background)
- [ ] **Snap to Grid**: 5px tolerance calculations
- [ ] **Responsive Sizing**: Adjust to screen + background image detection
- [ ] **Element Positioning**: Absolute pixel positions with zoom compensation

#### 3.5 Controls Placement
- [ ] **Top Left**: Back button (←)
- [ ] **Top Right**: Canvas name, Save button
- [ **Bottom Right**: Grid toggle, Snap toggle, Zoom controls (+/-)
- [ ] **Keyboard Shortcuts**: Ctrl+Z (undo), Ctrl+Y (redo), Delete, +/- (zoom)

### Phase 4: Advanced Canvas Features (Priority: Medium)
**Time Estimate**: 2-3 hours

#### 4.1 Undo/Redo System
- [ ] **Command Pattern**: Track all actions (create, move, delete, property changes)
- [ ] **History Management**: Array with current index
- [ ] **Memory Management**: Limit history depth (e.g., 50 actions)
- [ ] **Keyboard Shortcuts**: Ctrl+Z, Ctrl+Y
- [ ] **Visual Indicators**: Show when undo/redo available

#### 4.2 Element Management
- [ ] **Drag & Drop**: Click and drag elements on canvas
- [ ] **Multi-Selection**: Shift+click for multiple elements
- [ ] **Copy/Paste**: Duplicate elements within canvas
- [ ] **Alignment Tools**: Snap to center, edges, other elements
- [ ] **Z-Index Management**: Bring forward/send backward

#### 4.3 Enhanced Properties Panel
- [ ] **Real-time Updates**: Live preview of changes
- [ ] **Color Picker**: Enhanced color selection
- [ ] **Font Management**: Font family, size, weight controls
- [ ] **Shape Properties**: Border radius, shadow, opacity

#### 4.4 Canvas Settings
- [ ] **Background Options**: Color, image upload, transparency
- [ ] **Canvas Dimensions**: Custom size or image-based sizing
- [ ] **Grid Settings**: Custom grid size, color, opacity
- [ **Export Settings**: Resolution, format options

### Phase 5: Polish & Optimization (Priority: Low)
**Time Estimate**: 1-2 hours

#### 5.1 Performance Optimization
- [ ] **Virtual Scrolling**: For large element lists
- [ ] **Debounced Updates**: Optimize property changes
- [ ] **Memory Management**: Cleanup unused resources
- [ ] **Bundle Optimization**: Code splitting for faster loading

#### 5.2 User Experience Enhancements
- [ ] **Loading States**: Skeleton screens for data loading
- [ ] **Error Handling**: Graceful error messages and recovery
- [ ] **Tooltips**: Contextual help for controls
- [ ] **Keyboard Navigation**: Full keyboard accessibility

#### 5.3 Mobile Considerations
- [ ] **Responsive Design**: Tablet support (if needed)
- [ ] **Touch Events**: Basic touch support for tablets
- [ ] **UI Adaptations**: Smaller screen accommodations

## 🛠 Technical Implementation Details

### State Management Strategy
```typescript
// Canvas State Structure
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
}
```

### Grid System Implementation
```css
/* 20px dotted grid background */
.canvas-grid {
  background-image: 
    radial-gradient(circle, #ccc 1px, transparent 1px);
  background-size: 20px 20px;
  background-position: 0 0, 10px 10px;
}
```

### Zoom & Coordinate System
```typescript
// Transform coordinates accounting for zoom
const screenToCanvas = (screenX: number, screenY: number) => ({
  x: screenX / zoom,
  y: screenY / zoom
});

const canvasToScreen = (canvasX: number, canvasY: number) => ({
  x: canvasX * zoom,
  y: canvasY * zoom
});
```

### Undo/Redo Command Pattern
```typescript
interface Command {
  type: 'create' | 'update' | 'delete' | 'move';
  elementId?: string;
  beforeState?: any;
  afterState?: any;
  execute(): void;
  undo(): void;
}
```

## 🎯 Success Criteria

### Must-Have Features
- [x] Sortable table view with all required actions
- [ ] Full-screen canvas editor with collapsible sidebar
- [ ] Zoom functionality (25%-400%)
- [ ] Grid system with snap-to-grid
- [ ] Undo/redo with keyboard shortcuts
- [ ] OBS browser source view
- [ ] Responsive canvas sizing with background detection

### Nice-to-Have Features
- [ ] Advanced element selection (multi-select)
- [ ] Enhanced property panels
- [ ] Alignment and distribution tools
- [ ] Custom grid settings
- [ ] Performance optimizations

## 🧪 Testing Strategy

### Manual Testing Checklist
- [ ] Table sorting works correctly on all columns
- [ ] All action buttons work (edit, duplicate, archive, delete, view)
- [ ] OBS view renders correctly in browser
- [ ] Canvas editor loads and saves properly
- [ ] Zoom controls work smoothly
- [ ] Grid snap functionality works
- [ ] Undo/redo tracks all changes
- [ ] Keyboard shortcuts work

### Automated Testing (Future)
- [ ] Unit tests for CanvasState management
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical user flows

## 📅 Timeline Estimate

| Phase | Time Estimate | Priority |
|-------|---------------|----------|
| Phase 1: Table Refinements | 30 min | High |
| Phase 2: Route Setup | 45 min | High |
| Phase 3: Canvas Editor | 3-4 hours | High |
| Phase 4: Advanced Features | 2-3 hours | Medium |
| Phase 5: Polish & Optimize | 1-2 hours | Low |
| **Total** | **7-10 hours** | - |

## 🚨 Risks & Mitigations

### High Risk Items
1. **Canvas Editor Complexity**: Full rewrite of CanvasEditor component
   - **Mitigation**: Phase 2 creates basic structure first, Phase 3 builds incrementally
   
2. **State Management Complexity**: Undo/redo + zoom + grid + elements
   - **Mitigation**: Use proven patterns (Command pattern) and test thoroughly

3. **Performance**: Large canvases with many elements
   - **Mitigation**: Implement virtualization and optimize rendering

### Medium Risk Items
1. **Browser Compatibility**: Canvas features across browsers
   - **Mitigation**: Test on Chrome/Firefox/Safari, use standard web APIs

2. **OBS Integration**: Browser source compatibility
   - **Mitigation**: Keep OBS view simple and use standard web technologies

## 📝 Notes & Decisions

### Architecture Decisions
- **Route-based approach** over modal for better full-screen experience
- **CSS transforms** over HTML5 canvas for easier React integration
- **Command pattern** for undo/redo reliability
- **Absolute positioning** for precise control required by broadcast graphics

### Design Decisions
- **20px grid size** - good balance between precision and usability
- **25%-400% zoom range** - covers typical broadcast needs
- **5px snap tolerance** - forgiving but precise enough
- **Collapsible sidebar** - maximizes canvas space

### Future Considerations
- **Template System**: Save graphic templates for reuse
- **Animation Support**: Keyframe animations for elements
- **Real-time Collaboration**: Multiple users editing same graphic
- **Version History**: Graphic versioning and rollback
- **Export Formats**: PNG, JPEG, video, etc.

---

**Last Updated**: 2025-10-12  
**Next Review**: After Phase 2 completion  
**Dependencies**: None (all external components available)
