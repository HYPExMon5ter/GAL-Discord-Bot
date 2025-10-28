# Plan: Consolidate Dashboard Database Location with Cleanup

## Goal
All future dashboard database operations will use `dashboard/dashboard.db` only. Clean up duplicate database files after configuration changes.

## Implementation Steps

### Phase 1: Update Configuration (Ensures Future Writes Go to Dashboard Directory)

**1. Update API Database Configuration**
- **File:** `api/dependencies.py` (Line 33)
- **Change:** `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard.db")` 
- **To:** `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard/dashboard.db")`

**2. Set Explicit Environment Variable**
- **File:** `.env`
- **Add:** `DATABASE_URL=sqlite:///./dashboard/dashboard.db` (after existing database configuration comment)

**3. Update .gitignore**
- **File:** `.gitignore`
- **Add these lines to Data storage section:**
  ```
  dashboard.db
  api/dashboard.db
  dashboard/dashboard.db
  ```

### Phase 2: Cleanup Duplicate Files

**Remove duplicate database files:**
1. Delete `dashboard.db` from main directory (if exists)
2. Delete `api/dashboard.db` from api directory (if exists)
3. Delete `api/migrations/` directory (appears to be untracked migration artifacts)

**Keep:**
- `dashboard/dashboard.db` - This is the canonical location going forward

### Phase 3: Verification

**Test that configuration works:**
1. Start API server - verify it connects to `dashboard/dashboard.db`
2. Check logs for database connection path
3. Verify no errors about missing database files

## Database Strategy

**PostgreSQL (Primary):**
- Set `DATABASE_URL` env var to PostgreSQL connection in production
- SQLite ignored when PostgreSQL configured

**SQLite (Fallback):**
- Location: `dashboard/dashboard.db` only
- Used when `DATABASE_URL` not set or not PostgreSQL
- Single consolidated location

## Files Modified
1. `api/dependencies.py` - 1 line
2. `.env` - 1 line addition
3. `.gitignore` - 3 lines addition

## Files Deleted
1. `dashboard.db` (main directory root)
2. `api/dashboard.db` (if exists)
3. `api/migrations/` (untracked migration directory)

## Impact
- ✅ Clean project structure - database in logical location
- ✅ No future confusion about which database file is active
- ✅ PostgreSQL users unaffected
- ✅ Fresh start with correct location (no data migration needed per user request)