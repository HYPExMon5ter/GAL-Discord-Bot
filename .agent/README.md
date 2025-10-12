---
id: agent.readme
version: 1.0
last_updated: 2025-10-11
tags: [agent, docs, overview]
---

# Project Knowledge Hub (.agent)

This folder is the **single source of truth** for human + AI context.
It documents how the system works today and evolves over time.

## How to use
- Before implementing a feature, create/update a PRD in `./tasks/feature_prds/`.
- After coding, docs auto-refresh via **post-commit** hooks (see `scripts/`).
- Weekly audits run in CI and **log findings** (no auto-commit).

## Index
- `system/` — durable system docs (architecture, flows, schema, scheduling).
  - **Live Graphics Dashboard 2.0** — Complete dashboard system documentation
  - **Frontend Components** — React components and UI documentation
  - **API Integration** — Frontend-backend API contracts
  - **Developer Documentation** — Development guidelines and best practices
  - **Cross-References** — Complete system interconnection mapping
- `sops/` — step-by-step runbooks for common operations.
  - **Dashboard Operations** — Live Graphics Dashboard procedures
  - **Graphics Management** — Template and graphic workflows
  - **Dashboard Deployment** — Frontend CI/CD and deployment
  - **Canvas Locking** — Collaborative editing procedures
  - **Dashboard Security** — Authentication and access control
- `tasks/` — PRDs, roadmap items, and active logs.
- `prompts/` — Droid prompt files used by automations.
- `snapshots/` — lightweight context packs (gitignored).

## Live Graphics Dashboard 2.0 Documentation
The Live Graphics Dashboard 2.0 implementation includes comprehensive documentation:
- **System Architecture**: Complete frontend and backend architecture
- **Component Documentation**: All React components and hooks
- **API Contracts**: REST endpoints and WebSocket integration
- **Operational Procedures**: Step-by-step SOPs for all operations
- **Security Procedures**: Authentication, authorization, and compliance
- **Deployment Procedures**: CI/CD pipeline and environment management

## Conventions
- Small, link-rich docs, avoid duplication.
- YAML front-matter on each doc (`id`, `version`, `last_updated`, `tags`).
- Prefer bullet points + sections agents can skim quickly.
- Cross-reference extensively to maintain connectivity.
- Version consistently across related documentation.

