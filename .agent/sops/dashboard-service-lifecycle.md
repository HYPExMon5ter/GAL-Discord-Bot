---
id: sops.dashboard_service_lifecycle
version: 1.0
last_updated: 2025-01-18
tags: [dashboard, service-management, lifecycle, startup, shutdown, monitoring, auto-startup]
---

# Dashboard Service Lifecycle Management SOP

## Overview

This SOP outlines the procedures for managing the Guardian Angel League Dashboard services, including the FastAPI backend and Next.js frontend. The dashboard provides live graphics management, tournament standings, and administrative interfaces for the GAL Discord bot ecosystem.

## Service Architecture

### Components
1. **FastAPI Backend Service**
   - **Port**: 8000
   - **Process**: `uvicorn api.main:app`
   - **Health Endpoint**: `http://localhost:8000/health`
   - **API Documentation**: `http://localhost:8000/docs`

2. **Next.js Frontend Service**
   - **Port**: 3000
   - **Process**: `npm run dev`
   - **Development Server**: Hot reload enabled
   - **Build Target**: Production deployment

3. **Dashboard Manager**
   - **Location**: `services/dashboard_manager.py`
   - **Purpose**: Automated service lifecycle management
   - **Features**: Health monitoring, graceful shutdown, duplicate prevention

### Service Dependencies
```
Discord Bot ←→ Dashboard Manager ←→ FastAPI Backend ←→ Next.js Frontend
                                    ↓
                              Database Layer
```

## Startup Procedures

### Manual Startup

#### Standard Startup Method
**Use Case**: Development, manual service control  
**Frequency**: As needed

**Procedure**:
```bash
# Navigate to project root
cd /path/to/New-GAL-Discord-Bot

# Option 1: Using dashboard manager (recommended)
python start_dashboard.py

# Option 2: Direct script execution
python services/dashboard_manager.py

# Option 3: Manual component startup
# Terminal 1 - Start API
cd api
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ..

# Terminal 2 - Start Frontend (after API is ready)
cd dashboard
npm run dev
```

**Expected Output**:
```
Guardian Angel League Dashboard Starting Up...
==================================================
Starting FastAPI backend...
Starting Next.js frontend...
Dashboard is starting up!
Frontend: http://localhost:3000
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs
```

#### Verification Steps
1. **API Health Check**:
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status": "healthy", "timestamp": "..."}
   ```

2. **Frontend Access**:
   - Navigate to `http://localhost:3000`
   - Verify dashboard loads without errors
   - Check browser console for errors

3. **API Documentation**:
   - Access `http://localhost:8000/docs`
   - Verify Swagger UI loads correctly

### Automatic Startup

#### Bot Integration Startup
**Use Case**: Production deployment, automated service management  
**Frequency**: Bot startup

**Integration Points**:
```python
# In bot.py or main bot initialization
from services.dashboard_manager import get_dashboard_manager

async def on_ready():
    """Bot ready event - start dashboard services"""
    manager = get_dashboard_manager()
    success = await manager.start_services()
    
    if success:
        print("✅ Dashboard services started successfully")
    else:
        print("❌ Failed to start dashboard services")

async def on_disconnect():
    """Bot disconnect event - stop dashboard services"""
    manager = get_dashboard_manager()
    await manager.stop_services()
```

#### Service Registration
**Auto-startup Configuration**:
```yaml
# config.yaml
dashboard:
  auto_start: true
  startup_delay: 5  # seconds after bot ready
  health_check_interval: 30
  max_startup_attempts: 3
  
api:
  host: "0.0.0.0"
  port: 8000
  reload: true
  
frontend:
  port: 3000
  auto_install_deps: true
```

### Startup Troubleshooting

#### Common Startup Issues

**1. Port Already in Use**
**Symptoms**:
```
Error: [Errno 48] Address already in use
Port 8000 is already in use
```

