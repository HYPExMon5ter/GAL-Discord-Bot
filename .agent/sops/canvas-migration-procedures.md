---
id: sops.canvas-migration-procedures
version: 1.0
last_updated: 2025-10-12
tags: [sop, migration, canvas, modal-to-route, legacy, upgrade]
status: active
---

# Canvas Migration Procedures SOP

## Overview
This Standard Operating Procedure (SOP) details the comprehensive migration process from the legacy modal-based Canvas Editor to the new route-based Canvas Editor in the Live Graphics Dashboard 2.0.

## Purpose
- Provide systematic migration procedures for legacy canvas systems
- Ensure data integrity during transition
- Minimize disruption to active workflows
- Document technical migration steps and validation procedures

## Scope
- Legacy modal-based Canvas Editor deprecation
- Route-based Canvas Editor implementation
- Data migration and compatibility
- User training and transition procedures
- System configuration updates

## Prerequisites
- System Administrator access
- Understanding of both legacy and new canvas architectures
- Database backup capabilities
- User communication channels
- Testing environment access

## Migration Overview

### Legacy Architecture (Modal-Based)
```tsx
// DEPRECATED - Modal-based editing
<Modal isOpen={isEditorOpen}>
  <CanvasEditor graphic={selectedGraphic} />
</Modal>
```

### New Architecture (Route-Based)
```tsx
// CURRENT - Route-based editing
/app/canvas/edit/[id]/page.tsx    # Full-screen editor
/app/canvas/view/[id]/page.tsx    # OBS browser source
```

## Phase 1: Pre-Migration Preparation

### 1.1 System Assessment
1. **Inventory Active Graphics**
   - Count all active graphics in database
   - Identify graphics currently in use
   - Document existing workflows and dependencies
   - Note any custom integrations or special cases

2. **User Impact Analysis**
   - Identify active users and their workflows
   - Document current editing patterns
   - Assess training needs for new interface
   - Plan communication strategy

3. **Technical Assessment**
   - Review existing modal component implementations
   - Identify data format changes required
   - Check API endpoint compatibility
   - Validate database schema requirements

### 1.2 Backup Procedures
1. **Database Backup**
   ```sql
   -- Full database backup
   pg_dump gal_dashboard > backup_pre_migration_$(date +%Y%m%d).sql
   
   -- Graphics table specific backup
   CREATE TABLE graphics_backup_pre_migration AS 
   SELECT * FROM graphics;
   ```

2. **Configuration Backup**
   - Backup `.env.local` files
   - Archive configuration YAML files
   - Document current system settings
   - Save API endpoint configurations

3. **User Data Backup**
   - Export active sessions data
   - Archive canvas locks data
   - Backup user preferences and settings
   - Document current permission structures

### 1.3 Environment Preparation
1. **Staging Environment**
   - Create migration testing environment
   - Restore database backup to staging
   - Deploy new route-based editor code
   - Configure testing parameters

2. **Testing Data Setup**
   - Copy representative graphics for testing
   - Create test user accounts
   - Set up OBS browser source test scenarios
   - Prepare performance testing data

## Phase 2: Technical Migration

### 2.1 Code Migration

#### 2.1.1 Remove Modal Components
1. **Identify Modal Dependencies**
   ```bash
   # Find all modal-based canvas editor references
   grep -r "CanvasEditor" dashboard/components/ --include="*.tsx"
   grep -r "isEditorOpen" dashboard/components/ --include="*.tsx"
   grep -r "modal.*canvas" dashboard/components/ --include="*.tsx"
   ```

2. **Remove Legacy Components**
   - Archive `dashboard/components/canvas/CanvasEditor.tsx`
   - Remove modal-related imports and dependencies
   - Clean up unused modal state management
   - Remove modal-based navigation logic

3. **Update Component References**
   - Replace modal opens with route navigation
   - Update props interfaces for route-based editor
   - Remove modal-specific state management
   - Clean up unused event handlers

#### 2.1.2 Implement Route Structure
1. **Create Route Directory Structure**
   ```
   dashboard/app/
   ├── canvas/
   │   ├── edit/
   │   │   └── [id]/
   │   │       └── page.tsx    # Editor route
   │   └── view/
   │       └── [id]/
   │           └── page.tsx    # Viewer route
   ```

2. **Implement Editor Route**
   ```typescript
   // dashboard/app/canvas/edit/[id]/page.tsx
   'use client';
   
   import { useParams, useRouter } from 'next/navigation';
   import { FullscreenCanvasEditor } from '@/components/canvas/FullscreenCanvasEditor';
   import { useAuth } from '@/hooks/use-auth';
   import { useGraphics } from '@/hooks/use-graphics';
   
   export default function EditCanvasPage() {
     const params = useParams();
     const router = useRouter();
     const { user, loading: authLoading } = useAuth();
     const { getGraphic, loading: graphicsLoading } = useGraphics();
     
     // Implementation details...
   }
   ```

