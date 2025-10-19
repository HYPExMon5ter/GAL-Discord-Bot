---
id: agents.manifest
version: 2.0
last_updated: 2025-01-18
tags: [factory, droids, documentation, dashboard, orchestration]
---

# 🤖 Guardian Angel League — FactoryAI Agents Manifest

This file defines all **Custom Droids** and their relationships for the Guardian Angel League Discord Bot and Live Graphics Dashboard ecosystem.

## 🎯 Available Droids

| Category | Droid ID | Description | Status |
|-----------|-----------|-------------|---------|
| **Orchestration** | **Context Manager** (`context-manager`) | Intelligent context assembly and droid coordination | 🟢 Active |
| **Documentation** | **Documentation Manager** (`documentation-manager`) | Complete documentation lifecycle management | 🟢 Active |
| **QA / Auditing** | **System Auditor** (`system-auditor`) | Weekly drift audit and analysis | 🟡 Planned |
| **Architecture** | **Refactor Coordinator** (`refactor-coordinator`) | Oversees migrations & refactors | 🟡 Planned |
| **Architecture** | **Path Refactor Coordinator** (`path-refactor-coordinator`) | Specialized path and file system refactoring | 🟡 Planned |
| **Frontend** | **Dashboard Designer** (`dashboard-designer`) | Generates and refines shadcn/Tailwind UI | 🟡 Planned |
| **Backend** | **API Architect** (`api-architect`) | Maintains FastAPI endpoints & schema | 🟡 Planned |
| **Database** | **Database Migration Specialist** (`database-migration-specialist`) | Database schema and migration management | 🟡 Planned |
| **UX** | **UX Copywriter** (`ux-copywriter`) | Reviews and improves UI/Embed copy | 🟡 Planned |
| **QA / Testing** | **Integration Tester** (`integration-tester`) | Runs integration and sanity checks | 🟡 Planned |
| **Performance** | **Performance Auditor** (`performance-auditor`) | System performance analysis and optimization | 🟡 Planned |
| **Release** | **Release Drafter** (`release-drafter`) | Generates changelogs and draft releases | 🟡 Planned |

## 🧠 Context Manager - System Orchestrator

The **Context Manager** is the intelligent orchestrator that analyzes requests and provides optimized context packages to other droids.

### Capabilities
- **Request Analysis**: Understands complexity and requirements
- **Droid Selection**: Chooses optimal droids for each task
- **Context Assembly**: Builds targeted information packages
- **Multi-Droid Coordination**: Orchestrates complex workflows
- **Performance Optimization**: Learns and improves over time

### Usage Examples
```bash
# Simple single-droid task
droid start context-manager --request="Update API documentation for new endpoints"

# Complex multi-droid coordination
droid start context-manager --request="Implement real-time standings system"
```

## 📚 Documentation Manager - Lifecycle Management

The **Documentation Manager** handles the complete documentation lifecycle, replacing three separate documentation droids with one comprehensive system.

### Capabilities
- **Audit Detection**: Identifies documentation gaps and issues
- **Content Generation**: Creates comprehensive documentation
- **Draft Management**: Handles draft creation and promotion
- **Cross-Reference Maintenance**: Keeps all links current
- **Context Snapshots**: Creates system state snapshots
- **Secure Committing**: Safely commits changes

### Operations
```bash
# Full documentation lifecycle
droid start documentation-manager

# Audit and fix issues
droid start documentation-manager --audit-and-fix

# Create missing documentation
droid start documentation-manager --generate-missing

# Promote drafts to production
droid start documentation-manager --promote-drafts

# Create context snapshot
droid start documentation-manager --snapshot

# Commit documentation changes
droid start documentation-manager --commit
```

## 🧱 File Context Summary

### Core System Files
| Path | Used By | Purpose |
|------|----------|----------|
| `.agent/system/*` | Documentation Manager, System Auditor | Architecture and data flow |
| `.agent/sops/*` | Documentation Manager | Operational procedures |
| `.agent/tasks/*` | Documentation Manager, Release Drafter | PRDs and logs |
| `.agent/drafts/*` | Documentation Manager | Draft documentation workflow |
| `scripts/*` | Documentation Manager, System Auditor | Utility scripts |

