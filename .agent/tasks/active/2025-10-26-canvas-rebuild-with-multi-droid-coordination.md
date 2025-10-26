# Canvas Rebuild - Multi-Droid Coordination Strategy

## Droid Team Assignments

### 🎯 Droids to Use (5 Total)

#### 1. **Context Manager** (EXISTING - Active)
**Role:** Project Orchestrator & Task Coordinator
**Responsibilities:**
- Overall project coordination
- Task dependency management
- Progress tracking across all droids
- Conflict resolution between droids
- Final integration verification

**Why:** Already active and designed for multi-droid orchestration

---

#### 2. **Refactor Coordinator** (EXISTING - Will Activate)
**Role:** Code Demolition & Architecture Lead
**Responsibilities:**
- Phase 1: Delete old canvas system safely
- Phase 2: Create new type system
- Phase 3: Create utility functions (mock-data, factory, serializer, snapping)
- Ensure clean separation of concerns
- Verify no broken imports after deletion

**Phases Assigned:** 1, 2, 3
**Git Commits:** 3 commits

**Why:** Specialized in large-scale refactoring and file restructuring

---

#### 3. **Dashboard Designer** (EXISTING - Will Activate)
**Role:** UI Component Specialist
**Responsibilities:**
- Phase 4: Create base element components (TextElement, BackgroundRenderer, DynamicList)
- Phase 6: Build sidebar UI (TopBar, ToolsTab, LayersTab, PropertiesPanel, Sidebar)
- Phase 7: Build Viewport component
- Ensure shadcn/Tailwind consistency
- Polish visual feedback and interactions

**Phases Assigned:** 4, 6, 7
**Git Commits:** 3 commits

**Why:** Expert in React/shadcn component architecture

---

#### 4. **Canvas State Manager** (NEW - Create)
**Role:** State Management & Hooks Specialist
**Responsibilities:**
- Phase 5: Create all canvas hooks
  - `useCanvasState.ts` - State management
  - `usePanZoom.ts` - Viewport controls
  - `useElementDrag.ts` - Drag logic
  - `useSnapping.ts` - Snapping logic
  - `useTournamentData.ts` - API data fetching
- Ensure hooks follow React best practices
- Optimize performance and re-renders

**Phases Assigned:** 5
**Git Commits:** 1 commit

**Why:** Specialized focus on React hooks and state management logic

**Create with:**
```bash
droid create canvas-state-manager --description="React hooks specialist for canvas state management, pan/zoom, drag interactions, element snapping, and API data fetching. Ensures hooks follow React best practices, optimize performance, handle edge cases, and maintain clean separation between UI and logic. Experienced with custom hooks, useCallback, useMemo, and complex state interactions."
```

---

#### 5. **Canvas Integration Engineer** (NEW - Create)
**Role:** Integration & Main Component Assembly
**Responsibilities:**
- Phase 8: Build CanvasEditor (editor mode with mock preview)
- Phase 9: Build CanvasView (view mode with real data)
- Phase 10: Dashboard integration
- Connect all components and hooks
- Verify end-to-end functionality
- Test save/load workflow
- Ensure API integration works

**Phases Assigned:** 8, 9, 10
**Git Commits:** 3 commits

**Why:** Focused on assembling all pieces into working system

**Create with:**
```bash
droid create canvas-integration-engineer --description="Integration specialist for assembling canvas components into complete working systems. Builds main editor and view modes, connects UI components with state hooks, integrates with existing dashboard and API, ensures proper data flow between components, handles error states and loading, tests complete workflows, and verifies end-to-end functionality."
```

---

## Work Distribution

### Phase Assignments

| Phase | Droid | Tasks | Commit |
|-------|-------|-------|--------|
| 0 | Context Manager | Create plan, commit plan | ✓ |
| 1 | Refactor Coordinator | Delete old canvas files | ✓ |
| 2 | Refactor Coordinator | Create new type system | ✓ |
| 3 | Refactor Coordinator | Create utility functions | ✓ |
| 4 | Dashboard Designer | Create element components | ✓ |
| 5 | Canvas State Manager | Create all hooks | ✓ |
| 6 | Dashboard Designer | Build sidebar UI | ✓ |
| 7 | Dashboard Designer | Build Viewport | ✓ |
| 8 | Canvas Integration Engineer | Build CanvasEditor | ✓ |
| 9 | Canvas Integration Engineer | Build CanvasView | ✓ |
| 10 | Canvas Integration Engineer | Dashboard integration | ✓ |
| 11 | Context Manager | Final verification, documentation | ✓ |

**Total Commits:** 11 (one per phase)

---

## Parallel Execution Strategy

