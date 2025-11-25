# Fix Reverse Proxy - Remove Conflicting Root Endpoint

## Issue
The explicit `@app.get("/")` endpoint in api/main.py intercepts requests before the proxy catch-all route can handle them. FastAPI routes match in order of specificity, so explicit routes take priority over catch-all routes.

## Solution
Remove the root endpoint to allow the reverse proxy to handle `/` and `/dashboard` requests correctly.

## Changes:
- Delete the explicit `@app.get("/")` route that returns API JSON
- Keep the `/health` endpoint for health checks
- The catch-all `@app.api_route("/{path:path}")` will proxy all non-API routes to Next.js

## Expected Result:
- Root URL will serve the dashboard frontend (Next.js)
- Dashboard page will work properly
- API routes remain accessible via /api/* prefix
