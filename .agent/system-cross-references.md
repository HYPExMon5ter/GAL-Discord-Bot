---
id: system.cross-references
version: 2.0
last_updated: 2025-10-13
tags: [system, cross-references, architecture, documentation, mapping]
---

# 🔗 System Cross-References

**Complete interconnection mapping for the Guardian Angel League Live Graphics Dashboard ecosystem**

## 📋 Overview

This document provides comprehensive cross-references between all system components, documentation, and operational procedures. It serves as the navigation hub for understanding how different parts of the system connect and interact.

## 🏗️ Architecture Cross-References

### Frontend ↔ Backend Integration
```
Frontend Component                ↔ Backend Endpoint        ↔ Documentation
─────────────────────────────────────────────────────────────────────────────
GraphicsTab.tsx                  ↔ GET /api/v1/graphics    ↔ api-integration.md
GraphicsTable.tsx                ↔ GET /api/v1/graphics    ↔ frontend-components.md
CreateGraphicDialog.tsx          ↔ POST /api/v1/graphics   ↔ frontend-components.md
CanvasEditor.tsx                 ↔ PUT /api/v1/graphics/{id} ↔ canvas-editor-architecture.md
use-graphics.ts                  ↔ All graphics endpoints   ↔ api-integration.md
use-locks.tsx                    ↔ Lock management API    ↔ canvas-locking-management.md
use-auth.tsx                     ↔ Authentication API     ↔ dashboard-security.md
```

### Database ↔ Service Layer ↔ API
```
Database Model                    ↔ Service Layer           ↔ API Router            ↔ Documentation
──────────────────────────────────────────────────────────────────────────────────
graphics table                   ↔ GraphicsService.get_graphics ↔ GET /graphics        ↔ api-backend-system.md
graphics table                   ↔ GraphicsService.create_graphic ↔ POST /graphics       ↔ api-backend-system.md  
graphics table                   ↔ GraphicsService.update_graphic ↔ PUT /graphics/{id}  ↔ api-backend-system.md
graphics table                   ↔ GraphicsService.delete_graphic ↔ DELETE /graphics/{id} ↔ api-backend-system.md
canvas_locks table               ↔ LockService.acquire_lock   ↔ POST /lock/{id}       ↔ canvas-locking-management.md
canvas_locks table               ↔ LockService.release_lock   ↔ DELETE /lock/{id}    ↔ canvas-locking-management.md
```

## 📚 Documentation Cross-References

### System Documentation Matrix
```
System Doc                        ↔ Related Components          ↔ Operational SOPs         ↔ Implementation Files
────────────────────────────────────────────────────────────────────────────────────────────────────────
live-graphics-dashboard.md       ↔ dashboard/graphics/*          ↔ dashboard-operations.md  ↵ api/routers/graphics.py
canvas-editor-architecture.md    ↔ dashboard/canvas/*           ↔ canvas-editor-workflow.md ↵ dashboard/app/canvas/edit/[id]/page.tsx
api-backend-system.md             ↔ api/*                         ↔ api-deployment.md        ↵ api/main.py
frontend-components.md           ↔ dashboard/components/*       ↔ dashboard-operations.md  ↵ dashboard/hooks/*.tsx
dashboard-security.md             ↔ auth/*, security middleware    ↔ dashboard-security.md      ↵ api/auth.py
```

### SOP Interconnections
```
SOP                               ↔ System Documentation        ↔ Components               ↔ API Endpoints
──────────────────────────────────────────────────────────────────────────────────────────────
dashboard-operations.md            ↔ live-graphics-dashboard.md   ↔ GraphicsTab.tsx           ↔ GET /api/v1/graphics
graphics-management.md            ↔ api-integration.md            ↔ GraphicsTable.tsx         ↔ POST /api/v1/graphics
canvas-editor-workflow.md         ↔ canvas-editor-architecture.md ↔ CanvasEditor.tsx          ↔ PUT /api/v1/graphics/{id}
canvas-locking-management.md       ↔ canvas-editor-architecture.md ↔ use-locks.tsx             ↔ POST /api/v1/lock/{id}
dashboard-security.md              ↔ api-backend-system.md         ↔ use-auth.tsx              ↔ POST /auth/login
```

