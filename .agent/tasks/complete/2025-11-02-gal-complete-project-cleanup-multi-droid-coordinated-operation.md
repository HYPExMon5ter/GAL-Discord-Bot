# 🧹 GAL Complete Project Cleanup Plan (UPDATED)

## Summary
Comprehensive cleanup removing **~50 unused Python packages**, consolidating Node.js dependencies, removing obsolete files, and **streamlining startup scripts** (4 files → 2 files). Organized into **7 phases with individual commits** for safe rollback.

## Key Findings (UPDATED)

### Python Dependencies (88 → ~35 packages)
- **Unused AI/ML**: chromadb, langchain, openai, anthropic (~13 packages)
- **Unused Testing**: playwright Python package (browser automation - only used in dashboard via npm)
- **Unused Data**: pandas, numpy, openpyxl, reportlab (~6 packages)
- **Unused Infrastructure**: kubernetes, opentelemetry (11 packages), APScheduler

### Node.js Structure Issues
- ✅ **Root `node_modules/`**: DELETE (only needed in `/dashboard/`)
- ✅ **Root `package.json`**: DELETE (only 1 dependency, move to dashboard)
- ✅ **Root `package-lock.json`**: DELETE
- ⚠️ **Dashboard API files**: `dashboard/api/` contains 2 files (evaluate for merge/move)

### Startup Script Consolidation (4 files → 2 files)
**Current Mess:**
- ❌ `/start_api.py` (18 lines) - Standalone API starter
- ❌ `/start_api.bat` (15 lines) - Windows API starter
- ❌ `/start_dashboard.py` (82 lines) - Starts BOTH API + Frontend
- ❌ `/run_dashboard.bat` (24 lines) - Windows launcher for both

**Issues:**
1. **Redundancy**: 2 different ways to start API (standalone vs combined)
2. **Confusion**: `start_dashboard.py` actually starts BOTH services
3. **Duplication**: Both .py and .bat versions doing same thing
4. **Bot Integration**: Bot uses `services/dashboard_manager.py` (KEEP - used by bot.py)

**Proposed Structure:**
- ✅ `/scripts/launch_services.py` - Universal launcher (starts API + Frontend on Windows/Mac/Linux)
- ✅ `/scripts/launch_services.bat` - Windows-optimized version (opens separate windows)
- ✅ Keep `/services/dashboard_manager.py` - Bot integration (used by bot.py startup)
- ❌ DELETE all 4 current startup files

### Configuration Files Analysis

**pytest.ini** (root):
- ✅ KEEP - Used for API tests in `/api/tests/`
- Contains warnings filter for Python 3.13 deprecation

**pyproject.toml** (root):
- ✅ KEEP - Contains black/ruff configuration for entire project
- Used by both bot and API code

**Makefile** (root):
- ✅ KEEP - Provides `make quality` and `make test` shortcuts

**playwright.config.ts** (dashboard):
- ✅ KEEP - Dashboard e2e testing config
- Note: No e2e tests exist yet (`dashboard/tests/` directory missing)

### Obsolete Files (UPDATED)
- **Tests**: `core/test_components.py` (deprecated Discord UI tests)
- **Scripts**: `add_session_id_to_canvas_locks.py`, `migrate_json_to_database.py` (completed migrations)
- **Temp**: `dashboard/localhost.har` (20MB), `dashboard/tsconfig.tsbuildinfo` (94KB)
- **Dashboard API**: `dashboard/api/` directory (2 files to evaluate)

---

## 🤖 Execution Plan (7 Droids, 7 Phases, 7 Commits)

### 🤖 Droid 1: Dependency Auditor
**Phase 1 - Python Dependencies Cleanup**

Actions:
- Create new minimal `requirements.txt` (~35 core packages)
- Remove: AI/ML libs, pandas/numpy, playwright, kubernetes, opentelemetry, APScheduler
- Keep: discord.py, fastapi, gspread, sqlalchemy, redis, pytest, ruff, black

**Validation:**
```bash
pip install -r requirements.txt
python bot.py --help  # Should work
python -m pytest      # Should work
```

**Commit**: `chore: remove unused Python dependencies (88→35 packages)`

---

### 🤖 Droid 2: Node Structure Organizer  
**Phase 2 - Node.js Consolidation**

Actions:
- Delete `/node_modules/`
- Delete `/package.json`
- Delete `/package-lock.json`
- Add `@radix-ui/react-popover` to `dashboard/package.json` dependencies
- Run `cd dashboard && npm install`

**Validation:**
```bash
cd dashboard
npm run build  # Should succeed
npm run dev    # Should start
```