**Resolution**:
```bash
# Find processes using the ports
netstat -an | grep :8000
netstat -an | grep :3000

# On Windows
netstat -ano | findstr :8000
tasklist | findstr <PID>

# Kill conflicting processes
taskkill /F /PID <PID>
# OR
lsof -ti:8000 | xargs kill -9
```

**2. Missing Dependencies**
**Symptoms**:
```
ModuleNotFoundError: No module named 'uvicorn'
npm: command not found
```

**Resolution**:
```bash
# Install Python dependencies
pip install uvicorn fastapi

# Install Node.js dependencies
cd dashboard
npm install

# Verify installations
python -m uvicorn --version
npm --version
```

**3. Environment Issues**
**Symptoms**:
```
PYTHONPATH not set
Database connection failed
Environment variables missing
```

**Resolution**:
```bash
# Set environment variables
export PYTHONPATH=/path/to/project
export DATABASE_URL=sqlite:///dashboard.db

# Verify configuration
python -c "import api.main; print('API imports successful')"
```

## Shutdown Procedures

### Graceful Shutdown

#### Standard Shutdown Method
**Use Case**: Normal service termination, maintenance  
**Frequency**: As needed

**Procedure**:
```bash
# Option 1: Using dashboard manager (recommended)
from services.dashboard_manager import get_dashboard_manager
import asyncio

manager = get_dashboard_manager()
asyncio.run(manager.stop_services())

# Option 2: Ctrl+C (if running start_dashboard.py)
# Press Ctrl+C in the terminal

# Option 3: Manual process termination
# Find and kill processes
ps aux | grep uvicorn
ps aux | grep "npm run dev"
kill <PID>
```

**Expected Output**:
```
^C
Shutting down...
Dashboard services stopped
```

#### Bot-Integrated Shutdown
**Use Case**: Bot shutdown, system restart  
**Frequency**: Bot lifecycle events

**Implementation**:
```python
# In bot shutdown handlers
async def shutdown_dashboard():
    """Gracefully shutdown dashboard services"""
    manager = get_dashboard_manager()
    await manager.stop_services()
    logger.info("Dashboard services stopped gracefully")

# Register shutdown handlers
bot.add_listener(on_disconnect, shutdown_dashboard)
```

### Forced Shutdown

#### Emergency Shutdown
**Use Case**: Unresponsive services, system maintenance  
**Frequency**: Emergency situations only

**Procedure**:
```bash
# Force kill by port (Windows)
taskkill /F /PID $(netstat -ano | findstr :8000 | awk '{print $5}')
taskkill /F /PID $(netstat -ano | findstr :3000 | awk '{print $5}')

# Force kill by port (Unix)
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Force kill by process name
pkill -f uvicorn
pkill -f "npm run dev"
```

**Warning**: Forced shutdown may cause data corruption or incomplete operations. Use only when necessary.

## Health Monitoring

### Service Health Checks

#### API Health Monitoring
**Frequency**: Every 30 seconds (automated)  
**Manual Check**: As needed

**Health Endpoint**:
```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T10:30:00Z",
  "services": {
    "database": "connected",
    "api": "running"
  }
}
```

#### Frontend Health Monitoring
**Frequency**: Every 30 seconds (automated)  
**Manual Check**: As needed

**Health Check Script**:
```bash
#!/bin/bash
# Check frontend health
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)

if [ $response -eq 200 ]; then
    echo "✅ Frontend healthy (HTTP $response)"
else
    echo "❌ Frontend unhealthy (HTTP $response)"
    exit 1
fi
```

### Dashboard Manager Monitoring

#### Service Status Check
**Python Implementation**:
```python
from services.dashboard_manager import get_dashboard_manager
import asyncio

async def check_service_status():
    """Check comprehensive service status"""
    manager = get_dashboard_manager()
    status = await manager.get_service_status()
    
    print(f"Services Started: {status['startup_complete']}")
    print(f"API Running: {status['api']['running']} (PID: {status['api']['pid']})")
    print(f"Frontend Running: {status['frontend']['running']} (PID: {status['frontend']['pid']})")
    
    # Perform health check
    healthy = await manager.health_check()
    print(f"Overall Health: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

# Run status check
asyncio.run(check_service_status())
```