## 🔄 Data Flow Cross-References

### Graphics Management Flow
```
User Action → Frontend Component → API Call → Service Layer → Database → Documentation
───────────────────────────────────────────────────────────────────────────────────────────────────────
Login → LoginForm.tsx → POST /auth/login → N/A → N/A → dashboard-security.md
List Graphics → GraphicsTab.tsx → GET /api/v1/graphics → GraphicsService → graphics table → api-integration.md
Create Graphic → CreateGraphicDialog.tsx → POST /api/v1/graphics → GraphicsService → graphics table → graphics-management.md
Edit Graphic → CanvasEditor.tsx → GET /api/v1/graphics/{id} → GraphicsService → graphics table → canvas-editor-workflow.md
Save Changes → CanvasEditor.tsx → PUT /api/v1/graphics/{id} → GraphicsService → graphics table → canvas-editor-workflow.md
Delete Graphic → GraphicsTable.tsx → DELETE /api/v1/graphics/{id} → GraphicsService → graphics table → graphics-management.md
Archive Graphic → GraphicsTable.tsx → POST /api/v1/archive/{id} → GraphicsService → graphics table → graphics-management.md
```

### Canvas Lock Management Flow
```
Action → Component → API Call → Service Layer → Database → Documentation
─────────────────────────────────────────────────────────────────────────────────────────────────────
Open Editor → CanvasEditor.tsx → POST /api/v1/lock/{id} → LockService → canvas_locks table → canvas-locking-management.md
Refresh Lock → CanvasEditor.tsx → POST /api/v1/lock/{id}/refresh → LockService → canvas_locks table → canvas-locking-management.md
Release Lock → CanvasEditor.tsx → DELETE /api/v1/lock/{id} → LockService → canvas_locks table → canvas-locking-management.md
Check Status → use-locks.tsx → GET /api/v1/lock/status → LockService → canvas_locks table → canvas-locking-management.md
```

## 🗂️ File System Cross-References

### Core Application Structure
```
Directory/Files                    ↔ Purpose                    ↔ Related Docs            ↔ Dependencies
────────────────────────────────────────────────────────────────────────────────────────────────────────
api/main.py                       → FastAPI application        → api-backend-system.md   ↔ api/routers/*
api/routers/graphics.py           → Graphics endpoints          → api-integration.md       → api/services/graphics_service.py
api/schemas/graphics.py           → Pydantic models             → api-integration.md       → api/models.py
api/services/graphics_service.py  → Business logic              → api-integration.md       → api/models.py, api/schemas/*
api/models.py                     → Database models              → data-models.md             → SQLAlchemy
dashboard/app/page.tsx            → Root application page      → frontend-components.md   ↔ dashboard/components/auth/*
dashboard/app/dashboard/page.tsx → Main dashboard page        → live-graphics-dashboard.md ↔ dashboard/components/graphics/*
dashboard/components/graphics/*   → Graphics management UI     → frontend-components.md   ↔ dashboard/hooks/use-graphics.ts
dashboard/hooks/use-*.tsx           → Custom React hooks          → frontend-components.md   ↔ dashboard/lib/api.ts
dashboard/lib/api.ts              → API client                   → api-integration.md       ↔ FastAPI backend
```

### Configuration Files
```
File                              → Purpose                           ↔ Related Docs                  ↔ Used By
──────────────────────────────────────────────────────────────────────────────────────────────────────────────
.env.local                        → Environment variables            → dashboard-operations.md      → Frontend/Backend
requirements.txt                   → Python dependencies               → api-deployment.md             → Backend
package.json                       → Node.js dependencies             → dashboard-deployment.md      → Frontend
config.yaml                       → Bot configuration                 → bot_current_features.md     → Bot core
dashboard/tsconfig.json            → TypeScript configuration         → developer-documentation.md → Frontend
dashboard/tailwind.config.js       → Tailwind CSS configuration        → frontend-components.md      → UI styling
```

## 🔐 Security Cross-References

