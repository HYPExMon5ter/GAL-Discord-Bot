# GAL Codebase Simplification & Performance Sweep Plan
**Success looks like:** lean, modular modules; measurable performance gains; confident deployments; and documentation that reflects the simplified architecture, all while preserving GAL's polished user experience and critical tournament workflows.

**Author:** Codex (GPT-5)  
**Target Owner:** Refactor Coordinator  
**Objective:** Execute a multi-stage refactor that simplifies the Guardian Angel League Discord Bot, API, integrations, and Live Graphics Dashboard while preserving all existing features, real-time behaviour, and visual design.

---

## Project Context
- **System breadth:** Discord bot (`core/`, `helpers/`), FastAPI backend (`api/`), extensive Google Sheets and Riot API integrations (`integrations/`), and a Next.js 14 dashboard (`dashboard/`) backed by SQLite with Postgres readiness.
- **Current pain points:** Extremely large modules (for example `core/commands.py` >2k lines, `integrations/sheets.py` ~44k lines, API routers >400 lines), duplicated logic between configuration and persistence layers, ad-hoc caching, and mixed async patterns.
- **Documentation sources reviewed:** `.agent/system/architecture.md`, `frontend-components.md`, `api-backend-system.md`, `developer-documentation.md`, `core-modules.md`, `integration-modules.md`, `data-models.md`, `event-system.md`, plus `.agent/README.md` and `AGENTS.md`.

## Guardrails & Success Criteria
- **Feature parity:** No change to bot commands, tournament flows, canvas locking, or dashboard UX. Follow brand guidance in `.agent/system/branding-guidelines.md` and UI specifications in `frontend-components.md`.
- **Performance wins:** Target measurable improvements such as 30% faster Discord command execution for common flows, < 500 ms P95 API latency on graphics and tournament endpoints, 40% fewer Google Sheets round-trips during registration operations, and < 3 s dashboard TTI on mid-tier laptops.
- **Maintainability:** Break monolithic files into focused modules capped at ~500 LOC, eliminate duplicated sheet and config logic, codify shared types and interfaces, add targeted comments or docstrings where logic is non-obvious, and raise automated test coverage by at least 15% in both Python and TypeScript stacks.
- **Code clarity:** Replace parallel or duplicate implementations with shared helpers, prefer updating existing functions over creating new ones, and prune dead code after verifying no call sites depend on it.
- **Observability & resilience:** Preserve or enhance logging and sanitisation (`utils/logging_utils.py`), standardise structured logs across layers, add lightweight tracing around high-traffic paths, and harden error handling so failures surface actionable context without leaking sensitive data.

## Phase 0 - Baseline & Safety Nets
1. **Instrumentation review:** Confirm logging hooks and masking from `utils/logging_utils.py` are applied across refactor targets.
2. **Regression test harness:** Stabilise existing pytest and Jest suites; add smoke tests for core bot commands, sheets integration, and dashboard CRUD journeys.
3. **Performance benchmarks:** Capture current timings for Discord registration and check-in, critical FastAPI routes, Sheets batch operations, and dashboard load (Lighthouse CI).
4. **Snapshot UX:** Record key dashboard views (Playwright screenshot suite) to enforce “no visual regressions”.

## Phase 1 - Core Bot Simplification (`core/`, `helpers/`, `utils/`)
1. **Modular command architecture:** Split `core/commands.py` into domain-specific modules (for example `commands/tournaments.py`, `commands/roles.py`) with a shared registry and typed helpers.
2. **Shared validation and DTOs:** Move repeated registration and roster validation into reusable helpers aligned with `core/models/` dataclasses, documenting edge cases inline when logic is complex.
3. **Event lifecycle cleanup:** Review `core/events.py` and `core/views.py` usage; ensure new module boundaries keep persistent views registered via `bot.py` without duplication.
4. **Async consistency:** Audit command handlers for blocking calls; wrap sheet and API IO in async-friendly adapters or thread executors with backpressure, documenting threading boundaries where needed and ensuring new error paths funnel through shared logging utilities.
5. **Bot config consolidation:** Centralise environment access via `config.py` and typed settings objects; remove ad-hoc `os.getenv` calls scattered in commands and helpers.

## Phase 2 - Data Access & External Integrations (`integrations/`, `core/persistence.py`)
1. **Layered sheet integration:** Break `integrations/sheets.py` into smaller services (authentication, caching, batch operations) and align shared primitives with `sheet_base.py` and `sheet_utils.py`, documenting data flow expectations.
2. **Caching strategy:** Formalise cache invalidation windows (current 10 minute TTL) through a single manager; add metrics on hit and miss rates and guard race conditions with async locks.
3. **Schema harmonisation:** Map sheet column access to the canonical data models documented in `data-models.md`; generate typed adapters to eliminate fragile index-based access.
4. **Error handling standardisation:** Replace bespoke exception handling with domain-specific error classes, centralise retry policies consistent with `event-system.md`, and ensure each path logs structured context for triage.
5. **Riot and IGN integration sweep:** Extract rate-limiting and request serialisation into middleware; evaluate batching or memoisation on repeated lookups, removing redundant helper functions in the process.
- **Status (2025-10-15):** Introduced `SheetCacheManager`, TTL-aware refresh gating, structured logging across sheets service, and hardened Riot/IGN integrations with shared retry handling.

