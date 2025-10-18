# Phase 0 Baseline & Safety Net Findings
**Author:** Codex (GPT-5)  
**Date:** 2025-10-15  
**Scope:** Guardian Angel League (GAL) Discord Bot, FastAPI backend, integrations, and Live Graphics Dashboard

---

## 1. Instrumentation & Logging Review
- `utils/logging_utils.py` provides token masking and a `SecureLogger`, but **no runtime module currently instantiates `SecureLogger`**; almost all packages (`core/`, `integrations/`, `api/`) rely on the standard `logging` module directly.
- `bot.py` imports `sanitize_log_message` yet still uses bare `logging.info`/`error` without the sanitiser wrapper, leaving potential exposure if formatted messages include secrets.
- Integrations modules (`integrations/sheet_base.py`, `integrations/sheet_detector.py`, etc.) log success/failure events with `logging.info`/`error` but lack structured context and do not mask guild IDs, sheet IDs, or API responses; retry flows also re-log raw exceptions.
- API middleware (`api/middleware.py`) emits request/response logs but with plain strings and no correlation IDs, and sensitive paths (auth failures) are not masked.
- Dashboard frontend has no consistent client-side logging abstraction; ad-hoc `console.log` statements appear in components (see `components/canvas/CanvasEditor.tsx`), and error surfaces funnel through bespoke toasts without central tracking.
- **Phase 1+ action:** introduce structured logging adapters that wrap the existing masking helpers, wire them through bot/integrations/API, and create shared client logger utilities that redact tokens before emission.

## 2. Automated Test Baseline
- **Python:** Running `.venv\Scripts\python.exe -m pytest` fails with `No module named pytest`; there is no `api/tests/` or `core/tests/` directory yet. We need to add pytest to `requirements.txt` (or dev extras) and scaffold smoke suites covering bot setup, API auth, and key integrations.
- **Frontend:** `npm run lint` executes successfully but surfaces `react-hooks/exhaustive-deps` warnings in `components/canvas/CanvasEditor.tsx`; `npm run type-check` currently fails (TS2448/TS2454 scope issues, `Timeout` typing errors in `CanvasEditor` and `hooks/use-performance-monitor.tsx`). No Jest/Playwright suites are defined (`package.json` lacks `test` script). We should add ESLint + TypeScript fixes and bootstrap Jest/Playwright with minimal regression specs during later phases.
- **CI Insight:** No unified lint/test scripts at repo root. Establishing `make`/`npm`/`invoke` wrappers for combined linting will be necessary before Phase 5.

## 3. Performance & UX Baselines
- **API timings:** No existing benchmark scripts; `api/main.py` currently lacks middleware for timing beyond the simple `RequestLoggingMiddleware`. Plan to add a pytest/locust benchmark harness or scripted `httpx` calls once tests exist.
- **Discord command latency:** No metrics captured; bot logging does not time command execution. Add decorators to capture durations and ship them to the central logger/metrics sink after logging unification.
- **Google Sheets round-trips:** Integrations rely on cached clients but do not emit metrics; consider wrapping batch operations with timing logs once structured logging is in place.
- **Dashboard load:** No automated Lighthouse/Playwright runs. We should script `npm exec lighthouse` (or use `@lhci/cli`) and Playwright screenshot captures after we stabilise scripts in Phase 4.
- **Snapshots:** No baseline screenshots present; Playwright hasn’t been initialised. Phase 4 will need a dedicated `tests/playwright` setup capturing graphics list/editor/lock views.

## 4. Immediate Follow-Ups Before Phase 1
1. Add dev dependencies: `pytest`, `pytest-asyncio`, and `coverage` to backend requirements; `jest`, `@testing-library/react`, and `playwright` to dashboard devDependencies (to be installed after stakeholder approval).
2. Draft reusable logging wrapper (Python + TypeScript) taking advantage of `sanitize_log_message` and feed it through high-risk modules first (bot start-up, integrations sheet auth, API login).
3. Define command/test scripts in root `package.json` or a Makefile to orchestrate linting/tests once suites exist.
4. Prepare metric collection helpers (e.g., `core/metrics.py`) so later phases can hook durations without rework.

---

**Summary:** Logging infrastructure exists but is unused; tests are absent; baseline performance data must be captured via new tooling. Phase 1+ work should prioritise wiring the sanitising logger, standing up basic test suites, and enabling scripted benchmarks so future refactors have safety nets.