#### Automated Monitoring Setup
**Cron Job (Linux/macOS)**:
```bash
# Every 5 minutes, check dashboard health
*/5 * * * * /usr/bin/python3 /path/to/project/scripts/monitor_dashboard.py
```

**Windows Task Scheduler**:
- **Trigger**: Every 5 minutes
- **Action**: `python C:\path\to\project\scripts\monitor_dashboard.py`
- **Conditions**: Run whether user is logged on or not

## Service Recovery

### Automatic Recovery Procedures

#### Health-Based Recovery
**Implementation**: Built into DashboardManager  
**Frequency**: Continuous monitoring

**Recovery Logic**:
```python
class ServiceRecovery:
    """Automatic service recovery based on health checks"""
    
    async def monitor_and_recover(self):
        """Monitor services and attempt recovery"""
        while not self._shutdown_requested:
            try:
                # Check service health
                if not await self.health_check():
                    logger.warning("Service health check failed, attempting recovery")
                    await self.attempt_recovery()
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def attempt_recovery(self):
        """Attempt to recover failed services"""
        try:
            # Stop existing services
            await self.stop_services()
            
            # Wait before restart
            await asyncio.sleep(5)
            
            # Restart services
            success = await self.start_services()
            
            if success:
                logger.info("✅ Service recovery successful")
            else:
                logger.error("❌ Service recovery failed")
                
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
```

#### Failure Notification
**Slack Integration**:
```python
async def notify_service_failure(service: str, error: str):
    """Send notification when service fails"""
    message = f"""
    🚨 Dashboard Service Alert
    
    Service: {service}
    Error: {error}
    Time: {datetime.now().isoformat()}
    Status: Recovery attempt in progress
    """
    
    # Send to monitoring channel
    await slack_post_message(message, channel="alerts")
```

### Manual Recovery Procedures

#### Service Restart
**Use Case**: Health monitoring alerts, manual intervention  
**Frequency**: As needed

**Procedure**:
```bash
# Check current status
python -c "
import asyncio
from services.dashboard_manager import get_dashboard_manager
async def check_status():
    manager = get_dashboard_manager()
    status = await manager.get_service_status()
    print(status)
asyncio.run(check_status())
"

# Restart services
python -c "
import asyncio
from services.dashboard_manager import get_dashboard_manager
async def restart():
    manager = get_dashboard_manager()
    await manager.stop_services()
    await asyncio.sleep(2)
    success = await manager.start_services()
    print(f'Restart success: {success}')
asyncio.run(restart())
"
```

#### Database Recovery
**Use Case**: Database corruption, connection issues  
**Frequency**: As needed

**Procedure**:
```bash
# Check database integrity
sqlite3 dashboard.db "PRAGMA integrity_check;"

# Backup current database
cp dashboard.db dashboard.db.backup.$(date +%Y%m%d_%H%M%S)

# Reset to clean state (if needed)
rm dashboard.db
python -c "
import asyncio
from api.services.configuration_service import ConfigurationService
async def init():
    config = ConfigurationService()
    await config.initialize_database()
asyncio.run(init())
"
```

## Maintenance Procedures

### Regular Maintenance

#### Log Management
**Frequency**: Weekly  

**Log Locations**:
- API logs: `api/logs/`
- Dashboard manager logs: `logs/dashboard_manager.log`
- System logs: `/var/log/gal/` (production)

**Log Rotation**:
```bash
# Rotate API logs
find api/logs -name "*.log" -mtime +7 -delete

# Compress old logs
find api/logs -name "*.log" -mtime +1 -exec gzip {} \;

# Clean up compressed logs older than 30 days
find api/logs -name "*.log.gz" -mtime +30 -delete
```

