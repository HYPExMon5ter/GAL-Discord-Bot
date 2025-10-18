---
id: system.process-management
version: 1.0
last_updated: 2025-01-18
tags: [system, process, management, windows, subprocess, psutil]
---

# Process Management

## Overview
The Guardian Angel League bot system includes advanced process management capabilities specifically designed for Windows environments, with cross-platform support for Unix-like systems. This system addresses critical issues with subprocess management, process tree termination, and service lifecycle management.

## Architecture

### Core Components

#### Process Detection System
- **Windows**: Uses `netstat -ano` for port-to-PID mapping
- **Unix**: Uses `lsof -ti :port` for process identification
- **Cross-Platform**: Automatic platform detection and tool selection

#### Process Termination System
- **Windows**: `taskkill /F /T /PID` for process tree termination
- **Unix**: psutil for proper process tree management
- **Enhanced**: psutil integration for advanced process monitoring

#### Subprocess Chain Resolution
- **Problem**: Windows creates shell intermediates (cmd.exe) when spawning processes
- **Solution**: Traverses process trees to find actual service processes
- **Implementation**: psutil process tree navigation with name filtering

## Windows-Specific Process Management

### Shell Chain Handling

#### Problem Statement
When spawning processes on Windows using `subprocess.Popen` with `shell=True`, Windows creates intermediate shell processes:
```
cmd.exe (shell) → python.exe (actual service)
```

This creates challenges for:
- Accurate PID tracking
- Process termination
- Resource monitoring
- Service health checking

#### Solution Implementation

##### PID Resolution Algorithm
```python
def _find_actual_service_pid(self, shell_pid: int, target_process_name: str) -> Optional[int]:
    """
    Find the actual service process PID when spawned through a shell.
    
    Args:
        shell_pid: PID of the shell process (cmd.exe)
        target_process_name: Name of the target process (e.g., 'python.exe', 'node.exe')
        
    Returns:
        Actual service process PID or None if not found
    """
    if sys.platform != "win32":
        return shell_pid  # Unix doesn't have shell intermediates
    
    try:
        # Find child processes of the shell
        parent = psutil.Process(shell_pid)
        children = parent.children(recursive=True)
        
        for child in children:
            if child.name().lower() == target_process_name.lower():
                return child.pid
                
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    except ImportError:
        # Fallback: Windows-specific method using WMIC
        return self._find_pid_with_wmic(shell_pid, target_process_name)
    
    return None
```

##### Windows Management Instrumentation (WMIC) Fallback
```python
def _find_pid_with_wmic(self, shell_pid: int, target_process_name: str) -> Optional[int]:
    """Fallback method using WMIC when psutil is not available"""
    try:
        result = subprocess.run(
            ["wmic", "process", "get", "ParentProcessId,ProcessId,Name", "/format:csv"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if target_process_name.lower() in line.lower() and str(shell_pid) in line:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        return int(parts[1])  # ProcessId column
    except Exception:
        pass
    
    return None
```

### Process Tree Termination

#### Windows Process Tree Management
```python
async def _kill_process_tree(self, pid: int) -> int:
    """
    Kill a process and all its children with Windows-specific handling.
    
    Args:
        pid: Process ID to kill
        
    Returns:
        Number of processes killed
    """
    killed_count = 0
    
    try:
        if sys.platform == "win32":
            # Windows: use taskkill to kill process tree
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Count killed processes from output
                killed_count += result.stdout.count("PID")
            else:
                # Fallback: try killing just the process
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], timeout=5)
                killed_count += 1
        else:
            # Unix: use psutil for proper process tree killing
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.terminate()
                    killed_count += 1
                except psutil.NoSuchProcess:
                    continue
            
            # Kill parent
            parent.terminate()
            killed_count += 1
            
            # Wait and kill if still alive
            gone, alive = psutil.wait_procs([parent] + children, timeout=3)
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    continue
                    
    except Exception as e:
        logger.warning(f"Error killing process tree for PID {pid}: {e}")
        
    return killed_count
```

### Port-Based Process Detection

#### Windows Netstat Integration
```python
def _find_processes_by_port(self, port: int) -> List[Dict]:
    """
    Find all processes using a specific port on Windows.
    
    Args:
        port: Port number to check
        
    Returns:
        List of dictionaries with process info
    """
    processes = []
    
    try:
        if sys.platform == "win32":
            # Windows: use netstat to find PIDs, then get process info
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = int(parts[-1])
                            try:
                                # Get process name using tasklist
                                proc_result = subprocess.run(
                                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if proc_result.returncode == 0 and proc_result.stdout.strip():
                                    parts = proc_result.stdout.strip('"').split('","')
                                    if len(parts) >= 2:
                                        name = parts[0]
                                        processes.append({"pid": pid, "name": name})
                            except Exception:
                                # Fallback: just add PID without name
                                processes.append({"pid": pid, "name": "unknown"})
        else:
            # Unix implementation using lsof
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str.strip():
                        try:
                            pid = int(pid_str.strip())
                            process = psutil.Process(pid)
                            processes.append({
                                "pid": pid, 
                                "name": process.name()
                            })
                        except (psutil.NoSuchProcess, ValueError):
                            continue
                            
    except Exception as e:
        logger.error(f"Error finding processes on port {port}: {e}")
        
    return processes
```

