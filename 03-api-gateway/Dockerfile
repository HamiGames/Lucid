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
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

# System markers (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_API_GATEWAY_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_API_GATEWAY_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    echo "upgrading pip and setuptools" && \
    pip install --upgrade pip setuptools wheel &&\
    echo "upgrade complete" && \
    ls -lh /build/wheels/ | head -20 && \
    echo "total wheels built: $(ls -1 /build/wheels/ | wc -l)"

COPY 03-api-gateway/requirements.txt ./requirements.txt

# Step 1: Build wheels explicitly - shows compilation happening
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    echo "building wheels from source" &&\
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r ./requirements.txt && \
    echo "wheel build complete" && \
    ls -lh /build/wheels/ | head -20 && \
    echo "total wheels built: $(ls -1 /build/wheels/ | wc -l)"

# Step 2: Install wheels into system Python
RUN echo "installing wheels into system python" && \
    pip install --no-cache-dir --no-index --find-links /build/wheels -r ./requirements.txt && \
    echo "installation complete" && \
    

# Builder-stage verification - ensure all packages built correctly
RUN echo "=== Verifying pip installation success ===" && \
    python3.11 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, httpx, aiohttp, structlog, prometheus_client; print('✅ All critical packages installed')" && \
    test -d /usr/local/lib/python3.11/site-packages && \
    echo "Package count: $(ls -1 /usr/local/lib/python3.11/site-packages/ | wc -l)" && \
    echo "=== Full package listing ===" && \
    pip list && \
    echo "=== Verifying C extension packages compiled ===" && \
    python3.11 -m pip show cryptography && \
    python3.11 -m pip show motor && \
    python3.11 -m pip show redis && \
    python3.11 -m pip show uvloop && \
    echo "=== Verifying site-packages directory ===" && \
    ls -la /usr/local/lib/python3.11/site-packages/ | grep -E "^d" | wc -l && \
    echo "directories found in site-packages" && \
    echo " All packages ready for final image"

# Create marker files with actual content to lock in directory structure (per Dockerfile-copy-pattern.md)
RUN printf "LUCID_API_GATEWAY_PACKAGES_INSTALLED_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.keep&& \
    printf "LUCID_API_GATEWAY_BINARIES_INSTALLED_$(date +%s)" > /usr/local/bin/.keep && \
    chmod 644 /usr/local/lib/python3.11/site-packages/.keep && \
    chmod 644 /usr/local/bin/.keep && \
    echo " Marker files created to lock in directory structure"

# Verify marker files exist with content (critical for distroless COPY)


    RUN mkdir -p ./api ./gateway ./config ./api/app/endpoints ./sessions ./node ./gui-api-bridge ./infrastructure/service-mesh ./infrastructure/kubernetes ./src/gui ./electron-gui ./gui ./payment-systems ./contracts ./core ./configs/services ./service-mesh ./RDP \
    && printf "LUCID_API_GATEWAY_APP_API_$(date +%s)" > ./api/.keep \
    && touch ./api/.keep \
    && printf "LUCID_API_GATEWAY_APP_GATEWAY_$(date +%s)" > ./gateway/.keep \
    && touch ./gateway/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_CONFIG_$(date +%s)" > ./config/.keep \
    && printf "LUCID_API_GATEWAY_APP_ENDPOINTS_$(date +%s)" > ./api/app/endpoints/.keep \
    && touch ./api/app/endpoints/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_SESSIONS_$(date +%s)" > ./sessions/.keep \
    && touch ./sessions/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_NODE_$(date +%s)" > ./node/.keep \
    && touch ./node/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_GUI_API_BRIDGE_$(date +%s)" > ./gui-api-bridge/.keep \
    && touch ./gui-api-bridge/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_INFRASTRUCTURE_SERVICE_MESH_$(date +%s)" > ./infrastructure/service-mesh/.keep \
    && touch ./infrastructure/service-mesh/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_INFRASTRUCTURE_KUBERNETES_$(date +%s)" > ./infrastructure/kubernetes/.keep \
    && touch ./infrastructure/kubernetes/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_SRC_GUI_$(date +%s)" > ./src/gui/.keep \
    && touch ./src/gui/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_ELECTRON_GUI_$(date +%s)" > ./electron-gui/.keep \
    && touch ./electron-gui/.keep \
    \
    && printf "LUCID_API_GATEWAY_APP_GUI_$(date +%s)" > ./gui/.keep \
    && touch ./gui/.keep \
    && echo "GUI directory created" \
    
    && printf "LUCID_API_GATEWAY_APP_PAYMENT_SYSTEMS_$(date +%s)" > ./payment-systems/.keep \
    && touch ./payment-systems/.keep \
    && echo "Payment systems directory created" \
    \
    && printf "LUCID_API_GATEWAY_APP_CONTRACTS_$(date +%s)" > ./contracts/.keep \
    && touch ./contracts/.keep \
    && echo "Contracts directory created" \
    \
    && mkdir -p ./build/wheels ./configs/services \
    && printf "LUCID_API_GATEWAY_BUILD_WHEELS_$(date +%s)" > ./build/wheels/.keep \
    && printf "LUCID_API_GATEWAY_CONFIGS_SERVICES_$(date +%s)" > ./configs/services/.keep \
    && touch ./build/wheels/.keep \
    && touch ./configs/services/.keep \
    && echo "Build wheels directory created" \
    && echo "Configs services directory created" \
    && echo "Directory structure created" -exec find . -name ".keep" -exec cat {} \;

