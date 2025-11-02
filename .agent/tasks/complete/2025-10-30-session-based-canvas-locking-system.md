# Session-Based Canvas Locking System

## Problem
Currently, when a user opens a canvas for editing, a lock is acquired but it's not session-specific. If the same user opens a new tab and navigates to the same canvas, the existing lock allows them in because `acquire_lock()` returns the existing lock rather than rejecting the request. This defeats the purpose of locking since multiple tabs can edit simultaneously, causing potential data conflicts.

## Root Cause Analysis
1. **No Session Identification**: The `CanvasLock` model doesn't track which browser session/tab owns the lock
2. **Idempotent Lock Acquisition**: The `acquire_lock()` method returns existing locks instead of rejecting duplicate requests
3. **No Session Validation**: Lock refresh and status checks don't validate session ownership
4. **Frontend Doesn't Track Sessions**: The frontend has no concept of session identity

## Solution: Session-Based Lock System

### Backend Changes

#### 1. Add Session ID to CanvasLock Model (`api/models.py`)
```python
class CanvasLock(Base):
    # ... existing fields ...
    session_id = Column(String(255), nullable=False, index=True)  # NEW
```

#### 2. Update CanvasLock Schema (`api/schemas/graphics.py`)
```python
class CanvasLockResponse(CanvasLockBase):
    # ... existing fields ...
    session_id: str  # NEW

class CanvasLockCreate(CanvasLockBase):
    session_id: str  # NEW - required for lock acquisition
```

#### 3. Modify Graphics Service (`api/services/graphics_service.py`)
- Update `acquire_lock()`: Check if existing lock belongs to different session → raise `ConflictError`
- Update `release_lock()`: Validate session_id matches before releasing
- Update `refresh_lock()`: Validate session_id matches before refreshing
- Update `get_lock_status()`: Return session ownership information
- Update `_serialize_lock()`: Include session_id

#### 4. Update API Endpoints (`api/routers/graphics.py`)
- Modify lock endpoints to accept `session_id` in request body
- Pass session_id through to service layer

### Frontend Changes

#### 5. Generate Session ID on Mount (`dashboard/app/canvas/edit/[id]/page.tsx`)
```typescript
// Generate unique session ID for this editor instance
const sessionId = useRef(crypto.randomUUID());
```

#### 6. Update Lock API Calls (`dashboard/lib/api.ts`)
- Add `session_id` parameter to `acquire()`, `release()`, `refresh()` methods
- Pass session_id in all lock-related API calls

#### 7. Update CanvasEditor (`dashboard/components/canvas/CanvasEditor.tsx`)
- Accept `sessionId` prop
- Pass session_id to all lock operations
- Show specific error when lock is owned by another session

#### 8. Update Hook Layer (`dashboard/hooks/use-dashboard-data.tsx`)
- Add `session_id` parameter to lock functions
- Update type definitions

#### 9. Handle Lock Conflict UI
- Show blocking dialog when another session has the lock
- Provide "Check Status" button to see if lock has been released
- Add "Force Unlock" option (with warning) for emergencies

### Database Migration

#### 10. Create Alembic Migration
```bash
alembic revision -m "add_session_id_to_canvas_locks"
```

Migration will:
- Add `session_id` column to `canvas_locks` table
- Set default session_id for existing locks (or clear them)
- Make column NOT NULL after backfill

## Implementation Flow

1. **Backend First**: Update models, schemas, service, and API routes
2. **Database Migration**: Apply schema changes
3. **Frontend Updates**: Add session tracking and update API calls
4. **UI Enhancements**: Add lock conflict dialogs and messaging
5. **Testing**: Verify multi-tab locking works correctly

## Expected Behavior After Implementation

- ✅ User opens canvas in Tab A → Lock acquired with sessionId_A
- ✅ User opens same canvas in Tab B → Rejected with "Already being edited" error
- ✅ User closes Tab A → Lock released automatically (via cleanup or explicit release)
- ✅ User can now open in Tab B → Lock acquired with sessionId_B
- ✅ Lock refresh only works for the session that owns the lock
- ✅ Expired locks are cleaned up regardless of session

## Files to Modify

**Backend (7 files)**:
1. `api/models.py` - Add session_id to CanvasLock
2. `api/schemas/graphics.py` - Update lock schemas
3. `api/services/graphics_service.py` - Session validation logic
4. `api/routers/graphics.py` - Pass session_id through
5. `api/alembic/versions/XXX_add_session_id.py` - New migration
6. `api/types/index.ts` - Update CanvasLock type (if exists)

**Frontend (5 files)**:
1. `dashboard/types/index.ts` - Update CanvasLock type
2. `dashboard/lib/api.ts` - Add session_id to lock API calls
3. `dashboard/app/canvas/edit/[id]/page.tsx` - Generate sessionId
4. `dashboard/components/canvas/CanvasEditor.tsx` - Use sessionId
5. `dashboard/hooks/use-dashboard-data.tsx` - Pass sessionId through

**New Files (1-2)**:
1. `dashboard/components/canvas/LockConflictDialog.tsx` - UI for lock conflicts
2. Migration file in `api/alembic/versions/`

## Testing Strategy

1. Open canvas in Tab A → verify lock acquired
2. Open same canvas in Tab B → verify rejection with clear error
3. Close Tab A → verify Tab B can now acquire lock
4. Leave tab open for 30+ minutes → verify lock expires and can be reacquired
5. Hard refresh Tab A → verify new session ID generated and old lock prevents access