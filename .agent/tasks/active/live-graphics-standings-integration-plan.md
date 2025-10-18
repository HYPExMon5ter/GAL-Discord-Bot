# Live Graphics Standings Integration Plan

**Created:** 2025-10-18  
**Status:** DRAFT  
**Priority:** High  

## Objectives
- Wire tournament lobby standings from the Riot API into the Live Graphics dashboard so OBS views reflect current results without hand edits.
- Provide a Discord `/gal` command that staff can run to refresh standings for a selected lobby/round while respecting Riot rate limits.
- Extend canvas data bindings so elements tagged as `player`, `score`, `placement`, or `player_rank` pull from live datasets instead of static text.

## Current State
- **Discord Bot:** Already auto-starts the FastAPI backend and Next.js dashboard (`bot.py`, `services/dashboard_manager.py`). Tournament and sheet integrations yield player rosters but standings are placeholder data (`integrations/sheet_integration.py`).
- **Riot Integration:** `integrations/riot_api.py` and the IGN verification service handle Riot authentication, caching, and rate limiting but only fetch single-player validation or last placement snapshots.
- **Dashboard:** Canvas editor stores optional `dataBinding` metadata (`dashboard/components/canvas/CanvasEditor.tsx`, `dashboard/lib/canvas-helpers.ts`), yet OBS view renders stored text only (`dashboard/app/canvas/view/[id]/page.tsx`).
- **API:** Graphics CRUD exists (`api/routers/graphics.py`, `api/services/graphics_service.py`). No endpoints expose standings or match data, and the SQLite schema lacks tables for match results (`api/models.py`).

## Success Criteria
1. Command returns a confirmation embed with refreshed standings for the requested lobby/round, including total players processed and Riot calls made.
2. Dashboard OBS view updates bound elements with latest standings after a deliberate manual refresh (command/button) without further hand edits.
3. Standings persisted with audit metadata (tournament, round, match id, timestamps) in the API/database so the dashboard and future services consume a single source.
4. Archived graphics remain unchanged—refresh logic skips them and records the skip in logs for traceability.
5. Error handling covers Riot rate limits, missing match data, and dashboard lock contention, falling back gracefully with actionable messages and manual override guidance.
6. Manual refresh updates a unified “Round Scoreboard” graphic that lists every player, their per-round scores, and running totals, sorted by total (tie-breakers deferred).

## Data Flow & Source of Truth
- **Today:** Google Sheets holds registration and check-in state; the bot reads it through `integrations/sheets.py` and caches via `SheetIntegrationHelper` and persistence helpers (`core/persistence.py`). The FastAPI database currently stores graphics metadata, locks, archives, and auth logs—not per-player standings.
- **Implication:** Sheets remain the canonical roster for lobby composition. Database persistence acts as a cache/log layer, so refresh workflows must consult Sheets for the latest availability before contacting Riot.
- **V1 approach:** Keep Sheets authoritative, hydrate standings on demand (manual command) into new database tables, and expose those results to the dashboard. This prevents duplicate data entry while producing an auditable snapshot per refresh.
- **Cache discipline:** every cached dataset must capture the source sheet timestamp/guild and revalidate against Sheets before downstream API calls or rendering.

## Assumptions & Open Questions
- Scoring rubric: need confirmation on point values per placement and whether ties use tiebreakers (average placement, wins, etc.).
- Tournament context: confirm canonical IDs for tournaments/lobbies/rounds (sheet config vs. persistence). Today lobbies are derived on the fly in `integrations/sheet_integration.py`.
- Trigger inputs: decide whether command targets by `match_id`, `(tournament, lobby, round)`, or uses sheet-configured mappings.
- Tie-breakers: implement later; initial release focuses on raw placement/score with documented gaps.
- Lobby grouping (deprioritized for V1 scoreboard): still document heuristics for future use, but the initial scoreboard treats all players in one table; lobby detection becomes a later enhancement.
- Data freshness expectations: manual refresh only for v1; no background polling or auto updates yet.
- Graphics scope: V1 targets normal-mode tournaments; Double Up/team graphics will follow in a later iteration.

## Phase Plan

### Phase 0 - Alignment & Data Inventory (0.5d)
- Confirm tournament metadata sources (Sheets vs. persistence) and map identifiers needed to call Riot API and bind standings.
- Document scoring and tie-breaking rules; capture in config defaults with override capability (`config.yaml`, `core/config_ui.py`).
- Decide minimum command arguments and confirm user roles allowed to execute refreshes.
- Audit Google Sheet structure to confirm round score columns (or other markers) and document fallback strategy when data is missing or ambiguous.
- Catalogue existing dashboard graphic templates and identify target slots for the new "Round Scoreboard" overlay.
- **Testing:** Not applicable (planning/documentation only).

### Phase 1 - Standings Data Model & Storage (1.0d)
- Design and add SQLAlchemy tables for `matches` and `match_participants` (or a flattened `standings` table) in `api/models.py` with migrations/initialization steps.
- Create Pydantic schemas and repository/service abstractions (new module under `api/services/standings_service.py`, repository in `core/data_access` if shared).
- Add persistence helpers for upsert + history retention (match timestamp, source, Riot match id, scoring metadata).
- **Testing:** `.\.venv\Scripts\python.exe -m pytest` (2025-10-18) ✅

### Phase 2 - Riot Data Aggregation Service (1.5d)
- Build a dedicated standings aggregator that:
  - Pulls player rosters via `SheetIntegrationHelper.build_event_snapshot()` (Sheets as canonical source).
  - Detects available rounds by scanning configured sheet columns/tab naming (fallback: configurable max rounds).
  - Fetches Riot match details per player using batch concurrency with the existing `RiotAPI` utilities.
  - Computes per-round points and running totals per player, sorted descending by total (ties unresolved).
