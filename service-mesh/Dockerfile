# syntax=docker/dockerfile:1.5
# =============================================================================
# LUCID SERVICE MESH CONTROLLER - Distroless Build
# =============================================================================
# Container: service-mesh
# Image: pickme/lucid-service-mesh-controller:latest-arm64
# Ports: 8500, 8501, 8502, 8600, 8088
# Aligned with: dockerfile-design.md, Dockerfile-copy-pattern.md
# =============================================================================

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

# =============================================================================
# Stage 1: Builder
# =============================================================================
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

WORKDIR /build

# Install build dependencies
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

# Create system directory markers with actual content (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_SERVICE_MESH_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_SERVICE_MESH_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Upgrade pip tooling
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# Copy requirements
COPY service-mesh/requirements.txt ./requirements.txt

# Verify requirements.txt was copied (per Dockerfile-copy-pattern.md)
RUN test -f ./requirements.txt || (echo "ERROR: requirements.txt not found" && exit 1) && \
    echo "✅ requirements.txt verified"

# Create directory structure before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Create marker files with actual content (per Dockerfile-copy-pattern.md)
# CRITICAL: Must be AFTER pip install to lock in directory structure
RUN echo "LUCID_SERVICE_MESH_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_SERVICE_MESH_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed in builder stage
RUN python3 -c "import fastapi, uvicorn, pydantic, aiohttp, cryptography, yaml, jinja2; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"

# Copy service-mesh source code
COPY service-mesh/ ./service-mesh/

# Verify source code was copied (per Dockerfile-copy-pattern.md)
RUN test -d ./service-mesh || (echo "ERROR: service-mesh directory not copied" && exit 1) && \
    test -f ./service-mesh/main.py || (echo "ERROR: main.py not found" && exit 1) && \
    test -f ./service-mesh/config.py || (echo "ERROR: config.py not found" && exit 1) && \
    test -d ./service-mesh/controller || (echo "ERROR: controller directory not found" && exit 1) && \
    test -d ./service-mesh/config || (echo "ERROR: config directory not found" && exit 1) && \
    echo "✅ Source code directories verified"

# Create source marker files (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_SERVICE_MESH_SOURCE_$(date +%s)" > ./service-mesh/.lucid-source-marker && \
    echo "LUCID_SERVICE_MESH_CONFIG_$(date +%s)" > ./service-mesh/config/.lucid-config-marker && \
    chown -R 65532:65532 ./service-mesh

# =============================================================================
# Stage 2: Distroless Runtime
# =============================================================================
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid Service Mesh Controller" \
      org.opencontainers.image.description="Distroless service mesh controller for Lucid platform" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="service-mesh-controller" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless" \
      com.lucid.expose="8500,8501,8502,8600,8088"

# Environment variables (per dockerfile-design.md)
ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/service-mesh:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

# Service Configuration (from .env.* files)
ENV SERVICE_NAME=service-mesh-controller \
    SERVICE_MESH_HOST=0.0.0.0 \
    SERVICE_MESH_PORT=8500 \
    HTTP_PORT=8088 \
    HEALTHCHECK_PORT=8088 \
    HEALTHCHECK_PATH=/health

# Consul Configuration (from .env.* files)
ENV CONSUL_HOST=localhost \
    CONSUL_PORT=8500 \
    CONSUL_DATACENTER=lucid-dc \
    CONSUL_BOOTSTRAP_EXPECT=1 \
    CONSUL_UI_ENABLED=true \
    CONSUL_CONNECT_ENABLED=true

# Logging Configuration (from .env.* files)
ENV LOG_LEVEL=INFO \
    DEBUG=false \
    LOG_FORMAT=json

WORKDIR /app

# Copy system directories from builder (per Dockerfile-copy-pattern.md)
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Copy CA certificates
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy Python packages (per Dockerfile-copy-pattern.md)
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (per Dockerfile-copy-pattern.md - fails build if missing)
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
assert os.path.exists(os.path.join(site_packages, 'pydantic')), 'pydantic not found'; \
assert os.path.exists(os.path.join(site_packages, 'aiohttp')), 'aiohttp not found'; \
assert os.path.exists(os.path.join(site_packages, 'cryptography')), 'cryptography not found'; \
assert os.path.exists(os.path.join(site_packages, 'yaml')) or os.path.exists(os.path.join(site_packages, 'yaml.py')), 'yaml not found'; \
assert os.path.exists(os.path.join(site_packages, '.lucid-marker')), 'marker file not found'; \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.getsize(marker_path) > 0, 'marker file is empty: ' + marker_path; \
print('✅ Packages verified in runtime stage')"]

# Copy application code from builder
COPY --from=builder --chown=65532:65532 /build/service-mesh /app/service-mesh

# Verify application code was copied (per Dockerfile-copy-pattern.md)
RUN ["/usr/bin/python3.11", "-c", "import os; \
assert os.path.exists('/app/service-mesh'), '/app/service-mesh missing'; \
assert os.path.exists('/app/service-mesh/main.py'), 'main.py missing'; \
assert os.path.exists('/app/service-mesh/config.py'), 'config.py missing'; \
assert os.path.exists('/app/service-mesh/controller'), 'controller directory missing'; \
assert os.path.exists('/app/service-mesh/controller/main.py'), 'controller/main.py missing'; \
assert os.path.exists('/app/service-mesh/config'), 'config directory missing'; \
assert os.path.exists('/app/service-mesh/config/service-mesh.yaml'), 'service-mesh.yaml missing'; \
assert os.path.exists('/app/service-mesh/.lucid-source-marker'), 'source marker missing'; \
assert os.path.exists('/app/service-mesh/config/.lucid-config-marker'), 'config marker missing'; \
print('✅ Application code verified in runtime stage')"]

# Set working directory to service-mesh
WORKDIR /app/service-mesh

# Expose ports
EXPOSE 8500 8501 8502 8600 8088

# Health check (uses HTTP endpoint on HTTP_PORT per dockerfile-design.md)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8088)); s.close(); exit(0 if result == 0 else 1)"]

# Run as non-root user
USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected (per dockerfile-design.md)
ENTRYPOINT []

# Start application
CMD ["/usr/bin/python3.11", "-c", "import asyncio; from controller.main import main; asyncio.run(main())"]
