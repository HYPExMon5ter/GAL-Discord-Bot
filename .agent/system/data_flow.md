---
id: system.data_flow
version: 1.1
last_updated: 2025-10-10
tags: [data, flow, bug-fixed]
---

# Data Flow

```
Discord → Bot → Database (SQLite dev / PG prod) → (Sheets view, Dashboard view)
```

- **Writes**: Bot → DB
- **Views**: Sheets & Dashboard pull from DB
- **Sync**: background service `db → sheets`

## Reminder DM Flow (2025-10-10)
```
Sheets Cache → Filter Registered/Not-Checked-In → Resolve Discord Members → Send DMs → Log Summary
```

### Fixed Issues (2025-10-10)
- **Syntax Error**: Fixed missing `except` block in `send_reminder_dms` function
- **Exception Handling**: Improved DM error handling structure
- **Flow Stability**: Removed nested try blocks causing syntax errors
