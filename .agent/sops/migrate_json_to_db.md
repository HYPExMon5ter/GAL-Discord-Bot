---
id: sops.migrate_json_to_db
version: 1.0
last_updated: 2025-10-10
tags: [sop, migration]
---

# SOP: Migrate persisted_views.json → channel_views table

1. Stop the bot
2. Run migration script (TBD) to import JSON rows into DB
3. Start the bot; verify embeds rehydrate from DB
4. Delete JSON fallback after verification
