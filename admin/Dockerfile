# Multi-stage distroless build for Lucid Admin Interface
# Step 32: Phase 4 Container Builds - Support Services
# Aligned with essentials.md: pickme/lucid-admin-interface:latest-arm64, ports 8083,8088,8100, IP 172.20.0.26
# Network Configuration: lucid-pi-network (172.20.0.0/16)
# Fully aligned with plan/constants/ directory requirements

# Stage 1: Builder
FROM --platform=linux/arm64 python:3.12-slim-bookworm AS builder

# Set build arguments (aligned with path_plan.md)
ARG BUILDPLATFORM
ARG TARGETPLATFORM=linux/arm64
ARG PYTHON_VERSION=3.12
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
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt ./requirements.txt

# Create virtual environment and upgrade pip (faster builds, better wheel support for ARM64)
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel

# Install Python dependencies with optimizations
# PIP_PREFER_BINARY=1 forces use of pre-built wheels when available (critical for ARM64)
# Cache mount speeds up subsequent builds (BuildKit feature)
RUN --mount=type=cache,target=/root/.cache/pip \
    /opt/venv/bin/pip install --prefer-binary -r requirements.txt || \
    /opt/venv/bin/pip install --prefer-binary -r requirements.txt

# Copy application code
COPY . /app/
COPY __init__.py ./__init__.py
# Stage 2: Runtime (Distroless)
FROM --platform=linux/arm64 gcr.io/distroless/python3-debian12:nonroot

# Set core environment variables (aligned with path_plan.md)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Service identification (aligned with essentials.md lines 449-464)
ENV SERVICE_NAME=admin-interface
ENV CONTAINER_NAME=lucid-admin-interface
ENV HOSTNAME=lucid-admin-interface

# Port configuration (aligned with essentials.md, path_plan.md, Network_conig_requirements.md)
ENV SERVICE_PORT=8083
ENV ADMIN_PORT=8083
ENV ADMIN_PORT_STAGING=8088
ENV ADMIN_PORT_MONITORING=8100
ENV HOST=0.0.0.0
ENV HEALTHCHECK_PORT=8083
ENV HEALTHCHECK_PATH=/health

# Network configuration (aligned with Network_conig_requirements.md)
ENV ADMIN_INTERFACE_HOST=172.20.0.26
ENV ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
ENV API_URL=http://lucid-admin-interface:8083

# Database connections (aligned with Network_conig_requirements.md)
ENV MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_admin?authSource=admin
ENV REDIS_URL=redis://lucid-redis:6379/4

# Service dependencies (aligned with Network_conig_requirements.md)
ENV API_GATEWAY_URL=http://lucid-api-gateway:8080
ENV BLOCKCHAIN_CORE_URL=http://lucid-blockchain-engine:8084
ENV SESSION_MANAGEMENT_URL=http://lucid-session-api:8087
ENV NODE_MANAGEMENT_URL=http://lucid-node-management:8095
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

# Copy virtual environment from builder (with proper ownership for nonroot user)
COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv

# Copy application code (with proper ownership for nonroot user)
COPY --from=builder --chown=nonroot:nonroot /app /app

# Set PATH to include virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Health check configuration (aligned with Network_conig_requirements.md)
# Note: Uses Python urllib.request (not curl) since distroless images don't have curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/opt/venv/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/health').read()"]

# Expose ports (aligned with essentials.md: ports=8083:8083,8088:8088,8100:8100)
EXPOSE 8083 8088 8100

# Set entrypoint (aligned with admin interface: uvicorn main:app pattern)
# Replace this line:
    CMD ["/opt/venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]

    # With this:
    CMD ["/opt/venv/bin/python", "-m", "uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]
