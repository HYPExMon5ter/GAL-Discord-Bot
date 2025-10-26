# Canvas System Rebuild - Implementation Plan

## Overview
Complete rebuild of canvas system with clean architecture, removing all legacy complexity. This will be executed using coordinated droids with git commits after each phase.

## Team
- **Context Manager**: Overall orchestration
- **Refactor Coordinator**: Code demolition & type system
- **Dashboard Designer**: UI components
- **React Canvas Hooks Specialist**: State management hooks
- **Canvas Integration Specialist**: Component assembly & integration

## Phases

### Phase 0: Planning & Setup ✅
- Create plan document
- Create new droids
- Commit plan to git

### Phase 1: Demolition
**Droid:** Refactor Coordinator
**Tasks:**
- Delete `dashboard/components/canvas/CanvasEditor.tsx`
- Delete `dashboard/lib/canvas-helpers.ts`
- Delete `dashboard/lib/canvas-styling.ts`
- Clean canvas types from `dashboard/types/index.ts`

### Phase 2: New Type System
**Droid:** Refactor Coordinator
**Tasks:**
- Create `dashboard/lib/canvas/types.ts`
- Define clean interfaces (CanvasState, CanvasElement, etc.)
- Update exports in `dashboard/types/index.ts`

### Phase 3: Utility Functions
**Droid:** Refactor Coordinator
**Tasks:**
- Create `dashboard/lib/canvas/mock-data.ts`
- Create `dashboard/lib/canvas/element-factory.ts`
- Create `dashboard/lib/canvas/serializer.ts`
- Create `dashboard/lib/canvas/snapping.ts`

### Phase 4: Base Element Components
**Droid:** Dashboard Designer
**Tasks:**
- Create `dashboard/components/canvas/elements/TextElement.tsx`
- Create `dashboard/components/canvas/elements/BackgroundRenderer.tsx`
- Create `dashboard/components/canvas/elements/DynamicList.tsx`

### Phase 5: Canvas Hooks
**Droid:** React Canvas Hooks Specialist
**Tasks:**
- Create `dashboard/hooks/canvas/useCanvasState.ts`
- Create `dashboard/hooks/canvas/usePanZoom.ts`
- Create `dashboard/hooks/canvas/useElementDrag.ts`
- Create `dashboard/hooks/canvas/useSnapping.ts`
- Create `dashboard/hooks/canvas/useTournamentData.ts`

### Phase 6: Sidebar UI
**Droid:** Dashboard Designer
**Tasks:**
- Create `dashboard/components/canvas/TopBar.tsx`
- Create `dashboard/components/canvas/ToolsTab.tsx`
- Create `dashboard/components/canvas/LayersTab.tsx`
- Create `dashboard/components/canvas/PropertiesPanel.tsx`
- Create `dashboard/components/canvas/Sidebar.tsx`

### Phase 7: Viewport
**Droid:** Dashboard Designer
**Tasks:**
- Create `dashboard/components/canvas/Viewport.tsx`
- Implement pan/zoom controls
- Add element dragging with snapping

### Phase 8: Canvas Editor
**Droid:** Canvas Integration Specialist
**Tasks:**
- Create `dashboard/components/canvas/CanvasEditor.tsx`
- Assemble all editor components
- Wire up state management
- Test with mock data preview

### Phase 9: Canvas View
**Droid:** Canvas Integration Specialist
**Tasks:**
- Create `dashboard/components/canvas/CanvasView.tsx`
- Integrate with real API data
- Test dynamic updates

### Phase 10: Dashboard Integration
**Droid:** Canvas Integration Specialist
**Tasks:**
- Update dashboard routes
- Verify API integration
- Test complete workflows
- Add error handling

### Phase 11: Finalization
**Droid:** Context Manager
**Tasks:**
- Verify all phases complete
- Update documentation
- Final testing pass

## Git Commit Pattern
Each phase will commit with descriptive message:
```
[droid-name] [type]: [description]

Phase X: [phase description]
- Detail 1
- Detail 2
- Detail 3

Files:
- Created: [files]
- Modified: [files]
- Deleted: [files]
```

## Success Criteria
- [ ] Old canvas system removed
- [ ] New system < 1,500 total lines
- [ ] Editor shows mock data
- [ ] View mode shows real data
- [ ] All features work
- [ ] No JSX errors
- [ ] Clean git history

## Context
This is a complete rebuild - no migration needed. The goal is a clean, maintainable canvas system with clear separation of concerns.

Created: $(date)
Status: ✅ COMPLETED - All phases executed successfully