RUN echo "=== Verifying Keep files ===" && \
    printf " Checking for marker files in /usr/local/lib/python3.11/site-packages/.keep and /usr/local/bin/.keep" && \
    test -f /usr/local/lib/python3.11/site-packages/.keep && \
    printf "%s\n" "$(cat /usr/local/lib/python3.11/site-packages/.keep)" && \
    test -f /usr/local/bin/.keep && \
    printf "%s\n" "$(cat /usr/local/bin/.keep)" && \
    echo " .keep files verified with content"

    # Application source COPY (only directories that exist with content)

COPY 03-api-gateway/api/ ./api/
COPY 03-api-gateway/gateway/ ./gateway/
COPY 03-api-gateway/certs/ ./certs/
COPY 03-api-gateway/config/ ./config/
COPY 03-api-gateway/endpoints/ ./endpoints/
COPY 03-api-gateway/models/ ./models/
COPY 03-api-gateway/services/ ./services/
COPY 03-api-gateway/repositories/ ./repositories/
COPY 03-api-gateway/utils/ ./utils/
COPY 03-api-gateway/middleware/ ./middleware/
COPY 03-api-gateway/scripts/ ./scripts/


# sessions/ is a project-root dependency imported by session_service.py via sys.path
COPY ../../../sessions/ ./sessions/
COPY ../../../node/ ./node/
COPY ../../../gui-api-bridge/ ./gui-api-bridge/
COPY ../../../gui/ ./gui/
COPY ../../../contracts/ ./contracts/
COPY ../../../core/ ./core/
COPY ../../../configs/services/ ./configs/services/
COPY ../../../service-mesh/ ./service-mesh/
COPY ../../../RDP/ ./RDP/
COPY ../../../infrastructure/service-mesh/ ./infrastructure/service-mesh/
COPY ../../../infrastructure/kubernetes/ ./infrastructure/kubernetes/
COPY ../../../src/gui/ ./src/gui/
COPY ../../../electron-gui/ ./electron-gui/
COPY ../../../payment-systems/ ./payment-systems/
COPY ../../../api/ ./api/api/
COPY ../../../payment-systems/ ./payment-systems/
COPY ../../../configs/services/ ./configs/services/

# Create marker files in app directories (ensures COPY won't fail silently)