### Authentication Flow
```
Component/Endpoint                → Security Mechanism          → Documentation              ↔ Configuration
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
LoginForm.tsx                    → Master password validation    → dashboard-security.md        ↔ .env.local (DASHBOARD_MASTER_PASSWORD)
POST /auth/login                  → JWT token generation          → dashboard-security.md        ↔ api/auth.py
API middleware                   → Bearer token validation       → api-backend-system.md         ↔ JWT_SECRET
localStorage (auth_token)        → Client-side token storage      → dashboard-security.md        ↔ use-auth.tsx
Protected routes                   → Authentication guard         → dashboard-operations.md      ↔ dashboard/components/auth/*
```

### Lock Management Security
```
Action                            → Security Check                  → Documentation              ↔ Database Table
───────────────────────────────────────────────────────────────────────────────────────────────────────
Canvas editor access               → Lock verification              → canvas-locking-management.md ↔ canvas_locks table
Graphic operations                → Lock ownership validation     → canvas-locking-management.md ↔ canvas_locks table
Lock expiration                    → Automatic cleanup              → canvas-locking-management.md ↔ canvas_locks table
Lock conflicts                     → Conflict resolution             → canvas-locking-management.md ↔ LockService
```

## 📊 API Endpoint Cross-References

### Complete API Mapping
```
HTTP Method + Path                  → Purpose                          → Documentation              ↔ Frontend Hook
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
POST /auth/login                    → Authenticate user                 → dashboard-security.md        ↔ use-auth.tsx
GET /api/v1/graphics                → List all graphics                → api-integration.md           ↔ use-graphics.ts
POST /api/v1/graphics               → Create new graphic               → api-integration.md           ↔ use-graphics.ts
GET /api/v1/graphics/{id}           → Get specific graphic             → api-integration.md           ↔ use-graphics.ts
PUT /api/v1/graphics/{id}           → Update existing graphic          → api-integration.md           ↔ use-graphics.ts
DELETE /api/v1/graphics/{id}        → Delete graphic                   → api-integration.md           ↔ use-graphics.ts
POST /api/v1/archive/{id}           → Archive graphic                  → graphics-management.md      ↔ use-graphics.ts
POST /api/v1/archive/{id}/restore   → Restore archived graphic          → graphics-management.md      ↔ use-graphics.ts
GET /api/v1/archive                 → List archived graphics           → graphics-management.md      ↔ use-graphics.ts
POST /api/v1/lock/{id}               → Acquire canvas lock              → canvas-locking-management.md ↔ use-locks.tsx
DELETE /api/v1/lock/{id}            → Release canvas lock              → canvas-locking-management.md ↔ use-locks.tsx
GET /api/v1/lock/status             → Get lock status                  → canvas-locking-management.md ↔ use-locks.tsx
GET /api/v1/graphics/{id}/view      → Public OBS browser source        → canvas-editor-workflow.md  ↵ OBS browser source
```

## 🎨 UI Component Cross-References

### Graphics Management Components
```
Component                          → Purpose                        → Documentation              ↔ State Management
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
GraphicsTab.tsx                   → Main graphics interface        → frontend-components.md      ↔ use-graphics.ts, use-locks.tsx
GraphicsTable.tsx                 → Graphics data table             → frontend-components.md      ↔ Local state
CreateGraphicDialog.tsx           → Graphic creation modal         → frontend-components.md      ↔ Form state
GraphicsTable/ActionButtons.tsx    → Table action buttons            → frontend-components.md      ↔ Parent callbacks
```

### Canvas Editor Components
```
Component                          → Purpose                        → Documentation              ↔ Lock Management
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
CanvasEditor.tsx                   → Full-screen canvas editor       → canvas-editor-architecture.md ↔ use-locks.tsx
LockBanner.tsx                    → Lock status display             → canvas-locking-management.md ↔ use-locks.tsx
CanvasTools/                      → Canvas editing tools           → canvas-editor-architecture.md ↔ CanvasEditor state
```

