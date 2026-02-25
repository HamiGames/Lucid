# syntax=docker/dockerfile:1.5
# LUCID API GATEWAY - Distroless Python Service
# Aligned with dockerfile-design.md and Dockerfile-copy-pattern.md
# Image: pickme/lucid-api-gateway:latest-arm64
# Port: 8080

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

############################
# Stage 1 – Builder
############################
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

# System packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

# System markers (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_API_GATEWAY_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_API_GATEWAY_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY 03-api-gateway/requirements.txt ./requirements.txt

# Step 1: Build wheels explicitly - shows compilation happening
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    echo "=== BUILDING WHEELS FROM SOURCE ===" && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt && \
    echo "=== WHEEL BUILD COMPLETE ===" && \
    ls -lh /build/wheels/ && \
    echo "Total wheels built: $(ls -1 /build/wheels/ | wc -l)"

# Step 2: Install wheels into system Python
RUN echo "=== INSTALLING WHEELS INTO SYSTEM PYTHON ===" && \
    pip install --no-cache-dir --no-index --find-links /build/wheels -r requirements.txt && \
    echo "=== INSTALLATION COMPLETE ===" && \
    rm -rf /build/wheels

# Builder-stage verification - ensure all packages built correctly
RUN echo "=== Verifying pip installation success ===" && \
    python3 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, httpx, aiohttp, structlog, prometheus_client; print('✅ All critical packages installed')" && \
    test -d /usr/local/lib/python3.11/site-packages && \
    echo "Package count: $(ls -1 /usr/local/lib/python3.11/site-packages/ | wc -l)" && \
    echo "=== Full package listing ===" && \
    pip list && \
    echo "=== Verifying C extension packages compiled ===" && \
    python3 -m pip show cryptography && \
    python3 -m pip show motor && \
    python3 -m pip show redis && \
    python3 -m pip show uvloop && \
    echo "=== Verifying site-packages directory ===" && \
    ls -la /usr/local/lib/python3.11/site-packages/ | grep -E "^d" | wc -l && \
    echo "directories found in site-packages" && \
    echo "LUCID_API_GATEWAY_PACKAGES_INSTALLED_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.lucid-marker && \
    echo "✅ All packages ready for final image"

# Application source COPY (only directories that exist with content)
COPY 03-api-gateway/api/ ./api/
COPY 03-api-gateway/gateway/ ./gateway/
COPY 03-api-gateway/config/ ./config/

# Create marker files in app directories (ensures COPY won't fail silently)
RUN echo "LUCID_API_GATEWAY_APP_API_$(date +%s)" > ./api/.lucid-marker && \
    echo "LUCID_API_GATEWAY_APP_GATEWAY_$(date +%s)" > ./gateway/.lucid-marker && \
    echo "LUCID_API_GATEWAY_APP_CONFIG_$(date +%s)" > ./config/.lucid-marker && \
    find ./api ./gateway ./config -name ".lucid-marker" -exec cat {} \;

# Verify new modules are included in builder stage - file existence & imports
RUN echo "=== Verifying new GUI and TRON support modules ===" && \
    test -f ./api/app/routers/gui.py && echo "✅ gui.py found" && \
    test -f ./api/app/routers/gui_docker.py && echo "✅ gui_docker.py found" && \
    test -f ./api/app/routers/gui_tor.py && echo "✅ gui_tor.py found" && \
    test -f ./api/app/routers/gui_hardware.py && echo "✅ gui_hardware.py found" && \
    test -f ./api/app/routers/tron_support.py && echo "✅ tron_support.py found" && \
    test -f ./api/app/services/gui_bridge_service.py && echo "✅ gui_bridge_service.py found" && \
    test -f ./api/app/services/gui_docker_manager_service.py && echo "✅ gui_docker_manager_service.py found" && \
    test -f ./api/app/services/gui_tor_manager_service.py && echo "✅ gui_tor_manager_service.py found" && \
    test -f ./api/app/services/gui_hardware_manager_service.py && echo "✅ gui_hardware_manager_service.py found" && \
    test -f ./api/app/services/tron_support_service.py && echo "✅ tron_support_service.py found" && \
    test -f ./api/app/services/__init__.py && echo "✅ services/__init__.py found" && \
    echo "All new modules verified in builder stage" && \
    python3 -c "import sys; sys.path.insert(0, './api'); from app.routers import gui, gui_docker, gui_tor, gui_hardware, tron_support; from app.services import gui_bridge_service, gui_docker_manager_service, gui_tor_manager_service, gui_hardware_manager_service, tron_support_service; print('✅ All module imports successful in builder')"

############################
# Stage 2 – Runtime (Distroless)
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid API Gateway" \
      org.opencontainers.image.description="Distroless API Gateway for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="api-gateway" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/api:/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    API_GATEWAY_PORT=8080 \
    API_GATEWAY_HOST=0.0.0.0

WORKDIR /app

# System directories & certificates
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Bake Python packages into distroless image - explicit COPY with verification
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Application layout COPY (only directories that exist)
COPY --chown=65532:65532 --from=builder /build/api /app/api
COPY --chown=65532:65532 --from=builder /build/gateway /app/gateway
COPY --chown=65532:65532 --from=builder /build/config /app/config

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
