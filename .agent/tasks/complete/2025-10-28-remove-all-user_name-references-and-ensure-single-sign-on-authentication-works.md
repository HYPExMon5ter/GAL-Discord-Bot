# Complete user_name Removal & Auth Verification Spec

## Current Situation Analysis
The system is using **single password sign-on** (no user management). The `username` variable appears in many places but serves **NO functional purpose** since:
1. There's only ONE password for everyone
2. The auth system uses tokens, not usernames
3. All username comparisons are meaningless

## ✅ Already Fixed (from previous work)
- ✅ Removed `user_name` from GraphicCard.tsx
- ✅ Removed `user_name` from LockBanner.tsx  
- ✅ Removed `user_name` from hooks/use-locks.tsx

## ❌ Remaining Issues to Fix

### 1. **Auth System (use-auth.tsx & lib/api.ts)**
**Current:** Sets username to `'Dashboard User'` - meaningless hardcoded value
**Fix:** Remove username entirely from auth context since it serves no purpose

**Changes needed:**
- Remove `username` from AuthContextType interface
- Remove `setUsername` state management
- Remove all `setUsername('Dashboard User')` calls
- Keep all auth token management intact (this is what actually matters)

### 2. **Components Still Using username**
These components import and use username but **don't actually need it**:

**GraphicsTab.tsx** - Line 27: `const { username } = useAuth();`
- Used only for checking `graphic.created_by === username`
- **Fix:** Since single sign-on, all graphics are "owned" by the same user - this check is meaningless

**CreateGraphicDialog.tsx** - Line 21: `const { username } = useAuth();`
- Not actually used in the component
- **Fix:** Remove the destructure

**CopyGraphicDialog.tsx** - Line 22: `const { username } = useAuth();`
- Not actually used in the component  
- **Fix:** Remove the destructure

**ArchivedGraphicCard.tsx** - Line 25: `const { username } = useAuth();`
- Used for: `canDelete = graphic.created_by === username`
- **Fix:** Since single sign-on, user can delete any graphic they have access to

### 3. **Stale localStorage Reference (lib/api.ts)**
Line 41: `localStorage.removeItem('username');`
- Leftover cleanup code that does nothing
- **Fix:** Remove this line entirely

### 4. **Documentation/Test Files**
- `tests/e2e/smoke.spec.ts` - Contains test data with `user_name`
- `README.md` / `README-COMPONENTS.md` - Documentation references
- These are **non-critical** but should be cleaned up for consistency

## ✅ What MUST Remain Working

### Authentication Flow (Token-Based)
```typescript
// Login flow
authApi.login(password) → returns { access_token, expires_in }
localStorage.setItem('auth_token', token)
api.interceptors add: Authorization: `Bearer ${token}`
```

### Authorization Check
- `isAuthenticated` boolean - **KEEP THIS**
- Token expiration checking - **KEEP THIS**
- Auto-logout on 401 - **KEEP THIS**

### Public View Endpoint
**CanvasView.tsx** already handles this correctly:
```typescript
// Try public endpoint first (no auth)
api.get(`/graphics/${graphicId}/view`)
// Fall back to authenticated endpoint
api.get(`/graphics/${graphicId}`)
```
**This MUST continue working** ✅

## Implementation Steps

### Step 1: Update Auth Context
```typescript
// use-auth.tsx
interface AuthContextType {
  isAuthenticated: boolean;
  // username: string | null; // REMOVE
  login: (password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}
```

### Step 2: Clean Up Components
Remove all `const { username } = useAuth();` that aren't actually needed

### Step 3: Simplify Ownership Checks
For components checking `created_by === username`:
- Either remove the check entirely (single user)
- Or check `created_by` is not null/undefined (basic sanity check)

### Step 4: Remove Stale Code
- Remove `localStorage.removeItem('username')` from api.ts
- Clean up test/doc references (optional, non-breaking)

## Testing Verification

After changes, verify:
1. ✅ Login with master password still works
2. ✅ Token is stored and used in requests  
3. ✅ Protected routes require authentication
4. ✅ Public view endpoint works WITHOUT auth
5. ✅ Logout clears token and redirects
6. ✅ Build completes without TypeScript errors

## Files to Modify
1. `hooks/use-auth.tsx` - Remove username from context
2. `lib/api.ts` - Remove stale localStorage line
3. `components/graphics/GraphicsTab.tsx` - Remove username usage
4. `components/graphics/CreateGraphicDialog.tsx` - Remove username destructure
5. `components/graphics/CopyGraphicDialog.tsx` - Remove username destructure  
6. `components/archive/ArchivedGraphicCard.tsx` - Remove username comparison

## Non-Breaking Changes
All changes preserve the actual authentication mechanism (token-based). Only removing the meaningless username tracking.