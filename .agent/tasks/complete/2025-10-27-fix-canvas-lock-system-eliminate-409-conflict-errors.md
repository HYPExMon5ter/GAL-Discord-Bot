# Lock System Fix Plan

## Issues Identified

1. **React Strict Mode Double-Mounting**: Development mode causes duplicate lock acquisition attempts
2. **Race Conditions**: Hot reloads and simultaneous mount attempts cause conflicts
3. **Missing Idempotency**: Backend rejects legitimate reacquisition attempts
4. **Poor Error Recovery**: No graceful handling of transient failures
5. **Effect Dependency Issues**: Lock cleanup runs with wrong dependencies

## Proposed Fixes

### Backend Changes (api/services/graphics_service.py)

1. **Make lock acquisition idempotent**:
   - Check if an active lock already exists for the graphic
   - If exists and still valid (not expired), return the existing lock instead of throwing ConflictError
   - Only throw ConflictError if truly locked by another session (when we add session tracking)
   - Remove duplicate `cleanup_expired_locks` method

2. **Improve lock release to be truly idempotent**:
   - Already handles missing locks gracefully, but add explicit logging

3. **Add automatic cleanup call before acquisition**:
   - Already present, ensure it's consistently called

### Frontend Changes

1. **CanvasEditor.tsx**:
   - Add lock acquisition guard using a ref to prevent double-acquisition
   - Improve error handling to distinguish between real conflicts vs. transient errors
   - Fix cleanup effect dependencies (use lock?.id instead of full lock object)
   - Add retry logic for transient failures

2. **use-dashboard-data.tsx**:
   - Make acquireLock idempotent on frontend side
   - Check if lock already exists in state before making API call
   - Better error handling and state cleanup on failures

3. **Error Handling Strategy**:
   - 409 with "already editing" → Check if it's our own lock and continue
   - 409 with actual conflict → Show user-friendly message
   - Network errors → Retry with exponential backoff
   - Lock expiration → Clear state and allow reacquisition

## Implementation Order

1. Fix backend idempotency (api/services/graphics_service.py)
2. Add frontend acquisition guard (CanvasEditor.tsx)
3. Fix effect dependencies (CanvasEditor.tsx)
4. Improve error handling (CanvasEditor.tsx, use-dashboard-data.tsx)
5. Test with hot reload and Strict Mode enabled

## Expected Outcome

- Zero 409 errors during normal development workflow
- Graceful handling of hot reloads without lock conflicts
- Proper cleanup on component unmount
- Clear user feedback for genuine lock conflicts
- Idempotent operations that can be safely retried