#### Cache Cleanup
**Frequency**: Monthly  

**Procedure**:
```python
# Clean dashboard cache
import sqlite3

conn = sqlite3.connect('dashboard.db')
cursor = conn.cursor()

# Clear expired cache entries
cursor.execute("DELETE FROM cache WHERE expires_at < datetime('now')")

# Clear old API logs (older than 30 days)
cursor.execute("DELETE FROM api_logs WHERE created_at < datetime('now', '-30 days')")

conn.commit()
conn.close()
```

#### Dependency Updates
**Frequency**: Monthly  

**Procedure**:
```bash
# Update Python dependencies
pip list --outdated
pip install -r requirements.txt --upgrade

# Update Node.js dependencies
cd dashboard
npm outdated
npm update

# Test updates
python start_dashboard.py
# Verify all services work correctly
```

### Performance Monitoring

#### Key Metrics
- **API Response Time**: <500ms average
- **Frontend Load Time**: <3 seconds
- **Memory Usage**: <512MB per service
- **CPU Usage**: <50% average
- **Database Query Time**: <100ms average

#### Monitoring Script
```python
# scripts/monitor_performance.py
import psutil
import asyncio
import aiohttp
from datetime import datetime

async def monitor_performance():
    """Monitor dashboard service performance"""
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check API performance
    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=5) as response:
                response_time = (time.time() - start_time) * 1000
                metrics["services"]["api"] = {
                    "response_time_ms": response_time,
                    "status_code": response.status,
                    "status": "healthy" if response.status == 200 else "unhealthy"
                }
    except Exception as e:
        metrics["services"]["api"] = {"status": "error", "error": str(e)}
    
    # Check system resources
    metrics["system"] = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
    
    # Log metrics
    with open("logs/performance.log", "a") as f:
        f.write(f"{metrics}\n")
    
    return metrics

if __name__ == "__main__":
    asyncio.run(monitor_performance())
```

## Security Procedures

### Access Control

#### Service Security
**API Security**:
```python
# API security configuration
CORS_ORIGINS = ["http://localhost:3000"]
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
API_KEY_REQUIRED = False  # Development mode
```

**Frontend Security**:
```javascript
// Frontend security configuration
const NEXT_PUBLIC_API_URL = process.env.NODE_ENV === 'production' 
  ? 'https://api.guardianangel.gg' 
  : 'http://localhost:8000';
```

#### Network Security
**Firewall Rules**:
```bash
# Only allow local access during development
# Production should use proper reverse proxy
ufw allow from 127.0.0.1 to any port 8000
ufw allow from 127.0.0.1 to any port 3000
```

### SSL/TLS Configuration

#### Development Setup
**Self-signed certificates** (for testing):
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure API to use HTTPS
uvicorn api.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

#### Production Setup
**Let's Encrypt**:
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d dashboard.guardianangel.gg

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Backup and Recovery

### Data Backup

#### Database Backup
**Frequency**: Daily  
**Retention**: 30 days

**Backup Script**:
```bash
#!/bin/bash
# scripts/backup_dashboard.sh

BACKUP_DIR="/backup/gal/dashboard"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp dashboard.db $BACKUP_DIR/dashboard_$DATE.db

# Compress backup
gzip $BACKUP_DIR/dashboard_$DATE.db

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "dashboard_*.db.gz" -mtime +30 -delete

echo "Dashboard backup completed: dashboard_$DATE.db.gz"
```

#### Configuration Backup
**Frequency**: Weekly  
**Scope**: Configuration files, environment variables

**Procedure**:
```bash
# Backup configuration files
tar -czf backup/config_$(date +%Y%m%d).tar.gz \
    config.yaml \
    .env \
    dashboard/next.config.js \
    api/requirements.txt

# Backup database schema
sqlite3 dashboard.db ".schema" > backup/schema_$(date +%Y%m%d).sql
```

### Disaster Recovery

