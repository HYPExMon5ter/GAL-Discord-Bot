#!/usr/bin/env python3
"""
Simple dashboard startup script
"""
import subprocess
import sys
import time
import os


def start_api():
    """Start the FastAPI backend"""
    print("Starting FastAPI backend...")
    api_dir = os.path.join(os.path.dirname(__file__), "api")
    os.chdir(api_dir)

    # Use uvicorn directly with proper path setup
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(__file__)

    try:
        # Use shell=True for Windows compatibility
        cmd = f'{sys.executable} -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload'
        process = subprocess.Popen(cmd, shell=True, env=env)
        return process
    except Exception as e:
        print(f"Failed to start API: {e}")
        return None


def start_frontend():
    """Start the Next.js frontend"""
    print("Starting Next.js frontend...")
    dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
    os.chdir(dashboard_dir)

    try:
        # Check if node_modules exists
        if not os.path.exists("node_modules"):
            print("Installing dependencies...")
            subprocess.run(["npm", "install"], check=True, shell=True)

        # Use shell=True for Windows compatibility
        process = subprocess.Popen("npm run dev", shell=True)
        return process
    except Exception as e:
        print(f"Failed to start frontend: {e}")
        return None


if __name__ == "__main__":
    print("Guardian Angel League Dashboard Starting Up...")
    print("=" * 50)

    # Start API first
    api_process = start_api()
    if not api_process:
        sys.exit(1)

    # Wait a moment for API to start
    time.sleep(3)

    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        api_process.terminate()
        sys.exit(1)

    print("\nDashboard is starting up!")
    print("Frontend: http://localhost:3000")
    print("Backend API: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both services")

    try:
        # Wait for processes
        api_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        api_process.terminate()
        frontend_process.terminate()
        print("Services stopped")
