---
id: system.sqlite_migration_plan
version: 1.0
last_updated: 2025-10-10
tags: [migration, sqlite]
---

# Migration Plan — JSON/Sheets → SQLite

1. Create tables: `players`, `teams`, `team_members`, `registrations`, `checkins`, `schedules`, `channel_views`, `guild_config`, `audit_log`
2. Import existing Sheet data → DB
3. Import `persisted_views.json` → `channel_views`
4. Switch bot writes/reads to DB; keep Sheets as view
5. Add `db → sheets` sync worker (batch + on-demand)