## Cross-Platform Process Management

### Platform Detection
```python
import sys
import platform

def get_platform_info() -> Dict[str, str]:
    """Get comprehensive platform information"""
    return {
        "system": platform.system(),
        "platform": sys.platform,
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    }

# Example usage:
# Windows: {'system': 'Windows', 'platform': 'win32', 'version': '10.0.26200', ...}
# Linux: {'system': 'Linux', 'platform': 'linux', 'version': '5.15.0', ...}
# macOS: {'system': 'Darwin', 'platform': 'darwin', 'version': '22.6.0', ...}
```

### Process Management Strategies

#### Windows Strategy
1. **Process Detection**: netstat + tasklist combination
2. **Process Termination**: taskkill with /T flag for process trees
3. **Shell Chain Resolution**: psutil process tree navigation
4. **Fallback Methods**: WMIC when psutil unavailable

#### Unix Strategy
1. **Process Detection**: lsof for port mapping
2. **Process Termination**: psutil for clean process tree management
3. **Signal Handling**: Standard Unix signals (SIGTERM, SIGKILL)
4. **Resource Management**: psutil for system resource monitoring

## psutil Integration

### Enhanced Process Monitoring

#### Installation and Setup
```bash
# Install psutil in virtual environment
pip install psutil

# Verify installation
python -c "import psutil; print(psutil.__version__)"
```

#### Process Information Gathering
```python
import psutil

def get_process_info(pid: int) -> Dict[str, Any]:
    """Get comprehensive process information"""
    try:
        process = psutil.Process(pid)
        return {
            "pid": process.pid,
            "name": process.name(),
            "status": process.status(),
            "create_time": process.create_time(),
            "cpu_percent": process.cpu_percent(),
            "memory_info": process.memory_info()._asdict(),
            "num_threads": process.num_threads(),
            "connections": len(process.connections()),
            "children": [child.pid for child in process.children()],
            "parent": process.ppid() if process.ppid() else None
        }
    except psutil.NoSuchProcess:
        return {"error": "Process not found"}
    except psutil.AccessDenied:
        return {"error": "Access denied"}
```

#### System Resource Monitoring
```python
def get_system_resources() -> Dict[str, Any]:
    """Get system resource information"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage('/')._asdict(),
        "network": psutil.net_io_counters()._asdict(),
        "process_count": len(psutil.pids()),
        "boot_time": psutil.boot_time()
    }
```

## Virtual Environment Process Management

### Python Process Detection
```python
def is_python_process_in_venv(process: psutil.Process, venv_path: str) -> bool:
    """Check if a Python process is running in a specific virtual environment"""
    try:
        # Get process command line
        cmdline = process.cmdline()
        
        # Check if any part of the command line references the virtual environment
        for arg in cmdline:
            if venv_path in arg:
                return True
                
        # Check process working directory
        if venv_path in process.cwd():
            return True
            
        # Check environment variables (if accessible)
        try:
            environ = process.environ()
            if 'VIRTUAL_ENV' in environ and venv_path in environ['VIRTUAL_ENV']:
                return True
        except (psutil.AccessDenied, AttributeError):
            pass
            
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
```

### Virtual Environment Service Management
```python
class VirtualEnvironmentServiceManager:
    """Enhanced service manager for virtual environments"""
    
    def __init__(self, venv_path: str):
        self.venv_path = Path(venv_path)
        self.python_exe = self.venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else self.venv_path / "bin" / "python"
    
    def start_service_in_venv(self, service_script: str, *args) -> subprocess.Popen:
        """Start a service in the virtual environment"""
        cmd = [str(self.python_exe), service_script, *args]
        
        if sys.platform == "win32":
            # Windows: handle virtual environment activation
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(self.venv_path)
            env["PATH"] = f"{self.venv_path}\\Scripts;{env['PATH']}"
            
            return subprocess.Popen(
                cmd,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Unix: use virtual environment python directly
            return subprocess.Popen(cmd)
    
    def find_venv_processes(self, service_name: str) -> List[psutil.Process]:
        """Find processes running in this virtual environment"""
        venv_processes = []
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if process.info['name'] == 'python.exe' and is_python_process_in_venv(process, str(self.venv_path)):
                    if service_name in ' '.join(process.info['cmdline'] or []):
                        venv_processes.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return venv_processes
```

## Error Handling and Recovery

### Process Management Error Types

#### Platform-Specific Errors
```python
class ProcessManagementError(Exception):
    """Base exception for process management errors"""
    pass

class WindowsProcessError(ProcessManagementError):
    """Windows-specific process management errors"""
    pass

class UnixProcessError(ProcessManagementError):
    """Unix-specific process management errors"""
    pass

class ProcessNotFoundError(ProcessManagementError):
    """Process not found error"""
    pass

class AccessDeniedError(ProcessManagementError):
    """Access denied for process operation"""
    pass
```