3. **Implement Viewer Route**
   ```typescript
   // dashboard/app/canvas/view/[id]/page.tsx
   import { CanvasViewer } from '@/components/canvas/CanvasViewer';
   import { getGraphicPublic } from '@/lib/api';
   
   export default function ViewCanvasPage({ params }: { params: { id: string } }) {
     // Minimal OBS browser source implementation
   }
   ```

#### 2.1.3 Update Navigation Logic
1. **Replace Modal Triggers with Navigation**
   ```typescript
   // OLD - Modal-based
   const [isEditorOpen, setIsEditorOpen] = useState(false);
   
   // NEW - Route-based
   const router = useRouter();
   const handleEdit = (graphic: Graphic) => {
     router.push(`/canvas/edit/${graphic.id}`);
   };
   ```

2. **Update Table Action Buttons**
   - Replace "Edit" button onclick with navigation
   - Update "View" button to open viewer route
   - Maintain existing action patterns (archive, delete, duplicate)
   - Add loading states for navigation

### 2.2 API Migration

#### 2.2.1 Update API Endpoints
1. **Enhance Graphics Endpoints**
   - Add support for route-based editor data requirements
   - Implement OBS viewer endpoint with public access
   - Update response schemas for new data structures
   - Add enhanced error handling for route operations

2. **Implement Lock Management for Routes**
   - Update lock acquisition to work with route-based access
   - Implement automatic lock cleanup for route navigation
   - Add lock status API for editor route state management
   - Handle lock conflicts in route context

#### 2.2.2 Data Format Updates
1. **Graphic Data Structure**
   ```typescript
   // Enhanced graphic data structure for route-based editor
   interface GraphicData {
     elements: CanvasElement[];
     canvasSize: { width: number; height: number };
     backgroundImage?: string;
     gridSettings: {
       visible: boolean;
       snapEnabled: boolean;
       size: number;
     };
     version: string;
     lastModified: string;
   }
   ```

2. **Migration Scripts**
   ```python
   # Database migration script
   def migrate_graphics_data():
       """Migrate existing graphics data to new format"""
       graphics = db.query(Graphic).all()
       for graphic in graphics:
           # Convert legacy data format to new structure
           new_data = convert_legacy_format(graphic.data_json)
           graphic.data_json = json.dumps(new_data)
           graphic.version = "2.0"
       db.commit()
   ```

### 2.3 Frontend Migration

#### 2.3.1 Component Updates
1. **GraphicsTable Component**
   - Update edit action to use router navigation
   - Implement loading states for navigation
   - Add error handling for navigation failures
   - Maintain existing table functionality

2. **CreateGraphicDialog Component**
   - Update creation flow to redirect to editor route
   - Implement success handling with navigation
   - Add loading states for creation and navigation
   - Maintain form validation and error handling

#### 2.3.2 State Management Updates
1. **Remove Modal State**
   - Remove `isEditorOpen` state variables
   - Clean up modal-related useEffect hooks
   - Remove modal event listeners
   - Update context providers if needed

2. **Add Route State Management**
   - Implement route-based loading states
   - Add error boundary for route failures
   - Handle authentication redirects
   - Manage lock state across route navigation

## Phase 3: Testing and Validation

### 3.1 Functional Testing

#### 3.1.1 Editor Route Testing
1. **Basic Functionality**
   - [ ] Navigate to `/canvas/edit/{id}` successfully
   - [ ] Load graphic data correctly
   - [ ] Display editor interface properly
   - [ ] Save functionality works
   - [ ] Navigate back to dashboard

2. **Lock Management Testing**
   - [ ] Acquire lock on editor load
   - [ ] Display lock status correctly
   - [ ] Handle lock conflicts appropriately
   - [ ] Release lock on navigation away
   - [ ] Refresh lock with user activity

3. **Error Handling Testing**
   - [ ] Handle invalid graphic IDs
   - [ ] Display authentication errors
   - [ ] Show network error states
   - [ ] Handle lock timeout gracefully

#### 3.1.2 Viewer Route Testing
1. **OBS Integration Testing**
   - [ ] Load `/canvas/view/{id}` without authentication
   - [ ] Display graphic content correctly
   - [ ] Handle missing graphics gracefully
   - [ ] Support archived graphics appropriately
   - [ ] Performance testing for live streaming

2. **Browser Compatibility Testing**
   - [ ] Chrome browser source functionality
   - [ ] Firefox browser source functionality
   - [ ] OBS Studio integration
   - [ ] XSplit integration (if applicable)