# Verify new modules are included in builder stage - file existence & imports
RUN echo "Verifying new modules are included in builder stage" && \
    test -f /build/api/app/routers/gui.py && echo "gui.py found" && \
    test -f /build/api/app/routers/gui_docker.py && echo " gui_docker.py found" && \
    test -f /build/api/app/routers/gui_tor.py && echo " gui_tor.py found" && \
    test -f /build/api/app/routers/gui_hardware.py && echo "gui_hardware.py found" && \
    test -f /build/api/app/routers/tron_support.py && echo " tron_support.py found" && \
    test -f /build/api/app/services/gui_bridge_service.py && echo " gui_bridge_service.py found" && \
    test -f /build/api/app/services/gui_docker_manager_service.py && echo " gui_docker_manager_service.py found" && \
    test -f /build/api/app/services/gui_tor_manager_service.py && echo " gui_tor_manager_service.py found" && \
    test -f /build/api/app/services/gui_hardware_manager_service.py && echo " gui_hardware_manager_service.py found" && \
    test -f /build/api/app/services/tron_support_service.py && echo " tron_support_service.py found" && \
    test -f /build/api/app/services/__init__.py && echo " services/__init__.py found" && \
    echo "All new modules verified in builder stage" && \
    python3 -c "import sys; sys.path.insert(0, '/build/api'); sys.path.insert(0, '/build/sessions'); from app.routers import gui, gui_docker, gui_tor, gui_hardware, tron_support; from app.services import gui_bridge_service, gui_docker_manager_service, gui_tor_manager_service, gui_hardware_manager_service, tron_support_service; from pipeline import pipeline_manager; from core import session_generator; print('All module imports successful in builder')"

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
COPY --from=builder --chown=65532:65532 /var/run /app/var/run
COPY --from=builder --chown=65532:65532 /var/lib /app/var/lib
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /app/etc/ssl/certs/ca-certificates.crt

# Bake Python packages into distroless image - explicit COPY with verification
# Copy entire Python installation directory (includes site-packages and runtime libraries)
COPY --from=builder --chown=65532:65532 /usr/local/lib/python3.11 /app/usr/local/lib/python3.11
COPY --from=builder --chown=65532:65532 /build/build/wheels /app/build/wheels
COPY --from=builder --chown=65532:65532 /usr/local/bin   /app/usr/local/bin
COPY --from=builder --chown=65532:65532 /usr/bin/tini        /app/opt/bin/tini

# Application layout COPY (only directories that exist)
COPY --chown=65532:65532 --from=builder /build/configs/services             /app/configs/services
COPY --chown=65532:65532 --from=builder /build/api                          /app/api
COPY --chown=65532:65532 --from=builder /build/gateway                      /app/gateway
COPY --chown=65532:65532 --from=builder /build/config                       /app/config
COPY --chown=65532:65532 --from=builder /build/sessions                     /app/sessions
COPY --chown=65532:65532 --from=builder /build/infrastructure/service-mesh  /app/infrastructure/service-mesh
COPY --chown=65532:65532 --from=builder /build/infrastructure/kubernetes    /app/infrastructure/kubernetes
COPY --chown=65532:65532 --from=builder /build/src/gui                      /app/src/gui
COPY --chown=65532:65532 --from=builder /build/electron-gui                 /app/electron-gui
COPY --chown=65532:65532 --from=builder /build/gui                          /app/gui
COPY --chown=65532:65532 --from=builder /build/gui-api-bridge               /app/gui-api-bridge
COPY --chown=65532:65532 --from=builder /build/payment-systems              /app/payment-systems
COPY --chown=65532:65532 --from=builder /build/contracts                    /app/contracts
COPY --chown=65532:65532 --from=builder /build/core                         /app/core
COPY --chown=65532:65532 --from=builder /build/api/api                      /app/api/api
COPY --chown=65532:65532 --from=builder /build/configs/services             /app/configs/services
COPY --chown=65532:65532 --from=builder /build/service-mesh                 /app/service-mesh
COPY --chown=65532:65532 --from=builder /build/RDP                     /app/RDP
COPY --chown=65532:65532 --from=builder /build/node                    /app/node

# Verify packages were properly copied to runtime stage (distroless-compatible - no shell)
RUN ["/usr/bin/python3.11", "-c", "import os, sys; site_packages = '/usr/local/lib/python3.11/site-packages'; marker_file = os.path.join(site_packages, '.lucid-marker'); app_dirs = ['/app/api', '/app/gateway', '/app/config', '/app/sessions']; checks = [os.path.isdir(site_packages), os.path.isfile(marker_file), os.path.isdir('/usr/local/bin'), os.path.isfile('/usr/local/bin/.lucid-marker')] + [os.path.isdir(d) for d in app_dirs]; assert all(checks), f'Verification failed: site_packages={os.path.isdir(site_packages)}, marker={os.path.isfile(marker_file)}, bin={os.path.isdir(\"/usr/local/bin\")}, bin_marker={os.path.isfile(\"/usr/local/bin/.lucid-marker\")}, app_dirs={[os.path.isdir(d) for d in app_dirs]}'; print('✅ All package and application directories verified in runtime stage')"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/opt/bin/tini", "--"]

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
