# LUCID Session API Service - Distroless Container
# Step 17 Implementation: Session Storage & API

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDKIT_INLINE_CACHE=1
ARG BUILDKIT_PROGRESS=plain

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libzstd-dev \
    liblz4-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install --no-cache-dir --user .

# Runtime stage - Distroless Python
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build/sessions /app/sessions

# Set environment variables
ENV PYTHONPATH=/app
# Note: SESSION_API_HOST and SESSION_API_PORT are set by docker-compose
# SESSION_API_HOST is service name, bind address is always 0.0.0.0
# All configuration values come from docker-compose .env files:
# - MONGODB_URL, REDIS_URL from .env.foundation, .env.core
# - SESSION_API_PORT, SESSION_API_HOST from docker-compose environment section
# - API_GATEWAY_URL, BLOCKCHAIN_ENGINE_URL from .env.core, .env.application

# Create data directories
USER root
RUN mkdir -p /data/sessions /data/chunks /data/temp /data/backup
RUN chown -R 65532:65532 /data
USER 65532

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8087/health', timeout=5).read(); exit(0)"]

# Run the application
CMD ["/usr/bin/python3", "-m", "sessions.api.main"]
