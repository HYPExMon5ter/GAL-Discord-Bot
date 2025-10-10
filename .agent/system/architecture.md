---
id: system.architecture
version: 1.0
last_updated: 2025-10-10
tags: [system, architecture]
---

# Architecture Overview

- **Bot**: Python (`discord.py`) with slash commands, embeds, and Discord Scheduled Events.
- **Data**: Database-first (SQLite for dev, Postgres-ready). Google Sheets becomes a **view**.
- **Dashboard**: Next.js + TypeScript + shadcn/ui + Tailwind (future), reads DB via API.
- **Docs**: `.agent` auto-maintained via Droid + Git hooks + CI audits.

See:
- `./data_flow.md`
- `./flows_registration_checkin.md`
- `./scheduling_logic.md`
- `../sops/` runbooks