- Implement caching and rate-limit guards; reuse Redis if available (`api/services/ign_verification.py`) with fallbacks.
- Surface structured errors for missing Riot IDs, API failures, or incomplete match data, with hooks for manual re-run of specific players or lobbies.
- Ensure archived graphics (and any datasets tied to them) are excluded from refresh output, with explicit logging of skipped ids.
- **Testing (required):** `.\.venv\Scripts\python.exe -m pytest` plus targeted aggregation unit tests.

### Phase 3 - Command Trigger & Orchestration (1.0d)
- Add a new `/gal standings refresh` (working name) subcommand in `core/commands/registration.py` (or new module) that:
  - Validates staff permissions.
  - Accepts tournament/lobby/round parameters and optional Riot match id overrides.
  - Defaults to refreshing the entire scoreboard for the active tournament day when no parameters supplied.
  - Calls the aggregator, persists results, and reports summary metrics to the interaction.
- Integrate observability (structured logging, metrics counters) via `utils/logging_utils.py`.
- Document manual fallback/override switches (e.g., `--force`, `--replay`, `--player`) so staff can recover from partial failures without waiting on automation.
- **Testing (required):** `.\.venv\Scripts\python.exe -m pytest` plus command-level integration tests.

### Phase 4 - API Surface for Standings (1.0d)
- Expose REST endpoints (e.g., `GET /api/v1/standings/{tournament_id}` with filters for lobby/round) in `api/routers`.
- Add service methods to deliver normalized datasets ready for dashboard consumption (sorted by placement, include metadata, version stamps).
- Implement ETag/last-modified headers or version numbers so the dashboard can avoid redundant fetches.
- Include Sheet source metadata (timestamp, worksheet) in responses so consumers know when a refresh last synced from the canonical data.
- **Testing (required):** `.\.venv\Scripts\python.exe -m pytest` plus API contract tests (FastAPI client).

### Phase 5 - Dashboard Data Binding & OBS Rendering (1.0d)
- Extend `CanvasDataBinding` schema to include dataset identifiers and field selectors (e.g., `{ dataset: "scoreboard", row: 1, round: "round_1" }`). Update serialization helpers (`dashboard/lib/canvas-helpers.ts`, `dashboard/types/index.ts`).
- Update Canvas editor UI to support table-style layouts (rows × columns) bound to scoreboard datasets, persisting bindings back through `graphicsApi.update`.
- Introduce a "binding grid" template: designers draw a row prototype (player name cell + per-round cells + total cell) and assign semantic slots (`player_name`, `round_1`, …, `total`). The runtime duplicates this row for each dataset entry, auto-placing values without manual element duplication.
- Adapt OBS view (`dashboard/app/canvas/view/[id]/page.tsx`) to fetch scoreboard data via the new API, resolve bindings, and render fallbacks when data missing or stale.
- Consider websocket hook for live push; if deferred, implement polling with TTL.
- Respect archival state when resolving bindings (cached data for archived graphics, live fetch for active ones).
- Provide editor presets/templates for the scoreboard layout (e.g., up to N players per page, column headers for rounds plus total).
- **Testing (required):** `.\.venv\Scripts\python.exe -m pytest` plus dashboard E2E/UI regression tests.

### Phase 6 - QA, Testing, and Observability (0.5d)
- Add unit tests for aggregation logic (mock Riot responses) and API contracts (`api/tests`).
- Create integration test covering command -> aggregator -> API -> dashboard binding flow (may require fixtures/mocks).
- Add monitoring hooks/logging dashboards for Riot quota usage, failed refreshes, archived skip counts, and binding resolution issues.
- **Testing (required):** Full automation suite (`.\.venv\Scripts\python.exe -m pytest` + dashboard test harness) prior to release.`r`n`r`n## Iteration Strategy
- **Iteration 1 (MVP):** Command-driven refresh for a single lobby/round, synchronous update of one dashboard graphic, manual binding configuration.
- **Iteration 2:** Support multiple graphics/lobbies, caching & incremental updates, improved editor UX (bulk binding).
- **Iteration 3:** Button-triggered refresh from dashboard UI, background polling/websocket updates, spectator overlays.

## Risks & Mitigations
- **Riot Rate Limits:** Batch calls with shared semaphore, respect Retry-After headers, allow command-level dry-run to estimate API load.
- **Data Mapping Drift:** Implement validation that every bound element resolves to a dataset entry; surface warnings in the dashboard editor.
- **Concurrency:** Ensure dashboard lock acquisition (`graphics_service.acquire_lock`) before writing new bindings to avoid conflicts.
- **Partial Data:** Provide fallback content when Riot data missing (e.g., keep previous results, display "Pending" badge).
- **Archival Integrity:** Double-check archive status before any write, log skipped updates, and provide an explicit override pathway so staff understand when frozen graphics will not change.
- **Round Detection Errors:** When Sheets lack clear round columns/tabs, fall back to configured defaults and flag the issue in command output so staff can correct manually.
- **Graphic Layout Drift:** If canvas bindings become misaligned with available player rows or round columns, surface warnings and provide runtime fallbacks (hide unused cells, pad with blanks).

## Dependencies
- Valid `RIOT_API_KEY` and Redis (optional) availability.
- Accurate sheet column mappings for IGN and lobby assignments (`integrations/sheet_integration.py`).
- Updated config entries for scoring and tournament metadata (add to `config.yaml` with migration script).

## Future Enhancements
- Add dashboard button workflows via WebSocket-triggered refreshes.
- Stream overlay package export (auto-generate JSON/HTML fragments per lobby).
- Historical analytics for match timelines and player performance trends.



