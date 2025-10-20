# Dashboard Startup Guide

This guide explains how to start the Guardian Angel League Live Graphics Dashboard using the new centralized startup system.

## Overview

The GAL Dashboard has been consolidated to use a single, centralized startup system that manages both the FastAPI backend and Next.js frontend services. This ensures both services run together and are properly cleaned up when shutting down.

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Valid Google Sheets API credentials
- Discord Bot Token configured in `.env.local`

### Single Command Startup
```bash
# Start the entire dashboard system
python start_dashboard.py
```

### Windows Convenience Option
```bash
# Use the Windows convenience wrapper
start_dashboard.cmd
```

## Dashboard Startup Methods

### Method 1: Direct Python Execution (Recommended)
```bash
python start_dashboard.py
```

**What this does:**
- ✅ Starts FastAPI backend on port 8000
- ✅ Starts Next.js frontend on port 3000
- ✅ Handles automatic dependency installation
- ✅ Provides proper signal handling (Ctrl+C for shutdown)
- ✅ Includes logging to both console and file
- ✅ Ensures graceful shutdown of both services

### Method 2: Windows Convenience Wrapper
```bash
start_dashboard.cmd
```

**What this does:**
- ✅ Same as direct execution but in a separate window
- ✅ Easier for Windows users (double-click to run)
- ✅ Provides visual feedback during startup
- ✅ Shows error messages if startup fails

### Method 3: Bot Integration (Automatic)
When you run the Discord bot (`python bot.py`), it automatically:
- ✅ Starts dashboard services during bot initialization
- ✅ Stops dashboard services during bot shutdown
- ✅ Handles service health monitoring
- ✅ Provides fallback cleanup if services hang

## System Architecture

### Two-Service System
```
start_dashboard.py
├── FastAPI Backend (port 8000)
│   ├── API endpoints
│   ├── JWT authentication
│   └── Database operations
└── Next.js Frontend (port 3000)
    ├── Canvas editor
    ├── Real-time graphics
    └── Dashboard interface
```

### Process Management
- **Parent Process**: `start_dashboard.py`
- **Backend Process**: uvicorn (FastAPI)
- **Frontend Process**: npm development server
- **Signal Handling**: Ctrl+C triggers graceful shutdown

## Configuration

### Environment Variables
The dashboard startup system respects these environment variables:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./dashboard/dashboard.db

# Dashboard Authentication
DASHBOARD_MASTER_PASSWORD=your_secure_password

# API Configuration  
NEXT_PUBLIC_API_URL=http://localhost:8000

# Development Settings
DEV_GUILD_ID=123456789
```

### Configuration Files
- **`start_dashboard.py`**: Main startup script
- **`config.yaml`**: Bot and system configuration
- **`.env.local`**: Local environment overrides

## Service URLs

Once running, you can access:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend Dashboard** | http://localhost:3000 | Graphics editor and dashboard interface |
| **Backend API** | http://localhost:8000 | API endpoints and authentication |
| **API Documentation** | http://localhost:8000/docs | FastAPI documentation |
| **Health Check** | http://localhost:8000/health | Service health monitoring |

## Startup Process Details

### 1. Service Detection
```python
# Automatic service detection
- Checks for Node.js and Python
- Validates configuration files
- Verifies API credentials
- Tests database connectivity
```

### 2. Dependency Installation
```python
# Automatic dependency management
if not os.path.exists("dashboard/node_modules"):
    print("Installing frontend dependencies...")
    subprocess.run(["npm", "install"], check=True)
```

### 3. Service Startup
```python
# Backend startup
backend_cmd = [
    sys.executable, "-m", "uvicorn",
    "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"
]

# Frontend startup  
frontend_cmd = ["npm", "run", "dev"]
```

### 4. Health Monitoring
```python
# Service health checks
- Backend: GET /health endpoint
- Frontend: Basic connectivity test
- Automatic retry for failed services
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Error**: `Address already in use`
```bash
# Solution: Kill existing processes
netstat -ano | findstr :8000  # Find process on port 8000
taskkill /F /PID <process_id>  # Kill the process
```

#### 2. Missing Dependencies
**Error**: `npm command not found` or `pip command not found`
```bash
# Solution: Install missing dependencies
# Install Node.js: https://nodejs.org/
# Install Python packages: pip install -r requirements.txt
```

