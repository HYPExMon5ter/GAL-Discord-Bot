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

# Edit configuration files with your actual values
notepad .env.local        # or vim, nano, etc.
notepad config.yaml       # or vim, nano, etc.
```

**Required Configuration:**
- **Discord Token**: Get from Discord Developer Portal
- **Application ID**: Discord application ID
- **Riot API Key**: For IGN verification
- **Master Password**: For dashboard access
- **Google Sheets**: API credentials and sheet URLs

4. **Start Services**
```bash
# Option 1: Use the new centralized dashboard startup (RECOMMENDED)
python start_dashboard.py
# This starts both API backend and frontend automatically

# Option 2: Start services manually (for development or debugging)
# Start API backend
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Discord Bot (in another terminal)
python bot.py

# Start Dashboard (in another terminal)
cd dashboard
npm run dev
```

**Note**: The centralized `start_dashboard.py` is now the recommended method as it handles both services and provides better process management and cleanup.

5. **Access Dashboard**
- Open [http://localhost:3000](http://localhost:3000) in browser
- Use master password to login

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Bot Not Starting
**Symptoms**: Error messages about missing token or configuration

**Solutions**:
1. Verify Discord token is correct in `.env.local`
2. Check that config.yaml exists and is properly formatted
3. Ensure all required environment variables are set
4. Check Python environment is activated: `pip list` should show installed packages

```bash
# Verify Discord token
echo $DISCORD_TOKEN  # Should show your token

# Check Python environment
python --version
pip list | grep discord
```

#### Dashboard Login Fails
**Symptoms**: "Invalid credentials" or authentication errors

**Solutions**:
1. Verify master password in `.env.local` matches what you're entering
2. Check API backend is running on port 8000
3. Verify dashboard can reach API endpoint

```bash
# Check API is running
curl http://localhost:8000/health

# Test API authentication
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"master_password":"your_password"}'
```

#### API Connection Errors
**Symptoms**: 404 errors, connection refused, or CORS errors

**Solutions**:
1. Verify API is running: `ps aux | grep uvicorn`
2. Check port 8000 is not blocked by firewall
3. Verify Next.js configuration is correct

```bash
# Check if port is in use
netstat -an | grep :8000

# Restart API if needed
cd api && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Google Sheets Integration Issues
**Symptoms**: Errors accessing Google Sheets data

**Solutions**:
1. Verify `google-creds.json` file exists and is valid
2. Check sheet URLs in config.yaml are accessible
3. Ensure service account has necessary permissions

```bash
# Test Google Sheets access
python -c "
import gspread
gc = gspread.service_account('google-creds.json')
sh = gc.open_by_url('your_sheet_url')
print('Sheet access successful:', sh.title)
"
```

#### Canvas View Not Working
**Symptoms**: 404 errors when accessing `/canvas/view/{id}`

**Solutions**:
1. Verify graphic ID exists in database
2. Check API backend is running and accessible
3. Verify Next.js routing is working

```bash
# Test API endpoint
curl http://localhost:8000/api/v1/graphics/1/view

# Check database for graphics
python -c "
from api.models import engine
import sqlite3
conn = sqlite3.connect('dashboard.db')
cursor = conn.cursor()
cursor.execute('SELECT id FROM graphics LIMIT 5')
print('Graphics in DB:', cursor.fetchall())
conn.close()
"
```

#### Port Already in Use
**Symptoms**: "Address already in use" or "Port 3000/8000 is in use"

**Solutions**:
1. Kill processes using the ports
2. Or use different ports

```bash
# Find and kill processes on port 8000
netstat -tulpn | grep :8000
kill -9 <PID>

# Or use different ports
cd api && python -m uvicorn main:app --port 8001
cd dashboard && npm run dev -- -p 3001
```

#### Permission Errors (Linux/Mac)
**Symptoms**: Permission denied errors

**Solutions**:
1. Fix file permissions
2. Use virtual environment

```bash
# Fix permissions
chmod +x start_dashboard.py

# Ensure venv is owned by user
sudo chown -R $USER:$USER .venv
```

#### Memory Issues
**Symptoms**: Out of memory errors or slow performance

**Solutions**:
1. Close unnecessary applications
2. Increase memory allocation
3. Use lighter database (SQLite for development)

```bash
# Monitor memory usage
htop  # or Activity Monitor on Mac

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### Getting Help

1. **Check Logs**: Look at `gal_bot.log` for error details
2. **Verify Configuration**: Double-check all environment variables
3. **Network Issues**: Check firewall and proxy settings
4. **Community**: Ask for help in the Discord server

### Environment Verification

After installation, verify everything is working:

```bash
# 1. Check Python environment
python --version  # Should be 3.12+
pip list | grep -E "(discord|fastapi|next)"

# 2. Check Node environment
node --version    # Should be 18+
npm list --depth=0

# 3. Check configuration files exist
ls -la .env.local config.yaml google-creds.json

# 4. Test API health
curl http://localhost:8000/health

# 5. Test Discord bot (in Discord)
/gal help
```

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
