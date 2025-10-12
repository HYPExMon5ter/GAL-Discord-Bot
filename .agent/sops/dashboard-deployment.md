---
id: sops.dashboard_deployment
version: 2.0
last_updated: 2025-10-11
tags: [sop, deployment, frontend, build, ci-cd]
---

# Dashboard Deployment SOP

## Overview
This Standard Operating Procedure (SOP) outlines the comprehensive process for building, testing, and deploying the Live Graphics Dashboard 2.0 frontend application to production environments.

## Purpose
- Ensure consistent and reliable deployment processes
- Minimize downtime during updates
- Maintain quality standards across all deployments
- Provide rollback capabilities for failed deployments

## Scope
- Next.js application builds
- Production deployment procedures
- Environment configuration management
- CI/CD pipeline operations
- Rollback and recovery procedures

## Prerequisites
- Completed deployment training
- Appropriate access credentials for all environments
- Understanding of Next.js build processes
- Familiarity with Docker and container management

## Environment Architecture

### Environments
1. **Development** (`dev.gal.gg`)
   - Latest development builds
   - Hot reload enabled
   - Debug mode active
   - Connected to development API

2. **Staging** (`staging.gal.gg`)
   - Production-like environment
   - Latest approved builds
   - Performance testing
   - Connected to staging API

3. **Production** (`dashboard.gal.gg`)
   - Live production environment
   - Stable builds only
   - Performance optimized
   - Connected to production API

### Infrastructure Components
```
Production Architecture:
├── Load Balancer (CloudFlare)
├── CDN (CloudFlare CDN)
├── Web Servers (Docker Containers)
│   ├── Next.js Application
│   ├── Static Assets
│   └── Environment Configuration
├── API Backend
└── Monitoring & Logging
```

## Build and Deployment Process

### 1. Pre-Deployment Preparation

#### 1.1 Code Review Requirements
1. **All Changes Must**
   - Have approved pull requests
   - Pass automated tests
   - Complete code review process
   - Include documentation updates

2. **Quality Gates**
   - No failing tests
   - Code coverage > 80%
   - No TypeScript errors
   - ESLint checks passing
   - Performance budgets met

#### 1.2 Environment Preparation
1. **Check Environment Status**
   ```bash
   # Verify staging environment health
   curl -f https://staging.gal.gg/health
   
   # Check API connectivity
   curl -f https://api.staging.gal.gg/health
   
   # Monitor current active users
   curl -s https://api.staging.gal.gg/metrics/active-users
   ```

2. **Backup Current Configuration**
   ```bash
   # Export current environment variables
   docker exec dashboard-prod env > backup-$(date +%Y%m%d).env
   
   # Backup current build artifacts
   docker cp dashboard-prod:/app/.next ./backup-build-$(date +%Y%m%d)
   ```

### 2. Build Process

#### 2.1 Local Build Testing
1. **Setup Environment**
   ```bash
   # Clone latest code
   git checkout main
   git pull origin main
   
   # Install dependencies
   npm ci --production=false
   
   # Copy environment configuration
   cp .env.production.example .env.local
   ```

2. **Execute Build**
   ```bash
   # Run tests first
   npm run test
   
   # Type checking
   npm run type-check
   
   # Build application
   npm run build
   
   # Verify build output
   ls -la .next/
   ```

3. **Build Validation**
   ```bash
   # Start production build locally
   npm run start
   
   # Run smoke tests
   npm run test:smoke
   
   # Performance testing
   npm run test:performance
   ```

