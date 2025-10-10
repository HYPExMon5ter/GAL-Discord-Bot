---
id: agents.manifest
version: 1.0
last_updated: 2025-10-10
tags: [factory, droids, documentation, dashboard]
---

# 🤖 Guardian Angel League — FactoryAI Agents Manifest

This file defines all **Custom Droids** and their relationships for the Guardian Angel League Discord Bot and Live Graphics Dashboard ecosystem.

| Category | Droid | Description |
|-----------|--------|-------------|
| Documentation | **Documentation Maintainer** (`droid.documentation_maintainer`) | Updates `.agent/` docs on commit |
| QA / Auditing | **System Auditor** (`droid.system_auditor`) | Weekly drift audit |
| Architecture | **Refactor Coordinator** (`droid.refactor_coordinator`) | Oversees migrations & refactors |
| Frontend | **Dashboard Designer** (`droid.dashboard_designer`) | Generates and refines shadcn/Tailwind UI |
| Backend | **API Architect** (`droid.api_architect`) | Maintains FastAPI endpoints & schema |
| UX | **UX Copywriter** (`droid.ux_copywriter`) | Reviews and improves UI/Embed copy |
| QA / Testing | **Integration Tester** (`droid.integration_tester`) | Runs integration and sanity checks |
| Release | **Release Drafter** (`droid.release_drafter`) | Generates changelogs and draft releases |

## 🧱 File Context Summary

| Path | Used By | Purpose |
|------|----------|----------|
| `.agent/system/*` | Docs, Auditor, Refactor | Architecture and data flow |
| `.agent/tasks/*` | Maintainer, Drafter | PRDs and logs |
| `scripts/*` | Maintainer, Auditor | Utility scripts |
| `dashboard/src/*` | Dashboard Designer, Copywriter | Frontend design and UX text |
| `api/*` | API Architect | Endpoint validation |
| `tests/*` | Integration Tester | QA and regression coverage |

## ⚙️ Shared Workflows

- **Post-commit:** Maintainer updates `.agent` docs
- **Weekly:** Auditor checks `.agent` drift (log-only)
- **Manual:** Coordinator, Designer, or Architect for scoped work
- **Nightly:** Tester executes test suite
- **Release:** Drafter compiles changelogs for tagging

**Maintained by:** Guardian Angel League Development  
**Generated:** 2025-10-10
