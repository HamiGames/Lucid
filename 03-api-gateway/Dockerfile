# Multi-stage distroless build for Lucid API Gateway
# Step 32: Phase 3 Container Builds - Core Services
# Aligned with essentials.md: pickme/lucid-api-gateway:latest-arm64, ports 8080/8081, IP 172.20.0.10
# Network: lucid-pi-network (172.20.0.10), lucid-gui-network (172.22.0.10)

# Stage 1: Builder
FROM --platform=linux/arm64 python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM=linux/arm64
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG GIT_COMMIT=unknown
ARG PYTHON_VERSION=3.11

# Install build dependencies with apt cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set pip environment variables for optimization
ENV PIP_NO_CACHE_DIR=1
ENV PIP_PREFER_BINARY=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Upgrade pip to latest version
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel setuptools

# Copy requirements first for better layer caching
COPY requirements.txt ./requirements.txt

# Install Python dependencies with cache mount and optimizations
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pip/wheels \
    pip install --user \
    --prefer-binary \
    --no-warn-script-location \
    -r requirements.txt

# Copy source code
COPY api/ ./api/
COPY gateway/ ./gateway/
COPY scripts/ ./scripts/

# Stage 2: Runtime (Distroless)
FROM --platform=linux/arm64 gcr.io/distroless/python3-debian12

# Set labels for Phase 3 compliance
LABEL maintainer="Lucid Development Team" \
      description="Lucid API Gateway - Phase 3 Distroless Container" \
      version="1.0.0" \
      build_date="${BUILD_DATE}" \
      git_commit="${GIT_COMMIT}" \
      phase="3" \
      cluster="01-api-gateway" \
      service="api-gateway"

# Copy Python dependencies from builder
COPY --from=builder /root/.local /usr/local

# Copy application code
COPY --from=builder /app/api /app/api
COPY --from=builder /app/gateway /app/gateway
COPY --from=builder /app/scripts /app/scripts

# Set working directory
WORKDIR /app

# Set Python path and base environment variables
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Service Configuration (per essentials.md and Network_conig_requirements.md lines 242-303)
ENV SERVICE_NAME=api-gateway
ENV CONTAINER_NAME=lucid-api-gateway
ENV HOSTNAME=lucid-api-gateway

# Port Configuration
ENV PORT=8080
ENV GATEWAY_PORT=8080
ENV LUCID_API_PORT=8080
ENV HOST=0.0.0.0

# Network Configuration (per Network_conig_requirements.md lines 257-280)
ENV API_GATEWAY_URL=http://lucid-api-gateway:8080
ENV API_GATEWAY_HOST=172.20.0.10
ENV API_UPSTREAM=http://lucid-api-server:8081

# Database Configuration (per Network_conig_requirements.md lines 275-276)
ENV MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_gateway?authSource=admin
ENV REDIS_URL=redis://lucid-redis:6379/0

# Security Configuration (per Network_conig_requirements.md lines 277-280)
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENV SSL_ENABLED=true
ENV RATE_LIMIT_PER_MINUTE=1000
ENV CORS_ALLOWED_ORIGINS=*

# Health Check Configuration
ENV HEALTHCHECK_PORT=8080
ENV HEALTHCHECK_PATH=/health

# Project Configuration (per path_plan.md)
ENV PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
ENV PROJECT_NAME=Lucid
ENV PROJECT_VERSION=0.1.0
ENV LUCID_PLATFORM=arm64
ENV LUCID_ENV=production
ENV LUCID_ARCHITECTURE=linux/arm64

# Logging Configuration
ENV LOG_LEVEL=INFO
ENV DEBUG=false
ENV LOG_FORMAT=json

# Network Configuration (per network_defs.md)
ENV LUCID_PI_NETWORK=lucid-pi-network
ENV LUCID_PI_SUBNET=172.20.0.0/16
ENV LUCID_PI_GATEWAY=172.20.0.1
ENV LUCID_GUI_NETWORK=lucid-gui-network
ENV LUCID_GUI_SUBNET=172.22.0.0/16
ENV LUCID_GUI_GATEWAY=172.22.0.1

# Electron-GUI Endpoint (per essentials.md and Network_conig_requirements.md line 303)
ENV ELECTRON_GUI_ENDPOINT=http://172.20.0.10:8080/api/v1

# Use nonroot user (distroless default)
USER 65532:65532

# Health check (aligned with Network_conig_requirements.md: healthcheck_port=8080, healthcheck_path=/health)
# Note: Using urllib.request instead of curl for distroless images
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]

# Expose ports (aligned with Network_conig_requirements.md: ports 8080 HTTP, 8081 HTTPS)
EXPOSE 8080 8081

# Start application
CMD ["python3", "-m", "api.app.main"]
