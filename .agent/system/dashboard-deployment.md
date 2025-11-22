---
id: system.dashboard_deployment
version: 2.0
last_updated: 2025-11-19
tags: [dashboard, deployment, devops, ci-cd, production, railway]
---

# Dashboard Deployment Guide

## Overview

The Dashboard Deployment Guide provides comprehensive procedures for deploying the Live Graphics Dashboard across different environments, including development, staging, and production deployments with automated CI/CD pipelines.

## Deployment Architecture

### Environment Structure
```
Environments
├── Development (dev)
│   ├── Development server
│   ├── Hot reloading
│   └── Debug tools
├── Staging (staging)
│   ├── Production-like environment
│   ├── Integration testing
│   └── User acceptance testing
└── Production (prod)
    ├── Production deployment
    ├── Load balancing
    └── Monitoring
```

### Technology Stack
- **Frontend**: Next.js 14 with TypeScript
- **Deployment**: Docker containers
- **CI/CD**: GitHub Actions
- **Infrastructure**: Cloud provider (AWS/GCP/Azure)
- **Monitoring**: Application performance monitoring
- **Security**: SSL/TLS, security headers

## Local Development

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Git
- Docker (optional)

### Setup Process
1. **Repository Clone**:
```bash
git clone <repository-url>
cd dashboard
```

2. **Dependency Installation**:
```bash
npm install
```

3. **Environment Configuration**:
```bash
cp .env.local.example .env.local
# Edit .env.local with appropriate values
```

4. **Development Server Start**:
```bash
npm run dev
```

5. **Application Access**:
```bash
# Open http://localhost:3000
```

### Development Configuration
```typescript
// next.config.js (development)
const config = {
  reactStrictMode: true,
  swcMinify: false, // Disabled for faster builds
  compiler: {
    removeConsole: false, // Keep console logs in development
  },
  env: {
    NEXT_PUBLIC_API_URL: 'http://localhost:8000',
    NEXT_PUBLIC_ENV: 'development',
  },
};
```

## Railway Deployment (Recommended)

### Overview
Railway provides a simplified, container-based deployment platform that handles build, deployment, and infrastructure management automatically. The GAL Discord Bot with Dashboard is optimized for Railway deployment using a multi-runtime Dockerfile.

### Architecture on Railway
```
Railway Service (Single Container)
├── Discord Bot (Python)
├── FastAPI Backend (Python, port 8000)
└── Next.js Dashboard (Node.js, port 3000)
```

### Prerequisites
- GitHub repository with project code
- Railway account
- Discord Bot Token
- Railway PostgreSQL add-on

### Configuration Files

#### railway.toml
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
numReplicas = 1
startCommand = "python bot.py"

[deploy.env]
NODE_ENV = "production"
ENABLE_DASHBOARD = "true"
PYTHONUNBUFFERED = "1"
PYTHONDONTWRITEBYTECODE = "1"

[service]
name = "gal-discord-bot"

[service.healthcheck]
path = "/health"
port = 8000
```

#### Multi-Stage Dockerfile
```dockerfile
# Stage 1: Build Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci && npm cache clean --force
RUN npm update next eslint-config-next js-yaml
RUN npm audit fix --force || true
COPY dashboard/ ./
ENV NODE_ENV=production
RUN npm run build --no-lint
RUN npm prune --production

