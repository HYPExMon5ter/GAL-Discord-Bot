## Production-Ready Testing Strategy for Dashboard + Riot API Integration

### Overview
Create an end-to-end testing system that validates the entire data flow from live Riot API → Backend API → Dashboard, using real TFT players without running an actual tournament.

---

## Strategy: Multi-Tier Testing Approach

### Tier 1: Live Riot API Smoke Test Script
**Purpose**: Verify Riot API connectivity and data quality with real players

**Implementation**: `scripts/test_riot_integration.py`
- Fetch data for **known high-profile TFT players** (pros/streamers with consistent match history)
- Test players across multiple regions (NA, EUW, KR)
- Validate all critical data points:
  - Account lookup (PUUID retrieval)
  - Match history fetching
  - Placement extraction
  - Rank detection across accounts
- Report success/failure metrics
- **Benefit**: Tests against real, changing data without needing our own tournament

**Example Test Players**:
```python
TEST_PLAYERS = {
    "na": ["Dishsoap#NA1", "socks#NA1", "milk#NA1"],
    "euw": ["Shircane#EUW", "robinsongz#EUW"],
    "kr": ["빠숑#KR1", "감스트#KR1"]
}
```

---

### Tier 2: Backend API Integration Test
**Purpose**: Test full backend pipeline with realistic data

**Implementation**: `scripts/test_scoreboard_api.py`
- Create a **test tournament snapshot** using data from Tier 1
- POST to `/api/v1/scoreboard/refresh` with:
  - Test guild ID (dedicated for testing)
  - `fetch_riot=True` with real IGNs
  - `sync_sheet=False` (skip sheet integration)
  - Use `snapshot_override` for controlled player list
- Verify:
  - Scoreboard snapshot creation
  - Placement → Points conversion
  - Player ranking accuracy
  - Database persistence
- GET from `/api/v1/scoreboard/latest` to confirm retrieval
- **Benefit**: Tests entire aggregation pipeline without tournament setup

---

### Tier 3: Dashboard End-to-End Test
**Purpose**: Validate dashboard can fetch and display live data

**Implementation**: Playwright test in `dashboard/e2e/scoreboard.spec.ts`
- Start local services (API + Dashboard)
- Trigger scoreboard refresh via API
- Navigate to dashboard scoreboard view
- Assert:
  - Player names displayed correctly
  - Standings ranked properly
  - Points calculated accurately
  - Real-time updates work
- **Benefit**: Full user-facing validation

---

### Tier 4: Production Dry Run Script
**Purpose**: Simulate tournament day workflow

**Implementation**: `scripts/production_dry_run.py`
- **Phase 1: Pre-Tournament**
  - Validate Riot API key
  - Test connection to all regions
  - Verify database accessibility
- **Phase 2: Round Simulation**
  - Create fake "Round 1" with test players
  - Fetch latest placements
  - Generate scoreboard
  - Export standings
- **Phase 3: Health Checks**
  - API response times
  - Database query performance
  - Error rate monitoring
- **Output**: Production readiness report with pass/fail criteria

---

## Implementation Plan

### Step 1: Commit ALL Recent Changes ✅
**Files to commit**:

**Modified Files**:
- `api/tests/test_standings_aggregator.py` - Extended tests with Riot API integration
- `config.py` - Added poll configuration functions
- `config.yaml` - Poll configuration settings
- `core/commands/__init__.py` - Command registration updates
- `core/onboard.py` - Onboarding improvements
- `core/views.py` - View updates

**New Files**:
- `api/services/mock_riot_api.py` - Mock Riot API for testing
- `api/tests/test_riot_api.py` - Comprehensive Riot API unit tests
- `api/tests/test_standings_integration.py` - Integration tests
- `core/commands/poll.py` - New poll command
- `helpers/poll_helpers.py` - Poll helper functions
- Multiple completed task files in `.agent/tasks/complete/`

**Commit Message**:
```bash
git add .
git commit -m "feat: comprehensive testing infrastructure and poll command

Testing Infrastructure:
- Add unit tests for RiotAPI class with mocked HTTP responses
- Add MockRiotAPI service for deterministic testing
- Add integration tests for standings aggregation with Riot data
- Extend aggregator tests with fetch_riot=True scenarios

New Features:
- Add poll command for mass DM notifications with progress tracking
- Add poll configuration with customizable embeds and settings
- Implement LayoutView components for poll DMs

Bug Fixes:
- Fix onboarding welcome message gender inclusivity
- Update command registration and view handling

All changes tested and ready for production validation."
```

