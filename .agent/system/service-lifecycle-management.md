---
id: system.service-lifecycle-management
version: 1.0
last_updated: 2025-01-18
tags: [system, services, dashboard, lifecycle, management, process]
---

# Service Lifecycle Management

## Overview
The `services/` directory contains the enhanced dashboard service management system that provides automatic startup, health monitoring, and graceful shutdown for the Live Graphics Dashboard services. This system addresses critical issues with process cleanup, port management, and Windows-specific subprocess handling.

## Architecture

### Core Components

#### `services/dashboard_manager.py`
- **Purpose**: Enhanced dashboard service lifecycle management with comprehensive process cleanup
- **Size**: 28,671 bytes of production-ready service management code
- **Key Features**:
  - Port-based process detection and termination
  - Windows subprocess chain handling
  - Enhanced PID file management and validation
  - Process tree termination with psutil integration
  - Graceful shutdown with timeout enforcement
  - Duplicate instance prevention
  - Health monitoring and status reporting

### Service Architecture
```
Discord Bot (bot.py)
    ↓
DashboardManager (services/dashboard_manager.py)
    ├── FastAPI Backend (port 8000)
    │   ├── uvicorn server process
    │   ├── Python subprocess chain handling
    │   └── Health check endpoint (/health)
    └── Next.js Frontend (port 3000)
        ├── npm run dev process
        ├── Node.js subprocess chain handling
        └── Development server management
```

## Enhanced Features

### 1. Port-Based Process Management
The system uses advanced port-based process detection to ensure clean service shutdown:

#### Process Detection
- **Windows**: Uses `netstat -ano` to find PIDs using specific ports
- **Unix**: Uses `lsof -ti :port` for process identification
- **Cross-platform**: Automatic platform detection and appropriate tool selection

#### Process Termination
```python
# Kill processes by port with process name filtering
await self._kill_processes_by_port(port=8000, process_names=["python.exe", "uvicorn"])
await self._kill_processes_by_port(port=3000, process_names=["node.exe"])
```

### 2. Windows-Specific Subprocess Handling

#### Shell Chain Resolution
- **Problem**: Windows creates shell intermediates (cmd.exe) when spawning processes
- **Solution**: Detects actual service processes (python.exe, node.exe) within shell chains
- **Implementation**: Uses psutil to traverse process trees and find target processes

#### Process Tree Termination
```python
async def _kill_process_tree(self, pid: int) -> int:
    """Kill a process and all its children with Windows-specific handling"""
    if sys.platform == "win32":
        # Use taskkill /T to terminate process trees
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=10
        )
    else:
        # Unix: use psutil for proper process tree killing
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        # Terminate children first, then parent
```

### 3. Enhanced PID File Management

#### PID File Strategy
- **API Service**: `.dashboard_api.pid` in project root
- **Frontend Service**: `.dashboard_frontend.pid` in project root
- **Validation**: Automatic stale PID file cleanup
- **Duplicate Prevention**: Checks for existing instances before startup

#### PID Resolution
```python
def _find_actual_service_pid(self, shell_pid: int, target_process_name: str) -> Optional[int]:
    """Find the actual service process PID when spawned through a shell"""
    parent = psutil.Process(shell_pid)
    children = parent.children(recursive=True)
    
    for child in children:
        if child.name().lower() == target_process_name.lower():
            return child.pid
```

### 4. Graceful Shutdown Sequence

#### Multi-Stage Cleanup Process
1. **Port-Based Cleanup** (Primary): Kill processes by port and process name
2. **Tracked Process Cleanup**: Stop explicitly started processes
3. **PID File Cleanup**: Remove PID files
4. **Force Cleanup**: Verify ports are free, force termination if needed

#### Timeout Enforcement
```python
# Enhanced bot shutdown with timeout
try:
    await asyncio.wait_for(stop_dashboard_services(), timeout=15.0)
    logging.info("Stopped dashboard services")
except asyncio.TimeoutError:
    logging.warning("Dashboard services cleanup timed out - forcing termination")
    manager = get_dashboard_manager()
    await manager._cleanup_services_by_ports()
```

## Service Configuration

### Default Settings
- **API Port**: 8000 (FastAPI backend)
- **Frontend Port**: 3000 (Next.js development server)
- **Health Check Interval**: 30 seconds
- **Max Startup Attempts**: 3
- **Shutdown Timeout**: 15 seconds (bot integration)

### Environment Requirements
- **Python 3.12+**: Required for psutil integration
- **psutil**: Enhanced process management library
- **Node.js 16+**: Frontend service requirement
- **npm**: Frontend dependency management

## Integration Points

