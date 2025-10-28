# Plan: Remove Username from Lock System - Fresh Start

## Problem
The database has a `user_name` column in `canvas_locks` table that's NOT NULL, but the model definition doesn't include it. This causes a 500 error when trying to acquire locks.

## Root Cause
Schema mismatch between:
- **Database Schema**: Has `user_name VARCHAR(255) NOT NULL`
- **Model Definition**: No `user_name` field (intentionally removed for single shared login)

## Solution: Fresh Start with Correct Schema

Since there's no need to preserve existing data, we'll:
1. Delete the existing dashboard database
2. Let SQLAlchemy recreate it with the correct schema (matching the models)
3. Update the `acquire_lock` method to work without user_name

## Implementation Steps

### 1. Delete Existing Database
**File to delete:** `dashboard/dashboard.db`
- This will force a fresh schema creation on next API startup

### 2. Verify Model Definition (No Changes Needed)
**File:** `api/models.py` - CanvasLock model is already correct:
```python
class CanvasLock(Base):
    """Model for canvas editing locks - simplified for single shared login"""
    __tablename__ = "canvas_locks"
    
    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, unique=True, index=True)
    locked = Column(Boolean, default=True, nullable=False)
    locked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    # No user_name field - single shared login
```

### 3. Verify Service Methods (Already Correct)
**File:** `api/services/graphics_service.py` - `acquire_lock` method already doesn't use user_name:
```python
def acquire_lock(self, lock_request: CanvasLockCreate) -> Dict[str, Any]:
    lock = CanvasLock(
        graphic_id=lock_request.graphic_id,
        locked=True,
        locked_at=self._utcnow(),
        expires_at=self._utcnow() + timedelta(minutes=30),
    )
    # No user_name parameter
```

### 4. Test After Fresh Start
- Start API server
- SQLAlchemy will auto-create tables from models
- Test lock acquisition endpoint
- Verify it works without user_name

## Expected Outcome
- ✅ Fresh database with correct schema (no user_name in canvas_locks)
- ✅ Lock acquisition works properly
- ✅ Single shared login system fully functional
- ✅ No user tracking - all users share the same authentication

## Files Changed
- **Deleted:** `dashboard/dashboard.db`
- **No code changes needed** - models and services are already correct

## Risk Mitigation
- No data loss concerns (user explicitly confirmed wipe is acceptable)
- Database will be auto-recreated on next API startup
- All table schemas will match model definitions