### Step 2: Create Live Riot API Test Script
**File**: `scripts/test_riot_integration.py`
- Test against real TFT pros/streamers (public data)
- Validate all API flows work with live data
- Generate pass/fail report
- **Runtime**: ~2-3 minutes

### Step 3: Create Backend API Test Script
**File**: `scripts/test_scoreboard_api.py`
- Use test players from Step 2
- POST test tournament data
- Verify complete data flow
- Clean up test data after run
- **Runtime**: ~1-2 minutes

### Step 4: Add Dashboard E2E Test
**File**: `dashboard/e2e/test_scoreboard_display.spec.ts` (Playwright)
- Automated browser test
- Verify UI displays correct data
- Test real-time updates
- **Runtime**: ~30 seconds

### Step 5: Create Production Dry Run
**File**: `scripts/production_dry_run.py`
- Orchestrates all tests
- Simulates tournament workflow
- Generates readiness report
- **Runtime**: ~5 minutes total

---

## Validation Criteria (Pass/Fail)

### ✅ Production Ready If:
1. **Riot API Tests**: 90%+ success rate across all regions
2. **Backend API Tests**: All endpoints return 200/201
3. **Dashboard Tests**: UI displays data within 2 seconds
4. **Data Accuracy**: Points calculations 100% correct
5. **Error Handling**: Graceful degradation for missing data
6. **Performance**: API responses < 500ms average

### ❌ Block Production If:
- Riot API success rate < 80%
- Any critical endpoint fails
- Data corruption detected
- Dashboard crashes on load
- Average API response > 2 seconds

---

## Testing Data Sources

### Option 1: Public TFT Streamers (Recommended)
- **Pros**: Real, always-active accounts with match history
- **Cons**: Data changes constantly (not deterministic)
- **Examples**: Dishsoap, socks, milk, Shircane, robinsongz

### Option 2: Pre-Recorded Test Data
- **Pros**: Deterministic, repeatable
- **Cons**: Data can become stale (Riot API changes)
- **Use Case**: Unit tests, CI/CD

### Option 3: Hybrid Approach (Best)
- Use **Option 1** for smoke tests (verify API works)
- Use **Option 2** for unit/integration tests (verify logic)
- Use **Option 1** for pre-tournament validation

---

## Execution Flow

```bash
# 1. Commit ALL recent work (including poll command and test infrastructure)
git add .
git commit -m "feat: comprehensive testing infrastructure and poll command"
git push origin main

# 2. Run live Riot API test
python scripts/test_riot_integration.py

# 3. Run backend API integration test
python scripts/test_scoreboard_api.py

# 4. Run dashboard E2E test (if Playwright configured)
cd dashboard && npm run test:e2e

# 5. Run full production dry run
python scripts/production_dry_run.py

# Output: Production Readiness Report
```

---

## Expected Deliverables

1. **Scripts**:
   - `scripts/test_riot_integration.py` - Live API validation
   - `scripts/test_scoreboard_api.py` - Backend integration test
   - `scripts/production_dry_run.py` - Full system validation

2. **Documentation**:
   - `docs/TESTING.md` - How to run tests before tournament
   - `docs/PRODUCTION_CHECKLIST.md` - Pre-tournament validation steps

3. **Reports**:
   - JSON output from each test script
   - HTML summary report with pass/fail status
   - Performance metrics dashboard

---

## Timeline

- **Phase 1** (5 min): Commit ALL changes with comprehensive commit message
- **Phase 2** (30 min): Implement `test_riot_integration.py`
- **Phase 3** (30 min): Implement `test_scoreboard_api.py`
- **Phase 4** (20 min): Implement `production_dry_run.py`
- **Phase 5** (20 min): Run all tests, validate output
- **Phase 6** (10 min): Generate production readiness report

**Total Estimated Time**: ~2 hours

---

## Success Metrics

After running all tests, you'll have:
- ✅ Proof that Riot API integration works with real data
- ✅ Confidence that backend correctly processes placements
- ✅ Validation that dashboard displays data correctly
- ✅ Performance baseline for production
- ✅ Clear go/no-go decision for tournament use

---

## Next Steps After Approval

1. **Commit all uncommitted files** (test infrastructure + poll command + config changes)
2. Create the 3 production test scripts
3. Run each test and validate output
4. Generate final production readiness report
5. Provide recommendations for tournament day

Ready to proceed?