#### 2.2 CI/CD Pipeline Build
1. **GitHub Actions Workflow**
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy Dashboard
   on:
     push:
       branches: [main]
   
   jobs:
     build-and-deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-node@v3
           with:
             node-version: '18'
             cache: 'npm'
         
         - name: Install dependencies
           run: npm ci
         
         - name: Run tests
           run: npm run test:ci
         
         - name: Build application
           run: npm run build
           env:
             NEXT_PUBLIC_API_URL: ${{ secrets.PROD_API_URL }}
             NEXT_PUBLIC_WS_URL: ${{ secrets.PROD_WS_URL }}
         
         - name: Build Docker image
           run: |
             docker build -t gal/dashboard:${{ github.sha }} .
             docker tag gal/dashboard:${{ github.sha }} gal/dashboard:latest
         
         - name: Deploy to production
           run: |
             # Deployment commands here
   ```

### 3. Deployment Procedures

#### 3.1 Blue-Green Deployment Strategy
1. **Preparation Phase**
   ```bash
   # Create new deployment environment
   docker-compose -f docker-compose.blue.yml up -d
   
   # Wait for health check
   docker-compose -f docker-compose.blue.yml exec -T \
     dashboard curl -f http://localhost:3000/health
   
   # Run smoke tests on new deployment
   npm run test:smoke -- --env=blue
   ```

2. **Traffic Switching**
   ```bash
   # Update load balancer configuration
   # This is typically done through provider dashboard or API
   
   # Verify traffic routing
   curl -H "Host: dashboard.gal.gg" http://load-balancer/health
   
   # Monitor new deployment health
   docker logs -f dashboard-blue
   ```

3. **Old Deployment Cleanup**
   ```bash
   # Keep old deployment for rollback window (30 minutes)
   sleep 1800
   
   # If no issues, cleanup old deployment
   docker-compose -f docker-compose.green.yml down
   docker rmi gal/dashboard:previous
   ```

#### 3.2 Rolling Update Strategy
1. **Update Configuration**
   ```bash
   # Update Docker Compose configuration
   sed -i 's/gal-dashboard:latest/gal-dashboard:${NEW_VERSION}/' docker-compose.yml
   
   # Pull new image
   docker-compose pull dashboard
   ```

2. **Execute Rolling Update**
   ```bash
   # Update service with rolling restart
   docker-compose up -d --no-deps dashboard
   
   # Monitor update progress
   docker-compose ps
   
   # Verify all instances healthy
   docker-compose exec dashboard curl -f http://localhost:3000/health
   ```

### 4. Environment Configuration

#### 4.1 Production Environment Variables
```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.gal.gg
NEXT_PUBLIC_WS_URL=wss://api.gal.gg/ws
NEXT_PUBLIC_APP_NAME=Live Graphics Dashboard
NEXT_PUBLIC_VERSION=2.0.0
NEXT_PUBLIC_ENVIRONMENT=production

# Security
NEXTAUTH_URL=https://dashboard.gal.gg
NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
NEXTAUTH_ISSUER=https://auth.gal.gg

# Analytics
NEXT_PUBLIC_GA_ID=${GA_ID}
NEXT_PUBLIC_SENTRY_DSN=${SENTRY_DSN}

# Feature Flags
NEXT_PUBLIC_FEATURE_DARK_MODE=true
NEXT_PUBLIC_FEATURE_BETA_GRAPHICS=false
```

#### 4.2 Docker Configuration
```dockerfile
# Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Build the application
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### 5. Monitoring and Verification

#### 5.1 Health Checks
```javascript
// app/api/health/route.ts
export async function GET() {
  const checks = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_VERSION,
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    checks: {
      database: await checkDatabase(),
      redis: await checkRedis(),
      api: await checkBackendAPI()
    }
  };
  
  const isHealthy = Object.values(checks.checks).every(check => check.status === 'ok');
  
  return Response.json(checks, {
    status: isHealthy ? 200 : 503,
    headers: {
      'Cache-Control': 'no-cache'
    }
  });
}
```

#### 5.2 Performance Monitoring
```bash
# Core Web Vitals monitoring
npm run test:lighthouse -- --chrome-flags="--headless" --output=json

# Bundle size analysis
npm run analyze

# Real User Monitoring integration
# Sentry Real User Monitoring configured
# CloudFlare Analytics enabled
```

#### 5.3 Error Monitoring
```javascript
// app/utils/errorTracking.ts
import * as Sentry from '@sentry/nextjs';

export function reportError(error: Error, context?: any) {
  Sentry.captureException(error, {
    contexts: {
      application: context
    }
  });
}

export function reportMessage(message: string, level: Sentry.SeverityLevel) {
  Sentry.captureMessage(message, level);
}
```

