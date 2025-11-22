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
RUN mkdir -p /app/logs /app/storage /app/.dashboard

# Copy application code (excluding files in .dockerignore)
COPY --chown=gal:gal . .

# Ensure gal user has ownership of everything in /app
RUN chown -R gal:gal /app

# Change to non-root user
USER gal

# Expose ports
EXPOSE 3000 8000

# Health check - using python instead of curl for reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()"

# Default command - start the API server directly (Railway needs this as main process)
# Force Railway to rebuild - API server v2
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
