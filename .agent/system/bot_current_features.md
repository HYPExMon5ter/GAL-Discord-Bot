---
id: system.bot_current_features
version: 2.0
last_updated: 2025-10-10
tags: [bot, features, inventory]
---

# Discord Bot — Current Implemented Features (Inventory)

This captures the current slash commands and behaviors (registration, check-in/out, scheduling, Sheets, persisted views).
Edit as needed to reflect the exact bot state.

## Commands
- `/register`, `/unregister`
- `/checkin`
- `/sync`, `/standings refresh`
- `/eventmode`
- `/schedule create|edit|delete|list`
- `/reminder`
- `/resetroles`
- `/cache refresh`
- `/admin approve`, `/admin deny`
- `/status`

## Systems
- Registration & Check-In embeds (YAML-configured)
- Google Sheets read/write (current)
- Persisted views (JSON today; DB soon)
- Role management, reminders, scheduling via Discord Events
