---
id: agent.readme
version: 1.0
last_updated: 2025-10-10
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
- `sops/` — step-by-step runbooks for common operations.
- `tasks/` — PRDs, roadmap items, and active logs.
- `prompts/` — Droid prompt files used by automations.
- `snapshots/` — lightweight context packs (gitignored).

## Conventions
- Small, link-rich docs, avoid duplication.
- YAML front-matter on each doc (`id`, `version`, `last_updated`, `tags`).
- Prefer bullet points + sections agents can skim quickly.