## Phase 3 - API Backend Modernisation (`api/`)
1. **Router pruning:** Refactor `routers/graphics.py`, `routers/configuration.py`, and others into thin controllers that delegate to service layer methods; ensure response schemas stay aligned with `api/schemas`.
2. **Service abstractions:** Consolidate duplicated logic across `services/` modules; introduce shared repository interfaces bridging SQLAlchemy and the updated data access layer, and document tricky transactional flows.
3. **Dependency management:** Tighten `dependencies.py` to provide scoped sessions, typed auth contexts, and gating for upcoming read-only endpoints.
4. **WebSocket resilience:** Review `routers/websocket.py` for backpressure handling, connection lifetimes, and lock broadcasting; align with the event bus once simplified and make sure disconnect and error cases emit consistent telemetry.
5. **Security posture:** Confirm JWT issuance aligns with `access-control.md`, add automated tests for master password authentication, and maintain log sanitisation via middleware.

## Phase 4 - Live Graphics Dashboard Simplification (`dashboard/`)
1. **Routing cleanup:** Audit App Router segments for redundant layouts; ensure shared providers (auth, websocket) live at the appropriate boundary and eliminate unused wrappers.
2. **State management pass:** Evaluate Zustand usage alongside React Context; consolidate to a single predictable pattern per domain (graphics, canvas, archive), comment any intentional divergences, and funnel error notifications through shared toast/logging hooks.
3. **Component library hygiene:** Use barrel exports and consistent prop typing across `components/graphics`, `canvas`, and `ui`; remove obsolete props, reduce duplication by reusing existing primitives, and document complex component contracts.
4. **Performance tuning:** Apply React Server Components where beneficial, enable route-level chunking, prune unused Tailwind utilities, and validate with bundle analysis.
5. **Visual fidelity safeguards:** Add Playwright and screenshot assertions for critical flows (graphics list, editor, archive) to ensure the neon dark theme remains precise.

## Phase 5 - Cross-Cutting Tooling & Quality Gates
1. **Unified lint and type tooling:** Enforce Ruff and Black for Python and ESLint, Prettier, and TypeScript strict mode for the dashboard; integrate into CI.
2. **CI pipeline hardening:** Extend pipelines to run test, lint, and benchmark suites; publish artefacts such as coverage and Lighthouse scores for each merge.
3. **Telemetry and alerting:** Instrument key metrics (sheet latency, bot command duration, API response times) and set thresholds for regression alarms.
4. **Documentation sync:** Ensure `.agent/system/*` docs auto-refresh with refactors; add new diagrams or tables when module boundaries change and record rationale for major deletions.

## Phase 6 - Deployment & Change Management
1. **Staged rollout:** Sequence deliveries: integrations updates first (behind feature flags), then backend, then bot, and finally dashboard to keep recovery simple.
2. **Feature flags and rollback:** Wrap risky changes (for example, new sheet adapters) in toggles; document rollback steps in `.agent/sops`.
3. **Stakeholder sign-off:** Demo simplified flows to bot operators and dashboard users; capture feedback before deprecating legacy code paths.
4. **Post-mortem review:** After rollout, collect metrics versus baselines and log lessons learned; schedule follow-up backlog items for any deferred improvements.

## Dependencies & Coordination
- Confirm Redis (or an alternative) availability if cache moves out of process.
- Align data model updates with integration partners to avoid sheet schema drift.
- Coordinate with API consumers (dashboard and bot) for contract adjustments; update TypeScript types or generated clients accordingly.
- Maintain a close loop with the design owner for any UI refactors that touch brand or interaction patterns.

## Risks & Mitigations
- **Large surface area:** Tackle refactor work in vertical slices to avoid cross-cutting regressions; maintain feature flags.
- **Sheet API limits:** Schedule heavy operations during off-peak hours and rely on cached snapshots; validate quotas before load tests.
- **Async shifts:** Introducing async wrappers in bot or integrations can surface race conditions; back changes with targeted stress tests and clear comments.
- **Team bandwidth:** Use phased delivery with clear acceptance criteria so work can be parallelised without blocking.

## Immediate Next Actions
1. Ratify this plan with project stakeholders and assign owners for each phase.
2. Stand up baseline metrics and regression tests (Phase 0 deliverables).
3. Prepare detailed task breakdowns and timelines per phase for tracking in `.agent/tasks/feature_prds/`.

---

**Success looks like:** lean, modular modules; measurable performance gains; confident deployments; and documentation that reflects the simplified architecture, all while preserving GAL’s polished user experience and critical tournament workflows.
