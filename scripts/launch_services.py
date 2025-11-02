#!/usr/bin/env python3
"""
Guardian Angel League - Service Launcher
Launches both the FastAPI backend and Next.js frontend dashboard.

Usage:
    python scripts/launch_services.py  # Cross-platform
    Ctrl+C to stop both services gracefully
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

class ServiceLauncher:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.api_process = None
        self.frontend_process = None
        
    def start_api(self):
        """Start the FastAPI backend"""
        print("🚀 Starting FastAPI backend...")
        print(f"📁 Project root: {self.project_root}")
        
        # Ensure we're in the project root directory
        os.chdir(self.project_root)
        
        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)
        
        try:
            # Start uvicorn using subprocess
            cmd = [sys.executable, "-m", "uvicorn", 
                   "api.main:app",
                   "--host", "0.0.0.0", 
                   "--port", "8000",
                   "--reload"]
            
            self.api_process = subprocess.Popen(
                cmd, 
                env=env, 
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            print(f"✅ API started (PID: {self.api_process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start API: {e}")
            return False
    
    def start_frontend(self):
        """Start the Next.js frontend"""
        print("🎨 Starting Next.js frontend...")
        
        dashboard_dir = self.project_root / "dashboard"
        os.chdir(dashboard_dir)
        
        try:
            # Check if node_modules exists
            if not (dashboard_dir / "node_modules").exists():
                print("📦 Installing dependencies...")
                subprocess.run(["npm", "install"], check=True)
            
            # Start npm run dev
            self.frontend_process = subprocess.Popen(
                "npm run dev",
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            print(f"✅ Frontend started (PID: {self.frontend_process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
    
    def stop_services(self):
        """Stop all services gracefully"""
        print("\n🛑 Stopping services...")
        
        if self.frontend_process:
            print("   Stopping frontend...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
        
        if self.api_process:
            print("   Stopping API...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
        
        print("✅ All services stopped")
    
    def run(self):
        """Main launcher function"""
        print("=" * 60)
        print("🎮 Guardian Angel League Dashboard Launcher")
        print("=" * 60)
        
        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print(f"\nReceived signal {sig}")
            self.stop_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start API first
        if not self.start_api():
            print("❌ Failed to start API service")
            return 1
        
        # Wait for API to initialize
        print("⏳ Waiting for API to initialize...")
        time.sleep(5)
        
        # Start frontend
        if not self.start_frontend():
            print("❌ Failed to start frontend service")
            self.stop_services()
            return 1
        
        print("\n" + "=" * 60)
        print("🎉 Dashboard is running!")
        print("=" * 60)
        print("📊 Frontend:    http://localhost:3000")
        print("🔧 Backend API: http://localhost:8000")
        print("📚 API Docs:   http://localhost:8000/docs")
        print("=" * 60)
        print("💡 Press Ctrl+C to stop both services")
        print("=" * 60)
        
        try:
            # Keep the launcher running
            while True:
                time.sleep(1)
                
                # Check if processes are still running
                if self.api_process.poll() is not None:
                    print("❌ API process died unexpectedly")
                    self.stop_services()
                    return 1
                
                if self.frontend_process.poll() is not None:
                    print("❌ Frontend process died unexpectedly")
                    self.stop_services()
                    return 1
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
            self.stop_services()
            return 0
        
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.stop_services()
            return 1

def main():
    """Entry point"""
    launcher = ServiceLauncher()
    exit_code = launcher.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
