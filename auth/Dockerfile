# LUCID AUTH SERVICE - SPEC-1B Implementation
# Professional multi-platform Auth service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with plan/constants/ requirements
# Authentication and authorization service (lucid-auth-service) - Port 8089
# Image: pickme/lucid-auth-service:latest-arm64 (from essentials.md line 172, path_plan.md line 26)
# Tor-proxy compatible: Uses CMD (no ENTRYPOINT), allows command override in compose
# Configuration: All values from .env.foundation, .env.secrets via docker-compose (no hardcoded secrets)
# Build Context: . (project root) - paths must be relative to project root
# Deployment: Pi console at /mnt/myssd/Lucid/Lucid/
# Env Files: /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation, .env.secrets

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Builder - Install dependencies and compile packages
# =============================================================================
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    BUILD_ENV=production

# Set working directory
WORKDIR /build

# Install system build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy only requirements file first (for layer caching)
# Build context: project root, so use auth/ prefix
COPY auth/requirements.txt ./requirements.txt

# Install Python dependencies to user directory for distroless compatibility
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

# Verify critical packages are installed
RUN python -c "import fastapi, uvicorn, jwt, motor, redis; print('✅ Critical packages installed')"

# =============================================================================
# STAGE 2: Runtime - Distroless Python base
# =============================================================================
FROM gcr.io/distroless/python3-debian12:latest

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Metadata for professional container management (aligned with constants)
LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Auth Service for Lucid authentication support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Auth Service" \
      org.opencontainers.image.description="Distroless authentication service for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="auth-service" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8089" \
      com.lucid.cluster="foundation" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation,.env.secrets" \
      com.lucid.deployment.path="/mnt/myssd/Lucid/Lucid"

# =============================================================================
# ENVIRONMENT VARIABLES - MINIMAL DEFAULTS ONLY
# All configuration should come from .env.foundation, .env.secrets
# via docker-compose env_file directive. These are fallback defaults only.
# =============================================================================
# Essential PATH for runtime (aligned with distroless best practices and MongoDB/Tor Dockerfile pattern)
ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages \
    SERVICE_NAME=lucid-auth-service

# Minimal runtime defaults (will be overridden by docker-compose env_file)
# DO NOT hardcode production values here - use .env files on Pi console
# All Auth Service configuration comes from docker-compose.yml environment section:
#   - LUCID_ENV (from docker-compose.foundation.yml:272)
#   - LUCID_PLATFORM (from docker-compose.foundation.yml:273)
#   - AUTH_SERVICE_HOST (from docker-compose.foundation.yml:274)
#   - AUTH_SERVICE_PORT (from docker-compose.foundation.yml:275)
#   - AUTH_SERVICE_URL (from docker-compose.foundation.yml:276)
#   - JWT_SECRET_KEY (from docker-compose.foundation.yml:277 via .env.secrets)
#   - JWT_ALGORITHM (from docker-compose.foundation.yml:278)
#   - MONGODB_URI (from docker-compose.foundation.yml:279 via .env.secrets)
#   - REDIS_URL (from docker-compose.foundation.yml:280)
#   - TRON_NETWORK (from docker-compose.foundation.yml:281)
#   - TRON_SIGNATURE_VERIFICATION_ENABLED (from docker-compose.foundation.yml:282)

# =============================================================================
# Working Directory Setup
# =============================================================================
WORKDIR /app

# =============================================================================
# Copy Files from Builder Stage
# =============================================================================
# Copy Python packages from builder (distroless compatible location)
COPY --from=builder /root/.local /root/.local

# Copy application code (using full paths from project root - build context is project root)
COPY --chown=65532:65532 auth/api/ ./api/
COPY --chown=65532:65532 auth/middleware/ ./middleware/
COPY --chown=65532:65532 auth/models/ ./models/
COPY --chown=65532:65532 auth/utils/ ./utils/
COPY --chown=65532:65532 auth/__init__.py ./__init__.py
COPY --chown=65532:65532 auth/main.py ./main.py
COPY --chown=65532:65532 auth/config.py ./config.py
COPY --chown=65532:65532 auth/authentication_service.py ./authentication_service.py
COPY --chown=65532:65532 auth/user_manager.py ./user_manager.py
COPY --chown=65532:65532 auth/hardware_wallet.py ./hardware_wallet.py
COPY --chown=65532:65532 auth/session_manager.py ./session_manager.py
COPY --chown=65532:65532 auth/permissions.py ./permissions.py
COPY --chown=65532:65532 auth/healthcheck.py ./healthcheck.py

# =============================================================================
# Expose Service Port
# =============================================================================
# Expose Auth Service port (aligned with essentials.md line 176, Port-summary.md, Network_config_requirements.md line 207)
EXPOSE 8089

# Health check (aligned with docker-compose.foundation.yml lines 307-318 and Network_config_requirements.md line 223)
# Uses Python3 urllib.request (distroless-compatible) - matches docker-compose.foundation.yml
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8089/health').read(); exit(0)"]

# Run as non-root user (distroless default: 65532:65532, aligned with docker-compose.foundation.yml:293)
USER 65532:65532

# Default command (aligned with docker-compose.foundation.yml:291-292)
# NOTE: Uses CMD (not ENTRYPOINT) to allow docker-compose.yml to override entrypoint/command
# This ensures tor-proxy compatibility: compose can set depends_on: tor-proxy: condition: service_started
# Docker-compose sets: entrypoint: ["python3"], command: ["main.py"]
# Command arguments come from docker-compose.foundation.yml environment section
CMD ["python3", "main.py"]

# =============================================================================
# CONFIGURATION NOTES
# =============================================================================
# All configuration values come from:
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
# These are loaded via docker-compose.foundation.yml env_file directive (lines 263-265)
# No placeholders or hardcoded secrets in this Dockerfile
#
# Deployment on Pi Console:
#   1. Ensure .env.foundation and .env.secrets exist at:
#      /mnt/myssd/Lucid/Lucid/configs/environment/
#   2. Deploy using:
#      docker-compose --env-file configs/environment/.env.foundation \
#                     -f configs/docker/docker-compose.foundation.yml up -d
#   3. All environment variables are injected via docker-compose environment section
#   4. Service reads configuration from environment variables at runtime
#
# This Dockerfile pattern is applicable to all 35 Lucid images:
#   - Foundation Services (4): mongodb, redis, elasticsearch, auth-service
#   - Core Services (6): api-gateway, service-mesh-controller, blockchain-engine, etc.
#   - Application Services (10): session-pipeline, session-recorder, chunk-processor, etc.
#   - Support Services (7): admin-interface, tron-client, payout-router, etc.
#   - Specialized Services (5): gui, rdp, vm, database, storage
#
# For other services, adapt:
#   - Service name in LABELs and SERVICE_NAME
#   - Port in EXPOSE and HEALTHCHECK
#   - Source code paths in COPY commands
#   - Requirements file path
#   - Health check endpoint path
#   - Appropriate .env file references (foundation, core, application, support)
