---
id: system.cross_references
version: 1.0
last_updated: 2025-10-11
tags: [cross-references, integration, system-links, documentation-map]
---

# System Cross-References

## Overview
This document provides comprehensive cross-references between all system components, documentation, and operational procedures for the Guardian Angel League unified data flow architecture.

## Architecture Cross-References

### Core System Components

#### Data Flow Connections
```
Discord Bot ↔ Event System ↔ API Backend ↔ Data Access Layer ↔ Database
     ↓              ↓              ↓                ↓              ↓
 Commands → Event Bus → FastAPI → Repositories → PostgreSQL
 Views   → Handlers  → Routers → Cache Manager  → Redis
 Config  → Publishers → Services → Connection    → Sheets API
```

#### Module Dependencies
```
api/ (FastAPI Application)
├── Depends on: core/data_access/, core/models/, core/events/
├── Provides: REST endpoints, WebSocket connections, JWT auth
└── Referenced by: Dashboard frontend, External API consumers

core/data_access/ (DAL)
├── Depends on: core/models/, PostgreSQL, Redis, Google Sheets API
├── Provides: Repository pattern, caching, connection pooling
└── Referenced by: api/, core/events/, Legacy bot components

core/events/ (Event System)
├── Depends on: core/models/, core/data_access/
├── Provides: Event bus, handlers, subscribers
└── Referenced by: api/, Discord bot, Dashboard

core/models/ (Data Models)
├── Depends on: None (base layer)
├── Provides: Entity definitions, validation, business logic
└── Referenced by: All other components
```

## Documentation Cross-References

### System Documentation Map

#### Architecture Documentation
- **[Architecture Overview](./architecture.md)** - System architecture and data flow
  - References: All component documentation
  - Referenced by: Onboarding materials, system design docs

#### Component Documentation
- **[API Backend System](./api-backend-system.md)** - FastAPI application details
  - References: Data Models, Data Access Layer, Authentication SOP
  - Referenced by: API consumers, Dashboard developers

- **[Data Access Layer](./data-access-layer.md)** - Repository pattern and caching
  - References: Data Models, Database schema, Migration SOP
  - Referenced by: API layer, Event system, Developers

- **[Event System](./event-system.md)** - Event-driven architecture
  - References: Data Models, API WebSockets, Monitoring SOP
  - Referenced by: Real-time features, System integrators

- **[Data Models](./data-models.md)** - Entity definitions and validation
  - References: Database schema, API schemas, Business rules
  - Referenced by: All components, Developers, API consumers

#### Frontend System Documentation (NEW)
- **[Frontend Components Documentation](./frontend-components.md)** - React components and hooks
  - References: API Integration docs, Dashboard Operations SOP
  - Referenced by: Frontend developers, Dashboard operators

- **[API Integration Documentation](./api-integration.md)** - Frontend-backend API contracts
  - References: API Backend System, Frontend Components docs
  - Referenced by: Frontend developers, API consumers

- **[Developer Documentation](./developer-documentation.md)** - Development guidelines and best practices
  - References: All component docs, Dashboard Deployment SOP
  - Referenced by: All developers, New team members

#### Live Graphics Dashboard Documentation
- **[Live Graphics Dashboard System](./live-graphics-dashboard.md)** - Dashboard architecture and implementation
  - References: Frontend components, API integration, Dashboard deployment SOP
  - Referenced by: Dashboard operators, Frontend developers, System administrators

- **[Frontend Components Documentation](./frontend-components.md)** - React component architecture
  - References: Developer documentation, API integration, Dashboard operations SOP
  - Referenced by: Frontend developers, UI/UX team, Dashboard operators

- **[API Integration Documentation](./api-integration.md)** - Frontend-backend integration patterns
  - References: API backend system, Frontend components, WebSocket integration
  - Referenced by: Frontend developers, API consumers, Integration testers

- **[Developer Documentation](./developer-documentation.md)** - Development workflows and guidelines
  - References: Frontend components, API integration, System architecture
  - Referenced by: All developers, Code reviewers, Onboarding materials

#### Legacy Documentation
- **[Core Modules](./core-modules.md)** - Legacy bot components
  - References: Integration modules, Helper modules
  - Referenced by: Bot maintenance, Legacy development

- **[Integration Modules](./integration-modules.md)** - External service integrations
  - References: Google Sheets API, Riot API, DAL
  - Referenced by: Integration developers, System administrators