#### Error Recovery Strategies
```python
async def robust_process_termination(pid: int, max_attempts: int = 3) -> bool:
    """Robust process termination with multiple fallback methods"""
    
    for attempt in range(max_attempts):
        try:
            # Method 1: Graceful termination
            process = psutil.Process(pid)
            process.terminate()
            
            # Wait for graceful termination
            gone, alive = psutil.wait_procs([process], timeout=5)
            
            if not alive:
                return True
                
            # Method 2: Force termination
            process.kill()
            gone, alive = psutil.wait_procs([process], timeout=2)
            
            if not alive:
                return True
                
            # Method 3: Platform-specific force kill
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], timeout=5)
            else:
                os.kill(pid, signal.SIGKILL)
                
            return True
            
        except psutil.NoSuchProcess:
            return True  # Process already gone
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for PID {pid}: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(1)
    
    return False
```

## Performance Considerations

### Process Detection Optimization

#### Caching Strategies
```python
class ProcessCache:
    """Cache for process information to reduce system calls"""
    
    def __init__(self, ttl: int = 30):
        self._cache = {}
        self._ttl = ttl
    
    def get_processes_by_port(self, port: int) -> List[Dict]:
        """Get processes by port with caching"""
        cache_key = f"port_{port}"
        current_time = time.time()
        
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._ttl:
                return cached_data
        
        # Cache miss or expired - fetch fresh data
        processes = self._fetch_processes_by_port(port)
        self._cache[cache_key] = (processes, current_time)
        
        return processes
```

### Resource Usage Monitoring

#### System Resource Limits
```python
def check_system_resources() -> Dict[str, bool]:
    """Check if system resources are within acceptable limits"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_ok": cpu_percent < 80,  # Less than 80% CPU usage
        "memory_ok": memory.percent < 80,  # Less than 80% memory usage
        "disk_ok": disk.percent < 90,  # Less than 90% disk usage
        "process_count_ok": len(psutil.pids()) < 500  # Less than 500 processes
    }
```

## Security Considerations

### Process Isolation
- **User Permissions**: Services run with bot user permissions only
- **Port Binding**: Services bind to localhost by default
- **Process Access**: Only authorized processes can be managed
- **Resource Limits**: Implement resource usage limits

### Access Control
```python
def verify_process_ownership(pid: int, expected_user: str = None) -> bool:
    """Verify that a process belongs to the expected user"""
    try:
        process = psutil.Process(pid)
        
        if expected_user:
            # On Unix systems, we can check process ownership
            if hasattr(process, 'uids'):
                return process.uids().real == expected_user
        
        # On Windows, check if we have permission to manage the process
        process.status()  # This will raise AccessDenied if we don't have permission
        return True
        
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
```

## Troubleshooting

### Common Issues

#### Process Tree Termination Failures
- **Symptom**: Child processes continue running after parent termination
- **Solution**: Use platform-specific process tree termination methods
- **Windows**: `taskkill /T /PID <pid>`
- **Unix**: psutil process tree management

#### Shell Chain Resolution Issues
- **Symptom**: Cannot find actual service processes
- **Solution**: Implement multiple PID resolution methods
- **Primary**: psutil process tree navigation
- **Fallback**: WMIC on Windows
- **Last Resort**: Port-based process detection

#### psutil Installation Issues
- **Symptom**: ImportError: No module named 'psutil'
- **Solution**: Install psutil in virtual environment
- **Command**: `pip install psutil`
- **Verification**: `python -c "import psutil"`

### Debug Information
```python
def debug_process_state(pid: int) -> Dict[str, Any]:
    """Get comprehensive debug information for a process"""
    try:
        process = psutil.Process(pid)
        return {
            "basic_info": {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "create_time": process.create_time()
            },
            "resource_usage": {
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "num_threads": process.num_threads()
            },
            "process_tree": {
                "parent": process.ppid(),
                "children": [child.pid for child in process.children(recursive=True)]
            },
            "connections": [
                {
                    "local_address": conn.laddr,
                    "remote_address": conn.raddr,
                    "status": conn.status
                }
                for conn in process.connections()
            ]
        }
    except Exception as e:
        return {"error": str(e)}
```

## Best Practices

### Process Management
1. **Always use process tree termination** to avoid orphaned processes
2. **Implement platform-specific fallbacks** for robust cross-platform support
3. **Use timeouts** for all process operations to prevent hanging
4. **Cache process information** to reduce system call overhead
5. **Verify process ownership** before performing operations

### Virtual Environment Management
1. **Always use virtual environment Python executables** for consistency
2. **Set proper environment variables** for virtual environment activation
3. **Monitor virtual environment processes** separately from system processes
4. **Clean up virtual environment resources** on service shutdown

### Error Handling
1. **Implement graceful degradation** when psutil is unavailable
2. **Use multiple fallback methods** for critical operations
3. **Log all process management operations** for debugging
4. **Handle platform-specific exceptions** appropriately

---
**Module**: Process Management  
**Version**: 1.0  
**Last Updated**: 2025-01-18  
**Dependencies**: psutil, subprocess, asyncio, platform  
**Platform Support**: Windows, Linux, macOS
