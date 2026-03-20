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
RUN printf "LUCID_API_GATEWAY_RUNTIME_DIRECTORY" > /var/run/.keep && \
    printf "LUCID_API_GATEWAY_LIB_DIRECTORY" > /var/lib/.keep && \
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
    echo "installation complete" 

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
    echo "directories found in site-packages" 

# Create marker files with actual content to lock in directory structure (per Dockerfile-copy-pattern.md)
RUN printf "LUCID_API_GATEWAY_PACKAGES_INSTALLED_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.keep && \
    printf "LUCID_API_GATEWAY_BINARIES_INSTALLED_$(date +%s)" > /usr/local/bin/.keep && \
    chmod 644 /usr/local/lib/python3.11/site-packages/.keep && \
    chmod 644 /usr/local/bin/.keep && \
    echo " Marker files created to lock in directory structure"

# Verify marker files exist with content (critical for distroless COPY)


RUN mkdir -p ./api ./api/app ./api/app/db ./api/app/db/models ./api/app/database ./api/app/utils ./api/app/models ./api/app/routes \
    && mkdir -p ./api/app/schemas ./gateway ./api/app/routers ./api/app/services ./api/app/middleware ./api/app/scripts ./api/app/security \
    && mkdir -p ./config ./endpoints ./config ./models ./utils ./services ./database ./api/app/tests \
    && mkdir -p ./sidecar ./sessions ./sessions/pipeline ./sessions/api ./sessions/processor ./sessions/core ./sessions/api/integration  \
    # printf .keep in each directory
    && printf "LUCID_API_GATEWAY_API_$(date +%s)" > ./api/.keep \
    && printf "LUCID_API_GATEWAY_GATEWAY_$(date +%s)" > ./gateway/.keep \
    && touch ./gateway/.keep \
    && echo "gateway/.keep created" \
    && touch ./api/.keep \
    && echo "api/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_$(date +%s)" > ./api/app/.keep \
    && touch ./api/app/.keep \
    && echo "api/app/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_DB_$(date +%s)" > ./api/app/db/.keep \
    && touch ./api/app/db/.keep \
    && echo "api/app/db/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_DB_MODELS_$(date +%s)" > ./api/app/db/models/.keep \
    && touch ./api/app/db/models/.keep \
    && echo "api/app/db/models/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_DATABASE_$(date +%s)" > ./api/app/database/.keep \
    && touch ./api/app/database/.keep \
    && echo "api/app/database/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_SCHEMAS_$(date +%s)" > ./api/app/schemas/.keep \
    && touch ./api/app/schemas/.keep \
    && echo "api/app/schemas/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_ROUTERS_$(date +%s)" > ./api/app/routers/.keep \
    && touch ./api/app/routers/.keep \
    && echo "api/app/routers/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_SERVICES_$(date +%s)" > ./api/app/services/.keep \
    && touch ./api/app/services/.keep \
    && echo "api/app/services/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_UTILS_$(date +%s)" > ./api/app/utils/.keep \
    && touch ./api/app/utils/.keep \
    && echo "api/app/utils/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_MIDDLEWARE_$(date +%s)" > ./api/app/middleware/.keep \
    && touch ./api/app/middleware/.keep \
    && echo "api/app/middleware/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_SCRIPTS_$(date +%s)" > ./api/app/scripts/.keep \
    && touch ./api/app/scripts/.keep \
    && echo "api/app/scripts/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_TESTS_$(date +%s)" > ./api/app/tests/.keep \
    && touch ./api/app/tests/.keep \
    && echo "api/app/tests/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_MODELS_$(date +%s)" > ./api/app/models/.keep \
    && touch ./api/app/models/.keep \
    && echo "api/app/models/.keep created" \
    && printf "LUCID_API_GATEWAY_API_APP_ROUTES_$(date +%s)" > ./api/app/routes/.keep \
    && touch ./api/app/routes/.keep \
    && echo "api/app/routes/.keep created" \
    && printf "LUCID_API_GATEWAY_MODELS_$(date +%s)" > ./models/.keep \
    && touch ./models/.keep \
    && echo "models/.keep created" \
    && printf "LUCID_API_GATEWAY_SERVICES_$(date +%s)" > ./services/.keep \
    && touch ./services/.keep \
    && echo "services/.keep created" \
    && printf "LUCID_API_GATEWAY_UTILS_$(date +%s)" > ./utils/.keep \
    && touch ./utils/.keep \
    && echo "utils/.keep created" \
    && printf "LUCID_API_GATEWAY_ENDPOINTS_$(date +%s)" > ./endpoints/.keep \
    && touch ./endpoints/.keep \
    && echo "endpoints/.keep created" \
    && printf "LUCID_API_GATEWAY_CONFIG_$(date +%s)" > ./config/.keep \
    && touch ./config/.keep \
    && echo "config/.keep created" \
    && printf "LUCID_API_GATEWAY_DATABASE_$(date +%s)" > ./database/.keep \
    && touch ./database/.keep \
    && echo "database/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_$(date +%s)" > ./sessions/.keep \
    && touch ./sessions/.keep \
    && echo "sessions/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_PROCESSOR_$(date +%s)" > ./sessions/processor/.keep \
    && touch ./sessions/processor/.keep \
    && echo "sessions/processor/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_PIPELINE_$(date +%s)" > ./sessions/pipeline/.keep \
    && touch ./sessions/pipeline/.keep \
    && echo "sessions/pipeline/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_API_$(date +%s)" > ./sessions/api/.keep \
    && touch ./sessions/api/.keep \
    && echo "sessions/api/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_CORE_$(date +%s)" > ./sessions/core/.keep \
    && touch ./sessions/core/.keep \
    && echo "sessions/core/.keep created" \
    && printf "LUCID_API_GATEWAY_SESSIONS_API_INTEGRATION_$(date +%s)" > ./sessions/api/integration/.keep \
    && touch ./sessions/api/integration/.keep \
    && printf "LUCID_API_GATEWAY_CONFIG_RATE_LIMITING_$(date +%s)" > ./config/.keep \
    && touch ./config/.keep \
    && echo "config/.keep created" \

    && echo "sessions/api/integration/.keep created" \
    && printf "LUCID_API_GATEWAY_SIDECAR_$(date +%s)" > ./sidecar/.keep \
    && echo "all container directories created" 


    # Application source COPY (only directories that exist with content)
COPY /var/lib/ ./var/lib/
COPY /var/run/ ./var/run/
COPY /etc/ssl/certs/ca-certificates.crt ./etc/ssl/certs/ca-certificates.crt
COPY /usr/local/lib/python3.11/site-packages/ ./usr/local/lib/python3.11/site-packages/
COPY /usr/local/bin/ ./usr/local/bin/
COPY /usr/bin/ ./usr/bin/
COPY /usr/sbin/ ./usr/sbin/


#copy .api.app files
COPY 03_api_gateway/api/app/__init__.py ./api/app/__init__.py
COPY 03_api_gateway/api/app/main.py ./api/app/main.py
COPY 03_api_gateway/api/app/config.py ./api/app/config.py
COPY 03_api_gateway/api/app/deps.py ./api/app/deps.py
# import .api.app.middleware files
COPY 03_api_gateway/api/app/middleware/__init__.py ./api/app/middleware/__init__.py
COPY 03_api_gateway/api/app/middleware/auth.py ./api/app/middleware/auth.py
COPY 03_api_gateway/api/app/middleware/logging.py ./api/app/middleware/logging.py
COPY 03_api_gateway/api/app/middleware/rate_limit.py ./api/app/middleware/rate_limit.py
COPY 03_api_gateway/api/app/middleware/cors.py ./api/app/middleware/cors.py

# import .api.app.routers files
COPY 03_api_gateway/api/app/routers/__init__.py ./api/app/routers/__init__.py
COPY 03_api_gateway/api/app/routers/gui.py ./api/app/routers/gui.py
COPY 03_api_gateway/api/app/routers/gui_docker.py ./api/app/routers/gui_docker.py
COPY 03_api_gateway/api/app/routers/gui_tor.py ./api/app/routers/gui_tor.py
COPY 03_api_gateway/api/app/routers/gui_hardware.py ./api/app/routers/gui_hardware.py
COPY 03_api_gateway/api/app/routers/tron_support.py ./api/app/routers/tron_support.py
COPY 03_api_gateway/api/app/routers/sessions.py ./api/app/routers/sessions.py
COPY 03_api_gateway/api/app/routers/trust.py ./api/app/routers/trust.py
COPY 03_api_gateway/api/app/routers/users.py ./api/app/routers/users.py
COPY 03_api_gateway/api/app/routers/chain.py ./api/app/routers/chain.py
COPY 03_api_gateway/api/app/routers/manifests.py ./api/app/routers/manifests.py
COPY 03_api_gateway/api/app/routers/meta.py ./api/app/routers/meta.py
COPY 03_api_gateway/api/app/routers/auth.py ./api/app/routers/auth.py
COPY 03_api_gateway/api/app/routers/wallets.py ./api/app/routers/wallets.py
# copy .routes
COPY 03_api_gateway/api/app/routes/ ./api/app/routes/

# import .api.app.database files
COPY 03_api_gateway/api/app/database/__init__.py ./api/app/database/__init__.py
COPY 03_api_gateway/api/app/database/connection.py ./api/app/database/connection.py
#copy .api.app.models files
COPY 03_api_gateway/api/app/models/__init__.py ./api/app/models/__init__.py
COPY 03_api_gateway/api/app/models/common.py ./api/app/models/common.py

#copy .api.app.services files
COPY 03_api_gateway/api/app/services/__init__.py ./api/app/services/__init__.py
COPY 03_api_gateway/api/app/services/gui_bridge_service.py ./api/app/services/gui_bridge_service.py
COPY 03_api_gateway/api/app/services/mongo_service.py ./api/app/services/mongo_service.py
COPY 03_api_gateway/api/app/services/session_service.py ./api/app/services/session_service.py
#copy .api.app.db files
COPY 03_api_gateway/api/app/db/__init__.py ./api/app/db/__init__.py
COPY 03_api_gateway/api/app/db/connection.py ./api/app/db/connection.py
COPY 03_api_gateway/api/app/db/users_repo.py ./api/app/db/users_repo.py
# copy .api.app.db.models files
COPY 03_api_gateway/api/app/db/models/__init__.py ./api/app/db/models/__init__.py
COPY 03_api_gateway/api/app/db/models/user.py ./api/app/db/models/users.py
COPY 03_api_gateway/api/app/db/models/session.py ./api/app/db/models/session.py
# copy .api.app.utils files
COPY 03_api_gateway/api/app/utils/__init__.py ./api/app/utils/__init__.py
COPY 03_api_gateway/api/app/utils/config.py ./api/app/utils/config.py
COPY 03_api_gateway/api/app/utils/logging.py ./api/app/utils/logging.py
COPY 03_api_gateway/api/app/utils/logger.py ./api/app/utils/logger.py
# copy .api.app.schemas files
COPY 03_api_gateway/api/app/schemas/__init__.py ./api/app/schemas/__init__.py
COPY 03_api_gateway/api/app/schemas/auth.py ./api/app/schemas/auth.py
COPY 03_api_gateway/api/app/schemas/sessions.py ./api/app/schemas/sessions.py
COPY 03_api_gateway/api/app/schemas/users.py ./api/app/schemas/users.py
COPY 03_api_gateway/api/app/schemas/meta.py ./api/app/schemas/meta.py
COPY 03_api_gateway/api/app/schemas/errors.py ./api/app/schemas/errors.py
# copy .services
COPY 03_api_gateway/services/__init__.py ./services/__init__.py
COPY 03_api_gateway/services/gui_bridge_service.py ./services/gui_bridge_service.py
COPY 03_api_gateway/services/gui_docker_manager_service.py ./services/gui_docker_manager_service.py
COPY 03_api_gateway/services/gui_tor_manager_service.py ./services/gui_tor_manager_service.py
COPY 03_api_gateway/services/gui_hardware_manager_service.py ./services/gui_hardware_manager_service.py
COPY 03_api_gateway/services/tron_support_service.py ./services/tron_support_service.py
COPY 03_api_gateway/services/session_service.py ./services/session_service.py
COPY 03_api_gateway/services/proxy_service.py ./services/proxy_service.py
COPY 03_api_gateway/services/rate_limit_service.py ./services/rate_limit_service.py
#copy .config files
COPY 03_api_gateway/config/ ./config/

#copy .gateway files
COPY 03_api_gateway/gateway/ ./gateway/

# copy .utils
COPY 03_api_gateway/utils/__init__.py ./utils/__init__.py
COPY 03_api_gateway/utils/validation.py ./utils/validation.py
# copy .api.app.routes
COPY 03_api_gateway/api/app/routes/ ./api/app/routes/
COPY 03_api_gateway/api/app/scripts/ ./api/app/scripts/
COPY 03_api_gateway/api/app/security/ ./api/app/security/
# copy .endpoints
COPY 03_api_gateway/endpoints/ ./endpoints/
# copy .database
COPY 03_api_gateway/database/ ./database/
# copy .models
COPY 03_api_gateway/models/ ./models/
#copy to .sessions
COPY ../../../../sessions/ ./sessions/
COPY ../../../../sessions/pipeline/ ./sessions/pipeline/
COPY ../../../../sessions/api/ ./sessions/api/
COPY ../../../../sessions/core/                ./sessions/core/
COPY ../../../../sessions/encryption/          ./sessions/encryption/
COPY ../../../../sessions/api/integration/__init__.py         ./sessions/api/integration/__init__.py
COPY ../../../../sessions/api/integration/rdp_controller_client.py         ./sessions/api/integration/rdp_controller_client.py
# copy to .gateway
COPY ../../../../infrastructure/kubernetes/05-core/api-gateway.yaml ./gateway/api-gateway.yaml


# Create marker files in app directories (ensures COPY won't fail silently)

# Verify new modules are included in builder stage - file existence & imports
# ✅ This works - absolute imports in verification script
RUN echo "Verifying new modules are included in builder stage" && \
    python3 -c "
import os
modules = [
    '/build/api/app/routers/gui.py',
    '/build/api/app/routers/auth.py',
    '/build/api/app/routers/trust.py',
    '/build/api/app/routers/sessions.py',
    '/build/api/app/routers/tron_support.py',
    '/build/api/app/services/gui_bridge_service.py',
    '/build/api/app/services/tron_support_service.py',
    '/build/api/app/config.py',
    '/build/api/app/main.py',
    '/build/sessions/pipeline/pipeline_manager.py',
    '/build/sessions/core/session_generator.py',
    '/build/sessions/core/session_orchestrator.py'
]
missing = [m for m in modules if not os.path.isfile(m)]
if missing:
    print(f'❌ Missing files: {missing}')
    exit(1)
else:
    print('✅ All module files verified in builder stage') " && \
    echo "Verification complete"

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
COPY --from=builder --chown=65532:65532 /build/var/run           /app/var/run
COPY --from=builder --chown=65532:65532 /build/var/lib           /app/var/lib
COPY --from=builder --chown=65532:65532 /build/etc/ssl/certs/ca-certificates.crt     /app/etc/ssl/certs/ca-certificates.crt
COPY --from=builder --chown=65532:65532 /build/usr/local/lib/python3.11/site-packages   /app/usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /build/usr/local/bin              /app/usr/local/bin
COPY --from=builder --chown=65532:65532 /build/usr/bin/tini               /app/opt/bin/tini
COPY --from=builder --chown=65532:65532 /build/usr/bin/ ./usr/bin/
COPY --from=builder --chown=65532:65532 /build/usr/sbin/ ./usr/sbin/

# Bake Python packages into distroless image - explicit COPY with verification
# Copy entire Python installation directory (includes site-packages and runtime libraries)
COPY --from=builder --chown=65532:65532 /build/wheels         /app/build/wheels

# import .api.app files
COPY --chown=65532:65532 --from=builder /build/api/app/__init__.py                     /app/api/app/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/main.py                       /app/api/app/main.py
COPY --chown=65532:65532 --from=builder /build/api/app/config.py                     /app/api/app/config.py
COPY --chown=65532:65532 --from=builder /build/api/app/deps.py                       /app/api/app/deps.py
# import .api.app.middleware files
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/auth.py            /app/api/app/middleware/auth.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/logging.py         /app/api/app/middleware/logging.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/rate_limit.py   /app/api/app/middleware/rate_limit.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/cors.py            /app/api/app/middleware/cors.py
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/security.py        /app/api/app/middleware/security.py
# import .api.app.utils files
COPY --chown=65532:65532 --from=builder /build/api/app/utils/__init__.py             /app/api/app/utils/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/config.py               /app/api/app/utils/config.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/logging.py              /app/api/app/utils/logging.py
COPY --chown=65532:65532 --from=builder /build/api/app/utils/logger.py               /app/api/app/utils/logger.py
# import .api.app.schemas files
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/__init__.py          /app/api/app/schemas/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/auth.py             /app/api/app/schemas/auth.py
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/sessions.py         /app/api/app/schemas/sessions.py
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/user.py             /app/api/app/schemas/user.py
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/errors.py           /app/api/app/schemas/errors.py
# import .api.app.routers files
COPY --chown=65532:65532 --from=builder /build/api/app/routers/__init__.py       /app/api/app/routers/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui.py          /app/api/app/routers/gui.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_docker.py   /app/api/app/routers/gui_docker.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_tor.py      /app/api/app/routers/gui_tor.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/gui_hardware.py /app/api/app/routers/gui_hardware.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/tron_support.py /app/api/app/routers/tron_support.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/sessions.py     /app/api/app/routers/sessions.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/trust.py        /app/api/app/routers/trust.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/users.py        /app/api/app/routers/users.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/chain.py        /app/api/app/routers/chain.py       /app/api/app/routers/health.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/manifest.py     /app/api/app/routers/manifest.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/meta.py         /app/api/app/routers/meta.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/auth.py         /app/api/app/routers/auth.py
COPY --chown=65532:65532 --from=builder /build/api/app/routers/wallet.py       /app/api/app/routers/wallet.py
# import .api.app.routes files
COPY --chown=65532:65532 --from=builder /build/api/app/routes/          /app/api/app/routes/

# import .api.app.database files
COPY --chown=65532:65532 --from=builder /build/api/app/database/__init__.py    /app/api/app/database/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/database/connection.py  /app/api/app/database/connection.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/__init__.py          /app/api/app/db/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/connection.py       /app/api/app/db/connection.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/users_repo.py        /app/api/app/db/users_repo.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/models/__init__.py  /app/api/app/db/models/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/models/user.py     /app/api/app/db/models/user.py
COPY --chown=65532:65532 --from=builder /build/api/app/db/models/session.py  /app/api/app/db/models/session.py

# import app.api.app.services files
COPY --chown=65532:65532 --from=builder /build/api/app/services/__init__.py   /app/api/app/services/__init__.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/gui_bridge_service.py   /app/api/app/services/gui_bridge_service.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/session_service.py        /app/api/app/services/session_service.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/mongo_service.py        /app/api/app/services/mongo_service.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/tron_support_service.py        /app/api/app/services/tron_support_service.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/gui_docker_manager_service.py        /app/api/app/services/gui_docker_manager_service.py
COPY --chown=65532:65532 --from=builder /build/api/app/services/gui_hardware_manager_service.py        /app/api/app/services/gui_hardware_manager_service.py

#import .services files
COPY --chown=65532:65532 --from=builder /build/services/proxy_service.py        /app/services/proxy_service.py
COPY --chown=65532:65532 --from=builder /build/services/gui_tor_manager_service.py        /app/services/gui_tor_manager_service.py
COPY --chown=65532:65532 --from=builder /build/services/gui_hardware_manager_service.py        /app/services/gui_hardware_manager_service.py
COPY --chown=65532:65532 --from=builder /build/services/tron_support_service.py        /app/services/tron_support_service.py
COPY --chown=65532:65532 --from=builder /build/services/session_service.py        /app/services/session_service.py
COPY --chown=65532:65532 --from=builder /build/services/rate_limit_service.py        /app/services/rate_limit_service.py
COPY --chown=65532:65532 --from=builder /build/services/gui_docker_manager_service.py        /app/services/gui_docker_manager_service.py
COPY --chown=65532:65532 --from=builder /build/services/gui_hardware_manager_service.py        /app/services/gui_hardware_manager_service.py
COPY --chown=65532:65532 --from=builder /build/services/tron_support_service.py        /app/services/tron_support_service.py

# import .api.app.routes files
COPY --chown=65532:65532 --from=builder /build/api/app/routes/          /app/api/app/routes/
# import .config files
COPY --chown=65532:65532 --from=builder /build/config/ /app/config/
# import .sessions files
COPY --chown=65532:65532 --from=builder /build/sessions/api/integration/__init__.py         /app/sessions/api/integration/__init__.py
COPY --chown=65532:65532 --from=builder /build/sessions/api/integration/rdp_controller_client.py         /app/sessions/api/integration/rdp_controller_client.py
COPY --chown=65532:65532 --from=builder /build/sessions/encryption/      /app/sessions/encryption/
COPY --chown=65532:65532 --from=builder /build/sessions/                /app/sessions/
COPY --chown=65532:65532 --from=builder /build/sessions/pipeline/       /app/sessions/pipeline/
COPY --chown=65532:65532 --from=builder /build/sessions/api/            /app/sessions/api/
COPY --chown=65532:65532 --from=builder /build/sessions/core/           /app/sessions/core/
# import .gateway files
#import .endpoints files
COPY --chown=65532:65532 --from=builder /build/endpoints/               /app/endpoints/
# import .services files
COPY --chown=65532:65532 --from=builder /build/services/__init__.py                /app/services/__init__.py
COPY --chown=65532:65532 --from=builder /build/services/gui_bridge_service.py   /app/services/gui_bridge_service.py
COPY --chown=65532:65532 --from=builder /build/services/proxy_service.py        /app/services/proxy_service.py
COPY --chown=65532:65532 --from=builder /build/services/rate_limit_service.py   /app/services/rate_limit_service.py
#import .database files
COPY --chown=65532:65532 --from=builder /build/database/ /app/database/
# import .models files
COPY --chown=65532:65532 --from=builder /build/models/ /app/models/
# import .utils files
COPY --chown=65532:65532 --from=builder /build/utils/ /app/utils/
# import .gateway files
COPY --chown=65532:65532 --from=builder /build/gateway/ /app/gateway/

RUN echo "Verifying new modules are included in runtime stage" && \
    python3 -c "
import os
modules = [
    '/app/api/app/routers/gui.py',
    '/app/api/app/routers/auth.py',
    '/app/api/app/routers/trust.py',
    '/app/api/app/routers/sessions.py',
    '/app/api/app/routers/tron_support.py',
    '/app/api/app/services/gui_bridge_service.py',
    '/app/api/app/services/tron_support_service.py',
    '/app/api/app/config.py',
    '/app/api/app/main.py',
    '/app/sessions/pipeline/pipeline_manager.py',
    '/app/sessions/core/session_generator.py',
    '/app/sessions/core/session_orchestrator.py'
]
missing = [m for m in modules if not os.path.isfile(m)]
if missing:
    print(f'❌ Missing files: {missing}')
    exit(1)
else:
    print('✅ All module files verified in runtime stage') " && \
    echo "Verification complete"
    
# Verify packages were properly copied to runtime stage (distroless-compatible - no shell)
RUN ["/app/usr/bin/python3.11", "-c", "import os, sys; site_packages = '/app/usr/local/lib/python3.11/site-packages'; marker_file = os.path.join(site_packages, '.keep'); app_dirs = ['/app/api','/app/api/app/', '/app/api/app/db', '/app/api/app/database', '/app/api/app/utils', '/app/api/app/models', '/app/api/app/routes', '/app/api/app/schemas', '/app/api/app/services', '/app/api/app/middleware', '/app/api/app/scripts', '/app/api/app/security', '/app/endpoints', '/app/database', '/app/models', '/app/gateway', '/app/config', '/app/sessions', '/app/sidecar']; checks = [os.path.isdir(site_packages), os.path.isfile(marker_file), os.path.isdir('/app/usr/local/bin'), os.path.isfile('/app/usr/local/bin/.keep')] + [os.path.isdir(d) for d in app_dirs]; assert all(checks), f'Verification failed: site_packages={os.path.isdir(site_packages)}, marker={os.path.isfile(marker_file)}, bin={os.path.isdir(\"/app/usr/local/bin\")}, bin_marker={os.path.isfile(\"/app/usr/local/bin/.keep \")}, app_dirs={[os.path.isdir(d) for d in app_dirs]}'; print('✅ All package and application directories verified in runtime stage')"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["/app/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/opt/bin/tini", "--"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "app.api.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