### Bot Integration (bot.py)
```python
async def close(self):
    """Cleanup when the bot is shutting down."""
    try:
        # Stop dashboard services with timeout
        await asyncio.wait_for(stop_dashboard_services(), timeout=15.0)
        logging.info("Stopped dashboard services")
    except asyncio.TimeoutError:
        # Force cleanup if timeout occurs
        manager = get_dashboard_manager()
        await manager._cleanup_services_by_ports()
```

### API Service Details
- **Startup Command**: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- **Health Endpoint**: `http://localhost:8000/health`
- **Documentation**: `http://localhost:8000/docs`
- **Working Directory**: `project_root/api/`

### Frontend Service Details
- **Startup Command**: `npm run dev`
- **Development Server**: Next.js development server
- **Working Directory**: `project_root/dashboard/`
- **Auto-Install**: Automatically installs dependencies if node_modules missing

## Error Handling and Recovery

### Startup Failure Recovery
- **API Dependency**: Frontend waits for API to be ready before starting
- **Health Checks**: Continuous health monitoring with configurable intervals
- **Automatic Cleanup**: Failed startups trigger automatic service cleanup

### Process Management Errors
- **Stale PID Files**: Automatic detection and cleanup
- **Orphaned Processes**: Port-based detection kills orphaned services
- **Shell Chain Issues**: Windows-specific subprocess resolution

### Platform-Specific Handling
- **Windows**: cmd.exe shell chain navigation, taskkill for process trees
- **Unix**: Direct process management, psutil for process tree operations
- **Cross-Platform**: Automatic detection and appropriate method selection

## Performance Considerations

### Process Detection Efficiency
- **Netstat Caching**: Windows netstat results cached for performance
- **Lsof Optimization**: Unix lsof calls optimized for minimal overhead
- **Process Name Filtering**: Reduces false positive process terminations

### Resource Management
- **Memory**: psutil for efficient process monitoring
- **CPU**: Asynchronous operations prevent blocking
- **I/O**: Timeout enforcement prevents hanging operations

## Security Considerations

### Process Isolation
- **Port Binding**: Services bind to localhost only by default
- **Process Permissions**: Services run with bot user permissions
- **PID File Security**: PID files created with appropriate permissions

### Access Control
- **Service Access**: Only dashboard components can access service APIs
- **Health Endpoints**: Health checks require local access
- **Process Management**: Only authorized processes can be terminated

## Troubleshooting

### Common Issues

#### Port Already in Use
- **Symptom**: "Port already in use" errors during startup
- **Solution**: Enhanced port cleanup automatically resolves
- **Manual Fix**: `taskkill /F /PID <pid>` on Windows

#### Process Tree Issues
- **Symptom**: Services don't stop completely
- **Solution**: Enhanced process tree termination with force cleanup
- **Manual Fix**: `taskkill /F /T /PID <pid>` on Windows

#### Stale PID Files
- **Symptom**: Service won't start due to existing PID file
- **Solution**: Automatic stale PID detection and cleanup
- **Manual Fix**: Delete `.dashboard_*.pid` files

### Debug Information
```python
# Get detailed service status
status = await manager.get_service_status()
print(f"API Running: {status['api']['running']}")
print(f"Frontend Running: {status['frontend']['running']}")

# Check service health
health = await manager.health_check()
print(f"Services Healthy: {health}")
```

## Migration Guide

### From Previous Service Management
1. **Install psutil**: `pip install psutil`
2. **Update bot.py**: Enhanced shutdown sequence already implemented
3. **Configuration**: No configuration changes required
4. **Testing**: Verify service startup and shutdown behavior

### Virtual Environment Considerations
- **psutil Installation**: Ensure psutil is installed in virtual environment
- **Path Resolution**: Manager automatically detects project root
- **Process Detection**: Handles virtual environment Python processes

## Dependencies

### Required Python Packages
- **psutil**: Enhanced process management and monitoring
- **aiohttp**: Health check HTTP client
- **asyncio**: Asynchronous operations and timeouts
- **subprocess**: Process spawning and management
- **pathlib**: Path manipulation and file system operations

### System Dependencies
- **Windows**: `netstat`, `taskkill` (built-in)
- **Unix**: `lsof` (process and port management)
- **Node.js**: Frontend service requirement
- **npm**: Frontend package management

## Future Enhancements

### Planned Features
- **Service Discovery**: Automatic service detection and registration
- **Load Balancing**: Multiple service instance support
- **Metrics Collection**: Performance and health metrics
- **Configuration Management**: Dynamic service configuration

### Extensibility
- **Plugin Architecture**: Support for additional service types
- **Custom Health Checks**: Configurable health check endpoints
- **Process Policies**: Configurable process management policies

---
**Module**: Service Lifecycle Management  
**Version**: 1.0  
**Last Updated**: 2025-01-18  
**Dependencies**: psutil, aiohttp, asyncio  
**Integration**: Discord Bot, Dashboard Services