### Authentication Components
```
Component                          → Purpose                        → Documentation              ↔ Auth State
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
LoginForm.tsx                     → Login form                      → frontend-components.md      ↔ use-auth.tsx
AuthProvider.tsx                  → Authentication context         → frontend-components.md      ↔ localStorage, JWT
```

## 🔄 Workflow Cross-References

### Complete User Journey
```
User Action → Component → API → Service → Database → Result → Documentation
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Visit site → LoginForm.tsx → POST /auth/login → N/A → N/A → JWT token → dashboard-security.md
Dashboard → GraphicsTab.tsx → GET /api/v1/graphics → GraphicsService → graphics table → Graphics list → api-integration.md
Create → CreateGraphicDialog.tsx → POST /api/v1/graphics → GraphicsService → graphics table → New graphic → graphics-management.md
Edit → CanvasEditor.tsx → GET /api/v1/graphics/{id} → GraphicsService → graphics table → Graphic data → canvas-editor-workflow.md
Edit → CanvasEditor.tsx → POST /api/v1/lock/{id} → LockService → canvas_locks table → Lock acquired → canvas-locking-management.md
Edit → CanvasEditor.tsx → PUT /api/v1/graphics/{id} → GraphicsService → graphics table → Graphic saved → canvas-editor-workflow.md
Edit → CanvasEditor.tsx → DELETE /api/v1/lock/{id} → LockService → canvas_locks table → Lock released → canvas-locking-management.md
Delete → GraphicsTable.tsx → DELETE /api/v1/graphics/{id} → GraphicsService → graphics table → Graphic deleted → graphics-management.md
```

## 📈 Monitoring & Maintenance Cross-References

### Health Check References
```
Monitoring Point                     → Component/Endpoint          → Documentation              ↔ SOP
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
API Server Status                    → FastAPI health endpoint        → api-backend-system.md         → api-deployment.md
Database Connectivity               → SQLAlchemy connection check    → data-access-layer.md          → backup-recovery.md
Authentication Tokens                → JWT validation middleware      → dashboard-security.md        → dashboard-security.md
Canvas Lock Status                   → Lock expiration monitoring     → canvas-locking-management.md   → canvas-locking-management.md
Frontend Bundle Size                  → Next.js build metrics           → developer-documentation.md   → dashboard-deployment.md
```

## 🛠️ Development Workflow Cross-References

### Code Change Impact Matrix
```
Code Change Type                    → Files Affected                  → Documentation Updates        ↔ Testing Required
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
API Schema Change                    → api/schemas/*, api/routers/*    → api-integration.md, api-backend-system.md → Integration tests
Database Schema Change              → api/models.py, migrations/*    → data-models.md, data-access-layer.md → Migration tests
Frontend Component Change            → dashboard/components/*         → frontend-components.md      → Component tests
Authentication Change                → api/auth.py, auth/*             → dashboard-security.md, api-backend-system.md → Security tests
Canvas Editor Update                 → dashboard/canvas/*, hooks/*     → canvas-editor-architecture.md, canvas-editor-workflow.md → E2E tests
```

## 📞 Quick Reference Navigation

### For Developers
- **Architecture Overview**: Start with `live-graphics-dashboard.md`
- **API Development**: Reference `api-integration.md` and `api-backend-system.md`
- **Component Development**: Use `frontend-components.md`
- **Security Guidelines**: Follow `dashboard-security.md`

### For Operators
- **Daily Operations**: Follow `dashboard-operations.md`
- **Graphics Management**: Use `graphics-management.md`
- **Canvas Editing**: Follow `canvas-editor-workflow.md`
- **Lock Management**: Use `canvas-locking-management.md`
- **Security**: Follow `dashboard-security.md`

### For Administrators
- **Deployment**: Follow `dashboard-deployment.md` and `api-deployment.md`
- **Troubleshooting**: Use `troubleshooting.md`
- **Backup & Recovery**: Follow `backup-recovery.md`
- **System Maintenance**: Follow all relevant SOPs

---

**Maintained by**: Guardian Angel League Development  
**Generated**: 2025-10-13  
**Version**: 2.0  
**Status**: Complete cross-reference mapping - All system interconnections documented