**Commit**: `chore: consolidate Node.js to dashboard directory only`

---

### 🤖 Droid 3: Startup Scripts Consolidator
**Phase 3 - Startup Scripts Reorganization**

Actions:
1. Create `/scripts/launch_services.py`:
   - Starts API (uvicorn) and Frontend (npm run dev)
   - Cross-platform (Windows/Mac/Linux)
   - Proper error handling and graceful shutdown
   - Uses subprocess for both services

2. Create `/scripts/launch_services.bat`:
   - Windows-optimized version
   - Opens API and Frontend in separate CMD windows
   - Better for development (separate logs)

3. Delete obsolete files:
   - DELETE `/start_api.py`
   - DELETE `/start_api.bat`
   - DELETE `/start_dashboard.py`
   - DELETE `/run_dashboard.bat`

4. Keep `/services/dashboard_manager.py`:
   - Used by `bot.py` for automatic dashboard startup
   - Already has proper lifecycle management
   - NO CHANGES needed to bot.py (already uses this)

**Validation:**
```bash
# Test new launcher
python scripts/launch_services.py  # Should start both
# Or on Windows:
scripts\launch_services.bat

# Test bot integration (unchanged)
python bot.py  # Should auto-start dashboard via DashboardManager
```

**Commit**: `chore: consolidate startup scripts (4 files → 2 scripts)`

---

### 🤖 Droid 4: File Structure Coordinator
**Phase 4 - Dashboard API Files Evaluation**

Actions:
1. Analyze `dashboard/api/services/errors.py`:
   - Compare with `/api/services/errors.py`
   - If identical: DELETE dashboard version
   - If different: Merge into main API errors.py

2. Analyze `dashboard/api/utils/service_runner.py`:
   - Check if used in dashboard or API
   - If used: Move to `/api/utils/service_runner.py`
   - If unused: DELETE

3. Remove empty `dashboard/api/` directory structure

**Validation:**
```bash
python -m pytest api/tests/  # All API tests pass
cd dashboard && npm run build  # Dashboard builds
```

**Commit**: `chore: consolidate dashboard API files into main API`

---

### 🤖 Droid 5: Test File Manager
**Phase 5 - Test Files Cleanup**

Actions:
- Delete `core/test_components.py` (7,157 lines of deprecated Discord LayoutView tests)
- Keep all `api/tests/test_*.py` files (active API tests)
- Note: Dashboard has playwright config but no tests yet (future feature)

**Validation:**
```bash
pytest  # Should still pass (only removed unused test file)
```

**Commit**: `chore: remove obsolete test files`

---

### 🤖 Droid 6: Script Archeologist
**Phase 6 - Migration Scripts Cleanup**

Actions:
- DELETE `scripts/add_session_id_to_canvas_locks.py` (one-time migration, completed)
- DELETE `scripts/migrate_json_to_database.py` (one-time migration, completed)
- COMPLETED: `scripts/migrate_columns.py` - DELETED (one-time migration completed)

Keep:
- ✅ `scripts/update_system_docs.py` (documentation maintenance)
- ✅ `scripts/run_quality_checks.py` (CI/CD automation)
- ✅ `scripts/generate_snapshot.py` (AI context generation)
- ✅ `scripts/check_doc_drift.py` (documentation auditing)

**Commit**: `chore: remove completed one-time migration scripts`

---

### 🤖 Droid 7: Cache Janitor
**Phase 7 - Temporary Files Cleanup**

Actions:
- DELETE `dashboard/localhost.har` (20MB network capture file)
- DELETE `dashboard/tsconfig.tsbuildinfo` (TypeScript build cache)
- UPDATE `.gitignore`:
  ```gitignore
  # Build artifacts
  *.tsbuildinfo
  *.har
  dashboard/.next/
  dashboard/node_modules/
  
  # Logs
  *.log
  gal_bot.log
  
  # Dashboard database
  dashboard/dashboard.db
  ```

**Validation:**
```bash
git status  # Should not show ignored files
```

**Commit**: `chore: remove temporary files and update .gitignore`

---

## 📊 New Startup Structure (UPDATED)

### For Development (Manual Start)

**Option 1: Python Launcher (Cross-platform)**
```bash
python scripts/launch_services.py
# Starts both API (port 8000) and Dashboard (port 3000) in one terminal
# Ctrl+C stops both gracefully
```

**Option 2: Windows Batch (Separate Windows)**
```cmd
scripts\launch_services.bat
# Opens API in one CMD window, Dashboard in another
# Close windows individually or use Ctrl+C
```

**Option 3: Individual Services**
```bash
# API only
cd /path/to/project
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Dashboard only  
cd dashboard
npm run dev
```

