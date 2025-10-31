# Multi-stage distroless build for Lucid Service Mesh Controller
# Step 32: Phase 2 Container Builds - Core Services
# Aligned with essentials.md: pickme/lucid-service-mesh-controller:latest-arm64, ports 8500,8501,8502,8600,8088, IP 172.20.0.19
# Network Configuration: lucid-pi-network (172.20.0.0/16)
# Fully aligned with plan/constants/ directory requirements

# Stage 1: Builder
FROM --platform=linux/arm64 python:3.11-slim AS builder

# Set build arguments (aligned with path_plan.md)
ARG BUILDPLATFORM
ARG TARGETPLATFORM=linux/arm64
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG GIT_COMMIT=unknown
ARG PYTHON_VERSION=3.11

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

# Set working directory
WORKDIR /app

# Set pip environment variables for optimization
ENV PIP_PREFER_BINARY=1

# Upgrade pip to latest version
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel setuptools

# Copy requirements and install dependencies
COPY infrastructure/service-mesh/requirements.txt ./requirements.txt

# Install Python dependencies with cache mount and optimizations
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pip/wheels \
    pip install --user \
    --prefer-binary \
    --no-warn-script-location \
    -r requirements.txt

# Copy service mesh controller source code
COPY infrastructure/service-mesh/controller/ ./controller/
COPY infrastructure/service-mesh/sidecar/ ./sidecar/
COPY infrastructure/service-mesh/discovery/ ./discovery/
COPY infrastructure/service-mesh/communication/ ./communication/
COPY infrastructure/service-mesh/security/ ./security/

# Build the application
RUN python -m compileall -b .

# Stage 2: Runtime (Distroless)
FROM --platform=linux/arm64 gcr.io/distroless/python3-debian12

# Set metadata labels (aligned with essentials.md)
LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid Service Mesh Controller" \
      org.opencontainers.image.description="Distroless service mesh controller for Lucid platform" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Lucid" \
      org.opencontainers.image.licenses="MIT" \
      lucid.service="service-mesh-controller" \
      lucid.type="distroless" \
      lucid.platform="arm64" \
      lucid.security="hardened" \
      phase="2" \
      cluster="10-cross-cluster-integration"

# Copy Python packages from builder to distroless location
COPY --from=builder /root/.local /usr/local

# Copy application code
COPY --from=builder --chown=65532:65532 /app /app

# Set working directory
WORKDIR /app

# Locale and Timezone Configuration (distroless-compatible: C.UTF-8)
ENV TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    COUNTRY=US

# Set Python path and environment
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PATH=/usr/local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LUCID_ENV=production \
    LUCID_PLATFORM=arm64 \
    LUCID_ARCHITECTURE=linux/arm64

# Service Configuration (per essentials.md and Network_conig_requirements.md lines 307-360)
ENV SERVICE_NAME=service-mesh-controller \
    CONTAINER_NAME=lucid-service-mesh-controller \
    HOSTNAME=lucid-service-mesh-controller

# Port Configuration
ENV PORT=8500 \
    SERVICE_MESH_CONTROLLER_PORT=8500 \
    HEALTHCHECK_PORT=8500 \
    HEALTHCHECK_PATH=/v1/status/leader

# Network Configuration (per Network_conig_requirements.md lines 334-341)
ENV SERVICE_MESH_CONTROLLER_HOST=172.20.0.19 \
    SERVICE_DISCOVERY_URL=http://lucid-service-mesh-controller:8500 \
    SERVICE_MESH_ENABLED=true

# Consul Configuration (per Network_conig_requirements.md lines 334-341)
ENV CONSUL_PORT=8500 \
    CONSUL_DATACENTER=lucid-dc \
    CONSUL_BOOTSTRAP_EXPECT=1 \
    CONSUL_UI_ENABLED=true \
    CONSUL_CONNECT_ENABLED=true \
    CONSUL_NODE_NAME=lucid-service-mesh-controller

# Database Configuration (per Network_conig_requirements.md - if needed)
ENV MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin \
    REDIS_URL=redis://lucid-redis:6379/0

# Project Configuration (per path_plan.md)
ENV PROJECT_ROOT=/mnt/myssd/Lucid/Lucid \
    PROJECT_NAME=Lucid \
    PROJECT_VERSION=0.1.0

# Logging Configuration (per path_plan.md)
ENV LOG_LEVEL=INFO \
    DEBUG=false \
    LOG_FORMAT=json

# Network Configuration (per network_defs.md)
ENV LUCID_PI_NETWORK=lucid-pi-network \
    LUCID_PI_SUBNET=172.20.0.0/16 \
    LUCID_PI_GATEWAY=172.20.0.1

# Use nonroot user (distroless default)
USER 65532:65532

# Health check (aligned with essentials.md and Network_conig_requirements.md: healthcheck_port=8500, healthcheck_path=/v1/status/leader)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8500/v1/status/leader')"]

# Expose ports (aligned with essentials.md and Network_conig_requirements.md: 8500,8501,8502,8600,8088)
EXPOSE 8500 8501 8502 8600 8088

# Start application (async main in controller.main) - NOT FastAPI, uses asyncio.run(main())
CMD ["python3", "-c", "import asyncio; from controller.main import main; asyncio.run(main())"]