#### 3.1.3 Navigation Testing
1. **User Flow Testing**
   - [ ] Graphics table → Edit → Editor route
   - [ ] Create graphic → Editor route
   - [ ] Editor route → Save → Back to table
   - [ ] Editor route → View route (OBS)
   - [ ] Error states → Recovery navigation

2. **Browser Navigation Testing**
   - [ ] Back button functionality
   - [ ] Browser refresh behavior
   - [ ] Tab management with multiple editors
   - [ ] Direct URL access

### 3.2 Data Integrity Testing

#### 3.2.1 Graphic Data Testing
1. **Data Format Validation**
   - [ ] Legacy data loads correctly in new editor
   - [ ] New data saves in correct format
   - [ ] Data consistency across save/load cycles
   - [ ] Backward compatibility with legacy data

2. **Data Migration Testing**
   - [ ] All existing graphics migrate successfully
   - [ ] No data loss during migration
   - [ ] Performance testing with large graphics
   - [ ] Rollback procedures work correctly

#### 3.2.2 Database Testing
1. **Schema Validation**
   - [ ] Database schema updates apply correctly
   - [ ] Indexes work properly with new queries
   - [ ] Foreign key relationships maintained
   - [ ] Database performance remains acceptable

2. **Transaction Testing**
   - [ ] Graphic creation transactions work
   - [ ] Update operations maintain consistency
   - [ ] Lock transactions work correctly
   - [ ] Archive operations complete successfully

### 3.3 Performance Testing

#### 3.3.1 Load Testing
1. **Concurrent Users**
   - [ ] Multiple users editing different graphics
   - [ ] Lock management under load
   - [ ] Database performance under concurrent access
   - [ ] Frontend performance with multiple tabs

2. **Large Graphics Testing**
   - [ ] Performance with complex graphics
   - [ ] Memory usage with large canvases
   - [ ] Network performance for large data transfers
   - [ ] OBS viewer performance with complex graphics

## Phase 4: User Transition

### 4.1 User Communication

#### 4.1.1 Pre-Migration Communication
1. **Advance Notice (2 weeks before)**
   - Email announcement of upcoming changes
   - Documentation updates with new workflow guides
   - Training schedule announcement
   - FAQ document preparation

2. **Migration Week Communication**
   - Daily status updates
   - Migration timeline communication
   - Support contact information
   - Temporary work procedure documentation

#### 4.1.2 Training Preparation
1. **User Training Materials**
   - Video tutorials for new interface
   - Step-by-step workflow guides
   - Quick reference cards
   - Troubleshooting guides

2. **Training Sessions**
   - Live demonstration sessions
   - Hands-on practice in test environment
   - Q&A sessions for user concerns
   - Office hours for individual support

### 4.2 Go-Live Procedures

#### 4.2.1 Migration Day Checklist
1. **Pre-Migration (2 hours before)**
   - [ ] Final database backup completed
   - [ ] All users notified of upcoming maintenance
   - [ ] Test environment validation completed
   - [ ] Rollback procedures verified

2. **Migration Execution**
   - [ ] Deploy route-based editor code
   - [ ] Run database migration scripts
   - [ ] Update API endpoints
   - [ ] Clear application caches

3. **Post-Migration Validation**
   - [ ] Verify all graphics load correctly
   - [ ] Test editor functionality
   - [ ] Validate OBS viewer access
   - [ ] Check user authentication flows

#### 4.2.2 User Support
1. **Immediate Support (First 24 hours)**
   - Extended support hours
   - Real-time chat support
   - Priority ticket handling
   - Direct phone support for critical issues

2. **Ongoing Support (First Week)**
   - Daily check-ins with active users
   - Additional training sessions as needed
   - Documentation updates based on feedback
   - Performance monitoring and optimization

## Phase 5: Post-Migration

### 5.1 Legacy System Cleanup

#### 5.1.1 Code Cleanup
1. **Remove Legacy Components**
   ```bash
   # Archive legacy components
   mkdir -p archive/legacy-components
   mv dashboard/components/canvas/CanvasEditor.tsx archive/legacy-components/
   ```

2. **Clean Up Dependencies**
   - Remove unused modal component imports
   - Clean up related CSS files
   - Remove unused state management code
   - Update component documentation

#### 5.1.2 Database Cleanup
1. **Remove Legacy Data**
   ```sql
   -- Clean up any temporary migration tables
   DROP TABLE IF EXISTS graphics_migration_temp;
   
   -- Remove deprecated columns if any
   ALTER TABLE graphics DROP COLUMN IF EXISTS legacy_data;
   ```