- **[Helper Modules](./helper-modules.md)** - Utility functions and helpers
  - References: Core modules, Error handling
  - Referenced by: Bot developers, System maintainers

### Operations Documentation Cross-References

#### Standard Operating Procedures (SOPs)
- **[Deployment SOP](../sops/deployment.md)** - Bot deployment procedures
  - References: Architecture overview, Dependencies documentation
  - Referenced by: System administrators, DevOps team

- **[API Deployment SOP](../sops/api-deployment.md)** - API backend deployment
  - References: API backend system docs, Security SOP
  - Referenced by: API administrators, Deployment team

- **[Event System Monitoring SOP](../sops/event-system-monitoring.md)** - Event system monitoring
  - References: Event system docs, Troubleshooting SOP

#### Dashboard Operations SOPs (NEW)
- **[Dashboard Operations SOP](../sops/dashboard-operations.md)** - Live Graphics Dashboard operations
  - References: Live Graphics Dashboard docs, Frontend components docs
  - Referenced by: Dashboard operators, Content creators

- **[Graphics Management SOP](../sops/graphics-management.md)** - Graphics creation and template management
  - References: Dashboard Operations SOP, Canvas Locking SOP
  - Referenced by: Content managers, Graphic designers

- **[Dashboard Deployment SOP](../sops/dashboard-deployment.md)** - Frontend deployment and CI/CD
  - References: Frontend components docs, API Deployment SOP
  - Referenced by: Frontend developers, DevOps team

- **[Canvas Locking Management SOP](../sops/canvas-locking-management.md)** - Canvas lock system administration
  - References: Dashboard Operations SOP, API Integration docs
  - Referenced by: System administrators, Dashboard operators
- **[Route-Based Canvas Operations SOP](../sops/route-based-canvas-operations.md)** - Route-based canvas editor workflows
  - References: Canvas Editor Architecture, Dashboard Operations SOP, Graphics Management SOP
  - Referenced by: Dashboard operators, Graphics team, Frontend developers
- **[Canvas Migration Procedures SOP](../sops/canvas-migration-procedures.md)** - Modal-to-route migration procedures
  - References: Canvas Editor Architecture, Emergency Rollback SOP, Dashboard Deployment SOP
  - Referenced by: System administrators, Migration team, Frontend developers

- **[Dashboard Security SOP](../sops/dashboard-security.md)** - Dashboard authentication and access control
  - References: Security SOP, Dashboard Operations SOP
  - Referenced by: Security administrators, System administrators
  - Referenced by: System administrators, Monitoring team

- **[DAL Migration SOP](../sops/dal-migration.md)** - Data Access Layer migration
  - References: Data Access Layer docs, Architecture overview
  - Referenced by: Migration team, System administrators

- **[Security Management SOP](../sops/security.md)** - Security procedures
  - References: All component documentation, API deployment
  - Referenced by: Security team, System administrators

- **[Troubleshooting SOP](../sops/troubleshooting.md)** - System troubleshooting
  - References: All component documentation, Monitoring SOP
  - Referenced by: Support team, System administrators

- **[Backup and Recovery SOP](../sops/backup-recovery.md)** - System backup and disaster recovery
  - References: Data Access Layer, Security SOP, Deployment SOP
  - Referenced by: System administrators, DevOps team

- **[Performance Monitoring SOP](../sops/performance-monitoring.md)** - System performance monitoring and metrics
  - References: API Backend System, Event System, Troubleshooting SOP
  - Referenced by: Operations team, System administrators

- **[Team Onboarding SOP](../sops/team-onboarding.md)** - Team member onboarding and access management
  - References: Security SOP, Architecture Overview, Deployment SOP
  - Referenced by: Team leads, System administrators, HR team

- **[Emergency Rollback SOP](../sops/emergency-rollback.md)** - Emergency deployment rollback procedures
  - References: API Deployment SOP, Deployment SOP, Troubleshooting SOP
  - Referenced by: DevOps team, System administrators, On-call engineers

#### Live Graphics Dashboard SOPs
- **[Dashboard Operations SOP](../sops/dashboard-operations.md)** - Dashboard graphic management and operations
  - References: Frontend components, Canvas locking management SOP, Dashboard security SOP
  - Referenced by: Dashboard operators, Graphics team, System administrators

- **[Graphics Management SOP](../sops/graphics-management.md)** - Template and graphic lifecycle management
  - References: Dashboard operations SOP, Frontend components, Developer documentation
  - Referenced by: Graphics team, Template developers, Quality assurance

