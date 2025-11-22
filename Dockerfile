# Multi-stage Dockerfile for GAL Discord Bot with Dashboard
# Stage 1: Build Next.js frontend
FROM node:20-slim AS frontend-builder

# Set working directory
WORKDIR /app/dashboard

# Copy package files
COPY dashboard/package*.json ./

# Install ALL dependencies (including devDependencies needed for build)
RUN npm ci && npm cache clean --force

# Update to secure versions
RUN npm update next eslint-config-next js-yaml

# Fix security vulnerabilities (production build)
RUN npm audit fix --force || true

# Copy frontend source code
COPY dashboard/ ./

# Set production environment for the build
ENV NODE_ENV=production

# Build the Next.js application (disable linting and static generation issues)
RUN npm run build --no-lint

# Install only production dependencies for runtime
RUN npm prune --production

# Stage 2: Python environment with Node.js runtime
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash gal

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy built frontend from previous stage
COPY --from=frontend-builder --chown=gal:gal /app/dashboard ./dashboard

# Create necessary directories as root before switching users
RUN mkdir -p /app/logs /app/storage /app/.dashboard && \
    chown -R gal:gal /app/logs /app/storage /app/.dashboard

# Copy application code (excluding files in .dockerignore)
COPY --chown=gal:gal . .

# Create a simple startup script directly in Dockerfile
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'echo "Starting API server..."' >> /app/start.sh && \
    echo 'python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &' >> /app/start.sh && \
    echo 'API_PID=$!' >> /app/start.sh && \
    echo 'echo "Waiting for API to be ready..."' >> /app/start.sh && \
    echo 'sleep 5' >> /app/start.sh && \
    echo 'i=1' >> /app/start.sh && \
    echo 'while [ $i -le 30 ]; do' >> /app/start.sh && \
    echo '  if curl -f http://localhost:8000/health > /dev/null 2>&1; then' >> /app/start.sh && \
    echo '    echo "API is ready!"' >> /app/start.sh && \
    echo '    break' >> /app/start.sh && \
    echo '  fi' >> /app/start.sh && \
    echo '  echo "Attempt $i/30: API not ready yet, waiting..."' >> /app/start.sh && \
    echo '  sleep 2' >> /app/start.sh && \
    echo '  i=$((i+1))' >> /app/start.sh && \
    echo 'done' >> /app/start.sh && \
    echo 'echo "Starting Discord bot..."' >> /app/start.sh && \
    echo 'exec python bot.py' >> /app/start.sh && \
    chmod +x /app/start.sh && \
    chown gal:gal /app/start.sh

# Change to non-root user
USER gal

# Expose ports
EXPOSE 3000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - starts the services
CMD ["/app/start.sh"]
