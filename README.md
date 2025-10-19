# Guardian Angel League - Discord Bot & Live Graphics Dashboard

<div align="center">
  
![Guardian Angel League](https://img.shields.io/badge/GAL-Tournament%20Bot-blue?style=for-the-badge&logo=discord&logoColor=white)
![Version](https://img.shields.io/badge/Version-2.0-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

</div>

## 🎯 Overview

Guardian Angel League (GAL) is a comprehensive Discord bot and live graphics dashboard system designed for managing TFT (Teamfight Tactics) tournaments. The system provides tournament registration, check-in management, IGN verification, and real-time graphics editing capabilities.

## 🏗️ Architecture

### Core Components

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **Discord Bot** | Main bot handling tournaments, registration, and check-in | [Bot Architecture](.agent/system/bot_current_features.md) |
| **Live Graphics Dashboard** | Web-based editor for managing broadcast graphics | [Dashboard Overview](.agent/system/live-graphics-dashboard.md) |
| **API Backend** | FastAPI backend for dashboard authentication and data management | [API Backend](.agent/system/api-backend-system.md) |
| **Google Sheets Integration** | Tournament data synchronization and user management | [Integration](.agent/system/integration-modules.md) |
| **Authentication System** | Master password and JWT-based security | [Authentication](.agent/system/authentication-system.md) |

### System Flow
```
Discord Commands → Bot Logic → Google Sheets → API → Dashboard → Graphics Editor
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Discord Bot Token
- Google Sheets API Credentials
- Master Password for Dashboard Access

### Installation

1. **Clone Repository**
```bash
git clone <repository-url>
cd New-GAL-Discord-Bot
```

2. **Environment Setup**
```bash
# Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Node.js environment  
cd dashboard
npm install
cd ..
```

3. **Configuration**
```bash
# Copy environment files
cp .env.local.example .env.local
cp config.yaml.example config.yaml

# Edit configuration files
vim .env.local
vim config.yaml
```

4. **Start Services**
```bash
# Start API backend
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Discord Bot (in another terminal)
python bot.py

# Start Dashboard (in another terminal)
cd dashboard
npm run dev
```

5. **Access Dashboard**
- Open [http://localhost:3000](http://localhost:3000) in browser
- Use master password to login

## 📚 Documentation

### 📖 Complete Documentation
Comprehensive documentation is organized in the `.agent/` directory:

| Category | Files | Purpose |
|----------|-------|---------|
| **🏗️ System Architecture** | [system/](.agent/system/) | Core system design and architecture |
| **🛠️ Operational Procedures** | [sops/](.agent/sops/) | Standard operating procedures and workflows |
| **📋 Tasks & Projects** | [tasks/](.agent/tasks/) | Feature implementations and PRDs |
| **📝 Drafts** | [drafts/](.agent/drafts/) | Work-in-progress documentation |

### 🔧 Technical Documentation

#### Core Systems
- [**Architecture Overview**](.agent/system/architecture-overview.md) - High-level system architecture
- [**Data Models**](.agent/system/data-models.md) - Database and data structures
- [**Event System**](.agent/system/event-system.md) - Event-driven architecture
- [**Authentication**](.agent/system/authentication-system.md) - Security and auth flows

#### API Documentation
- [**API Backend**](.agent/system/api-backend-system.md) - FastAPI backend architecture
- [**API Integration**](.agent/system/api-integration.md) - External API integration patterns
- [**WebSocket Integration**](.agent/system/websocket-integration.md) - Real-time communication

#### Frontend Documentation
- [**Dashboard Overview**](.agent/system/live-graphics-dashboard.md) - Dashboard architecture
- [**Canvas Editor**](.agent/system/canvas-editor-architecture.md) - Graphics editor system
- [**Frontend Components**](.agent/system/frontend-components.md) - React component structure

#### Operational Documentation
- [**Deployment Procedures**](.agent/sops/deployment.md) - System deployment guide
- [**Security Architecture**](.agent/system/security-architecture.md) - Security implementation
- [**Performance Monitoring**](.agent/sops/performance-monitoring-sop.md) - System monitoring
- [**Incident Response**](.agent/sops/incident-response.md) - Emergency procedures

### 🎯 Key Features

### Discord Bot Features
- **Tournament Registration**: User registration with IGN verification
- **Check-in Management**: Automated check-in and checkout system
- **IGN Verification**: Riot Games API integration for player verification
- **Tournament Modes**: Support for normal and doubleup tournaments
- **Automated Reminders**: DM reminders for unchecked-in users
- **Role Management**: Automatic role assignment and management

### Dashboard Features
- **Graphics Editor**: Canvas-based graphic creation and editing
- **Real-time Locking**: Prevents concurrent editing with visual indicators
- **Archive System**: Safe archiving and restoration of graphics
- **Authentication**: JWT-based secure access
- **Live Updates**: WebSocket integration for real-time updates

### Integration Features
- **Google Sheets**: Tournament data synchronization
- **Riot API**: Player verification and stats
- **Discord Webhooks**: Automated notifications and logging
- **Database**: SQLite/PostgreSQL data persistence

## 🛠️ Development

### Code Organization
```
New-GAL-Discord-Bot/
├── api/                    # FastAPI backend
├── dashboard/              # Next.js frontend
├── bot.py                  # Main Discord bot
├── config.yaml             # Configuration file
├── core/                   # Core bot logic
├── integrations/           # External service integrations
├── services/               # Business logic services
├── utils/                  # Utility functions
└── tests/                  # Test files
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Follow existing code style and patterns
4. Add tests for new features
5. Update documentation as needed
6. Submit a pull request

### Testing
```bash
# Run API tests
cd api
pytest tests/

# Run frontend tests  
cd dashboard
npm test

# Run integration tests
python -m pytest tests/integration/
```

## 🔒 Security

### Authentication
- **Bot**: Discord OAuth2 and role-based permissions
- **Dashboard**: JWT tokens with 15-minute timeout
- **API**: Master password authentication

### Data Protection
- **Encryption**: Sensitive data encrypted at rest
- **Rate Limiting**: API rate limiting to prevent abuse
- **Access Control**: Role-based access control (RBAC)
- **Audit Logging**: Comprehensive logging of all operations

## 📈 Monitoring

### Health Checks
- **API Health**: `/health` endpoint for service monitoring
- **Database**: Connection pool monitoring
- **Discord**: Bot connection status monitoring
- **External APIs**: Integration health monitoring

### Logging
- **Application Logs**: Structured logging with timestamps
- **Error Tracking**: Exception logging and monitoring
- **Performance**: Performance metrics and profiling
- **Security**: Security event logging and alerts

## 🚀 Deployment

### Production Deployment
- Use Docker containers for consistent deployment
- Environment-specific configuration management
- Automated health checks and monitoring
- Rolling updates with zero downtime

### Environment Configuration
- **Development**: Local development with hot reload
- **Staging**: Pre-production testing environment
- **Production**: Live environment with monitoring

## 🆘 Support

### Getting Help
1. **Documentation**: Check comprehensive docs in `.agent/` directory
2. **Issues**: Report bugs or feature requests via GitHub issues
3. **Discord**: Join our community server for support
4. **Wiki**: Community knowledge base

### Common Issues
- **Bot Not Starting**: Check Discord bot token and permissions
- **Dashboard Login**: Verify master password configuration
- **API Connection**: Check backend service status
- **Google Sheets**: Verify API credentials and permissions

## 📊 Metrics

| Metric | Target | Status |
|--------|--------|---------|
| Documentation Coverage | 90%+ | 75% 🟡 |
| Test Coverage | 85%+ | 80% 🟢 |
| Uptime | 99.9% | 99.5% 🟢 |
| Response Time | <500ms | 300ms 🟢 |

## 🔄 Changelog

### v2.0 (Current)
- ✅ Live Graphics Dashboard v2.0
- ✅ Canvas Editor with real-time locking
- ✅ Archive and restore system
- ✅ Enhanced security architecture
- ✅ Improved performance monitoring

### v1.0 (Previous)
- ✅ Basic Discord bot functionality
- ✅ Tournament registration system
- ✅ Google Sheets integration
- ✅ IGN verification

---

**Maintained by**: Guardian Angel League Development Team  
**Last Updated**: 2025-01-18  
**License**: proprietary  

<div align="center">

[🏠 Home](#) • [📖 Docs](#documentation) • [🛠️ Development](#development) • [🔒 Security](#security) • [📈 Monitoring](#monitoring) • [🚀 Deployment](#deployment) • [🆘 Support](#support)

</div>
