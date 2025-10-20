# Canvas Data Assignment Simplification Plan

**Project**: Guardian Angel League Live Graphics Dashboard  
**Created**: 2025-01-25  
**Status**: 🟡 In Progress  
**Priority**: High  

## Overview

Transform the current complex data assignment system into an intuitive visual "draw boxes, auto-fill data" approach for canvas elements.

## Current Problems Identified

- ✅ Complex manual field assignments for each element
- ✅ Confusing template/static modes with row/slot configurations  
- ✅ No visual preview of how data will actually look
- ✅ Required individual player assignment instead of automatic ranking

## Proposed Solution: "Draw Boxes, Auto-Fill Data"

**Core Concept**: Draw boxes on canvas where you want player names, scores, placements → Style them → Preview with mock data → Auto-populate with real ranked data

## Implementation Phases

### Phase 1: Core Infrastructure 🟡 In Progress

#### 1.1 New Element Type System 
- [ ] Create simplified element types: `name`, `score`, `placement`, `static-text`
- [ ] Design `SimpleCanvasElement` interface with position, size, style, sortOrder
- [ ] Implement `TemplateBinding` interface for auto-population configuration
- [ ] Create `PreviewMode` interface for mock data visualization

**Status**: Planning complete, ready to implement

#### 1.2 Simplified Data Structures
- [ ] Define new TypeScript interfaces in `dashboard/types/`
- [ ] Create Python Pydantic models for backend API
- [ ] Design data migration strategy for existing graphics

#### 1.3 Canvas Editor Infrastructure
- [ ] Analyze current canvas editor implementation
- [ ] Identify integration points for new tools
- [ ] Plan UI component changes

**Estimated Time**: 3-4 days

### Phase 2: Visual Box Drawing Tools ⏳ Not Started

#### 2.1 Simplified Tool Palette
- [ ] Create new simplified tools: select, name-box, score-box, placement-box, style, preview
- [ ] Design tool UI with clear icons and labels
- [ ] Implement tool switching logic

#### 2.2 Drag-and-Drop Box Creation
- [ ] Implement click-and-drag box creation
- [ ] Add automatic grid snapping
- [ ] Create real-time dimension display
- [ ] Add visual element type indicators

#### 2.3 Element Styling Panel
- [ ] Simplified style properties (font, color, size, alignment)
- [ ] Live style preview during editing
- [ ] Style presets for common use cases

**Estimated Time**: 4-5 days

### Phase 3: Template-Based Data Binding ⏳ Not Started

#### 3.1 Template Engine
- [ ] Create template population logic
- [ ] Implement auto-sorting by total points
- [ ] Handle dynamic player count variations
- [ ] Create template validation system

#### 3.2 Unified Data Service
- [ ] Create `SimplifiedDataService` class
- [ ] Integrate with existing `StandingsAggregator`
- [ ] Add Google Sheets connectivity
- [ ] Implement mock data generation for preview

#### 3.3 Preview Mode Implementation
- [ ] Toggle between design and preview modes
- [ ] Live data updates in preview
- [ ] Show data source indicators
- [ ] Handle empty/missing data gracefully

**Estimated Time**: 5-6 days

### Phase 4: User Experience Enhancements ⏳ Not Started

#### 4.1 Guided Setup Flow
- [ ] Create setup wizard with 4 steps
- [ ] Step 1: Choose template type (leaderboard, bracket, grid, custom)
- [ ] Step 2: Configure data source (latest, snapshot, manual)
- [ ] Step 3: Style elements (fonts, colors, sizes)
- [ ] Step 4: Preview and adjust (spacing, alignment)

#### 4.2 Smart Templates
- [ ] Leaderboard template: Vertical name/score/placement columns
- [ ] Bracket layout: Tournament bracket positioning
- [ ] Grid layout: Multiple columns for large tournaments
- [ ] Custom: Free-form arrangement

#### 4.3 Auto-Arrangement Features
- [ ] Intelligent positioning based on template type
- [ ] Automatic spacing calculations
- [ ] Responsive layout adjustments

**Estimated Time**: 4-5 days

### Phase 5: Backend API Updates ⏳ Not Started

#### 5.1 Simplified Graphics Schema
- [ ] Create `SimplifiedGraphicCreate` Pydantic model
- [ ] Design `TemplateConfig` model
- [ ] Update existing graphic creation endpoints

#### 5.2 Enhanced Scoreboard API
- [ ] Create `/scoreboard/simplified` endpoint
- [ ] Optimize data for template consumption
- [ ] Add template validation endpoint

#### 5.3 Mock Data Service
- [ ] Create realistic mock data generation
- [ ] Add data snapshot functionality
- [ ] Implement preview data caching

**Estimated Time**: 3-4 days

### Phase 6: Integration & Testing ⏳ Not Started

#### 6.1 Integration Testing
- [ ] Test with existing Google Sheets data
- [ ] Verify scoreboard snapshot integration
- [ ] Test Riot API connectivity (if applicable)
- [ ] Validate data flow end-to-end

#### 6.2 User Acceptance Testing
- [ ] Test complete workflow with real users
- [ ] Performance testing with large tournaments
- [ ] Error handling and edge cases
- [ ] Documentation and training materials

#### 6.3 Migration Strategy
- [ ] Plan migration of existing graphics
- [ ] Create backward compatibility layer
- [ ] Data migration scripts
- [ ] Rollback procedures

**Estimated Time**: 3-4 days

## Required Files & Components

### Frontend Changes
- `dashboard/components/canvas/` - New simplified tools
- `dashboard/types/index.ts` - New simplified interfaces
- `dashboard/lib/api.ts` - Updated API calls
- `dashboard/lib/canvas-helpers.ts` - New helper functions

### Backend Changes  
- `api/routers/graphics.py` - New simplified endpoints
- `api/services/graphics_service.py` - Template processing logic
- `core/data_access/` - Enhanced data access patterns

### Database Changes
- New template storage schema
- Migration scripts for existing graphics
- Enhanced caching for preview data

## Success Metrics

- **Setup Time Reduction**: From 15+ minutes to 2-3 minutes for basic graphics
- **User Satisfaction**: Intuitive interface requiring minimal training  
- **Error Reduction**: Eliminate complex data binding mistakes
- **Preview Accuracy**: Realistic preview matches final output
- **Template Reuse**: Easy adaptation of existing graphics

## Dependencies & Risks

### Dependencies
- Existing canvas editor infrastructure
- StandingsAggregator service stability
- Google Sheets API access
- Database schema changes approval

### Risks
- Breaking existing graphics functionality
- Performance impact with real-time preview
- Data migration complexity
- User adoption of new workflow

## Timeline

- **Week 1**: Phase 1 - Core Infrastructure (3-4 days)
- **Week 2**: Phase 2 - Visual Box Drawing Tools (4-5 days)  
- **Week 3**: Phase 3 - Template-Based Data Binding (5-6 days)
- **Week 4**: Phase 4 - User Experience Enhancements (4-5 days)
- **Week 5**: Phase 5 - Backend API Updates (3-4 days)
- **Week 6**: Phase 6 - Integration & Testing (3-4 days)

**Total Estimated Time**: 6 weeks

## Current Status

🟡 **Phase 1 In Progress** - Planning complete, ready to start implementation of core infrastructure

## Next Steps

1. Implement simplified element type interfaces
2. Create new canvas tool infrastructure  
3. Begin visual box drawing implementation
4. Update todo tracking system

---

**Last Updated**: 2025-01-25  
**Next Review**: After Phase 1 completion  
**Assigned to**: Context Manager Droid
