---
id: system.scheduling_logic
version: 1.0
last_updated: 2025-10-10
tags: [scheduling, discord, events]
---

# Scheduling via Discord Scheduled Events

- Track create/edit/delete → store `event_id`, `open_at`, `close_at`
- On bot startup: backfill upcoming events and reconcile
- Background executor flips open/close at scheduled times (channels, embeds)
- Manual admin override allowed, actions audited