### Wave 1: Foundation (Sequential)
1. **Context Manager** creates plan → commit
2. **Refactor Coordinator** deletes old code → commit
3. **Refactor Coordinator** creates types → commit
4. **Refactor Coordinator** creates utilities → commit

**Why Sequential:** Each builds on the previous

---

### Wave 2: Components (Can Parallelize)
5. **Dashboard Designer** creates element components → commit
6. **Canvas State Manager** creates hooks → commit

**Can run in parallel** - no dependencies between them

---

### Wave 3: UI Assembly (Sequential)
7. **Dashboard Designer** builds sidebar → commit
8. **Dashboard Designer** builds viewport → commit

**Why Sequential:** Viewport may reference sidebar patterns

---

### Wave 4: Integration (Sequential)
9. **Canvas Integration Engineer** builds CanvasEditor → commit
10. **Canvas Integration Engineer** builds CanvasView → commit
11. **Canvas Integration Engineer** integrates with dashboard → commit

**Why Sequential:** Each depends on previous completion

---

### Wave 5: Finalization
12. **Context Manager** verifies everything works, updates docs → commit

---

## Coordination Protocol

### Context Manager Responsibilities:
- Start each wave when previous wave complete
- Monitor for blockers or conflicts
- Resolve any integration issues
- Track progress across all droids
- Ensure each commit is clean and tested
- Final quality check

### Droid Communication:
- Each droid reports completion to Context Manager
- Each droid creates git commit with clear message
- Each droid runs basic tests before committing
- Any blockers reported immediately to Context Manager

---

## Git Commit Strategy

Each droid follows this pattern:
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

**Example:**
```
[refactor-coordinator] refactor: remove legacy canvas system

Phase 1: Demolition of old canvas code
- Deleted CanvasEditor.tsx (1,994 lines)
- Deleted canvas-helpers.ts (874 lines)
- Deleted canvas-styling.ts
- Cleaned canvas types from index.ts

Files:
- Deleted: dashboard/components/canvas/CanvasEditor.tsx
- Deleted: dashboard/lib/canvas-helpers.ts
- Deleted: dashboard/lib/canvas-styling.ts
- Modified: dashboard/types/index.ts
```

---

## Success Metrics

Each droid must verify:
- ✅ Code compiles (no TypeScript errors)
- ✅ No broken imports
- ✅ Git commit is clean
- ✅ Basic functionality works
- ✅ Hand-off to next droid is clean

Context Manager verifies:
- ✅ All phases complete
- ✅ All commits made
- ✅ Integration works end-to-end
- ✅ Documentation updated

---

## Timeline Estimate

| Wave | Estimated Time | Parallelizable |
|------|---------------|----------------|
| Wave 1 (Foundation) | 20-30 min | No |
| Wave 2 (Components) | 15-20 min | **Yes** |
| Wave 3 (UI Assembly) | 15-20 min | No |
| Wave 4 (Integration) | 20-30 min | No |
| Wave 5 (Finalization) | 10-15 min | No |

**Total:** ~80-115 minutes (1.3-1.9 hours)
**With Parallelization:** ~70-100 minutes (1.2-1.7 hours)

---

## Commands to Execute

### 1. Create New Droids
```bash
droid create canvas-state-manager --description="React hooks specialist for canvas state management, pan/zoom, drag interactions, element snapping, and API data fetching. Ensures hooks follow React best practices, optimize performance, handle edge cases, and maintain clean separation between UI and logic. Experienced with custom hooks, useCallback, useMemo, and complex state interactions."

droid create canvas-integration-engineer --description="Integration specialist for assembling canvas components into complete working systems. Builds main editor and view modes, connects UI components with state hooks, integrates with existing dashboard and API, ensures proper data flow between components, handles error states and loading, tests complete workflows, and verifies end-to-end functionality."
```

### 2. Start Orchestration
```bash
droid start context-manager --request="Coordinate canvas system rebuild with refactor-coordinator, dashboard-designer, canvas-state-manager, and canvas-integration-engineer. Execute phases sequentially with git commits after each phase. Ensure clean hand-offs between droids."
```

### 3. Monitor Progress
```bash
# Context Manager will dispatch tasks automatically
# Each droid will report completion
# Final integration verification by Context Manager
```

---

## This Approach Achieves:

✅ **Speed:** Parallel execution where possible (Wave 2)
✅ **Quality:** Each droid specialized in their domain
✅ **Safety:** Git commits after each phase for rollback
✅ **Clarity:** Clear responsibilities and hand-offs
✅ **Verification:** Context Manager ensures everything integrates
✅ **Documentation:** Automatic tracking via git commits

Ready to create the droids and start execution?