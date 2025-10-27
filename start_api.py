#!/usr/bin/env python3
"""
Script to start the API server
"""
import os
import sys
import subprocess

# Add project root to Python path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

if __name__ == "__main__":
    print("Starting API server...")
    print("API will be available at http://localhost:8000")
    print("API Docs at http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    
    # Start uvicorn using subprocess to allow Ctrl+C to work properly
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])
