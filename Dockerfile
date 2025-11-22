# Minimal Dockerfile for API-only deployment
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Copy all necessary modules for the API
COPY --chown=gal:gal api/ ./api/
COPY --chown=gal:gal core/ ./core/
COPY --chown=gal:gal utils/ ./utils/
COPY --chown=gal:gal helpers/ ./helpers/
COPY --chown=gal:gal integrations/ ./integrations/
COPY --chown=gal:gal config.py ./
COPY --chown=gal:gal .env.example ./

# Create necessary directories
RUN mkdir -p /app/logs /app/storage && \
    chown -R gal:gal /app/logs /app/storage

# Give gal user write permissions
RUN chown -R gal:gal /app

# Change to non-root user
USER gal

# Expose port 8000 for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()"

# Default command - run only the API server
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
