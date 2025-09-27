#!/usr/bin/env python3
"""
Entry point for the Live Graphics Dashboard.
This script properly sets up the Python path and runs the FastAPI application.
"""

import os
import sys
import uvicorn

# Add the dashboard directory to Python path
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, dashboard_dir)

if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting Live Graphics Dashboard on port {port}")
    print(f"📂 Dashboard directory: {dashboard_dir}")
    print(f"🌐 Open http://localhost:{port} to view the dashboard")
    print(f"📚 API docs available at http://localhost:{port}/docs")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )