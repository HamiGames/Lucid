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
        rustc \
        cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . /root/.cargo/env && \
    rustup default stable

ENV PATH=/root/.cargo/bin:$PATH

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

COPY 03_api_gateway/requirements.txt ./requirements.txt

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
    rm -rf /build/wheels

# Builder-stage verification - ensure all packages built correctly
RUN echo "=== Verifying pip installation success ===" && \
    python3.11 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, blake3, zstandard, lz4, cryptography, httpx, aiohttp, structlog, prometheus_client; print('✅ All critical packages installed')" && \
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


    RUN mkdir -p ./api ./api/app ./api/app/db ./api/app/database ./api/app/schemas ./api/app/routers \
    ./services ./models ./endpoints ./config ./api/app/utils ./sessions/ ./sessions/pipeline ./sessions/api \
    ./sessions/core ./sessions/api/integration./gui_api_bridge ./gui_api_bridge/integration  ./sessions/integration \
    # printf .keep in each directory
    && printf "LUCID_API_GATEWAY_API_APP_$(date +%s)" > ./api/app/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_DB_$(date +%s)" > ./api/app/db/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_DATABASE_$(date +%s)" > ./api/app/database/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_SCHEMAS_$(date +%s)" > ./api/app/schemas/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_ROUTERS_$(date +%s)" > ./api/app/routers/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_SERVICES_$(date +%s)" > ./api/app/services/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_UTILS_$(date +%s)" > ./api/app/utils/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_MIDDLEWARE_$(date +%s)" > ./api/app/middleware/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_SCRIPTS_$(date +%s)" > ./api/app/scripts/.keep \
    && printf "LUCID_API_GATEWAY_API_APP_TESTS_$(date +%s)" > ./api/app/tests/.keep \
    # still in 03_api_gateway collection
    && printf "LUCID_API_GATEWAY_MODELS_$(date +%s)" > ./models/.keep \
    && printf "LUCID_API_GATEWAY_SERVICES_$(date +%s)" > ./services/.keep \
    && printf "LUCID_API_GATEWAY_UTILS_$(date +%s)" > ./utils/.keep \
    && printf "LUCID_API_GATEWAY_ENDPOINTS_$(date +%s)" > ./endpoints/.keep \
    && printf "LUCID_API_GATEWAY_CONFIG_$(date +%s)" > ./config/.keep \
    # NOW SESSIONS COLLECTION
    && printf "LUCID_API_GATEWAY_SESSIONS_$(date +%s)" > ./sessions/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_PROCESSOR_$(date +%s)" > ./sessions/processor/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_PIPELINE_$(date +%s)" > ./sessions/pipeline/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_API_$(date +%s)" > ./sessions/api/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_CORE_$(date +%s)" > ./sessions/core/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_API_INTEGRATION_$(date +%s)" > ./sessions/api/integration/.keep \
    && printf "LUCID_API_GATEWAY_GUI_API_BRIDGE_$(date +%s)" > ./gui_api_bridge/.keep \
    && printf "LUCID_API_GATEWAY_GUI_API_BRIDGE_INTEGRATION_$(date +%s)" > ./gui_api_bridge/integration/.keep \
    && printf "LUCID_API_GATEWAY_SESSIONS_INTEGRATION_$(date +%s)" > ./sessions/integration/.keep \
    # NOW GUI_API_BRIDGE COLLECTION
    && printf "LUCID_API_GATEWAY_GUI_API_BRIDGE_$(date +%s)" > ./gui_api_bridge/.keep \
    && printf "LUCID_API_GATEWAY_GUI_API_BRIDGE_INTEGRATION_$(date +%s)" > ./gui_api_bridge/integration/.keep \
    # USE TOUCH TO AFFIRM DIRECTORY CREATION
    && touch ./api/app/.keep ./api/app/db/.keep ./api/app/database/.keep ./api/app/schemas/.keep ./api/app/routers/.keep ./api/app/services/.keep ./api/app/utils/.keep ./api/app/middleware/.keep ./api/app/scripts/.keep ./api/app/tests/.keep ./models/.keep ./services/.keep ./utils/.keep ./endpoints/.keep ./config/.keep ./sessions/.keep ./sessions/processor/.keep ./sessions/pipeline/.keep ./sessions/api/.keep ./sessions/core/.keep ./sessions/api/integration/.keep ./gui_api_bridge/.keep ./gui_api_bridge/integration/.keep ./sessions/integration/.keep
    # Check the new directories with echo (list all .keep files in echo)
    && echo "Directories created successfully" \

    # Application source COPY (only directories that exist with content)
# copy 03_api_gateway/api/* directories to api/
COPY 03_api_gateway/api/app/main.py ./api/app/main.py
COPY 03_api_gateway/api/app/config.py ./api/app/config.py
COPY 03_api_gateway/api/app/deps.py ./api/app/deps.py
# import middleware files
COPY 03_api_gateway/api/app/middleware/auth.py ./api/app/middleware/auth.py
COPY 03_api_gateway/api/app/middleware/logging.py ./api/app/middleware/logging.py
COPY 03_api_gateway/api/app/middleware/rate_limiting.py ./api/app/middleware/rate_limiting.py
COPY 03_api_gateway/api/app/middleware/cors.py ./api/app/middleware/cors.py
COPY 03_api_gateway/api/app/middleware/security.py ./api/app/middleware/security.py
COPY 03_api_gateway/api/app/middleware/error_handling.py ./api/app/middleware/error_handling.py
COPY 03_api_gateway/api/app/middleware/performance.py ./api/app/middleware/performance.py
# import router files
COPY 03_api_gateway/api/app/routers/gui.py ./api/app/routers/gui.py
COPY 03_api_gateway/api/app/routers/gui_docker.py ./api/app/routers/gui_docker.py
COPY 03_api_gateway/api/app/routers/gui_tor.py ./api/app/routers/gui_tor.py
COPY 03_api_gateway/api/app/routers/gui_hardware.py ./api/app/routers/gui_hardware.py
COPY 03_api_gateway/api/app/routers/tron_support.py ./api/app/routers/tron_support.py
COPY 03_api_gateway/api/app/routers/sessions.py ./api/app/routers/sessions.py
COPY 03_api_gateway/api/app/routers/trust.py ./api/app/routers/trust.py
COPY 03_api_gateway/api/app/routers/users.py ./api/app/routers/users.py
COPY 03_api_gateway/api/app/routers/chain.py ./api/app/routers/chain.py
COPY 03_api_gateway/api/app/routers/db_health.py ./api/app/routers/db_health.py
COPY 03_api_gateway/api/app/routers/health.py ./api/app/routers/health.py
COPY 03_api_gateway/api/app/routers/manifest.py ./api/app/routers/manifest.py
COPY 03_api_gateway/api/app/routers/meta.py ./api/app/routers/meta.py
COPY 03_api_gateway/api/app/routers/auth.py ./api/app/routers/auth.py
COPY 03_api_gateway/api/app/routers/wallet.py ./api/app/routers/wallet.py
# import database files
COPY 03_api_gateway/api/app/database/connection.py ./api/app/database/connection.py
COPY 03_api_gateway/models/common.py ./models/common.py
COPY 03_api_gateway/models/auth.py ./models/auth.py
COPY 03_api_gateway/models/session.py ./models/session.py
COPY 03_api_gateway/api/models/user.py ./models/user.py

COPY 03_api_gateway/services/gui_bridge_service.py ./services/gui_bridge_service.py
COPY 03_api_gateway/services/proxy_service.py ./services/proxy_service.py
COPY 03_api_gateway/services/rate_limit_service.py ./services/rate_limit_service.py

