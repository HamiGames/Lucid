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

RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Marker files (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_API_GATEWAY_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_API_GATEWAY_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Builder-stage verification
RUN python3 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, httpx; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"

# Application source COPY (only directories that exist with content)
COPY 03-api-gateway/api/ ./api/
COPY 03-api-gateway/gateway/ ./gateway/
COPY 03-api-gateway/config/ ./config/

# Create marker files in app directories (ensures COPY won't fail silently)
RUN echo "LUCID_API_GATEWAY_APP_API_$(date +%s)" > ./api/.lucid-marker && \
    echo "LUCID_API_GATEWAY_APP_GATEWAY_$(date +%s)" > ./gateway/.lucid-marker && \
    echo "LUCID_API_GATEWAY_APP_CONFIG_$(date +%s)" > ./config/.lucid-marker && \
    find ./api ./gateway ./config -name ".lucid-marker" -exec cat {} \;

# Verify new modules are included in builder stage
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
    echo "All new modules verified in builder stage"

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

# Python packages (per COPY pattern guide)
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Runtime verification of packages
RUN ["python3", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
assert os.path.exists(os.path.join(site_packages, 'pydantic')), 'pydantic not found'; \
assert os.path.exists(os.path.join(site_packages, 'motor')), 'motor not found'; \
assert os.path.exists(os.path.join(site_packages, 'redis')), 'redis not found'; \
assert os.path.exists(os.path.join(site_packages, '.lucid-marker')), 'marker file not found'; \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.getsize(marker_path) > 0, 'marker file is empty: ' + marker_path; \
print('Packages verified in runtime stage')"]

# Application layout COPY (only directories that exist)
COPY --chown=65532:65532 --from=builder /build/api /app/api
COPY --chown=65532:65532 --from=builder /build/gateway /app/gateway
COPY --chown=65532:65532 --from=builder /build/config /app/config

# Verify app directories were copied (fails build if missing)
RUN ["python3", "-c", "import os; \
assert os.path.exists('/app/api/.lucid-marker'), 'api directory not copied'; \
assert os.path.exists('/app/gateway/.lucid-marker'), 'gateway directory not copied'; \
assert os.path.exists('/app/config/.lucid-marker'), 'config directory not copied'; \
assert os.path.exists('/app/api/app/main.py'), 'main.py not found'; \
print('Application directories verified')"]

# Verify new GUI and TRON support modules in runtime stage
RUN ["python3", "-c", "import os; modules = ['/app/api/app/routers/gui.py', '/app/api/app/routers/gui_docker.py', '/app/api/app/routers/gui_tor.py', '/app/api/app/routers/gui_hardware.py', '/app/api/app/routers/tron_support.py', '/app/api/app/services/gui_bridge_service.py', '/app/api/app/services/gui_docker_manager_service.py', '/app/api/app/services/gui_tor_manager_service.py', '/app/api/app/services/gui_hardware_manager_service.py', '/app/api/app/services/tron_support_service.py', '/app/api/app/services/__init__.py']; missing = [m for m in modules if not os.path.exists(m)]; sys.exit(0 if not missing else 1)" ]

# Verify new module imports work correctly
RUN ["python3", "-c", "import sys; sys.path.insert(0, '/app/api'); from app.routers import gui, gui_docker, gui_tor, gui_hardware, tron_support; from app.services import gui_bridge_service, gui_docker_manager_service, gui_tor_manager_service, gui_hardware_manager_service, tron_support_service; print('✅ All new module imports successful'); print(f'✅ GUI Bridge router: {gui.router}'); print(f'✅ GUI Docker router: {gui_docker.router}'); print(f'✅ GUI Tor router: {gui_tor.router}'); print(f'✅ GUI Hardware router: {gui_hardware.router}'); print(f'✅ TRON Support router: {tron_support.router}'); print(f'✅ GUI Bridge service: {gui_bridge_service}'); print(f'✅ GUI Docker service: {gui_docker_manager_service}'); print(f'✅ GUI Tor service: {gui_tor_manager_service}'); print(f'✅ GUI Hardware service: {gui_hardware_manager_service}'); print(f'✅ TRON Support service: {tron_support_service}')" ]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