#### 3. Database Issues
**Error**: `Database connection failed`
```bash
# Solution: Check database file and permissions
ls -la dashboard/dashboard.db
# Ensure the dashboard directory exists and is writable
```

#### 4. Authentication Issues
**Error**: `Dashboard login failed`
```bash
# Solution: Check master password
cat .env.local | grep DASHBOARD_MASTER_PASSWORD
# Verify the password is correctly configured
```

### Debug Mode
```bash
# Run with enhanced logging
python start_dashboard.py

# Check logs
tail -f gal_bot.log | grep -E "(dashboard|startup|error)"
```

### Manual Service Management
```bash
# If automated startup fails, you can start services manually:

# 1. Start backend
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Start frontend (in separate terminal)
cd dashboard
npm run dev
```

## Bot Integration

### Automatic Dashboard Management
When using the full GAL system, the Discord bot handles dashboard services automatically:

```python
# Bot startup includes dashboard
python bot.py
# → Automatically starts dashboard services

# Bot shutdown includes cleanup
# → Automatically stops dashboard services
```

### Dashboard Manager Features
- **Automatic Startup**: Dashboard starts when bot starts
- **Health Monitoring**: Continuous service health checks
- **Graceful Shutdown**: Proper cleanup on bot shutdown
- **Error Recovery**: Automatic restart of failed services
- **Port Management**: Handles port conflicts automatically

## Performance Considerations

### Resource Usage
- **Backend**: ~50-100MB RAM, low CPU
- **Frontend**: ~200-500MB RAM, moderate CPU during development
- **Database**: ~10-50MB RAM, minimal CPU usage

### Development vs Production
```bash
# Development Mode (Hot Reload)
python start_dashboard.py
# • Hot reload enabled
# • Debug logging active
# • Multiple processes for services

# Production Mode (Recommended for deployment)
# • Use process managers like systemd or PM2
# • Disable hot reload for performance
# • Enable production logging levels
```

## Deployment

### Production Deployment
For production deployment, consider:

1. **Process Management**: Use systemd or PM2
2. **Reverse Proxy**: Nginx or Apache in front of services
3. **Database**: Use PostgreSQL instead of SQLite
4. **SSL**: Use HTTPS with valid certificates
5. **Monitoring**: Add health checks and monitoring

### Example systemd Service
```ini
# /etc/systemd/system/gal-dashboard.service
[Unit]
Description=Guardian Angel League Dashboard
After=network.target

[Service]
Type=exec
User=gal
WorkingDirectory=/opt/gal-dashboard
ExecStart=/opt/gal-dashboard/venv/bin/python start_dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Backup and Recovery

### Data Backup
```bash
# Backup important files
cp dashboard/dashboard.db /backup/gal-dashboard-$(date +%Y%m%d).db
cp config.yaml /backup/config-$(date +%Y%m%d).yaml
cp .env.local /backup/.env.local-$(date +%Y%m%d)
```

### Recovery Procedures
1. **Service Failure**: Restart using `python start_dashboard.py`
2. **Database Corruption**: Restore from backup
3. **Configuration Loss**: Restore from backup
4. **API Token Issues**: Update `.env.local` with new tokens

## Integration with External Systems

### Google Sheets Integration
The dashboard automatically integrates with Google Sheets for:
- Tournament data synchronization
- Player registration and scoring
- Real-time updates to tournament standings

### Discord Integration
- Bot manages dashboard services
- Dashboard provides Discord webhook integration
- Real-time notifications for tournament events

## Best Practices

### 1. Regular Maintenance
- Monitor logs for errors
- Keep dependencies updated
- Regular backups of configuration and data
- Monitor resource usage

### 2. Security
- Use strong master passwords
- Keep environment variables secure
- Regular security updates
- Monitor for unauthorized access

### 3. Performance
- Monitor service health
- Optimize database queries
- Use production build for frontend
- Consider CDN for static assets

### 4. Development
- Use development mode for local testing
- Commit configuration changes
- Test startup procedures regularly
- Document any custom configurations

## Support

### Getting Help
1. **Check Logs**: `tail -f gal_bot.log`
2. **Health Check**: `curl http://localhost:8000/health`
3. **Discord**: Join #support channel on GAL Discord
4. **Documentation**: See `.agent/sops/` for operational procedures

### Common Commands
```bash
# Check dashboard status
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs

# Stop dashboard services
# Use Ctrl+C in startup terminal or kill processes on ports 8000 and 3000
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-18  
**Maintained by**: Guardian Angel League Development Team