COPY 03_api_gateway/api/app/routes/ ./api/app/routes/
COPY 03_api_gateway/api/app/schemas/ ./api/app/schemas/
COPY 03_api_gateway/api/app/utils/config.py ./api/app/utils/config.py
COPY 03_api_gateway/api/app/utils/logging.py ./api/app/utils/logging.py
COPY 03_api_gateway/api/app/utils/logger.py ./api/app/utils/logger.py
COPY 03_api_gateway/endpoints/ ./endpoints/
COPY 03_api_gateway/models/ ./models/
COPY 03_api_gateway/config/ ./config/
COPY 03_api_gateway/gateway/openapi.yml ./gateway/openapi.yml
COPY 03_api_gateway/config/rate-limiting-config.yml ./config/rate-limiting-config.yml
COPY 03_api_gateway/config/routing-config.yml ./config/routing-config.yml
#copy ../../../../sessions/ to sessions/
COPY ../../../../sessions/ ./sessions/
COPY ../../../../sessions/pipeline/ ./sessions/pipeline/
COPY ../../../../sessions/api/ ./sessions/api/
COPY ../../../../sessions/core/                ./sessions/core/
COPY ../../../../sessions/encryption/          ./sessions/encryption/
COPY ../../../../sessions/api/integration/rdp_controller_client.py         ./sessions/api/integration/rdp_controller_client.py

COPY ../../../../sessions/integration/blockchain_client.py         ./sessions/integration/blockchain_client.py
COPY ../../../../sessions/integration/service_base.py         ./sessions/integration/service_base.py
COPY ../../../../sessions/integration/integration_manager.py         ./sessions/integration/integration_manager.py
COPY ../../../../sessions/integration/session_pipeline_client.py         ./sessions/integration/session_pipeline_client.py
COPY ../../../../sessions/integration/session_storage_client.py         ./sessions/integration/session_storage_client.py
COPY ../../../../sessions/integration/session_pipeline_client.py         ./sessions/integration/session_pipeline_client.py



# Create marker files in app directories (ensures COPY won't fail silently)

# Verify new modules are included in builder stage - file existence & imports
RUN echo "Verifying new modules are included in builder stage" && \
    test -f /build/api/app/routers/gui.py && echo "gui.py found" && \
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
COPY --from=builder --chown=65532:65532 /var/run           /app/var/run
COPY --from=builder --chown=65532:65532 /var/lib           /app/var/lib
COPY --from=builder /etc/ssl/certs/ca-certificates.crt     /app/etc/ssl/certs/ca-certificates.crt

# Bake Python packages into distroless image - explicit COPY with verification
# Copy entire Python installation directory (includes site-packages and runtime libraries)
COPY --from=builder --chown=65532:65532 /usr/local/lib/python3.11   /app/usr/local/lib/python3.11
COPY --from=builder --chown=65532:65532 /build/wheels         /app/build/wheels
COPY --from=builder --chown=65532:65532 /usr/local/bin              /app/usr/local/bin
COPY --from=builder --chown=65532:65532 /usr/bin/tini               /app/opt/bin/tini

# Application layout COPY (only directories that exist)
COPY --chown=65532:65532 --from=builder /build/api/app/main.py                       /app/api/app/main.py
COPY --chown=65532:65532 --from=builder /build/api/app/config.py                     /app/api/app/config.py
COPY --chown=65532:65532 --from=builder /build/api/app/deps.py                       /app/api/app/deps.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/auth.py            /app/api/app/middleware/auth.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/logging.py         /app/api/app/middleware/logging.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/rate_limiting.py   /app/api/app/middleware/rate_limiting.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/cors.py            /app/api/app/middleware/cors.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/security.py        /app/api/app/middleware/security.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/config.py               /app/api/app/utils/config.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/logging.py              /app/api/app/utils/logging.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/logger.py               /app/api/app/utils/logger.py

