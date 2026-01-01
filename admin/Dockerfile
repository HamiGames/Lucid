# syntax=docker/dockerfile:1.5
# LUCID ADMIN INTERFACE - Distroless Container
# Professional multi-platform Admin Interface service for Pi deployment
# Compatible with ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with build/docs/dockerfile-design.md and build/docs/master-docker-design.md
# Admin Interface service (lucid-admin-interface) - Port 8083
# Image: pickme/lucid-admin-interface:latest-arm64
# Configuration: All values from .env.support, .env.core, .env.secrets, .env.foundation via docker-compose
# Build Context: . (project root) - copy admin/ directory

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
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

# Ensures /var/run and /var/lib exist with real content (COPY won't be silent)
RUN echo "LUCID_ADMIN_INTERFACE_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_ADMIN_INTERFACE_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Python Dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY admin/requirements.txt ./requirements.txt

RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Marker Files (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_ADMIN_INTERFACE_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_ADMIN_INTERFACE_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Builder-Stage Verification
RUN python3 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, httpx, aiohttp, jinja2, email_validator, blake3, bcrypt, cryptography, aiofiles, yaml, tenacity; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    test -s /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "✅ Marker file verified in builder (non-empty)"

# Application Source COPY
COPY admin/ ./admin/

# Verify entrypoint and main application files exist
RUN test -f ./admin/entrypoint.py && \
    echo "✅ entrypoint.py found" && \
    test -f ./admin/main.py && \
    echo "✅ main.py found" && \
    test -f ./admin/config.py && \
    echo "✅ config.py found"

# Verify config JSON schema files exist
RUN test -f ./admin/config/health-schema.json && \
    echo "✅ health-schema.json found" && \
    test -f ./admin/config/metrics-schema.json && \
    echo "✅ metrics-schema.json found" && \
    test -f ./admin/config/rbac-schema.json && \
    echo "✅ rbac-schema.json found" && \
    test -f ./admin/config/config-schema.json && \
    echo "✅ config-schema.json found" && \
    test -f ./admin/config/api-schemas.json && \
    echo "✅ api-schemas.json found" && \
    test -f ./admin/config/operational-config.json && \
    echo "✅ operational-config.json found" && \
    echo "✅ All config JSON files verified"

# Verify config YAML files exist
RUN test -f ./admin/config/admin-interface-config.yaml && \
    echo "✅ admin-interface-config.yaml found" && \
    test -f ./admin/config/operational-config.yaml && \
    echo "✅ operational-config.yaml found" && \
    test -s ./admin/config/operational-config.yaml && \
    echo "✅ operational-config.yaml is non-empty" && \
    echo "✅ All config YAML files verified"

# Verify cross-container service modules exist
RUN test -d ./admin/services && \
    echo "✅ services directory found" && \
    test -f ./admin/services/__init__.py && \
    echo "✅ services/__init__.py found" && \
    test -f ./admin/services/service_client.py && \
    echo "✅ services/service_client.py found" && \
    test -f ./admin/services/service_discovery.py && \
    echo "✅ services/service_discovery.py found" && \
    test -f ./admin/services/service_registry.py && \
    echo "✅ services/service_registry.py found" && \
    python3 -c "import sys; sys.path.insert(0, './admin'); from admin.services import ServiceClient, ServiceDiscovery, ServiceRegistry; print('✅ Service modules importable')" && \
    echo "✅ All cross-container service modules verified"

############################
# Stage 2 – Runtime (Distroless)
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid Admin Interface" \
      org.opencontainers.image.description="Distroless admin interface service for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="admin-interface" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="support" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ADMIN_INTERFACE_PORT=8083 \
    ADMIN_INTERFACE_HOST=0.0.0.0

WORKDIR /app

# System Directories & Certificates
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Distroless base already has correct linker/runtime; only copy CA certs
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Python Packages (Per COPY Pattern Guide)
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Runtime Verification of Packages
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; site_packages = '/usr/local/lib/python3.11/site-packages'; sys.path.insert(0, site_packages); assert os.path.exists(site_packages), site_packages + ' does not exist'; assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; assert os.path.exists(os.path.join(site_packages, 'motor')), 'motor not found'; assert os.path.exists(os.path.join(site_packages, 'pymongo')), 'pymongo not found'; assert os.path.exists(os.path.join(site_packages, 'jinja2')), 'jinja2 not found'; assert os.path.exists(os.path.join(site_packages, 'httpx')), 'httpx not found'; assert os.path.exists(os.path.join(site_packages, 'aiohttp')), 'aiohttp not found'; assert os.path.exists(os.path.join(site_packages, 'tenacity')), 'tenacity not found'; assert os.path.exists(os.path.join(site_packages, 'email_validator')) or os.path.exists(os.path.join(site_packages, 'email_validator.py')), 'email_validator not found'; marker_path = os.path.join(site_packages, '.lucid-marker'); assert os.path.exists(marker_path), 'marker file not found'; assert os.path.getsize(marker_path) > 0, 'marker file is empty: ' + marker_path; import uvicorn; assert uvicorn, 'uvicorn import failed'; import fastapi; assert fastapi, 'fastapi import failed'; import jinja2; assert jinja2, 'jinja2 import failed'; import httpx; assert httpx, 'httpx import failed'; import aiohttp; assert aiohttp, 'aiohttp import failed'; import tenacity; assert tenacity, 'tenacity import failed'; import email_validator; assert email_validator, 'email_validator import failed'; print('✅ All packages verified in runtime stage')"]

# Application Layout COPY
COPY --chown=65532:65532 --from=builder /build/admin /app/admin

# Verify application files, config files, and service modules
RUN ["/usr/bin/python3.11", "-c", "import os; import sys; sys.path.insert(0, '/app'); assert os.path.exists('/app/admin/entrypoint.py'), 'entrypoint.py not found'; assert os.path.exists('/app/admin/main.py'), 'main.py not found'; assert os.path.exists('/app/admin/config.py'), 'config.py not found'; assert os.path.exists('/app/admin/config/health-schema.json'), 'health-schema.json not found'; assert os.path.exists('/app/admin/config/metrics-schema.json'), 'metrics-schema.json not found'; assert os.path.exists('/app/admin/config/rbac-schema.json'), 'rbac-schema.json not found'; assert os.path.exists('/app/admin/config/config-schema.json'), 'config-schema.json not found'; assert os.path.exists('/app/admin/config/api-schemas.json'), 'api-schemas.json not found'; assert os.path.exists('/app/admin/config/operational-config.json'), 'operational-config.json not found'; assert os.path.exists('/app/admin/config/admin-interface-config.yaml'), 'admin-interface-config.yaml not found'; assert os.path.exists('/app/admin/config/operational-config.yaml'), 'operational-config.yaml not found'; assert os.path.getsize('/app/admin/config/operational-config.yaml') > 0, 'operational-config.yaml is empty'; assert os.path.exists('/app/admin/services'), 'services directory not found'; assert os.path.exists('/app/admin/services/__init__.py'), 'services/__init__.py not found'; assert os.path.exists('/app/admin/services/service_client.py'), 'services/service_client.py not found'; assert os.path.exists('/app/admin/services/service_discovery.py'), 'services/service_discovery.py not found'; assert os.path.exists('/app/admin/services/service_registry.py'), 'services/service_registry.py not found'; from admin.services import ServiceClient, ServiceDiscovery, ServiceRegistry; print('✅ Application files, config files, and cross-container service modules verified')"]

EXPOSE 8083

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/python3.11", "-c", "import socket; import os; port = int(os.getenv('ADMIN_INTERFACE_PORT', '8083')); s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', port)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["/usr/bin/python3.11", "/app/admin/entrypoint.py"]

# All configuration values provided by .env.support, .env.core, .env.secrets, .env.foundation
