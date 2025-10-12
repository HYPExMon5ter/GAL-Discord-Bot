# Feature: Live Graphics Dashboard 2.0 (Password-Gated Access)

## Purpose
Rebuild the Live Graphics Dashboard as a secure, lightweight, password-gated web portal
for staff to create, manage, and archive live broadcast graphics.  
This plan removes multi-user editing complexity and focuses on **single-user edit locks, archival safety, and basic password-based authentication.**

---

## 🔐 Authentication (Current Implementation)

### Overview
The system currently uses a **single shared password** for staff to access the dashboard.
This approach is acceptable for early internal builds but must be replaced before production deployment.

### Requirements
- Store password as an **environment variable** (`DASHBOARD_PASSWORD`) — not hardcoded.
- Validate login sessions via secure cookies.
- Implement 15-minute inactivity timeout.
- Log all login attempts to `auth_logs` table in SQLite.

### Database Tables

#### `auth_logs`
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| username | text | Staff-entered name on login |
| ip_address | text | Origin IP |
| success | boolean | True if login succeeded |
| timestamp | timestamp | UTC timestamp |

#### `active_sessions`
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| username | text | Active user |
| session_token | text | UUID for browser session |
| expires_at | timestamp | Expiration timestamp |

---

## 🧱 Architecture Overview

### Frontend
- **Next.js 14 + TypeScript + Tailwind + shadcn/ui**
- Uses cookie-based login form (single password field)
- UI tabs: **Graphics** and **Archive**
- Graphics Tab:
  - Create, edit, duplicate, or delete graphics
  - Show “In Use” badge for locked graphics
- Archive Tab:
  - List archived graphics
  - Allow restore or permanent delete (admin only)

### Backend
- **FastAPI (Python)** serving:
  - `/api/login` — authenticate shared password
  - `/api/logout` — clear session token
  - `/api/graphics` — CRUD for graphics
  - `/api/archive` — archive/restore endpoints
  - `/api/lock` — manage canvas locks
- PostgresSQL with SQLite fallback database for persistent storage.

---

## 🧩 Locking & Concurrency Logic

### Core Principle
Only one user may edit a given graphic/canvas at a time.  
Others may **view** but cannot **edit**, **delete**, or **archive** locked items.

### Table: `canvas_locks`
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| graphic_id | int | FK to `graphics` |
| user_name | text | Active user editing |
| locked | boolean | True while editing |
| locked_at | timestamp | When editing began |
| expires_at | timestamp | When lock auto-expires |

### Rules
1. User opens a graphic → system checks for an existing lock.
2. If locked, user sees a **“Locked by [username]”** banner.
3. Lock automatically expires after 5 minutes of inactivity.
4. Locked graphics cannot be:
   - Edited by others
   - Deleted
   - Archived
   - Restored from archive

---

## 📂 Tabs and Features

### 1️⃣ Graphics Tab
- Create new graphic
- Edit or duplicate existing ones
- Displays “In Use” badge when locked
- Save or publish to overlay

### 2️⃣ Archive Tab
- List archived graphics with date/user metadata
- Restore old graphics
- Prevent archiving of locked items
- Admin-only permanent delete

---

## 🧾 API Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|--------|-----------|-------------|----------------|
| POST | `/api/login` | Validate shared password, issue token | 🔐 |
| POST | `/api/logout` | Invalidate session | 🔐 |
| GET | `/api/graphics` | List all active graphics | 🔐 |
| POST | `/api/graphics` | Create new graphic | 🔐 |
| PUT | `/api/graphics/{id}` | Edit graphic (requires unlocked) | 🔐 |
| DELETE | `/api/graphics/{id}` | Delete (requires unlocked, admin only) | 🔐 |
| POST | `/api/archive/{id}` | Archive (if unlocked) | 🔐 |
| POST | `/api/archive/{id}/restore` | Restore archived graphic | 🔐 |
| POST | `/api/lock/{graphic_id}` | Lock canvas for editing | 🔐 |
| DELETE | `/api/lock/{graphic_id}` | Release lock | 🔐 |
| GET | `/api/lock/status` | Check current locks | 🔐 |

---

## 🧩 Database Schema Additions

### `graphics`
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| title | text | Graphic name |
| data_json | text | Serialized canvas data |
| created_by | text | Username |
| updated_at | timestamp | Last modified time |
| archived | boolean | True if archived |

### `archives`
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| graphic_id | int | FK to graphics |
| archived_at | timestamp | Archive timestamp |
| restored_from | int | FK to previous ID if restored |

---

## ⚙️ Security & Compliance

### Current State
- Shared password stored as environment variable.
- All admin actions logged to `auth_logs`.
- Sessions expire automatically after 15 minutes.

### To Do
- [ ] Add rate limiting (5 failed attempts → temporary ban)
- [ ] Encrypt all passwords in transit (HTTPS)
- [ ] Replace shared password with OAuth (Phase 2)

---

## 🧾 Subtasks (for Refactor Coordinator)

### Backend
- [ ] Implement FastAPI endpoints for login/logout
- [ ] Add PostgreSQL/SQLite tables: `auth_logs`, `active_sessions`, `canvas_locks`
- [ ] Add cron job for expired lock cleanup

### Frontend
- [ ] Add login screen with shared password input
- [ ] Implement lock indicator on graphics
- [ ] Add alert when attempting to edit/archived locked item
- [ ] Build Archive Tab UI with restore and delete actions

### Security
- [ ] Move password to environment variable
- [ ] Add rate limiting and brute-force protection
- [ ] Add HTTPS certificate configuration
- [ ] Write Security SOP for dashboard access

### Future Expansion
- [ ] Integrate Discord OAuth once user system is stable
- [ ] Add role-based access control
- [ ] Add activity logs for edits and deletions

---

## 🧠 Expected Output

When complete:
- The dashboard is password-protected.
- Only one user can edit a graphic at a time.
- Locked graphics cannot be deleted or archived.
- Session tracking and audit logging are active.
- PostgreSQL is the single source of truth with SQLite for users, graphics, and archives.
- Migration to proper auth (Discord OAuth) can be done with minimal refactor.

---

## 🧩 Dependencies
- `.agent/system/architecture.md`
- `.agent/system/sqlite_migration_plan.md`
- `.agent/sops/security.md`
- `.agent/sops/deployment.md`
- `.agent/sops/user-management.md`