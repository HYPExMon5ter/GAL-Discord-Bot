---
id: sops.bot-lifecycle-management
version: 1.0
last_updated: 2025-01-18
tags: [sops, bot, lifecycle, management, shutdown, startup, dashboard]
---

# Bot Lifecycle Management SOP

## Overview
This SOP outlines the procedures for managing the Guardian Angel League Discord bot lifecycle, including startup, shutdown, and dashboard service management. The enhanced system provides comprehensive process cleanup, port management, and Windows-specific subprocess handling.

## Scope
- Discord bot startup and shutdown procedures
- Dashboard service lifecycle management
- Process cleanup and port management
- Emergency procedures and troubleshooting
- Windows-specific considerations

## Prerequisites
- Python 3.12+ with virtual environment
- psutil dependency installed (`pip install psutil`)
- Appropriate Discord bot permissions
- Dashboard dependencies (Node.js, npm) installed

## Bot Startup Procedures

### Standard Startup
1. **Navigate to project directory**
   ```bash
   cd /path/to/New-GAL-Discord-Bot
   ```

2. **Activate virtual environment**
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Unix
   source .venv/bin/activate
   ```

3. **Verify environment**
   ```bash
   # Check Python version
   python --version
   
   # Verify psutil installation
   python -c "import psutil; print('psutil version:', psutil.__version__)"
   
   # Check configuration
   python -c "import config; print('Config loaded successfully')"
   ```

4. **Start the bot**
   ```bash
   python bot.py
   ```

### Automated Startup with Dashboard Services
The bot automatically starts dashboard services during initialization:

1. **Dashboard Manager Initialization**
   - Service manager automatically detects project root
   - Checks for existing service instances
   - Prevents duplicate service startup

2. **Service Startup Sequence**
   ```python
   # Order of operations:
   1. Start FastAPI backend (port 8000)
   2. Wait for API health check (http://localhost:8000/health)
   3. Start Next.js frontend (port 3000)
   4. Verify all services are healthy
   ```

3. **Service Health Verification**
   - API health endpoint: `http://localhost:8000/health`
   - Frontend accessibility: `http://localhost:3000`
   - API documentation: `http://localhost:8000/docs`

### Startup Troubleshooting

#### Port Already in Use
**Symptoms**: "Port already in use" errors during startup

**Resolution**:
1. The enhanced dashboard manager automatically handles port cleanup
2. If issues persist, manually clean up:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   netstat -ano | findstr :3000
   taskkill /F /PID <PID>
   
   # Unix
   lsof -ti :8000 | xargs kill -9
   lsof -ti :3000 | xargs kill -9
   ```

#### Virtual Environment Issues
**Symptoms**: ImportError or missing dependencies

**Resolution**:
```bash
# Reinstall psutil in virtual environment
pip install psutil

# Verify installation
python -c "import psutil; print('psutil installed successfully')"
```

#### Service Health Check Failures
**Symptoms**: Services start but fail health checks

**Resolution**:
1. Check service logs for errors
2. Verify port accessibility
3. Check for conflicting services
4. Restart individual services if needed

## Bot Shutdown Procedures

### Standard Shutdown
1. **Graceful Shutdown (Recommended)**
   ```bash
   # Press Ctrl+C in the bot terminal
   # OR send SIGTERM signal (Unix)
   kill -TERM <bot_pid>
   ```

2. **Automated Shutdown Sequence**
   The bot automatically performs the following shutdown steps:
   ```python
   async def close(self):
       # 1. Stop dashboard services with timeout (15 seconds)
       await asyncio.wait_for(stop_dashboard_services(), timeout=15.0)
       
       # 2. Handle timeout with force cleanup
       except asyncio.TimeoutError:
           manager = get_dashboard_manager()
           await manager._cleanup_services_by_ports()
       
       # 3. Clean up bot resources
       # 4. Close Discord connection
   ```

### Enhanced Shutdown Process
The enhanced shutdown system includes:

#### Multi-Stage Cleanup
1. **Port-Based Cleanup** (Primary Method)
   - Kills processes using ports 8000 and 3000
   - Filters by process name (python.exe, node.exe)
   - Cross-platform process detection

2. **Tracked Process Cleanup**
   - Stops explicitly started service processes
   - Handles subprocess chain termination

3. **PID File Cleanup**
   - Removes `.dashboard_api.pid` and `.dashboard_frontend.pid`
   - Validates PID file integrity

4. **Force Cleanup**
   - Verifies ports are actually free
   - Forces termination of lingering processes

#### Windows-Specific Handling
- **Shell Chain Resolution**: Navigates cmd.exe → python.exe process chains
- **Process Tree Termination**: Uses `taskkill /F /T` for complete cleanup
- **WMIC Fallback**: Alternative process detection when psutil unavailable

### Emergency Shutdown
1. **Force Termination**
   ```bash
   # Windows
   taskkill /F /IM python.exe
   taskkill /F /IM node.exe
   
   # Unix
   pkill -f python
   pkill -f node
   ```

2. **Manual Port Cleanup**
   ```bash
   # Find and kill processes by port
   # Windows
   netstat -ano | findstr :8000
   netstat -ano | findstr :3000
   
   # Unix
   lsof -i :8000
   lsof -i :3000
   ```

3. **PID File Cleanup**
   ```bash
   # Remove stale PID files
   rm -f .dashboard_api.pid
   rm -f .dashboard_frontend.pid
   ```

## Service Management Procedures

### Manual Service Control
1. **Start Services Only**
   ```python
   from services.dashboard_manager import start_dashboard_services
   
   # In Python console
   import asyncio
   asyncio.run(start_dashboard_services())
   ```

2. **Stop Services Only**
   ```python
   from services.dashboard_manager import stop_dashboard_services
   
   # In Python console
   import asyncio
   asyncio.run(stop_dashboard_services())
   ```

3. **Service Status Check**
   ```python
   from services.dashboard_manager import get_dashboard_manager
   
   manager = get_dashboard_manager()
   status = asyncio.run(manager.get_service_status())
   print(status)
   ```

### Service Health Monitoring
1. **Automated Health Checks**
   - Health check interval: 30 seconds
   - API endpoint monitoring
   - Frontend accessibility verification

2. **Manual Health Verification**
   ```bash
   # Check API health
   curl http://localhost:8000/health
   
   # Check frontend
   curl http://localhost:3000
   
   # Check API documentation
   curl http://localhost:8000/docs
   ```

### Service Configuration
1. **Default Configuration**
   - API Port: 8000
   - Frontend Port: 3000
   - Health Check Interval: 30 seconds
   - Shutdown Timeout: 15 seconds

2. **Custom Configuration**
   ```python
   from services.dashboard_manager import DashboardManager
   
   # Custom manager with different configuration
   manager = DashboardManager(
       project_root="/custom/path",
       api_port=8001,
       frontend_port=3001
   )
   ```

## Troubleshooting Guide

### Common Issues

#### Bot Won't Start
**Possible Causes**:
- Missing psutil dependency
- Configuration errors
- Port conflicts

**Resolution Steps**:
1. Check virtual environment activation
2. Verify psutil installation: `pip install psutil`
3. Check configuration files
4. Clear port conflicts

#### Services Don't Stop Cleanly
**Possible Causes**:
- Process tree termination issues
- Shell chain resolution problems
- Insufficient permissions

**Resolution Steps**:
1. Check for orphaned processes: `netstat -ano` (Windows) or `lsof` (Unix)
2. Force cleanup with manual commands
3. Verify psutil is working correctly
4. Check system permissions

#### Dashboard Services Fail to Start
**Possible Causes**:
- Port already in use
- Missing dependencies
- Virtual environment issues

**Resolution Steps**:
1. Check port availability
2. Verify Node.js and npm installation
3. Install frontend dependencies: `cd dashboard && npm install`
4. Check virtual environment Python

#### Windows-Specific Issues

**Shell Chain Problems**:
- **Symptom**: Processes don't terminate properly
- **Solution**: Enhanced shell chain resolution automatically handles this
- **Manual Fix**: Use `taskkill /F /T` for process tree termination

**psutil Installation Issues**:
- **Symptom**: ImportError: No module named 'psutil'
- **Solution**: Install in virtual environment: `pip install psutil`
- **Verification**: `python -c "import psutil"`

**Process Permission Issues**:
- **Symptom**: Access denied errors
- **Solution**: Run with appropriate user permissions
- **Prevention**: Use consistent user account for all operations

### Debug Information Collection
1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Collect System Information**
   ```python
   import platform
   import psutil
   
   print(f"System: {platform.system()}")
   print(f"Platform: {platform.platform()}")
   print(f"Python: {platform.python_version()}")
   print(f"psutil: {psutil.__version__}")
   ```

3. **Process State Analysis**
   ```python
   from services.dashboard_manager import get_dashboard_manager
   
   manager = get_dashboard_manager()
   status = asyncio.run(manager.get_service_status())
   health = asyncio.run(manager.health_check())
   
   print(f"Service Status: {status}")
   print(f"Health Check: {health}")
   ```

## Maintenance Procedures

### Daily Checks
1. **Service Health Verification**
   - Check bot is running and responsive
   - Verify dashboard services are accessible
   - Review logs for errors or warnings

2. **Resource Usage Monitoring**
   - Check CPU and memory usage
   - Monitor disk space
   - Review process count

### Weekly Maintenance
1. **Log Review**
   - Analyze error logs
   - Check for repeated issues
   - Review performance metrics

2. **Dependency Updates**
   - Check for psutil updates
   - Review Python package updates
   - Update frontend dependencies if needed

### Monthly Maintenance
1. **System Health Assessment**
   - Full system resource review
   - Performance optimization
   - Security assessment

2. **Documentation Review**
   - Update procedures as needed
   - Review and update troubleshooting guides
   - Document any new issues or solutions

## Emergency Procedures

### Bot Crash Recovery
1. **Immediate Actions**
   - Check system logs for crash cause
   - Verify system resources are available
   - Clear any port conflicts

2. **Recovery Steps**
   - Fix underlying issue (configuration, dependencies, etc.)
   - Clear any orphaned processes
   - Restart bot using standard procedures

3. **Verification**
   - Confirm bot starts successfully
   - Verify dashboard services start correctly
   - Test basic bot functionality

### Service Failure Recovery
1. **Individual Service Failure**
   - Identify which service failed (API or frontend)
   - Check service-specific logs
   - Restart individual service if needed

2. **Complete Service Failure**
   - Stop all services completely
   - Clear PID files and process conflicts
   - Restart using standard procedures

### Data Corruption Recovery
1. **Immediate Containment**
   - Stop bot to prevent further damage
   - Identify affected data
   - Assess corruption extent

2. **Recovery Process**
   - Restore from most recent backup
   - Verify data integrity
   - Restart services
   - Monitor for recurrence

## Security Considerations

### Process Security
- Services run with bot user permissions only
- Port binding restricted to localhost
- Process access controls enforced
- PID files protected with appropriate permissions

### Access Control
- Only authorized users can manage services
- Service management requires appropriate permissions
- API access controlled through authentication

### Monitoring and Auditing
- All service management actions logged
- Process creation and termination tracked
- Resource usage monitored
- Security events audited

## Performance Optimization

### Startup Optimization
- Parallel service startup where possible
- Dependency checking before startup
- Intelligent port conflict resolution
- Cached service configuration

### Shutdown Optimization
- Timeout enforcement prevents hanging
- Parallel process termination
- Resource cleanup optimization
- Graceful degradation for failures

### Resource Management
- Process monitoring and cleanup
- Memory usage optimization
- CPU usage balancing
- Disk I/O optimization

## Documentation and Training

### Documentation Requirements
- All procedures documented and accessible
- Troubleshooting guides maintained
- Configuration examples provided
- Performance metrics tracked

### Training Requirements
- Team members trained on startup/shutdown procedures
- Emergency response procedures reviewed
- Windows-specific considerations covered
- Troubleshooting skills developed

### Knowledge Transfer
- Procedure documentation shared with team
- Troubleshooting experiences documented
- Lessons learned captured
- Best practices identified and shared

---
**SOP Version**: 1.0  
**Last Updated**: 2025-01-18  
**Next Review**: 2025-02-18  
**Related Documents**: 
- [Service Lifecycle Management](../system/service-lifecycle-management.md)
- [Process Management](../system/process-management.md)
- [Integration Modules](../system/integration-modules.md)
- [Dashboard Operations](./dashboard-operations.md)
