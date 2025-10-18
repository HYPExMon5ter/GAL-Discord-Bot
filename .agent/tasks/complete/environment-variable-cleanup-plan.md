# Environment Variable Cleanup Plan

**Created:** 2025-06-18  
**Status:** Active  
**Priority:** High  

## Current Issues Identified

### 1. Inconsistent API URL Configuration
- `dashboard/.env.local.example` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `dashboard/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` 
- `dashboard/lib/api.ts` has hardcoded fallback to `http://localhost:8000/api/v1`
- `dashboard/next.config.js` has hardcoded `http://localhost:8000/api/:path*`

### 2. Duplicate/Conflicting Variables
- `.env` and `.env.local` both contain Discord/development variables
- No clear separation between backend and frontend env vars
- Mixed environment variable loading order

### 3. Missing Variables
- Some Python files expect variables that aren't defined in any .env file
- Frontend missing proper production environment configuration
- Inconsistent variable naming patterns

### 4. Hardcoded Values in Code
- Multiple hardcoded localhost URLs throughout codebase
- Direct references to environment variables without proper fallbacks
- Inconsistent error handling for missing variables

## Cleanup Strategy

### Phase 1: Environment File Reorganization

#### 1.1 Backend Environment Files
- **`.env`**: Core backend variables (Discord, API keys, database)
  ```
  DISCORD_TOKEN=...
  APPLICATION_ID=...
  RIOT_API_KEY=...
  TRACKER_API_KEY=...
  DATABASE_URL=...
  DASHBOARD_MASTER_PASSWORD=...
  ```

- **`.env.local`**: Local development overrides and sensitive data
  ```
  DEV_GUILD_ID=...
  GOOGLE_CREDS_JSON=... (if needed for local dev)
  ```

#### 1.2 Frontend Environment Files
- **`dashboard/.env.local`**: Frontend-specific variables
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  NEXT_PUBLIC_APP_TITLE="GAL Live Graphics Dashboard"
  NODE_ENV=development
  ```

- **`dashboard/.env.local.example`**: Updated frontend example template
  ```
  # FastAPI Backend URL
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

  # Optional: Custom app title
  NEXT_PUBLIC_APP_TITLE="GAL Live Graphics Dashboard"

  # Optional: Environment (development, production)
  NODE_ENV=development
  ```

### Phase 2: Code Updates

#### 2.1 API Configuration Standardization
- Update `dashboard/lib/api.ts` to use consistent environment variable pattern
- Remove hardcoded URLs and use environment variables with proper fallbacks
- Ensure production/development environment detection works correctly

#### 2.2 Next.js Configuration
- Update `dashboard/next.config.js` to use environment variables instead of hardcoded URLs
- Add proper environment variable validation
- Support both development and production configurations

#### 2.3 Backend Configuration
- Review and update `config.py` for consistent environment variable usage
- Add proper validation and error messages for missing required variables
- Ensure environment-specific logic (dev/prod) works correctly

### Phase 3: Variable Deduplication and Standardization

#### 3.1 Remove Duplicates
- Consolidate duplicate variables across .env files
- Establish clear priority order for environment variable loading
- Remove unused or obsolete variables

#### 3.2 Standardize Naming
- Ensure consistent naming conventions (UPPER_CASE for backend, NEXT_PUBLIC_* for frontend)
- Add descriptive comments for each variable
- Group related variables together

#### 3.3 Add Missing Variables
- Identify and add missing variables required by the codebase
- Provide sensible defaults where appropriate
- Add validation for required variables

### Phase 4: Documentation and Validation

#### 4.1 Documentation
- Add comprehensive comments to all .env files
- Create environment setup documentation if needed
- Document variable purposes and expected values

#### 4.2 Validation
- Add environment variable validation at startup
- Provide clear error messages for missing required variables
- Add environment-specific health checks

## Implementation Steps

1. **Commit Current State** - Create a commit before making any changes
2. **Backup Current .env Files** - Keep copies of current configuration
3. **Reorganize Environment Files** - Implement the new file structure
4. **Update Code References** - Modify all files that reference environment variables
5. **Test Configuration** - Verify all services start correctly with new configuration
6. **Update Documentation** - Ensure all documentation reflects new structure

## Expected Outcomes

- ✅ Clean separation of backend and frontend environment variables
- ✅ No duplicate or conflicting variables
- ✅ Consistent usage of environment variables throughout codebase
- ✅ Proper error handling for missing required variables
- ✅ Clear documentation and examples for setup
- ✅ Support for both development and production environments
- ✅ No hardcoded URLs or configuration values in code

## Risk Mitigation

- **Backup Strategy**: Keep copies of all current .env files before making changes
- **Gradual Implementation**: Implement changes in phases to reduce risk
- **Testing**: Thoroughly test each phase before proceeding to the next
- **Rollback Plan**: Document steps to revert changes if needed

## Dependencies

- None - This is a self-contained cleanup task

## Notes

This cleanup will improve maintainability, reduce configuration errors, and make it easier to set up new development environments. The separation of concerns between backend and frontend variables will also make the codebase more secure and easier to understand.
