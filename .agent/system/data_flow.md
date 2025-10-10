---
id: system.data_flow
version: 1.0
last_updated: 2025-10-10
tags: [data, flow]
---

# Data Flow

```
Discord → Bot → Database (SQLite dev / PG prod) → (Sheets view, Dashboard view)
```

- **Writes**: Bot → DB
- **Views**: Sheets & Dashboard pull from DB
- **Sync**: background service `db → sheets`
