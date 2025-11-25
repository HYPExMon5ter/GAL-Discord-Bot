# Fix Railway Production Dashboard - Single URL Access

## Issue
Railway only exposes port 8000 (API) publicly. The Next.js frontend runs on port 8080 internally but is not accessible from the public URL.

## Solution
Implement a reverse proxy in FastAPI to route non-API requests to the Next.js frontend.

### Changes Made:
1. Add httpx to requirements.txt for HTTP proxying
2. Update dashboard_manager.py to use port 8080 for frontend
3. Update dashboard/package.json to start Next.js on port 8080
4. Add proxy middleware to api/main.py to route requests correctly

### Expected Result:
- Root URL serves the dashboard frontend
- API routes continue to work normally
- Everything accessible through a single Railway URL