### For Bot Auto-Start (Unchanged)

```python
# bot.py already uses services/dashboard_manager.py
# NO CHANGES NEEDED - continues to work as-is
python bot.py  # Automatically starts dashboard services
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   bot.py                            │
│  (Discord Bot - Auto-starts Dashboard)              │
│                                                     │
│  Uses: services/dashboard_manager.py ✅             │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│         services/dashboard_manager.py               │
│  (Lifecycle Management for Bot Integration)         │
│   - Auto-start API + Frontend                       │
│   - Health monitoring                               │
│   - Graceful shutdown                               │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│    Manual Development Launch (NEW)                  │
│                                                     │
│  scripts/launch_services.py       ✅ Cross-platform │
│  scripts/launch_services.bat      ✅ Windows-only   │
│   - Start API + Frontend manually                   │
│   - Development use                                 │
└─────────────────────────────────────────────────────┘
```

---

## ✅ Validation Checklist (UPDATED)

After each phase:

**Phase 1 (Dependencies):**
- [ ] `pip install -r requirements.txt` succeeds
- [ ] Bot starts: `python bot.py`
- [ ] API starts manually: `python -m uvicorn api.main:app`
- [ ] Tests pass: `pytest`
- [ ] Linting works: `ruff check .`

**Phase 2 (Node.js):**
- [ ] Dashboard installs: `cd dashboard && npm install`
- [ ] Dashboard builds: `npm run build`
- [ ] Dashboard dev server: `npm run dev`

**Phase 3 (Startup Scripts):**
- [ ] New launcher works: `python scripts/launch_services.py`
- [ ] Windows batch works: `scripts\launch_services.bat`
- [ ] Bot auto-start unchanged: `python bot.py` (uses DashboardManager)
- [ ] Both services start successfully
- [ ] Graceful shutdown works (Ctrl+C)

**Phase 4 (Dashboard API):**
- [ ] API tests pass: `pytest api/tests/`
- [ ] Dashboard builds: `cd dashboard && npm run build`
- [ ] No import errors

**Phase 5 (Tests):**
- [ ] Remaining tests pass: `pytest`

**Phase 6 (Scripts):**
- [ ] No broken references to deleted scripts

**Phase 7 (Cleanup):**
- [ ] `.gitignore` properly excludes temp files
- [ ] No tracked build artifacts

---

## 📊 Expected Results (UPDATED)

### Before
- Python Packages: **88 installed**
- Node.js Locations: **2** (root + dashboard)
- Startup Scripts: **4 files** (confusing, redundant)
- Requirements.txt: **28 lines**
- Project Size: **~3GB** (duplicated node_modules)
- Test Files: **4** (1 obsolete)
- Scripts: **7** (3+ obsolete)
- Dashboard API: **2 files misplaced**

### After
- Python Packages: **~35-40** core dependencies
- Node.js Locations: **1** (dashboard only)
- Startup Scripts: **2 files** (clear purpose) + DashboardManager (bot integration)
- Requirements.txt: **~35 lines** (clean, organized)
- Project Size: **~1.5-2GB** (single node_modules)
- Test Files: **3** (all active)
- Scripts: **4** (all useful) + **2 launchers**
- Dashboard API: **Consolidated into main API**

---

## 🚨 Risk Assessment (UPDATED)

### Low Risk ✅
- Removing unused AI/ML/data libraries (not imported)
- Removing root node_modules (duplicate)
- Consolidating startup scripts (functionality preserved)
- Removing obsolete test files
- Removing completed migration scripts

### Medium Risk ⚠️
- Moving dashboard API files (must verify imports)
- Updating startup flow (must test bot.py integration)

### Mitigation Strategy
- ✅ Test after each phase
- ✅ Commit after each phase (easy rollback)
- ✅ Keep `services/dashboard_manager.py` unchanged (bot.py dependency)
- ✅ Validate all 3 startup methods (bot, Python script, Windows batch)

---

## 🎯 Success Criteria

1. ✅ Bot starts and auto-launches dashboard (unchanged behavior)
2. ✅ Manual dashboard launch works via new scripts
3. ✅ All tests pass
4. ✅ Code quality checks pass
5. ✅ Dashboard builds and runs
6. ✅ API responds correctly
7. ✅ ~50% reduction in dependencies
8. ✅ Clear, documented startup process
9. ✅ No duplicate/redundant files

---

**Plan Status**: 🟡 READY FOR REVIEW
**Phases**: 7 phases, 7 commits
**Estimated Time**: 3-4 hours (with thorough testing)
**Risk Level**: LOW-MEDIUM (each phase is independently committable)