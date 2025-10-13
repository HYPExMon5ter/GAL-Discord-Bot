---
id: agents.manifest
version: 1.0
last_updated: 2025-10-13
tags: [factory, droids, documentation, dashboard]
---

# 🤖 Guardian Angel League — FactoryAI Agents Manifest

This file defines all **Custom Droids** and their relationships for the Guardian Angel League Discord Bot and Live Graphics Dashboard ecosystem.

## 🎯 Available Droids

| Category | Droid ID | Description | Status |
|-----------|-----------|-------------|---------|
| **Documentation** | **Documentation Maintainer** (`droid.documentation_maintainer`) | Updates `.agent/` docs on commit | 🟡 Planned |
| **QA / Auditing** | **System Auditor** (`droid.system_auditor`) | Weekly drift audit | 🟡 Planned |
| **Architecture** | **Refactor Coordinator** (`droid.refactor_coordinator`) | Oversees migrations & refactors | 🟡 Planned |
| **Frontend** | **Dashboard Designer** (`droid.dashboard_designer`) | Generates and refines shadcn/Tailwind UI | 🟡 Planned |
| **Backend** | **API Architect** (`droid.api_architect`) | Maintains FastAPI endpoints & schema | 🟡 Planned |
| **UX** | **UX Copywriter** (`droid.ux_copywriter`) | Reviews and improves UI/Embed copy | 🟡 Planned |
| **QA / Testing** | **Integration Tester** (`droid.integration_tester`) | Runs integration and sanity checks | 🟡 Planned |
| **Release** | **Release Drafter** (`droid.release_drafter`) | Generates changelogs and draft releases | 🟡 Planned |
| **Docs** | **Doc Rebuilder** (`droid.doc_rebuilder`) | Rebuilds missing documentation files | 🟡 Planned |

## 🧱 File Context Summary

### Core System Files
| Path | Used By | Purpose |
|------|----------|----------|
| `.agent/system/*` | Docs, Auditor, Refactor | Architecture and data flow |
| `.agent/sops/*` | Maintainer, Drafter | Operational procedures |
| `.agent/tasks/*` | Maintainer, Drafter | PRDs and logs |
| `scripts/*` | Maintainer, Auditor | Utility scripts |

### Dashboard System Files
| Path | Used By | Purpose |
|------|----------|----------|
| `dashboard/src/*` | Dashboard Designer, Copywriter | Frontend design and UX text |
| `api/*` | API Architect | Endpoint validation |
| `tests/*` | Integration Tester | QA and regression coverage |

## ⚙️ Shared Workflows

### Post-commit Workflow
- **Trigger**: Git commit to main branch
- **Action**: Documentation Maintainer updates `.agent` docs
- **Scope**: System changes, API updates, component changes

### Weekly Audit Workflow  
- **Trigger**: Scheduled (weekly)
- **Action**: System Auditor checks `.agent` drift
- **Output**: Log-only audit report

### Manual Refactor Workflow
- **Trigger**: Major architecture changes
- **Action**: Refactor Coordinator oversees migration
- **Scope**: Database schema, API contracts, component architecture

### UI Enhancement Workflow
- **Trigger**: New features or design changes
- **Action**: Dashboard Designer generates/updates components
- **Scope**: React components, Tailwind styling, UX improvements

### API Development Workflow
- **Trigger**: Backend changes
- **Action**: API Architect validates endpoints and schemas
- **Scope**: FastAPI routes, Pydantic models, database operations

### Release Workflow
- **Trigger**: Version bump or deployment
- **Action**: Release Drafter compiles changelogs
- **Scope**: Tag creation, release notes, deployment docs

## 🎮 Usage Examples

### Documentation Maintenance
```bash
droid run documentation_maintainer
```
Automatically updates `.agent/` docs based on recent code changes.

### System Audit
```bash
droid run system_auditor
```
Generates weekly audit report of documentation drift.

### Dashboard Component Creation
```bash
droid run dashboard_designer --component=GraphicsTable --style=shadcn
```
Creates new shadcn-styled component for graphics management.

### API Endpoint Generation
```bash
droid run api_architect --endpoint=/graphics --method=POST
```
Generates FastAPI endpoint with proper schema and documentation.

### Documentation Rebuild
```bash
droid run doc_rebuilder
```
Rebuilds missing documentation files based on audit findings.

## 🔧 Configuration

### Droid Locations
- **Project**: `C:\Users\blake\PycharmProjects\New-GAL-Discord-Bot\.factory\droids`
- **Personal**: `C:\Users\blake\.factory\droids`

### Environment Setup
```bash
# Factory configuration directory
mkdir -p .factory/droids

# Personal droids directory  
mkdir -p ~/.factory/droids
```

### Droid Registration
Droids are automatically registered when created. Manifest file tracks all available droids and their relationships.

## 📋 Development Guidelines

### Creating New Droids
1. Use `GenerateDroid` command to create droid configuration
2. Define clear scope and responsibilities
3. Include comprehensive error handling
4. Add proper logging and status reporting
5. Test with sample data before deployment

### Droid Integration
- All droids should follow consistent naming conventions
- Use shared utilities and common patterns
- Include proper error handling and validation
- Provide clear status reporting and logging

### Maintenance
- Regular droid updates based on system changes
- Weekly audit of droid performance and accuracy
- User feedback collection and improvement cycles

## 🚀 Current Status

**Last Updated**: 2025-10-13  
**Total Droids**: 9 planned  
**Active Droids**: 0 (configuration phase)  
**System Health**: 🟡 Ready for Implementation  

## 📞 Support

**Repository**: Guardian Angel League Discord Bot  
**Development Team**: GAL Development Team  
**Framework**: FactoryAI Custom Droids  

---

**Maintained by**: Guardian Angel League Development  
**Generated**: 2025-10-13  
**Status**: Configuration Complete - Ready for Droid Implementation