### 6. Rollback Procedures

#### 6.1 Immediate Rollback (Blue-Green)
```bash
# Switch traffic back to previous deployment
# Update load balancer configuration to point to green environment

# Verify rollback success
curl -H "Host: dashboard.gal.gg" http://load-balancer/health

# Monitor rollback health
docker logs -f dashboard-green
```

#### 6.2 Version Rollback
```bash
# Deploy previous version
git checkout ${PREVIOUS_VERSION_TAG}
npm ci
npm run build
docker build -t gal/dashboard:${PREVIOUS_VERSION} .
docker tag gal/dashboard:${PREVIOUS_VERSION} gal/dashboard:latest
docker-compose up -d
```

#### 6.3 Database Rollback
```bash
# If database changes were made, rollback schema
docker-compose exec api python -m alembic downgrade -1

# Restore database backup if needed
docker-compose exec db psql -U gal -d gal_dashboard < backup.sql
```

### 7. Deployment Validation

#### 7.1 Smoke Tests
```bash
# Essential functionality tests
npm run test:smoke

# Test cases include:
# - User authentication
# - Dashboard loading
# - WebSocket connections
# - Basic graphic operations
```

#### 7.2 Integration Tests
```bash
# Full workflow testing
npm run test:integration

# Test cases include:
# - Graphic creation and editing
# - Real-time updates
# - Multi-user interactions
# - Canvas locking
```

#### 7.3 Performance Tests
```bash
# Load testing
npm run test:load

# Performance benchmarks
npm run test:performance

# Memory leak detection
npm run test:memory
```

### 8. Incident Response

#### 8.1 Deployment Failure Response
1. **Immediate Actions**
   - Stop deployment process
   - Assess failure impact
   - Notify incident response team
   - Document failure details

2. **Investigation**
   - Review deployment logs
   - Check system resources
   - Analyze error messages
   - Identify root cause

3. **Resolution**
   - Implement fix or rollback
   - Verify resolution success
   - Conduct post-mortem
   - Update procedures

#### 8.2 Performance Degradation Response
1. **Monitoring**
   - Check key performance indicators
   - Monitor error rates
   - Track user complaints
   - Analyze system metrics

2. **Mitigation**
   - Scale resources if needed
   - Enable caching
   - Optimize database queries
   - Temporary feature disabling

## Maintenance Procedures

### 9.1 Regular Maintenance
1. **Daily Tasks**
   - Monitor deployment health
   - Review error logs
   - Check performance metrics
   - Verify backup integrity

2. **Weekly Tasks**
   - Update dependencies
   - Review deployment metrics
   - Optimize build process
   - Update documentation

3. **Monthly Tasks**
   - Security vulnerability scanning
   - Performance optimization review
   - Capacity planning
   - Procedure updates

### 9.2 Dependency Management
```bash
# Check for outdated dependencies
npm outdated

# Update major dependencies (requires testing)
npm update package-name

# Security audit
npm audit

# Fix security vulnerabilities
npm audit fix
```

## Documentation Requirements

### Deployment Logs
Each deployment must include:
- Deployment timestamp
- Version deployed
- Environment deployed to
- Test results
- Performance metrics
- Issues encountered

### Change Management
- Document all deployment changes
- Maintain deployment history
- Track rollback frequency
- Analyze deployment success rates

## Training Requirements

### Deployment Team Training
- CI/CD pipeline operation
- Docker container management
- Environment configuration
- Rollback procedures

### On-Call Training
- Incident response procedures
- System monitoring
- Performance optimization
- Communication protocols

## References
- [API Deployment SOP](api-deployment.md)
- [Emergency Rollback SOP](emergency-rollback.md)
- [Performance Monitoring SOP](performance-monitoring.md)
- [Incident Response SOP](incident-response.md)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: DevOps Manager
- **Classification**: Internal Use Only