2. **Optimize Database**
   - Rebuild indexes for new query patterns
   - Update statistics for query optimizer
   - Clean up orphaned lock records
   - Optimize table structures

### 5.2 Monitoring and Maintenance

#### 5.2.1 Performance Monitoring
1. **Key Metrics**
   - Page load times for editor routes
   - API response times for graphics operations
   - Database query performance
   - User session durations and error rates

2. **Alerting Setup**
   - Performance threshold alerts
   - Error rate monitoring
   - Database performance alerts
   - User experience metrics

#### 5.2.2 User Feedback Collection
1. **Feedback Mechanisms**
   - In-app feedback forms
   - Regular user surveys
   - Support ticket analysis
   - Usage analytics review

2. **Continuous Improvement**
   - Weekly performance reviews
   - Monthly user feedback analysis
   - Quarterly system optimization
   - Annual architecture review

## Rollback Procedures

### 1. Immediate Rollback (Within 1 hour)
1. **Stop New Services**
   - Disable route-based editor endpoints
   - Stop application server
   - Preserve current database state

2. **Restore Previous Version**
   - Revert code deployment
   - Restore database from pre-migration backup
   - Restart application services
   - Verify modal-based editor works

3. **User Communication**
   - Notify users of rollback
   - Provide timeline for re-migration
   - Document rollback causes
   - Schedule follow-up planning

### 2. Data Rollback (Within 24 hours)
1. **Database Restoration**
   ```sql
   -- Restore from backup
   DROP TABLE graphics;
   CREATE TABLE graphics AS SELECT * FROM graphics_backup_pre_migration;
   
   -- Restore constraints and indexes
   ALTER TABLE graphics ADD PRIMARY KEY (id);
   CREATE INDEX idx_graphics_title ON graphics(title);
   -- ... other indexes
   ```

2. **Configuration Restoration**
   - Restore configuration files
   - Update environment variables
   - Restart services with old configuration
   - Validate system functionality

## Troubleshooting Guide

### 1. Common Migration Issues

#### 1.1 Route Navigation Fails
- **Symptoms**: Edit buttons don't navigate to editor
- **Causes**: Router configuration issues, authentication problems
- **Solutions**: 
  - Check Next.js routing configuration
  - Verify authentication middleware
  - Validate component import paths
  - Check browser console for JavaScript errors

#### 1.2 Graphic Data Doesn't Load
- **Symptoms**: Editor loads but shows empty canvas
- **Causes**: Data format incompatibility, API endpoint issues
- **Solutions**:
  - Check API response format
  - Validate data migration scripts
  - Verify database schema
  - Check network requests in browser dev tools

#### 1.3 OBS Browser Source Not Working
- **Symptoms**: OBS shows error or blank screen
- **Causes**: URL format issues, network accessibility, authentication
- **Solutions**:
  - Verify URL format and graphic ID
  - Check network accessibility from OBS machine
  - Ensure graphic is not archived
  - Test URL in regular browser first

### 2. Performance Issues

#### 2.1 Slow Editor Loading
- **Symptoms**: Editor route takes long time to load
- **Causes**: Large graphic data, database performance, network issues
- **Solutions**:
  - Optimize graphic data loading
  - Check database query performance
  - Implement data compression
  - Add loading states and progress indicators

#### 2.2 Lock Management Issues
- **Symptoms**: Locks not acquiring or releasing properly
- **Causes**: Database transaction issues, timing problems
- **Solutions**:
  - Check database transaction isolation levels
  - Verify lock cleanup procedures
  - Monitor lock table performance
  - Implement retry mechanisms for lock conflicts

## Success Criteria

### 1. Technical Success Criteria
- [ ] All existing graphics accessible in new editor
- [ ] No data loss during migration
- [ ] All users can successfully edit graphics
- [ ] OBS browser sources work correctly
- [ ] System performance meets or exceeds previous benchmarks

### 2. User Success Criteria
- [ ] Users complete training with 90% satisfaction
- [ ] Support tickets related to editor reduced by 50%
- [ ] User adoption rate of new interface exceeds 95%
- [ ] Average time to complete graphic editing tasks maintained or improved
- [ ] User feedback indicates improved workflow efficiency

### 3. Business Success Criteria
- [ ] No disruption to live broadcast operations
- [ ] System reliability maintained (99.9% uptime)
- [ ] Support costs reduced through improved interface
- [ ] Future feature development accelerated by new architecture
- [ ] User satisfaction scores improve

---

**Last Updated**: 2025-10-12  
**Version**: 1.0  
**Status**: Draft - Ready for Review  
**Dependencies**: Canvas Editor Architecture v2.1, Route-Based Canvas Operations SOP  
**Related SOPs**: Canvas Editor Workflow, Dashboard Operations, Emergency Rollback