### Dashboard System Files
| Path | Used By | Purpose |
|------|----------|----------|
| `dashboard/src/*` | Dashboard Designer, UX Copywriter | Frontend design and UX text |
| `api/*` | API Architect, Database Migration Specialist | Endpoint validation and schemas |
| `tests/*` | Integration Tester, Performance Auditor | QA and regression coverage |

### Development Files
| Path | Used By | Purpose |
|------|----------|----------|
| `core/*` | System Auditor, Refactor Coordinators | Core system architecture |
| `integrations/*` | Database Migration Specialist | External integrations |
| `utils/*` | All droids (as needed) | Shared utilities |

## ⚙️ Shared Workflows

### Orchestration Workflow
- **Trigger**: Any user request or automated task
- **Action**: Context Manager analyzes and dispatches appropriate droids
- **Scope**: System-wide coordination and optimization

### Documentation Lifecycle
- **Trigger**: Code changes, manual requests, scheduled audits
- **Action**: Documentation Manager handles complete lifecycle
- **Scope**: All documentation maintenance and creation

### System Audit Workflow  
- **Trigger**: Scheduled (weekly) or manual
- **Action**: System Auditor checks documentation and code drift
- **Output**: Comprehensive audit report and recommendations

### Refactor Workflow
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

## 🎮 Enhanced Usage Examples

### Context Manager Operations
```bash
# Intelligent droid dispatch
droid start context-manager --request="Add user authentication to dashboard"

# Multi-droid coordination
droid start context-manager --request="Migrate database from SQLite to PostgreSQL"

# Performance optimization
droid start context-manager --optimize-context --droid=api-architect
```

### Documentation Manager Operations
```bash
# Complete documentation overhaul
droid start documentation-manager --complete-overhaul

# Emergency documentation updates
droid start documentation-manager --emergency-updates

# Quality improvement cycle
droid start documentation-manager --quality-improvement
```

### Specialized Droid Operations
```bash
# Database migration
droid start database-migration-specialist --migrate-to=postgresql

# Performance analysis
droid start performance-auditor --analyze-full-system

# Path refactoring
droid start path-refactor-coordinator --restructure=api/v2
```

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
Droids are automatically registered when created. The Context Manager maintains awareness of all available droids and their capabilities.

## 📋 Development Guidelines

### Creating New Droids
1. Use `GenerateDroid` command to create droid configuration
2. Define clear scope and responsibilities
3. Include comprehensive error handling
4. Add proper logging and status reporting
5. Test with Context Manager integration
6. Register capabilities in AGENTS.md

### Droid Integration
- All droids should follow consistent naming conventions (kebab-case)
- Use shared utilities and common patterns
- Include proper error handling and validation
- Provide clear status reporting and logging
- Design for Context Manager optimization

### Documentation Standards
- All droids must have comprehensive documentation
- Include usage examples and integration patterns
- Document dependencies and requirements
- Provide troubleshooting guides
- Maintain version compatibility information

## 🚀 Current Status

**Last Updated**: 2025-01-18  
**Total Droids**: 13 planned (2 active, 11 planned)  
**Active Droids**: 2 (Context Manager, Documentation Manager)  
**System Health**: 🟢 Operational - Core orchestration and documentation systems active  
**Next Priority**: Implement System Auditor for automated quality monitoring

## 📞 Support

**Repository**: Guardian Angel League Discord Bot  
**Development Team**: GAL Development Team  
**Framework**: FactoryAI Custom Droids  
**Documentation**: Complete droid documentation in `.factory/droids/`

## 🔄 Version History

### v2.0 (2025-01-18)
- ✅ Added Context Manager for intelligent orchestration
- ✅ Consolidated 3 documentation droids into 1 comprehensive Documentation Manager
- ✅ Updated droid organization and capabilities
- ✅ Enhanced workflow documentation
- ✅ Removed duplicate AGENTS.md file

### v1.0 (2025-10-10)
- ✅ Initial droid framework
- ✅ Basic droid definitions
- ✅ Core workflow patterns

---

**Maintained by**: Guardian Angel League Development  
**Generated**: 2025-01-18  
**Status**: Active - Context Manager and Documentation Manager operational