- **[Dashboard Deployment SOP](../sops/dashboard-deployment.md)** - Frontend build and deployment procedures
  - References: API deployment SOP, Frontend components, Developer documentation
  - Referenced by: DevOps team, Frontend developers, System administrators

- **[Canvas Locking Management SOP](../sops/canvas-locking-management.md)** - Canvas lock conflict resolution
  - References: Dashboard operations SOP, API integration, WebSocket documentation
  - Referenced by: Dashboard operators, Graphics team, System administrators

- **[Dashboard Security SOP](../sops/dashboard-security.md)** - Dashboard authentication and session management
  - References: Security SOP, API integration, Frontend components
  - Referenced by: Dashboard operators, Security team, System administrators

## Integration Points

### API Integration Matrix

| API Endpoint | Data Model | Repository | Event Type | Documentation |
|--------------|------------|------------|------------|---------------|
| `GET /tournaments/` | Tournament | TournamentRepository | TOURNAMENT_LISTED | [API Backend](./api-backend-system.md) |
| `POST /tournaments/` | Tournament | TournamentRepository | TOURNAMENT_CREATED | [API Backend](./api-backend-system.md) |
| `PUT /tournaments/{id}` | Tournament | TournamentRepository | TOURNAMENT_UPDATED | [API Backend](./api-backend-system.md) |
| `GET /users/` | User | UserRepository | USER_LISTED | [API Backend](./api-backend-system.md) |
| `POST /users/` | User | UserRepository | USER_CREATED | [API Backend](./api-backend-system.md) |
| `GET /config/` | Configuration | ConfigurationRepository | CONFIG_ACCESSED | [API Backend](./api-backend-system.md) |
| `WS /ws/events` | Multiple | Various | ALL_EVENTS | [Event System](./event-system.md) |

### Event Handler Mapping

| Event Type | Handler | Repository | WebSocket Update | Documentation |
|------------|---------|------------|------------------|---------------|
| TOURNAMENT_CREATED | TournamentEventHandler | TournamentRepository | tournament_created | [Event System](./event-system.md) |
| TOURNAMENT_UPDATED | TournamentEventHandler | TournamentRepository | tournament_updated | [Event System](./event-system.md) |
| USER_REGISTERED | UserEventHandler | UserRepository | user_registered | [Event System](./event-system.md) |
| CONFIGURATION_UPDATED | ConfigEventHandler | ConfigurationRepository | config_updated | [Event System](./event-system.md) |
| ERROR_OCCURRED | ErrorEventHandler | AuditRepository | system_alert | [Event System](./event-system.md) |

### Database Schema Cross-References