# Stage 2: Python environment with Node.js runtime
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 NODE_ENV=production PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y nodejs npm curl \
  && rm -rf /var/lib/apt/lists/* && apt-get clean
RUN useradd --create-home --shell /bin/bash gal
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt
COPY --from=frontend-builder --chown=gal:gal /app/dashboard ./dashboard
COPY --chown=gal:gal . .
USER gal
EXPOSE 3000 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "bot.py"]
```

### Environment Variables

#### Required Variables
```bash
DISCORD_TOKEN=your_discord_bot_token
APPLICATION_ID=your_discord_application_id
DATABASE_URL=your_production_database_url  # Railway PostgreSQL
ENABLE_DASHBOARD=true
```

#### Optional Variables
```bash
RIOT_API_KEY=your_riot_api_key
DASHBOARD_MASTER_PASSWORD=your_secure_password
```

### Deployment Process

#### 1. Connect Repository to Railway
1. Go to Railway dashboard
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Click "Deploy"

#### 2. Configure Services
1. **Add PostgreSQL Add-on**:
   - Go to project → New → PostgreSQL
   - Railway will provide `DATABASE_URL`
   - Copy to environment variables

2. **Set Environment Variables**:
   - Go to project → Settings → Variables
   - Add all required variables listed above

3. **Configure Environment**:
   - Railway automatically detects `railway.toml`
   - Sets `NODE_ENV=production` and `ENABLE_DASHBOARD=true`
   - Starts container with `python bot.py`

### Deployment Flow
1. **Build Phase** (~2-3 minutes):
   - Railway detects `Dockerfile` and `railway.toml`
   - Multi-stage build: Next.js frontend → Python runtime
   - Security patches applied automatically

2. **Startup Phase** (~30 seconds):
   - Container starts with `python bot.py`
   - Bot initializes Discord connection
   - `ENABLE_DASHBOARD=true` triggers dashboard startup
   - Dashboard manager starts services

3. **Runtime**:
   - Bot processes Discord commands
   - API serves on port 8000 with health checks
   - Dashboard serves on port 3000
   - Railway monitors health and restarts on failures

### Features in Railway
- ✅ **Zero Configuration**: Auto-detects and builds from Dockerfile
- ✅ **Health Monitoring**: Built-in health checks with automatic restart
- ✅ **Security Updates**: Automated package security patches
- ✅ **Multi-Runtime**: Node.js + Python in single container
- ✅ **Environment Management**: Automatic production configuration
- ✅ **Zero Downtime**: Rolling updates and deployments
- ✅ **Built-in Database**: PostgreSQL add-on with automatic connection
- ✅ **Custom Domains**: Easy SSL certificate management

### Troubleshooting Railway Deployment

#### Common Issues and Solutions

##### Dashboard Build Fails
```bash
# Solution: Railway automatically handles build issues
# Multi-stage build ensures compatibility
# Build failures logged in Railway dashboard
```

##### Environment Variables Not Working
```bash
# Verify in Railway Settings → Variables
# Check for typos in variable names
# Railway env overrides all other sources
```

##### Health Checks Failing
```bash
# Check /health endpoint is responding
# Verify DATABASE_URL is correct
# Review logs in Railway dashboard
```

##### Services Not Starting
```bash
# Check ENABLE_DASHBOARD=true is set
# Verify Dockerfile is in repository root
# Review build logs for errors
```

### Monitoring and Logs

#### Railway Dashboard
- **Real-time logs**: View container logs
- **Build logs**: Debug build failures
- **Metrics**: CPU, memory, and performance
- **Health status**: Service health indicators

#### Log Locations
```bash
# Bot logs
Starting dashboard services...
✅ Dashboard services started successfully

# API logs
INFO:     Application startup complete
INFO:     127.0.0.1:33714 - "GET /health HTTP/1.1" 200 OK

# Next.js logs
✓ Starting...
✓ Ready in 15.2s
```

### Scaling Considerations

#### Current Limitations
- **Single Service**: Bot + Dashboard in one container
- **Database**: Single PostgreSQL instance
- **Performance**: Shared resources for all services

#### Scaling Options
```bash
# Horizontal Scaling
numReplicas = 3  # In railway.toml

# Database Scaling
- Use connection pooling
- Consider read replicas for heavy loads
```

### Migration from Local Development

#### Key Differences
| Local | Railway |
|-------|---------|
| SQLite | PostgreSQL |
| Development mode | Production mode |
| Manual starts | Automatic deployment |
| File-based cache | Memory-based cache |
| Manual config | Auto configuration |

#### Migration Steps
1. **Export Local Data** (if needed)
2. **Set up Railway Environment Variables**
3. **Add Railway PostgreSQL**
4. **Deploy and Verify**
5. **Test All Functionality**

### Best Practices

#### Deployment
- Always test in Railway staging first
- Use environment-specific configuration
- Monitor build logs for issues
- Keep `railway.toml` in repository root

#### Security
- Never commit secrets to repository
- Use Railway environment variables
- Regular security updates via Railway
- Monitor dependency vulnerabilities

#### Performance
- Use Railway's built-in metrics
- Monitor database connection pooling
- Optimize Next.js build size
- Regular performance audits

## Build Process

### Production Build
```bash
npm run build
npm run start
```

### Build Configuration
```typescript
// next.config.js (production)
const config = {
  reactStrictMode: true,
  swcMinify: true, // Enabled for production
  compiler: {
    removeConsole: true, // Remove console logs in production
  },
  compress: true,
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_ENV: 'production',
  },
};
```

### Build Optimization
- **Code Splitting**: Automatic code splitting by routes
- **Tree Shaking**: Unused code elimination
- **Minification**: JavaScript and CSS minification
- **Image Optimization**: Automatic image optimization
- **Bundle Analysis**: Bundle size monitoring

## Docker Deployment

### Dockerfile
```dockerfile
# Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api
    restart: unless-stopped

  api:
    image: gal-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy Dashboard

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run linting
      run: npm run lint
    
    - name: Run type checking
      run: npm run type-check
    
    - name: Run tests
      run: npm run test:ci
    
    - name: Build application
      run: npm run build

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to staging
      run: |
        # Deployment script for staging
        echo "Deploying to staging environment"

  deploy-production:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        # Deployment script for production
        echo "Deploying to production environment"
```

### Deployment Scripts
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-staging}
VERSION=$(git rev-parse --short HEAD)

echo "Deploying dashboard version $VERSION to $ENVIRONMENT"

# Build Docker image
docker build -t gal-dashboard:$VERSION .

# Tag for environment
docker tag gal-dashboard:$VERSION gal-dashboard:$ENVIRONMENT

# Push to registry
docker push gal-dashboard:$VERSION
docker push gal-dashboard:$ENVIRONMENT

# Deploy to environment
case $ENVIRONMENT in
  "staging")
    kubectl set image deployment/dashboard-staging dashboard=gal-dashboard:$VERSION -n staging
    ;;
  "production")
    kubectl set image deployment/dashboard dashboard=gal-dashboard:$VERSION -n production
    ;;
esac

echo "Deployment completed successfully"
```

## Kubernetes Deployment

### Deployment Manifest
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard
  labels:
    app: dashboard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dashboard
  template:
    metadata:
      labels:
        app: dashboard
    spec:
      containers:
      - name: dashboard
        image: gal-dashboard:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.gal.com"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service Configuration
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dashboard-service
spec:
  selector:
    app: dashboard
  ports:
    - protocol: TCP
      port: 80
      targetPort: 3000
  type: LoadBalancer
```

### Ingress Configuration
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - dashboard.gal.com
    secretName: dashboard-tls
  rules:
  - host: dashboard.gal.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard-service
            port:
              number: 80
```

## Environment Configuration

### Environment Variables
```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.gal.com
NEXT_PUBLIC_ENV=production
NEXT_PUBLIC_VERSION=1.0.0
NEXT_PUBLIC_COMMIT_SHA=${COMMIT_SHA}

# Backend URLs
NEXT_PUBLIC_WS_URL=wss://api.gal.com/ws

# Feature flags
NEXT_PUBLIC_FEATURE_DARK_MODE=true
NEXT_PUBLIC_FEATURE_ANALYTICS=true
NEXT_PUBLIC_FEATURE_DEBUG=false

# Analytics and monitoring
NEXT_PUBLIC_GA_TRACKING_ID=${GA_TRACKING_ID}
NEXT_PUBLIC_SENTRY_DSN=${SENTRY_DSN}

# Security
NEXT_PUBLIC_HOMEPAGE_URL=https://gal.com
```

### Configuration Management
- **Environment-specific configs**: Separate configs per environment
- **Secret management**: Secure secret storage and injection
- **Feature flags**: Dynamic feature enablement
- **Runtime configuration**: Configurable at runtime

## Monitoring and Logging

### Application Monitoring
```typescript
// lib/monitoring.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV,
  tracesSampleRate: 1.0,
});

// Performance monitoring
export const trackPerformance = (name: string, duration: number) => {
  // Send performance metrics to monitoring service
};

// Error tracking
export const trackError = (error: Error, context?: any) => {
  Sentry.captureException(error, { extra: context });
};
```

### Health Checks
```typescript
// pages/api/health.ts
export default function handler(req, res) {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_VERSION,
    environment: process.env.NEXT_PUBLIC_ENV,
  });
}

// pages/api/ready.ts
export default function handler(req, res) {
  // Check database connectivity
  // Check external service availability
  // Return ready status
  res.status(200).json({ status: 'ready' });
}
```

### Logging Configuration
```typescript
// lib/logging.ts
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
  ],
});

export default logger;
```

## Security Configuration

### Security Headers
```typescript
// next.config.js
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  },
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
  }
];

module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ];
  },
};
```

### SSL/TLS Configuration
- **Certificate Management**: Automated SSL certificate renewal
- **HTTPS Enforcement**: Redirect all HTTP traffic to HTTPS
- **HSTS Headers**: HTTP Strict Transport Security
- **Certificate Pinning**: Optional certificate pinning for security

## Performance Optimization

### Caching Strategy
- **Static Asset Caching**: Long-term caching for static assets
- **API Response Caching**: Appropriate API response caching
- **CDN Integration**: Content delivery network for global performance
- **Browser Caching**: Optimal browser cache headers

### Performance Monitoring
```typescript
// lib/performance.ts
export const reportWebVitals = (metric: any) => {
  // Send performance metrics to analytics
  if (process.env.NEXT_PUBLIC_GA_TRACKING_ID) {
    // Send to Google Analytics
  }
  
  // Send to custom monitoring
  if (process.env.NEXT_PUBLIC_PERFORMANCE_ENDPOINT) {
    fetch(process.env.NEXT_PUBLIC_PERFORMANCE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metric),
    });
  }
};
```

## Backup and Recovery

### Data Backup Strategy
- **Database Backups**: Regular automated database backups
- **Configuration Backups**: Version control for configuration
- **Asset Backups**: Backup of user-generated content
- **Disaster Recovery**: Comprehensive disaster recovery plan

### Recovery Procedures
1. **System Failure**: Automated failover procedures
2. **Data Corruption**: Point-in-time recovery from backups
3. **Security Incident**: Security incident response procedures
4. **Performance Issues**: Performance degradation recovery

## Troubleshooting

### Common Issues
- **Build Failures**: Build error resolution
- **Deployment Failures**: Deployment troubleshooting
- **Performance Issues**: Performance problem diagnosis
- **Security Issues**: Security incident response

### Debugging Tools
- **Application Logs**: Comprehensive application logging
- **Performance Metrics**: Real-time performance monitoring
- **Error Tracking**: Automated error collection and analysis
- **Health Checks**: System health monitoring

## Related Documentation

- [Dashboard UI Components](./dashboard-ui-components.md) - UI component details
- [Live Graphics Dashboard](./live-graphics-dashboard.md) - Dashboard overview
- [API Backend System](./api-backend-system.md) - Backend deployment
- [Security Architecture](./security-architecture.md) - Security configuration

---

*Generated: 2025-01-24*
*Last Updated: Complete dashboard deployment documentation*
