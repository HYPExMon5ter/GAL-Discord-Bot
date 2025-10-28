# Spec: Simplify Lock System to Single-User, Graphic-Based Locking

## Current State Analysis

The current locking system is designed for multi-user scenarios where:
- Locks are tied to both `graphic_id` AND `user_name`
- Lock conflicts are checked by comparing usernames
- Frontend checks if lock is owned by current user vs. another user
- All users authenticate with individual credentials

## Problem

Since all staff will use the same shared login (master password), the current system creates issues:
- All locks will have the same `user_name` (e.g., "dashboard_user")
- Multiple browser tabs/windows with same credentials can acquire locks simultaneously
- The "locked by another user" check is meaningless when everyone is the same user
- Lock conflicts won't be detected properly

## Proposed Solution

Simplify to a **graphic-based exclusive lock system** where:
1. Only ONE lock per graphic (regardless of who/where)
2. Lock is tied ONLY to `graphic_id` (no user tracking)
3. First to acquire the lock gets it, others blocked until released
4. Lock auto-expires after timeout
5. Lock released on save OR on exit (cleanup)

## Changes Required

### 1. Database Model (`api/models.py`)
**Remove:** `user_name` column (no longer needed)
**Keep:** `graphic_id`, `locked`, `locked_at`, `expires_at`
**Update:** Index to just `graphic_id` and `locked` status

```python
class CanvasLock(Base):
    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, unique=True, index=True)
    locked = Column(Boolean, default=True, nullable=False)
    locked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
```

### 2. Backend Service (`api/services/graphics_service.py`)

**`acquire_lock`:**
- Remove user_name parameter and checks
- Simply check if graphic has ANY active lock
- If locked → raise ConflictError("Graphic is currently being edited")
- If not locked → create lock with just graphic_id

**`release_lock`:**
- Remove user_name parameter
- Find lock by graphic_id only
- Delete if exists (already idempotent)

**`refresh_lock`:**
- Remove user_name parameter
- Find by graphic_id only
- Extend expiration

**`get_lock_status`:**
- Remove user_name parameter
- Return simple: `{locked: bool, expires_at: datetime | null}`
- Remove `can_edit` field (always true if not locked)

**`_serialize_lock`:**
- Remove user_name from serialization

**Remove all user_name checks in:**
- `delete_graphic`
- `archive_graphic`
- `permanent_delete_graphic`

### 3. API Schemas (`api/schemas/graphics.py`)

```python
class CanvasLockBase(BaseModel):
    graphic_id: int

class CanvasLockResponse(CanvasLockBase):
    id: int
    locked: bool
    locked_at: datetime
    expires_at: datetime

class LockStatusResponse(BaseModel):
    locked: bool
    expires_at: Optional[datetime] = None
```

### 4. API Router (`api/routers/graphics.py`)

**Update endpoints:**
- `acquire_lock`: Remove user_name from CanvasLockCreate
- `release_lock`: Remove user_name from service call
- `refresh_lock`: Remove user_name from service call
- `get_lock_status`: Remove user_name from service call

### 5. Frontend Types (`dashboard/types/index.ts`)

```typescript
export interface CanvasLock {
  id: number;
  graphic_id: number;
  locked: boolean;
  locked_at: string;
  expires_at: string;
}
```

### 6. Frontend API Client (`dashboard/lib/api.ts`)

No changes needed - already uses graphic_id for all lock operations.

### 7. Frontend Hooks (`dashboard/hooks/use-locks.tsx`)

**Remove:**
- `isLockedByUser` helper (no longer relevant)
- `isLockedByOtherUser` helper (no longer relevant)

**Simplify:**
- Just check if graphic has any active lock

### 8. Frontend Components (`dashboard/components/canvas/CanvasEditor.tsx`)

**On mount (acquire lock):**
- If lock acquisition fails → show "Graphic is currently being edited in another window/tab"
- Block editing if lock not acquired

**On save:**
- Keep existing lock through save
- DON'T release lock on save (only on exit)

**On unmount/exit:**
- Release lock (already handles 404 gracefully)

**Lock refresh:**
- Continue every 2 minutes as-is

### 9. Database Migration

Create migration script to:
1. Drop `user_name` column
2. Drop `idx_graphic_user_lock` index
3. Create unique constraint on `graphic_id`
4. Update `idx_expires_active` index if needed

## Benefits

1. **Prevents concurrent edits** - Only one person can edit at a time, period
2. **Simpler logic** - No user comparisons, just locked/unlocked
3. **Works across tabs/windows** - Same user in multiple tabs properly blocked
4. **Clearer messaging** - "Currently being edited" vs "locked by John"
5. **Less code** - Remove all user_name handling and comparison logic

## Edge Cases Handled

- **Lock expires during edit**: Auto-refresh keeps lock alive
- **Browser crash**: Lock expires after 30min
- **Save then continue**: Lock maintained (not released)
- **Exit without save**: Lock released immediately
- **Multiple tabs**: Only first tab gets lock, others blocked

## Testing Plan

1. Open graphic in one tab → lock acquired
2. Try to open same graphic in second tab → blocked with message
3. Save in first tab → lock retained, editing continues
4. Close first tab → lock released
5. Now second tab can acquire lock
6. Let lock expire (wait 30min) → can acquire new lock
7. Test lock refresh during long editing session