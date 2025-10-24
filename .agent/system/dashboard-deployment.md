---
id: system.dashboard_deployment
version: 1.0
last_updated: 2025-01-24
tags: [dashboard, deployment, devops, ci-cd, production]
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
