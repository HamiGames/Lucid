# Multi-stage distroless build for Lucid Node Management
# Step 32: Phase 3 Container Builds - Node Management
# Aligned with essentials.md: pickme/lucid-node-management:latest-arm64, ports 8095,8099, IP 172.20.0.25
# Network Configuration: lucid-pi-network (172.20.0.0/16), lucid-gui-network (172.22.0.0/16)
# Fully aligned with plan/constants/ directory requirements

# Stage 1: Builder
FROM --platform=linux/arm64 python:3.11-slim AS builder

# Set build arguments (aligned with path_plan.md)
ARG BUILDPLATFORM
ARG TARGETPLATFORM=linux/arm64
ARG PYTHON_VERSION=3.11
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set environment variables for pip optimization (aligned with path_plan.md)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_PREFER_BINARY=1

# Install build dependencies with apt cache mount (BuildKit optimization)
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

# Upgrade pip to latest version (faster builds, better wheel support for ARM64)
RUN pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt ./requirements.txt

# Install Python dependencies with optimizations
# PIP_PREFER_BINARY=1 forces use of pre-built wheels when available (critical for ARM64)
# Cache mount speeds up subsequent builds (BuildKit feature)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --prefer-binary -r requirements.txt || \
    pip install --user --prefer-binary -r requirements.txt

# Copy source code
COPY worker / ./worker/
COPY pools/ ./pools/
COPY resources/ ./resources/
COPY poot/ ./poot/
COPY __init__.py ./__init__.py
COPY api/ ./api/
COPY models/ ./models/






# Stage 2: Runtime (Distroless)
FROM --platform=linux/arm64 gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build/worker /app/worker
COPY --from=builder /build/__init__.py /app/__init__.py
COPY --from=builder /build/pools /app/pools
COPY --from=builder /build/resources /app/resources
COPY --from=builder /build/api /app/api
COPY --from=builder /build/models /app/models
COPY --from=builder /build/poot /app/poot

# Set working directory
WORKDIR /app

# Set core environment variables (aligned with path_plan.md)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Service identification (aligned with essentials.md lines 428-443)
ENV SERVICE_NAME=lucid-node-management
ENV CONTAINER_NAME=lucid-node-management
ENV HOSTNAME=lucid-node-management

# Port configuration (aligned with essentials.md, path_plan.md, Network_conig_requirements.md)
ENV PORT=8095
ENV NODE_MANAGEMENT_PORT=8095
ENV NODE_STAGING_PORT=8099
ENV NODE_API_PORT=8095
ENV HOST=0.0.0.0
ENV HEALTHCHECK_PORT=8095
ENV HEALTHCHECK_PATH=/health

# Network configuration (aligned with Network_conig_requirements.md)
ENV NODE_MANAGEMENT_HOST=172.20.0.25
ENV NODE_MANAGEMENT_URL=http://lucid-node-management:8095
ENV API_URL=http://lucid-node-management:8095

# Database connections (aligned with Network_conig_requirements.md)
ENV MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_nodes?authSource=admin
ENV REDIS_URL=redis://lucid-redis:6379/3

# Service dependencies (aligned with Network_conig_requirements.md)
ENV API_GATEWAY_URL=http://lucid-api-gateway:8080
ENV BLOCKCHAIN_CORE_URL=http://lucid-blockchain-engine:8084
ENV TRON_PAYMENT_URL=http://lucid-payment-gateway:8097

# Project configuration (aligned with path_plan.md)
ENV PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
ENV PROJECT_NAME=Lucid
ENV LUCID_PLATFORM=arm64
ENV LUCID_ARCHITECTURE=linux/arm64
ENV LUCID_ENV=production

# Logging configuration (aligned with path_plan.md)
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Health check configuration (aligned with Network_conig_requirements.md)
# Note: Uses Python urllib.request (not curl) since distroless images don't have curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8095/health')"]

# Expose ports (aligned with essentials.md: ports=8095:8095,8099:8099)
EXPOSE 8095 8099

# Set entrypoint (aligned with other session Dockerfiles: node.main pattern)
# Replace this line:
  # FastAPI entrypoint
ENTRYPOINT ["python", "-m", "uvicorn"]

# FastAPI application
CMD ["node.main:app", "--host", "0.0.0.0", "--port", "8095"]