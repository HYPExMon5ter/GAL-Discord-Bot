"""
Dashboard Service Manager for automatic startup and lifecycle management.
Handles the FastAPI backend and Next.js frontend services.
"""

import asyncio
import logging
import os
import sys
import signal
import subprocess
import time
import psutil
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DashboardManager:
    """
    Manages dashboard services (API backend and frontend) lifecycle.
    Provides automatic startup, health monitoring, and graceful shutdown.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize dashboard manager.
        
        Args:
            project_root: Root directory of the project. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.api_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self._startup_complete = False
        self._shutdown_requested = False
        
        # Service configuration
        self.api_port = 8000
        self.frontend_port = 8080  # Use port 8080 for Railway deployment
        self.health_check_interval = 30
        self.max_startup_attempts = 3
        
        # PID files for duplicate instance prevention
        self.api_pid_file = self.project_root / ".dashboard_api.pid"
        self.frontend_pid_file = self.project_root / ".dashboard_frontend.pid"
        
        # Track actual service PIDs (not shell intermediates)
        self._actual_api_pids: List[int] = []
        self._actual_frontend_pids: List[int] = []

    async def start_services(self) -> bool:
        """
        Start all dashboard services (API and frontend).
        
        Returns:
            True if services started successfully, False otherwise.
        """
        if self._startup_complete:
            logger.warning("Dashboard services already started")
            return True
            
        if self._shutdown_requested:
            logger.warning("Cannot start services after shutdown requested")
            return False

        logger.info("Starting dashboard services...")
        
        # Check for existing instances
        if await self._check_existing_instances():
            logger.warning("Dashboard services already running - skipping startup")
            return True

        try:
            # Start API backend first
            if not await self._start_api_service():
                logger.error("Failed to start API service")
                return False
                
            # Wait for API to be ready
            if not await self._wait_for_api_ready():
                logger.error("API service failed to become ready")
                await self.stop_services()
                return False

            # Start frontend
            if not await self._start_frontend_service():
                logger.error("Failed to start frontend service")
                await self.stop_services()
                return False

            self._startup_complete = True
            logger.info("✅ Dashboard services started successfully")
            logger.info(f"📊 Frontend: http://localhost:{self.frontend_port}")
            logger.info(f"🔧 Backend API: http://localhost:{self.api_port}")
            logger.info(f"📚 API Docs: http://localhost:{self.api_port}/docs")
            
            return True

        except Exception as e:
            logger.error(f"Failed to start dashboard services: {e}")
            await self.stop_services()
            return False

    async def stop_services(self) -> None:
        """
        Stop all dashboard services gracefully with enhanced cleanup.
        """
        if not self._startup_complete:
            return

        logger.info("Stopping dashboard services...")
        self._shutdown_requested = True

        # Enhanced cleanup: stop services by port first (primary method)
        await self._cleanup_services_by_ports()
        
        # Then try to stop tracked processes
        await self._stop_tracked_processes()
        
        # Cleanup PID files
        await self._cleanup_pid_files()
        
        # Final verification and force cleanup if needed
        await self._verify_and_force_cleanup()

        self._startup_complete = False
        self._actual_api_pids.clear()
        self._actual_frontend_pids.clear()
        logger.info("Dashboard services stopped")

    async def _check_existing_instances(self) -> bool:
        """
        Check if dashboard services are already running to prevent duplicates.
        
        Returns:
            True if services are already running, False otherwise.
        """
        # Check API PID file
        if self.api_pid_file.exists():
            try:
                with open(self.api_pid_file, 'r') as f:
                    api_pid = int(f.read().strip())
                # Check if process is still running
                if self._is_process_running(api_pid):
                    logger.info(f"API service already running (PID: {api_pid})")
                    return True
                else:
                    # Stale PID file
                    self.api_pid_file.unlink()
            except (ValueError, FileNotFoundError, ProcessLookupError):
                self.api_pid_file.unlink()

        # Check Frontend PID file
        if self.frontend_pid_file.exists():
            try:
                with open(self.frontend_pid_file, 'r') as f:
                    frontend_pid = int(f.read().strip())
                if self._is_process_running(frontend_pid):
                    logger.info(f"Frontend service already running (PID: {frontend_pid})")
                    return True
                else:
                    # Stale PID file
                    self.frontend_pid_file.unlink()
            except (ValueError, FileNotFoundError, ProcessLookupError):
                self.frontend_pid_file.unlink()

        return False

    async def _cleanup_services_by_ports(self) -> None:
        """
        Clean up services using port-based process killing.
        This is the primary cleanup method that works across different platforms.
        """
        logger.info(f"Cleaning up services on ports {self.api_port} and {self.frontend_port}...")
        
        # Kill processes using API port
        api_killed = await self._kill_processes_by_port(self.api_port, ["python.exe", "uvicorn"])
        if api_killed > 0:
            logger.info(f"Killed {api_killed} process(es) using API port {self.api_port}")
        
        # Kill processes using frontend port
        frontend_killed = await self._kill_processes_by_port(self.frontend_port, ["node.exe"])
        if frontend_killed > 0:
            logger.info(f"Killed {frontend_killed} process(es) using frontend port {self.frontend_port}")
    
    async def _kill_processes_by_port(self, port: int, process_names: List[str]) -> int:
        """
        Kill processes using a specific port, filtered by process name.
        
        Args:
            port: Port number to check
            process_names: List of allowed process names to kill
            
        Returns:
            Number of processes killed
        """
        killed_count = 0
        
        try:
            # Find processes using the port
            processes_on_port = self._find_processes_by_port(port)
            
            for proc_info in processes_on_port:
                pid = proc_info["pid"]
                name = proc_info["name"]
                
                # Only kill if it's one of our target process types
                if name.lower() in [p.lower() for p in process_names]:
                    try:
                        # Kill the process and all its children
                        killed_count += await self._kill_process_tree(pid)
                        logger.info(f"Killed process {name} (PID: {pid}) using port {port}")
                    except Exception as e:
                        logger.warning(f"Failed to kill process {name} (PID: {pid}): {e}")
                else:
                    logger.debug(f"Skipping process {name} (PID: {pid}) on port {port} - not a target process")
                    
        except Exception as e:
            logger.error(f"Error killing processes on port {port}: {e}")
            
        return killed_count
    
    def _find_processes_by_port(self, port: int) -> List[Dict]:
        """
        Find all processes using a specific port.
        
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
                                    # Get process name
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
                # Unix-like systems: use lsof
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
    
    async def _kill_process_tree(self, pid: int) -> int:
        """
        Kill a process and all its children.
        
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
                # Unix-like: use psutil for proper process tree killing
                try:
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
                            
                except psutil.NoSuchProcess:
                    # Process already gone
                    pass
                    
        except Exception as e:
            logger.warning(f"Error killing process tree for PID {pid}: {e}")
            
        return killed_count
    
    async def _stop_tracked_processes(self) -> None:
        """
        Stop the processes we explicitly started and tracked.
        """
        # Stop frontend first (it depends on API)
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                await asyncio.sleep(2)
                if self.frontend_process.poll() is None:
                    self.frontend_process.kill()
                logger.info("Frontend service stopped")
            except Exception as e:
                logger.error(f"Error stopping frontend: {e}")
            finally:
                self.frontend_process = None

        # Stop API
        if self.api_process:
            try:
                self.api_process.terminate()
                await asyncio.sleep(2)
                if self.api_process.poll() is None:
                    self.api_process.kill()
                logger.info("API service stopped")
            except Exception as e:
                logger.error(f"Error stopping API: {e}")
            finally:
                self.api_process = None
    
    async def _cleanup_pid_files(self) -> None:
        """
        Clean up PID files.
        """
        try:
            if self.frontend_pid_file.exists():
                self.frontend_pid_file.unlink()
                logger.debug("Removed frontend PID file")
        except Exception as e:
            logger.warning(f"Error removing frontend PID file: {e}")
            
        try:
            if self.api_pid_file.exists():
                self.api_pid_file.unlink()
                logger.debug("Removed API PID file")
        except Exception as e:
            logger.warning(f"Error removing API PID file: {e}")
    
    async def _verify_and_force_cleanup(self) -> None:
        """
        Verify that ports are actually free and force cleanup if needed.
        """
        await asyncio.sleep(2)  # Give processes time to terminate
        
        # Check if ports are still in use
        api_processes = self._find_processes_by_port(self.api_port)
        frontend_processes = self._find_processes_by_port(self.frontend_port)
        
        if api_processes:
            logger.warning(f"Port {self.api_port} still in use after cleanup, forcing termination")
            for proc_info in api_processes:
                await self._kill_process_tree(proc_info["pid"])
                
        if frontend_processes:
            logger.warning(f"Port {self.frontend_port} still in use after cleanup, forcing termination")
            for proc_info in frontend_processes:
                await self._kill_process_tree(proc_info["pid"])

    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process with the given PID is running.
        """
        try:
            if sys.platform == "win32":
                # Windows approach
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                      capture_output=True, text=True)
                return str(pid) in result.stdout
            else:
                # Unix approach
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False

    async def _start_api_service(self) -> bool:
        """
        Start the FastAPI backend service.
        
        Returns:
            True if API started successfully, False otherwise.
        """
        logger.info("Starting FastAPI backend...")
        
        api_dir = self.project_root / "api"
        if not api_dir.exists():
            logger.error(f"API directory not found: {api_dir}")
            return False

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)

        try:
            # Use uvicorn to start the API from project root directory
            # This ensures relative imports work correctly
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "api.main:app",
                "--host", "0.0.0.0",
                "--port", str(self.api_port),
                "--reload"
            ]

            # Start from project root directory, not api directory
            # This ensures utils module can be found during import
            self.api_process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(self.project_root)  # Changed from api_dir to project_root
            )

            # Try to find the actual Python process (not cmd.exe on Windows)
            actual_pid = self._find_actual_service_pid(self.api_process.pid, "python.exe")
            if actual_pid:
                self._actual_api_pids.append(actual_pid)
            
            # Write PID file
            with open(self.api_pid_file, 'w') as f:
                f.write(str(actual_pid or self.api_process.pid))

            logger.info(f"API service started (PID: {self.api_process.pid}, actual: {actual_pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start API service: {e}")
            return False

    async def _start_frontend_service(self) -> bool:
        """
        Start the Next.js frontend service in production mode.
        
        Returns:
            True if frontend started successfully, False otherwise.
        """
        logger.info("Starting Next.js frontend (production mode)...")
        
        frontend_dir = self.project_root / "dashboard"
        if not frontend_dir.exists():
            logger.error(f"Frontend directory not found: {frontend_dir}")
            return False

        try:
            # Check if production build exists (verify BUILD_ID file exists)
            build_id_file = frontend_dir / ".next" / "BUILD_ID"
            if not build_id_file.exists():
                logger.warning("Production build not found - falling back to development mode")
                logger.info("💡 To fix this, run 'npm run build' in the dashboard directory or deploy with Docker")
                
                # Fall back to development mode
                if sys.platform == "win32":
                    cmd_str = "npm run dev"
                    self.frontend_process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        cwd=str(frontend_dir),
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    self.frontend_process = subprocess.Popen(
                        ["npm", "run", "dev"],
                        cwd=str(frontend_dir)
                    )
            else:
                # Production build exists - use production mode
                logger.info("Starting Next.js in production mode...")
                if sys.platform == "win32":
                    cmd_str = "npm start"
                    self.frontend_process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        cwd=str(frontend_dir),
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    self.frontend_process = subprocess.Popen(
                        ["npm", "start"],
                        cwd=str(frontend_dir)
                    )

            # Try to find the actual Node.js process (not cmd.exe on Windows)
            actual_pid = self._find_actual_service_pid(self.frontend_process.pid, "node.exe")
            if actual_pid:
                self._actual_frontend_pids.append(actual_pid)
            
            # Write PID file
            with open(self.frontend_pid_file, 'w') as f:
                f.write(str(actual_pid or self.frontend_process.pid))

            mode = "production" if build_id_file.exists() else "development"
            logger.info(f"Frontend service started in {mode} mode (PID: {self.frontend_process.pid}, actual: {actual_pid})")
            logger.info(f"📊 Dashboard URL: http://localhost:{self.frontend_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start frontend service: {e}")
            return False

    async def _wait_for_api_ready(self) -> bool:
        """
        Wait for the API service to be ready to accept requests.
        
        Returns:
            True if API becomes ready, False otherwise.
        """
        import aiohttp
        
        for attempt in range(self.max_startup_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{self.api_port}/health", 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info("API service is ready")
                            return True
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            
            logger.info(f"Waiting for API to be ready... (attempt {attempt + 1}/{self.max_startup_attempts})")
            await asyncio.sleep(3)
        
        logger.error("API service failed to become ready")
        return False

    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of all dashboard services.
        
        Returns:
            Dictionary containing service status information.
        """
        status = {
            "startup_complete": self._startup_complete,
            "shutdown_requested": self._shutdown_requested,
            "api": {
                "running": self.api_process is not None and self.api_process.poll() is None,
                "pid": self.api_process.pid if self.api_process else None,
                "port": self.api_port
            },
            "frontend": {
                "running": self.frontend_process is not None and self.frontend_process.poll() is None,
                "pid": self.frontend_process.pid if self.frontend_process else None,
                "port": self.frontend_port
            }
        }
        
        return status

    async def health_check(self) -> bool:
        """
        Perform health check on dashboard services.
        
        Returns:
            True if all services are healthy, False otherwise.
        """
        try:
            import aiohttp
            
            # Check API health
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{self.api_port}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status != 200:
                            return False
                except aiohttp.ClientError:
                    return False

            # Check frontend (basic connectivity)
            try:
                async with session.get(
                    f"http://localhost:{self.frontend_port}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Frontend should return some response
                    return response.status < 500
            except aiohttp.ClientError:
                return False

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def __del__(self):
        """
        Cleanup when the manager is destroyed.
        """
        if self._startup_complete and not self._shutdown_requested:
            logger.warning("DashboardManager destroyed without proper shutdown - attempting cleanup")
            try:
                if self.api_process:
                    self.api_process.terminate()
                if self.frontend_process:
                    self.frontend_process.terminate()
            except Exception:
                pass
    
    def _find_actual_service_pid(self, shell_pid: int, target_process_name: str) -> Optional[int]:
        """
        Find the actual service process PID when spawned through a shell.
        
        Args:
            shell_pid: PID of the shell process
            target_process_name: Name of the target process (e.g., 'python.exe', 'node.exe')
            
        Returns:
            Actual service process PID or None if not found
        """
        if sys.platform != "win32":
            return shell_pid  # On Unix, we usually don't have shell intermediates
        
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
            # psutil not available, fallback to Windows-specific method
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
                                try:
                                    return int(parts[1])  # ProcessId is usually second column
                                except ValueError:
                                    continue
            except Exception:
                pass
        
        return None


# Global instance for bot integration
_dashboard_manager: Optional[DashboardManager] = None


def get_dashboard_manager() -> DashboardManager:
    """
    Get the global dashboard manager instance.
    """
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager


async def start_dashboard_services() -> bool:
    """
    Convenience function to start dashboard services.
    """
    manager = get_dashboard_manager()
    return await manager.start_services()


async def stop_dashboard_services() -> None:
    """
    Convenience function to stop dashboard services.
    """
    manager = get_dashboard_manager()
    await manager.stop_services()
