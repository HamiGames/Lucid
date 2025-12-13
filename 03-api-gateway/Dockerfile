# LUCID API GATEWAY - SPEC-1B Implementation
# Professional multi-platform API Gateway service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with plan/constants/ requirements
# API Gateway service (lucid-api-gateway) - Ports 8080, 8081
# Image: pickme/lucid-api-gateway:latest-arm64 (from essentials.md, path_plan.md line 29)
# Tor-proxy compatible: Uses CMD (no ENTRYPOINT), allows command override in compose
# Configuration: All values from .env.core, .env.secrets, .env.foundation via docker-compose (no hardcoded secrets)
# Build Context: . (project root) - paths must be relative to project root
# Deployment: Pi console at /mnt/myssd/Lucid/Lucid/
# Env Files: /mnt/myssd/Lucid/Lucid/configs/environment/.env.core, .env.secrets, .env.foundation

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

# =============================================================================
# STAGE 1: Builder - Install dependencies and compile packages
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    BUILD_ENV=production

# Install build dependencies with apt cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /build

# Create placeholder files in system directories with actual content (ensures they're baked into image)
RUN mkdir -p /var/run /var/lib && \
    echo "LUCID_API_GATEWAY_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_API_GATEWAY_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Create placeholder files for application directories (ensures COPY succeeds even if directories are empty)
RUN mkdir -p ./api ./gateway ./scripts ./utils ./middleware ./endpoints && \
    cat <<'EOF' > ./middleware/__init__.py
"""
Lucid API Gateway - Middleware Package
Shared middleware utilities and configurations.

This package provides middleware components for the Lucid API Gateway.
Currently this is a placeholder for future shared middleware implementations.

Note: Application-specific middleware is located in api/app/middleware/
"""

__version__ = "1.0.0"

__all__ = []
EOF

# Set pip environment variables for optimization
ENV PIP_PREFER_BINARY=1

# Upgrade pip to latest version with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel setuptools

# Copy requirements first for better layer caching
# Build context: project root, so use 03-api-gateway/ prefix
COPY 03-api-gateway/requirements.txt ./requirements.txt

# Ensure directory structure exists before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

# Build wheels from requirements (pywheel pattern for better caching and faster installs)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pip/wheels \
    pip wheel -r requirements.txt -w ./wheels

# Install Python dependencies from wheels (faster install, better caching, no network dependency)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pip/wheels \
    pip install --user --no-index --find-links ./wheels -r requirements.txt && \
    rm -rf ./wheels

# Create marker files with actual content (ensures directory structure is locked in)
# CRITICAL: Must be AFTER pip install, with actual content (not empty)
RUN echo "LUCID_API_GATEWAY_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_API_GATEWAY_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed and verify directory structure
RUN python3 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, httpx; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"

# Copy source code (only existing directories - entrypoints/ does not exist)
COPY 03-api-gateway/api/ ./api/
COPY 03-api-gateway/gateway/ ./gateway/
COPY 03-api-gateway/scripts/ ./scripts/
COPY 03-api-gateway/utils/ ./utils/
COPY 03-api-gateway/middleware/ ./middleware/
COPY 03-api-gateway/endpoints/ ./endpoints/

# =============================================================================
# STAGE 2: Runtime - Distroless Python base
# =============================================================================
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Metadata for professional container management (aligned with constants)
LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless API Gateway for Lucid core support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid API Gateway" \
      org.opencontainers.image.description="Distroless API Gateway for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="api-gateway" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8080,8081" \
      com.lucid.cluster="core" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.core,.env.secrets,.env.foundation" \
      com.lucid.deployment.path="/mnt/myssd/Lucid/Lucid"

# =============================================================================
# ENVIRONMENT VARIABLES - MINIMAL DEFAULTS ONLY
# All configuration should come from .env.core, .env.secrets, .env.foundation
# via docker-compose env_file directive. These are fallback defaults only.
# =============================================================================
# Essential PATH for runtime (aligned with distroless best practices)
ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages

# Minimal runtime defaults (will be overridden by docker-compose env_file)
# DO NOT hardcode production values here - use .env files on Pi console
# All API Gateway configuration comes from docker-compose.yml environment section:
#   - SERVICE_NAME (from docker-compose)
#   - PORT (from docker-compose)
#   - HOST (from docker-compose)
#   - MONGODB_URI (from docker-compose via .env.secrets)
#   - REDIS_URL (from docker-compose)
#   - API_GATEWAY_URL (from docker-compose)
#   - API_GATEWAY_HOST (from docker-compose)
#   - LOG_LEVEL (from docker-compose)
#   - DEBUG (from docker-compose)
#   - ... (all other configuration from .env files)

# =============================================================================
# Working Directory Setup
# =============================================================================
WORKDIR /app

# =============================================================================
# Copy Files from Builder Stage
# =============================================================================
# Copy runtime directories from builder (directory already populated with .keep files)
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Copy Python packages (directory already populated with packages + marker files from builder stage)
# Following Dockerfile-copy-pattern.md: copy to /usr/local for better distroless compatibility
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (this will fail the build if packages are missing)
# Following Dockerfile-copy-pattern.md: verify in runtime stage with correct path
RUN ["/usr/bin/python3", "-c", "import sys; import os; site_packages = '/usr/local/lib/python3.11/site-packages'; assert os.path.exists(site_packages), f'{site_packages} does not exist'; assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; assert os.path.exists(os.path.join(site_packages, 'pydantic')), 'pydantic not found'; assert os.path.exists(os.path.join(site_packages, 'motor')), 'motor not found'; assert os.path.exists(os.path.join(site_packages, 'redis')), 'redis not found'; assert os.path.exists(os.path.join(site_packages, '.lucid-marker')), 'marker file not found'; marker_path = os.path.join(site_packages, '.lucid-marker'); assert os.path.getsize(marker_path) > 0, f'marker file is empty: {marker_path}'; print('Packages verified in runtime stage')"]

# Copy application code (only directories that were copied in builder stage)
COPY --chown=65532:65532 --from=builder /build/api /app/api
COPY --chown=65532:65532 --from=builder /build/gateway /app/gateway
COPY --chown=65532:65532 --from=builder /build/scripts /app/scripts
COPY --chown=65532:65532 --from=builder /build/utils /app/utils
COPY --chown=65532:65532 --from=builder /build/middleware /app/middleware
COPY --chown=65532:65532 --from=builder /build/endpoints /app/endpoints

# =============================================================================
# Expose Service Ports
# =============================================================================
# Expose API Gateway ports (aligned with essentials.md, Port-summary.md)
EXPOSE 8080 8081

# Health check (aligned with docker-compose and Network_config_requirements.md)
# Uses Python3 urllib.request (distroless-compatible, no curl available)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/meta/health').read(); exit(0)"]

# Run as non-root user (distroless default: 65532:65532, aligned with docker-compose)
USER 65532:65532

# Default command (aligned with docker-compose)
# NOTE: Uses CMD (not ENTRYPOINT) to allow docker-compose.yml to override entrypoint/command
# This ensures tor-proxy compatibility: compose can set depends_on: tor-proxy: condition: service_started
# Docker-compose sets: entrypoint: ["python3"], command: ["-m", "api.app.main"]
# Command arguments come from docker-compose.yml environment section
CMD ["python3", "-m", "api.app.main"]


# =============================================================================
# CONFIGURATION NOTES
# =============================================================================
# All configuration values come from:
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
# These are loaded via docker-compose.core.yml env_file directive
# No placeholders or hardcoded secrets in this Dockerfile
#
# Deployment on Pi Console:
#   1. Ensure .env.core, .env.secrets, .env.foundation exist at:
#      /mnt/myssd/Lucid/Lucid/configs/environment/
#   2. Deploy using:
#      docker-compose --env-file configs/environment/.env.core \
#                     -f configs/docker/docker-compose.core.yml up -d
#   3. All environment variables are injected via docker-compose environment section
#   4. Service reads configuration from environment variables at runtime
#
# Build Command:
#   docker buildx build \
#     --platform linux/arm64 \
#     -t pickme/lucid-api-gateway:latest-arm64 \
#     -f 03-api-gateway/Dockerfile \
#     --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
#     --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#     --build-arg VERSION=1.0.0 \
#     --push \
#     .