# import router files
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui.py          /app/api/app/routers/gui.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_docker.py   /app/api/app/routers/gui_docker.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_tor.py      /app/api/app/routers/gui_tor.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_hardware.py /app/api/app/routers/gui_hardware.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/tron_support.py /app/api/app/routers/tron_support.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/sessions.py     /app/api/app/routers/sessions.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/trust.py        /app/api/app/routers/trust.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/users.py        /app/api/app/routers/users.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/chain.py        /app/api/app/routers/chain.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/db_health.py    /app/api/app/routers/db_health.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/health.py       /app/api/app/routers/health.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/manifest.py     /app/api/app/routers/manifest.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/meta.py         /app/api/app/routers/meta.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/auth.py         /app/api/app/routers/auth.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/wallet.py       /app/api/app/routers/wallet.py
# import database files
COPY --chown=65532:65532 --from=builder /build/api/app/database/connection.py  /app/api/app/database/connection.py
COPY --chown=65532:65532 --from=builder /build/models/common.py                /app/models/common.py
COPY --chown=65532:65532 --from=builder /build/models/auth.py                  /app/models/auth.py
COPY --chown=65532:65532 --from=builder /build/models/session.py               /app/models/session.py
COPY --chown=65532:65532 --from=builder /build/models/user.py                  /app/models/user.py
# import services files
COPY --chown=65532:65532 --from=builder /build/services/gui_bridge_service.py   /app/services/gui_bridge_service.py
COPY --chown=65532:65532 --from=builder /build/services/proxy_service.py        /app/services/proxy_service.py
COPY --chown=65532:65532 --from=builder /build/services/rate_limit_service.py   /app/services/rate_limit_service.py
# import routes files
COPY --chown=65532:65532 --from=builder /build/api/app/routes/          /app/api/app/routes/
# import schemas files
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/         /app/api/app/schemas/
# import config files
COPY --chown=65532:65532 --from=builder /build/config/config.py         /app/config/config.py
# import endpoints files
COPY --chown=65532:65532 --from=builder /build/endpoints/               /app/endpoints/

COPY --chown=65532:65532 --from=builder /build/sessions/api/integration/rdp_controller_client.py         /app/sessions/api/integration/rdp_controller_client.py
COPY --chown=65532:65532 --from=builder /build/sessions/integration/blockchain_client.py         /app/sessions/integration/blockchain_client.py
COPY --chown=65532:65532 --from=builder /build/sessions/integration/service_base.py         /app/sessions/integration/service_base.py
COPY --chown=65532:65532 --from=builder /build/sessions/integration/integration_manager.py         /app/sessions/integration/integration_manager.py
COPY --chown=65532:65532 --from=builder /build/sessions/integration/session_storage_client.py         /app/sessions/integration/session_storage_client.py
COPY --chown=65532:65532 --from=builder /build/sessions/integration/session_pipeline_client.py         /app/sessions/integration/session_pipeline_client.py

COPY --chown=65532:65532 --from=builder /build/sessions/encryption/      /app/sessions/encryption/
COPY --chown=65532:65532 --from=builder /build/sessions/                /app/sessions/
COPY --chown=65532:65532 --from=builder /build/sessions/pipeline/       /app/sessions/pipeline/
COPY --chown=65532:65532 --from=builder /build/sessions/api/            /app/sessions/api/
COPY --chown=65532:65532 --from=builder /build/sessions/core/           /app/sessions/core/
# import gateway files
COPY --chown=65532:65532 --from=builder /build/gateway/openapi.yml       /app/gateway/openapi.yml
COPY --chown=65532:65532 --from=builder /build/config/rate-limiting-config.yml /app/config/rate-limiting-config.yml
COPY --chown=65532:65532 --from=builder /build/config/routing-config.yml   /app/config/routing-config.yml
# import gui_api_bridge files
# Verify packages were properly copied to runtime stage (distroless-compatible - no shell)
RUN ["/usr/bin/python3.11", "-c", "import os, sys; site_packages = '/usr/local/lib/python3.11/site-packages'; marker_file = os.path.join(site_packages, '.lucid-marker'); app_dirs = ['/app/api', '/app/gateway', '/app/config', '/app/sessions']; checks = [os.path.isdir(site_packages), os.path.isfile(marker_file), os.path.isdir('/usr/local/bin'), os.path.isfile('/usr/local/bin/.lucid-marker')] + [os.path.isdir(d) for d in app_dirs]; assert all(checks), f'Verification failed: site_packages={os.path.isdir(site_packages)}, marker={os.path.isfile(marker_file)}, bin={os.path.isdir(\"/usr/local/bin\")}, bin_marker={os.path.isfile(\"/usr/local/bin/.lucid-marker\")}, app_dirs={[os.path.isdir(d) for d in app_dirs]}'; print('✅ All package and application directories verified in runtime stage')"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/opt/bin/tini", "--"]

CMD ["python3", "-m", "uvicorn", "app.api.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