#### Complete Service Recovery
**Use Case**: System failure, data corruption  
**Recovery Time Objective**: 1 hour

**Recovery Procedure**:
1. **Assess Damage**: Identify failed components
2. **Restore Database**: From latest backup
3. **Restart Services**: Using dashboard manager
4. **Verify Functionality**: Test all endpoints
5. **Monitor Stability**: Watch for issues

**Recovery Script**:
```bash
#!/bin/bash
# scripts/recover_dashboard.sh

echo "Starting dashboard recovery..."

# Stop any running services
pkill -f uvicorn
pkill -f "npm run dev"

# Restore database from backup
LATEST_BACKUP=$(ls -t /backup/gal/dashboard/dashboard_*.db.gz | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    echo "Restoring from backup: $LATEST_BACKUP"
    gunzip -c $LATEST_BACKUP > dashboard.db
else
    echo "No backup found, starting with fresh database"
    rm -f dashboard.db
fi

# Restart services
python start_dashboard.py

# Verify recovery
sleep 10
curl -f http://localhost:8000/health
if [ $? -eq 0 ]; then
    echo "✅ Dashboard recovery successful"
else
    echo "❌ Dashboard recovery failed"
    exit 1
fi
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Service Startup Failures

**Issue**: API fails to start with import errors
```bash
# Symptoms
ModuleNotFoundError: No module named 'api.main'
ImportError: cannot import name 'FastAPI'
```

**Solutions**:
```bash
# Check Python path
export PYTHONPATH=$(pwd)
echo $PYTHONPATH

# Verify API module
python -c "import api.main; print('API module OK')"

# Install missing dependencies
pip install -r api/requirements.txt
```

**Issue**: Frontend fails with build errors
```bash
# Symptoms
npm ERR! code ENOENT
Module not found: Can't resolve 'react'
```

**Solutions**:
```bash
# Clean and reinstall dependencies
cd dashboard
rm -rf node_modules package-lock.json
npm install

# Check Node.js version
node --version  # Should be >= 16
npm --version   # Should be >= 8
```

#### Performance Issues

**Issue**: Slow API response times
```bash
# Symptoms
API requests taking >5 seconds
Timeout errors in frontend
```

**Diagnosis**:
```bash
# Check system resources
top -p $(pgrep -f uvicorn)
htop

# Check database performance
sqlite3 dashboard.db "EXPLAIN QUERY PLAN SELECT * FROM graphics;"

# Profile API endpoints
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/graphics
```

**Solutions**:
```bash
# Restart services
python -c "
import asyncio
from services.dashboard_manager import get_dashboard_manager
async def restart():
    manager = get_dashboard_manager()
    await manager.stop_services()
    await asyncio.sleep(2)
    await manager.start_services()
asyncio.run(restart())
"

# Optimize database
sqlite3 dashboard.db "VACUUM; ANALYZE;"
```

#### Network Issues

**Issue**: Frontend cannot connect to API
```bash
# Symptoms
CORS errors in browser console
Network connection failed
```

**Diagnosis**:
```bash
# Check API is accessible
curl http://localhost:8000/health

# Check network connectivity
netstat -an | grep :8000
netstat -an | grep :3000
```

**Solutions**:
```bash
# Update CORS configuration
# In api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check firewall settings
sudo ufw status
```

### Debug Mode

#### Enable Debug Logging
```python
# In config.yaml
logging:
  level: DEBUG
  format: detailed
  
dashboard:
  debug: true
  auto_reload: true
```

#### Manual Debug Commands
```bash
# Start API with debug mode
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Start frontend with debug output
DEBUG=* npm run dev

# Monitor logs in real-time
tail -f api/logs/api.log
tail -f logs/dashboard_manager.log
```

---

**SOP Version**: 1.0  
**Last Updated**: 2025-01-18  
**Related Documentation**: [Dashboard Architecture](../system/dashboard-architecture.md), [API Integration](../system/api-integration.md), [Service Manager](../../services/dashboard_manager.py)
