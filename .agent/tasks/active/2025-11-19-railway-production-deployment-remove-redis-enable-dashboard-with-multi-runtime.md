## Analysis Summary

### Redis Usage
Redis is used in 2 places but **never actually operational**:
1. **`core/data_access/cache_manager.py`** - Optional Redis caching (disabled by default)
2. **`api/services/ign_verification.py`** - Optional caching (graceful degradation already implemented)

Both already have fallback to in-memory caching, so **safe to remove entirely**.

### Code Dependencies
✅ **Good news**: The architecture is already well-separated!
- **API → Core/Utils**: API imports from `core` and `utils` (shared repositories, models)
- **Bot → API**: Only 1 import: `core.commands.placement` imports `api.routers.websocket.send_placement_update`
- **Dashboard**: Pure Next.js frontend, only communicates via HTTP API calls

**Recommendation**: Keep everything in monorepo, just need multi-runtime Railway deployment.

---

## Solution: Multi-Runtime Railway Deployment

### Option 1: Single Dockerfile with Multi-Stage Build (RECOMMENDED)
✅ **Pros**: 
- Single Railway service
- Shared file system for database/config
- Simplest deployment
- All processes in one container

❌ **Cons**:
- Slightly larger image (~150MB for Node.js + Python)

### Implementation Plan

#### 1. **Remove Redis Completely**
- Remove `redis>=6.4` from `requirements.txt`
- Update `core/__init__.py` - change `redis_enabled: True` → `False`
- Remove Redis initialization from `api/services/ign_verification.py`
- Remove Redis imports and related code from `cache_manager.py`

#### 2. **Create Multi-Runtime Dockerfile**
```dockerfile
FROM node:20-slim AS frontend-builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci --only=production
COPY dashboard/ ./
RUN npm run build

FROM python:3.12-slim
# Install Node.js runtime for Next.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Copy Python app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend
COPY --from=frontend-builder /app/dashboard ./dashboard

# Copy application code
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Expose ports
EXPOSE 8000 3000

# Start script will run both services
CMD ["python", "bot.py"]
```

#### 3. **Update Dashboard Manager**
- Remove Node.js availability check (always available in container)
- Remove npm installation logic (dependencies pre-built)
- Update to use `npm start` (production mode) instead of `npm run dev`
- Add proper health checks for Railway environment

#### 4. **Add Startup Script** (Optional - Better Control)
Create `start.sh`:
```bash
#!/bin/bash
# Start API in background
cd /app && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Start Next.js frontend in background  
cd /app/dashboard && npm start &

# Start Discord bot (foreground)
cd /app && python bot.py
```

#### 5. **Update Railway Configuration**
Add `railway.toml` (or configure in Railway UI):
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python bot.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
```

#### 6. **Environment Variables for Railway**
Required Railway environment variables:
```bash
# Discord
DISCORD_TOKEN=<token>
APPLICATION_ID=<id>

# Database (use Railway PostgreSQL add-on)
DATABASE_URL=postgresql://...

# Environment
RAILWAY_ENVIRONMENT_NAME=production
ENABLE_DASHBOARD=true

# Riot API (if used)
RIOT_API_KEY=<key>

# NO REDIS_URL needed anymore!
```

#### 7. **Update Bot Startup Logic**
- Add environment check: `ENABLE_DASHBOARD` env var
- If Railway + dashboard enabled, start all services
- Improve error handling for dashboard startup failures
- Add Railway-specific logging

---

## File Changes Summary

### Files to Modify:
1. **`requirements.txt`** - Remove `redis>=6.4`
2. **`core/__init__.py`** - Set `redis_enabled: False`
3. **`core/data_access/cache_manager.py`** - Remove Redis class and imports
4. **`api/services/ign_verification.py`** - Remove Redis code, keep in-memory fallback
5. **`services/dashboard_manager.py`** - Update for production Next.js deployment
6. **`bot.py`** - Add `ENABLE_DASHBOARD` environment check

### Files to Create:
1. **`Dockerfile`** - Multi-stage build with Node.js + Python
2. **`railway.toml`** - Railway deployment configuration
3. **`start.sh`** (optional) - Process orchestration script
4. **`.dockerignore`** - Optimize build performance

### Files to Update (documentation):
1. **`README.md`** - Update deployment instructions
2. **`.env.example`** - Add ENABLE_DASHBOARD, remove REDIS_URL

---

## Deployment Flow

1. Railway detects Dockerfile
2. Multi-stage build:
   - Stage 1: Build Next.js frontend
   - Stage 2: Install Python deps + copy built frontend
3. Container starts with `python bot.py`
4. Bot startup checks `ENABLE_DASHBOARD=true`
5. Dashboard manager starts:
   - FastAPI backend on port 8000
   - Next.js frontend on port 3000 (production mode)
6. Bot continues normal operation
7. All services share filesystem for SQLite DB

---

## Testing Checklist

- [ ] Local Docker build succeeds
- [ ] Bot starts without Redis errors
- [ ] Dashboard starts in production mode
- [ ] API endpoints accessible
- [ ] Frontend loads correctly
- [ ] WebSocket connections work
- [ ] Database persistence works
- [ ] Railway deployment succeeds
- [ ] Health checks pass

---

## Rollback Plan

If issues occur:
1. Set `ENABLE_DASHBOARD=false` in Railway
2. Bot continues operating without dashboard
3. Investigate and fix dashboard issues
4. Re-enable when ready

---

This approach keeps everything in one monorepo, removes unused Redis, and enables the dashboard in production with minimal complexity.