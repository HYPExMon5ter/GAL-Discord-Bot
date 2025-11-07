## Deprecated Code Cleanup Plan

### 1. **Remove `build_unified_embed()` Function** ⚠️ HIGH PRIORITY
**Location**: `core/components_traditional.py` lines 628-750+
- **Status**: Marked as DEPRECATED with comment "Use build_unified_view() for new Components V2 implementation"
- **Impact**: Function is defined but **not called anywhere** in the codebase
- **Action**: Delete entire function (~120+ lines)

### 2. **Remove Legacy Adapter System** 🔴 MAJOR CLEANUP
The entire legacy adapter system is **no longer needed** based on the previous task completion:

**Files to Remove**:
- `core/data_access/legacy_adapter.py` (419 lines) - Complete file removal
- Legacy adapter references in:
  - `core/persistence.py` lines 420-421
  - `config.py` lines 560-561
  - `integrations/sheets.py` lines 314-357 (already partially disabled)

**Reasoning**: The task notes indicate "Legacy adapter integration fully disabled for cache consistency"

### 3. **Remove Legacy Cache Manager** 
**Location**: `integrations/sheets.py` lines 52-65
- `_LegacySheetCacheManager` class - only used when feature flag disabled
- **Action**: Remove class and simplify to only use `SheetCacheManager`

### 4. **Remove Legacy Functions in sheets.py**
**Location**: `integrations/sheets.py`
- `_legacy_fetch_required_columns()` lines 88-105
- `_legacy_update_cells()` lines 108-124
- Both marked as "emulate legacy flow" and dispatch logic (lines 127-145)

### 5. **Cleanup Legacy Config References**
**Multiple files** contain legacy compatibility code:
- `core/data_access/configuration_repository.py` - Legacy config loading
- `core/data_access/persistence_repository.py` - Legacy persistence references
- `core/data_access/sheets_repository.py` - Legacy cache references

### 6. **Remove commands/legacy.py** ❓ CLARIFICATION NEEDED
**Location**: `core/commands/legacy.py` (76 lines)
- **Current Purpose**: Defines the `gal` command group and error handling
- **Name**: "legacy" but **actively used** by command system
- **Recommendation**: Either rename to `core/commands/base.py` or keep as-is (NOT legacy)

### 7. **Additional Cleanups**
- Remove oauth2client comment "Legacy, no updates" from `requirements.txt`
- Clean up legacy file fallback code in `helpers/waitlist_helpers.py`
- Remove legacy support code from `core/persistence.py` (multiple functions)

## Before Starting
✅ **Git commit existing changes** (as requested):
- Modified: config.py, config.yaml, core/components_traditional.py, core/onboard.py, core/test_components.py, integrations/sheets.py, storage/fallback.db
- Untracked: 3 task completion markdown files

## Execution Order
1. Commit existing changes
2. Remove `build_unified_embed()` (safe - not called)
3. Remove legacy adapter system (complex - cascading changes)
4. Remove legacy cache manager and functions
5. Cleanup legacy references in repositories
6. Run tests to ensure nothing breaks
7. Final commit with cleanup changes

## Risk Assessment
- **Low Risk**: build_unified_embed (unused)
- **Medium Risk**: Legacy adapter (multiple references to update)
- **High Risk**: Legacy cache/sheet functions (verify feature flags first)

Ready to proceed?