| Table | Model | Repository | API Endpoints | Events | Documentation |
|-------|-------|------------|---------------|--------|---------------|
| tournaments | Tournament | TournamentRepository | /tournaments/* | TOURNAMENT_* | [Data Models](./data-models.md) |
| users | User | UserRepository | /users/* | USER_* | [Data Models](./data-models.md) |
| tournament_registrations | TournamentRegistration | TournamentRepository | /tournaments/{id}/registrations | USER_REGISTERED | [Data Models](./data-models.md) |
| configurations | SystemConfig | ConfigurationRepository | /config/* | CONFIG_* | [Data Models](./data-models.md) |
| audit_log | AuditEntry | AuditRepository | /admin/audit | ALL_EVENTS | [Data Models](./data-models.md) |

## Configuration Cross-References

### Environment Variables Mapping

| Variable | Component | Default Value | Documentation | Security |
|----------|-----------|---------------|---------------|----------|
| `DASHBOARD_MASTER_PASSWORD` | API Backend | Required | [API Deployment](../sops/api-deployment.md) | High |
| `DATABASE_URL` | DAL, API | SQLite | [DAL Migration](../sops/dal-migration.md) | High |
| `REDIS_URL` | DAL, Cache | localhost:6379 | [Data Access Layer](./data-access-layer.md) | Medium |
| `DISCORD_BOT_TOKEN` | Discord Bot | Required | [Security SOP](../sops/security.md) | High |
| `GOOGLE_SHEETS_CREDENTIALS` | Sheets Integration | Required | [Integration Modules](./integration-modules.md) | High |
| `RIOT_API_KEY` | Riot API Integration | Required | [Integration Modules](./integration-modules.md) | Medium |

### Configuration File References

| File | Component | Purpose | Documentation |
|------|-----------|---------|---------------|
| `config.yaml` | Bot Core | Main bot configuration | [Configuration Management](./helper-modules.md) |
| `.env.local` | API, DAL | Environment variables | [API Deployment](../sops/api-deployment.md) |
| `alembic.ini` | Database | Migration configuration | [DAL Migration](../sops/dal-migration.md) |
| `requirements.txt` | All | Python dependencies | [Dependencies](./dependencies.md) |

## Security Cross-References

### Authentication and Authorization

| Component | Method | Documentation | SOP |
|-----------|--------|---------------|-----|
| Discord Bot | OAuth2 Bot Token | [Security SOP](../sops/security.md) | [Security Management](../sops/security.md) |
| API Backend | JWT + Master Password | [API Backend](./api-backend-system.md) | [API Deployment](../sops/api-deployment.md) |
| Google Sheets | Service Account | [Integration Modules](./integration-modules.md) | [Security SOP](../sops/security.md) |
| Database | PostgreSQL Auth | [Data Access Layer](./data-access-layer.md) | [Security SOP](../sops/security.md) |
| Redis | Redis Auth | [Data Access Layer](./data-access-layer.md) | [API Deployment](../sops/api-deployment.md) |

### Data Protection

| Data Type | Storage | Encryption | Documentation |
|-----------|---------|------------|---------------|
| User Data | PostgreSQL | TLS + At-rest | [Security SOP](../sops/security.md) |
| Configuration | PostgreSQL + Files | TLS + At-rest | [Security SOP](../sops/security.md) |
| Cache | Redis | TLS + At-rest | [Data Access Layer](./data-access-layer.md) |
| Logs | Files | Rotation | [Security SOP](../sops/security.md) |
| Backups | Files | Encryption | [Security SOP](../sops/security.md) |

## Monitoring and Observability

### Monitoring Cross-References

| Metric | Component | Documentation | SOP |
|--------|-----------|---------------|-----|
| API Response Time | API Backend | [API Backend](./api-backend-system.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Event Queue Size | Event System | [Event System](./event-system.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Database Query Time | DAL | [Data Access Layer](./data-access-layer.md) | [Troubleshooting](../sops/troubleshooting.md) |
| Cache Hit Rate | DAL | [Data Access Layer](./data-access-layer.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Bot Uptime | Discord Bot | [Core Modules](./core-modules.md) | [Troubleshooting](../sops/troubleshooting.md) |

### Logging Cross-References

| Log Type | Component | Location | Documentation |
|-----------|-----------|----------|---------------|
| API Requests | API Backend | /var/log/gal-api/ | [API Deployment](../sops/api-deployment.md) |
| Event Processing | Event System | /var/log/gal-api/events.log | [Event Monitoring](../sops/event-system-monitoring.md) |
| Bot Commands | Discord Bot | gal_bot.log | [Core Modules](./core-modules.md) |
| Database Queries | DAL | /var/log/gal-api/dal.log | [Data Access Layer](./data-access-layer.md) |
| System Errors | All | /var/log/gal-api/error.log | [Troubleshooting](../sops/troubleshooting.md) |

## Development Cross-References

### Code Organization

| Directory | Purpose | Documentation | Related |
|-----------|---------|---------------|---------|
| `api/` | FastAPI application | [API Backend](./api-backend-system.md) | `core/`, `requirements.txt` |
| `core/data_access/` | Data Access Layer | [Data Access Layer](./data-access-layer.md) | `core/models/`, `api/` |
| `core/events/` | Event System | [Event System](./event-system.md) | `core/models/`, `api/` |
| `core/models/` | Data Models | [Data Models](./data-models.md) | All components |
| `integrations/` | External APIs | [Integration Modules](./integration-modules.md) | `core/`, Google Sheets API |
| `helpers/` | Utility functions | [Helper Modules](./helper-modules.md) | `core/` |
| `scripts/` | Utility scripts | [Scripts](./scripts.md) | All components |

### Testing Cross-References

| Test Type | Component | Documentation | Tools |
|-----------|-----------|---------------|-------|
| Unit Tests | All | Component docs | pytest |
| Integration Tests | API, DAL | [API Backend](./api-backend-system.md) | pytest, test client |
| Load Tests | API | [API Deployment](../sops/api-deployment.md) | aiohttp, locust |
| Migration Tests | DAL | [DAL Migration](../sops/dal-migration.md) | pytest |
| Event Tests | Event System | [Event System](./event-system.md) | pytest |

## Deployment and Operations

### Deployment Dependencies

| Component | Dependencies | Documentation | Deployment Order |
|-----------|--------------|---------------|------------------|
| Database | PostgreSQL, Redis | [DAL Migration](../sops/dal-migration.md) | 1 |
| API Backend | Database, Models | [API Deployment](../sops/api-deployment.md) | 2 |
| Discord Bot | Database, API | [Deployment](../sops/deployment.md) | 3 |
| Monitoring | All components | [Event Monitoring](../sops/event-system-monitoring.md) | 4 |

### Service Dependencies

```
System Startup Order:
1. PostgreSQL Database
2. Redis Cache
3. API Backend (FastAPI)
4. Event System (integrated with API)
5. Discord Bot
6. Monitoring Services
7. Dashboard (if applicable)
```

## Migration Cross-References

### Legacy to New System

| Legacy Component | New Component | Migration Path | Documentation |
|------------------|---------------|----------------|---------------|
| `core/persistence.py` | `core/data_access/` | Gradual via LegacyAdapter | [DAL Migration](../sops/dal-migration.md) |
| Direct DB access | Repository Pattern | Phase migration | [Data Access Layer](./data-access-layer.md) |
| Polling updates | Event System | Event-driven migration | [Event System](./event-system.md) |
| Manual configuration | Dynamic Config | Configuration migration | [Data Models](./data-models.md) |

### Data Migration References

| Data Type | Source | Destination | Documentation |
|-----------|--------|-------------|---------------|
| Tournament Data | Old tables | New schema | [DAL Migration](../sops/dal-migration.md) |
| User Data | Old tables | New schema | [DAL Migration](../sops/dal-migration.md) |
| Configuration | YAML files | Database | [Data Models](./data-models.md) |
| Audit Logs | Files | Database table | [Data Models](./data-models.md) |

## Troubleshooting Cross-References

### Issue Resolution Matrix

| Symptom | Component | Documentation | SOP |
|---------|-----------|---------------|-----|
| API not responding | API Backend | [API Backend](./api-backend-system.md) | [Troubleshooting](../sops/troubleshooting.md) |
| Events not processing | Event System | [Event System](./event-system.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Database errors | DAL | [Data Access Layer](./data-access-layer.md) | [Troubleshooting](../sops/troubleshooting.md) |
| Bot commands failing | Discord Bot | [Core Modules](./core-modules.md) | [Troubleshooting](../sops/troubleshooting.md) |
| Configuration issues | All | [Helper Modules](./helper-modules.md) | [Troubleshooting](../sops/troubleshooting.md) |

### Emergency Procedures

| Emergency | Affected Components | Rollback Documentation | SOP |
|-----------|-------------------|----------------------|-----|
| Database failure | DAL, API, Bot | [DAL Migration](../sops/dal-migration.md) | [Troubleshooting](../sops/troubleshooting.md) |
| API backend down | Dashboard, External apps | [API Deployment](../sops/api-deployment.md) | [Troubleshooting](../sops/troubleshooting.md) |
| Event system failure | Real-time features | [Event System](./event-system.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Security breach | All components | [Security SOP](../sops/security.md) | [Security Management](../sops/security.md) |

## API Reference Cross-References

### Endpoints by Category

#### Tournament Management
- `GET /tournaments/` - List tournaments → [API Backend](./api-backend-system.md)
- `POST /tournaments/` - Create tournament → [API Backend](./api-backend-system.md)
- `GET /tournaments/{id}` - Get tournament → [API Backend](./api-backend-system.md)
- `PUT /tournaments/{id}` - Update tournament → [API Backend](./api-backend-system.md)
- `DELETE /tournaments/{id}` - Delete tournament → [API Backend](./api-backend-system.md)

#### User Management
- `GET /users/` - List users → [API Backend](./api-backend-system.md)
- `POST /users/` - Create user → [API Backend](./api-backend-system.md)
- `GET /users/{id}` - Get user → [API Backend](./api-backend-system.md)
- `PUT /users/{id}` - Update user → [API Backend](./api-backend-system.md)

#### Configuration
- `GET /config/` - Get configuration → [API Backend](./api-backend-system.md)
- `PUT /config/` - Update configuration → [API Backend](./api-backend-system.md)
- `POST /config/reload` - Reload configuration → [API Backend](./api-backend-system.md)

#### Real-time Updates
- `WS /ws/events` - WebSocket events → [Event System](./event-system.md)
- `GET /health/events` - Event system health → [Event Monitoring](../sops/event-system-monitoring.md)

## Data Model Cross-References

### Entity Relationships

```
Tournament (1) ←→ (N) TournamentRegistration ←→ (1) User
Tournament (1) ←→ (N) TournamentMatch
User (1) ←→ (N) UserStats
Guild (1) ←→ (N) User
Configuration (1) ←→ (N) FeatureFlag
```

### Field Mappings

| Entity | Primary Key | Foreign Keys | Indexes | Documentation |
|--------|-------------|--------------|---------|---------------|
| Tournament | id | organizer_id, guild_id | name, status, start_date | [Data Models](./data-models.md) |
| User | discord_id | guild_ids | username, status, roles | [Data Models](./data-models.md) |
| TournamentRegistration | composite (tournament_id, user_id) | tournament_id, user_id | registration_date, status | [Data Models](./data-models.md) |
| Configuration | key | - | category, environment | [Data Models](./data-models.md) |

## Integration Cross-References

### External API Integration

| Service | Purpose | Component | Documentation |
|---------|---------|-----------|---------------|
| Discord API | Bot functionality | Discord Bot | [Core Modules](./core-modules.md) |
| Google Sheets API | External data view | Sheets Repository | [Integration Modules](./integration-modules.md) |
| Riot Games API | Player verification | IGN Verification | [Integration Modules](./integration-modules.md) |
| PostgreSQL | Primary database | DAL | [Data Access Layer](./data-access-layer.md) |
| Redis | Caching layer | Cache Manager | [Data Access Layer](./data-access-layer.md) |

### Third-Party Dependencies

| Dependency | Version | Component | Documentation |
|------------|---------|-----------|---------------|
| FastAPI | Latest | API Backend | [API Backend](./api-backend-system.md) |
| discord.py | Latest | Discord Bot | [Core Modules](./core-modules.md) |
| SQLAlchemy | Latest | DAL | [Data Access Layer](./data-access-layer.md) |
| Pydantic | Latest | API, Models | [Data Models](./data-models.md) |
| asyncpg | Latest | DAL | [Data Access Layer](./data-access-layer.md) |
| redis | Latest | Cache Manager | [Data Access Layer](./data-access-layer.md) |

## Quick Reference Index

### By Functionality

| Function | Primary Documentation | Secondary Documentation |
|----------|----------------------|------------------------|
| Tournament Management | [API Backend](./api-backend-system.md) | [Data Models](./data-models.md) |
| User Management | [API Backend](./api-backend-system.md) | [Data Models](./data-models.md) |
| Real-time Updates | [Event System](./event-system.md) | [API Backend](./api-backend-system.md) |
| Data Persistence | [Data Access Layer](./data-access-layer.md) | [Data Models](./data-models.md) |
| Authentication | [API Backend](./api-backend-system.md) | [Security SOP](../sops/security.md) |
| Configuration | [Helper Modules](./helper-modules.md) | [Data Models](./data-models.md) |
| Monitoring | [Event Monitoring](../sops/event-system-monitoring.md) | [Troubleshooting](../sops/troubleshooting.md) |

### By Role

| Role | Primary Documentation | Quick Start |
|------|----------------------|------------|
| Developer | [Architecture Overview](./architecture.md) | [Data Models](./data-models.md) |
| System Administrator | [Deployment SOP](../sops/deployment.md) | [API Deployment](../sops/api-deployment.md) |
| DevOps Engineer | [API Deployment](../sops/api-deployment.md) | [Event Monitoring](../sops/event-system-monitoring.md) |
| Security Engineer | [Security SOP](../sops/security.md) | [API Backend](./api-backend-system.md) |
| Support Engineer | [Troubleshooting SOP](../sops/troubleshooting.md) | [Event Monitoring](../sops/event-system-monitoring.md) |

---

**Cross-Reference Status**: ✅ Complete  
**Coverage**: All system components documented with interconnections  
**Navigation**: Clear mapping between documentation, code, and operations  
**Maintenance**: Update process defined for ongoing changes  
**Accessibility**: Multiple access methods for different user roles  
**Last Updated**: 2025-10-12 (Added Route-Based Canvas Operations & Migration SOPs)
