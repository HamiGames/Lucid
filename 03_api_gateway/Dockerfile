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

WORKDIR /build
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
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        rustc \
        cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /root/.cargo/bin  /root/.cargo/env /root/.cargo/rustc /root && \
    printf "LUCID_API_GATEWAY_ROOT_$(date +%s)" > /root/.keep && \
    touch /root/.keep && \    
    printf "LUCID_API_GATEWAY_CARGO_RUSTC_$(date +%s)" > /root/.cargo/rustc/.keep && \
    touch /root/.cargo/bin/.keep && \
    printf "LUCID_API_GATEWAY_CARGO_ENV_$(date +%s)" > /root/.cargo/env/.keep && \
    touch /root/.cargo/env/.keep && \
    chown -R 65532:65532 /root/.cargo/bin /root/.cargo/env /root/.cargo/rustc /root && \
    chmod +x /root/.keep  /root/.cargo/bin/.keep  /root/.cargo/env/.keep  /root/.cargo/rustc/.keep

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

ENV PATH=/root/.cargo/bin:$PATH

# System markers (per Dockerfile-copy-pattern.md)
RUN printf "LUCID_API_GATEWAY_RUNTIME_DIRECTORY" > /var/run/.keep && \
    printf "LUCID_API_GATEWAY_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib && \
    chmod 644 /var/run/.keep /var/lib/.keep

RUN mkdir -p /usr /usr/local /usr/local/lib /usr/local/bin /usr/local/lib/python3.11 /usr/local/lib/python3.11/site-packages && \
    printf "LUCID_API_GATEWAY_USR_$(date +%s)" > /usr/.keep && \
    touch /usr/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_$(date +%s)" > /usr/local/.keep && \
    touch /usr/local/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_LIB_$(date +%s)" > /usr/local/lib/.keep && \
    touch /usr/local/lib/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_LIB_PYTHON3_11_$(date +%s)" > /usr/local/lib/python3.11/.keep && \
    touch /usr/local/lib/python3.11/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_LIB_PYTHON3_11_SITE_PACKAGES_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.keep && \
    touch /usr/local/lib/python3.11/site-packages/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_BIN_$(date +%s)" > /usr/local/bin/.keep && \
    touch /usr/local/bin/.keep && \
    chown -R 65532:65532 /usr /usr/local /usr/local/lib /usr/local/bin /usr/local/lib/python3.11 /usr/local/lib/python3.11/site-packages && \
    chmod 644 /usr/.keep /usr/local/.keep /usr/local/lib/.keep /usr/local/lib/python3.11/.keep /usr/local/lib/python3.11/site-packages/.keep /usr/local/bin/.keep && \
    echo " Marker files created to lock in directory structure"
# Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    printf "LUCID_API_GATEWAY_BUILD_WHEELS_$(date +%s)" > /build/wheels/.keep && \
    touch /build/wheels/.keep && \
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
    python3.11 -m pip show uvicorn && \
    python3.11 -m pip show fastapi && \
    python3.11 -m pip show pydantic && \
    echo "=== Verifying site-packages directory ===" && \
    ls -la ./usr/local/lib/python3.11/site-packages/ | grep -E "^d" | wc -l && \
    echo "directories found in site-packages" 

# Verify marker files exist with content (critical for distroless COPY)
RUN mkdir -p ./api ./api/app ./api/app/db ./api/app/services ./api/app/db && \
    mkdir -p ./api/app/db/models ./api/app/schemas ./api/app/routers ./api/app/middleware && \
    mkdir -p ./api/app/utils ./api/app/models ./api/app/routes ./api/app/database ./api/app/scripts && \
    mkdir -p ./api/app/security ./infrastructure ./infrastructure/kubernetes ./common ./common/tor && \
    mkdir -p ./config ./endpoints ./config ./services ./models ./database ./utils ./scripts ./tmp ./rust && \
    printf "LUCID_API_GATEWAY_API_$(date +%s)" > ./api/.keep && \
    touch ./api/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_$(date +%s)" > ./api/app/.keep && \
    touch ./api/app/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_SERVICES_$(date +%s)" > ./api/app/services/.keep && \
    touch ./api/.keep ./api/app/.keep ./api/app/services/.keep && \
    echo "api/.keep, api/app/.keep, api/app/services/.keep created" && \
    printf "LUCID_API_GATEWAY_API_APP_ROUTERS_$(date +%s)" > ./api/app/routers/.keep && \
    touch ./api/app/routers/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_UTILS_$(date +%s)" > ./api/app/utils/.keep && \
    touch ./api/app/utils/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_MIDDLEWARE_$(date +%s)" > ./api/app/middleware/.keep && \
    touch ./api/app/middleware/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_DATABASE_$(date +%s)" > ./api/app/database/.keep && \
    touch ./api/app/database/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_SCRIPTS_$(date +%s)" > ./api/app/scripts/.keep && \
    touch ./api/app/scripts/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_MODELS_$(date +%s)" > ./api/app/models/.keep && \
    touch ./api/app/models/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_ROUTES_$(date +%s)" > ./api/app/routes/.keep && \
    touch ./api/app/routes/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_SCHEMAS_$(date +%s)" > ./api/app/schemas/.keep && \
    touch ./api/app/schemas/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_SECURITY_$(date +%s)" > ./api/app/security/.keep && \
    touch ./api/app/security/.keep && \
    echo "api/app/routers/.keep, api/app/utils/.keep, api/app/middleware/.keep, api/app/database/.keep, api/app/scripts/.keep, api/app/models/.keep, api/app/routes/.keep, api/app/security/.keep created" && \
    printf "LUCID_API_GATEWAY_INFRAStrUCTURE_$(date +%s)" > ./infrastructure/.keep && \
    touch ./infrastructure/.keep && \
    printf "LUCID_API_GATEWAY_INFRAStrUCTURE_KUBERNETES_$(date +%s)" > ./infrastructure/kubernetes/.keep && \
    touch ./infrastructure/kubernetes/.keep && \
    touch ./infrastructure/.keep ./infrastructure/kubernetes/.keep && \
    echo "infrastructure/kubernetes/.keep created" && \
    printf "LUCID_COMMON_$(date +%s)" > ./common/.keep && \
    touch ./common/.keep && \
    printf "LUCID_API_COMMON_TOR_$(date +%s)" > ./common/tor/.keep && \
    touch ./common/tor/.keep && \
    printf "LUCID_API_GATEWAY_TMP_$(date +%s)" > ./tmp/.keep && \
    touch ./tmp/.keep && \
    printf "LUCID_API_GATEWAY_RUST_$(date +%s)" > ./rust/.keep && \
    touch ./rust/.keep && \
    echo "rust/.keep created" && \
    echo "common/.keep, common/tor/.keep created" && \
    echo "common directories created" && \
    printf "LUCID_API_GATEWAY_API_APP_DB_$(date +%s)" > ./api/app/db/.keep && \
    touch ./api/app/db/.keep && \
    printf "LUCID_API_GATEWAY_API_APP_DB_MODELS_$(date +%s)" > ./api/app/db/models/.keep && \
    touch ./api/app/db/models/.keep && \
    echo "api/app/db/.keep, api/app/db/models/.keep created" && \  
    printf "LUCID_API_GATEWAY_UTILS_$(date +%s)" > ./utils/.keep && \
    touch ./utils/.keep && \
    printf "LUCID_API_GATEWAY_SERVICES_$(date +%s)" > ./services/.keep && \
    touch ./services/.keep && \
    printf "LUCID_API_GATEWAY_CONFIG_$(date +%s)" > ./config/.keep && \
    touch ./config/.keep && \
    printf "LUCID_API_GATEWAY_SCRIPTS_$(date +%s)" > ./scripts/.keep && \
    touch ./scripts/.keep && \
    printf "LUCID_API_GATEWAY_ENDPOINTS_$(date +%s)" > ./endpoints/.keep && \
    touch ./endpoints/.keep && \
    printf "LUCID_API_GATEWAY_MODELS_$(date +%s)" > ./models/.keep && \
    touch ./models/.keep && \
    printf "LUCID_API_GATEWAY_DATABASE_$(date +%s)" > ./database/.keep && \
    touch ./database/.keep && \
    echo "utils/.keep, scripts/.keep, config/.keep, endpoints/.keep, models/.keep, database/.keep, services/.keep created" && \
    echo "ALL Container directories created"

    
    # Application source COPY (only directories that exist with content)

COPY 03_api_gateway/verify_files.py ./tmp/verify_files.py
RUN echo "=== Checking if verify_files.py was copied ===" && \
    ls -la ./tmp/ && \
    head -5 ./tmp/verify_files.py

COPY common/__init__.py ./common/__init__.py
RUN echo "=== Checking if common/__init__.py was copied ===" && \
    ls -la ./common/ &&  \
    head -5 ./common/__init__.py

COPY common/tor/ ./common/tor/
RUN echo "=== Checking if common/tor/ was copied ===" && \
    ls -la ./common/tor/ && \
    head -5 ./common/tor/

COPY 03_api_gateway/api/__init__.py ./api/__init__.py
COPY infrastructure/kubernetes/01_configmaps/api-gateway-config.yaml ./infrastructure/kubernetes/api-gateway-config.yaml

#copy .api.app files
COPY 03_api_gateway/api/app/ ./api/app/
RUN echo "=== Checking if api/app/ was copied ===" && \
    ls -la ./api/app/ && \
    head -5 ./api/app/

COPY 03_api_gateway/api/app/db/ ./api/app/db/
COPY 03_api_gateway/api/app/db/models/ ./api/app/db/models/
COPY 03_api_gateway/api/app/database/ ./api/app/database/
COPY 03_api_gateway/api/app/schemas/ ./api/app/schemas/
COPY 03_api_gateway/api/app/routers/ ./api/app/routers/

RUN echo "=== Checking if api/app/routers/ was copied ===" && \
    ls -la ./api/app/routers/ && \
    head -5 ./api/app/routers/

COPY 03_api_gateway/api/app/routes/ ./api/app/routes/
COPY 03_api_gateway/api/app/services/ ./api/app/services/
COPY 03_api_gateway/api/app/utils/ ./api/app/utils/
COPY 03_api_gateway/api/app/scripts/ ./api/app/scripts/
COPY 03_api_gateway/api/app/security/ ./api/app/security/
COPY 03_api_gateway/api/app/middleware/ ./api/app/middleware/

# copy .services
COPY 03_api_gateway/services/ ./services/
# copy .database
COPY 03_api_gateway/database/ ./database/
COPY 03_api_gateway/models/ ./models/
COPY 03_api_gateway/utils/ ./utils/
# copy .endpoints
COPY 03_api_gateway/endpoints/ ./endpoints/
COPY 03_api_gateway/config/ ./config/

RUN echo "=== Checking /build contents ===" && \
    ls -la /build/ && \
    echo "=== Checking specific paths ===" && \
    ls -la /build/api/app/ || echo "api/app/ missing" && \
    ls -la /build/models/ || echo "models/ missing" && \
    ls -la /build/api/app/routers/ || echo "api/app/routers/ missing" && \
    ls -la /build/api/app/routes/ || echo "api/app/routes/ missing" && \
    ls -la /build/api/app/services/ || echo "api/app/services/ missing" && \
    ls -la /build/api/app/utils/ || echo "api/app/utils/ missing" && \
    ls -la /build/services/ || echo "services/ missing" && \
    ls -la /build/database/ || echo "database/ missing" && \
    ls -la /build/endpoints/ || echo "endpoints/ missing" && \
    ls -la /build/common/ || echo "common/ missing" 

RUN echo "verifying files in /build directory" && \
    python3.11 ./tmp/verify_files.py || echo "ERROR: verify_files.py failed" && exit 1 && \
    echo "All files verified successfully"


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
COPY --from=builder --chown=65532:65532 /root/.cargo/        /app/rust/
COPY --from=builder --chown=65532:65532 /var/run/          /app/var/run/
COPY --from=builder --chown=65532:65532 /var/lib/           /app/var/lib/
COPY --from=builder --chown=65532:65532 /etc/ssl/certs/ca-certificates.crt     /app/etc/ssl/certs/ca-certificates.crt
COPY --from=builder --chown=65532:65532 /usr/local/lib/python3.11/site-packages/   /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder --chown=65532:65532 /usr/local/bin/              /app/usr/local/bin/
COPY --from=builder --chown=65532:65532 /usr/bin/tini/               /app/usr/bin/tini/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/sbin/ /app/usr/sbin/

# Bake Python packages into distroless image - explicit COPY with verification
# Copy entire Python installation directory (includes site-packages and runtime libraries)
COPY --from=builder --chown=65532:65532 /build/wheels/         /app/build/wheels/
COPY --from=builder --chown=65532:65532 /build/common/__init__.py         /app/common/__init__.py
COPY --from=builder --chown=65532:65532 /build/common/tor/         /app/common/tor/
#kubernetes configmaps
COPY --chown=65532:65532 --from=builder /build/infrastructure/kubernetes/api-gateway-config.yaml     /app/infrastructure/kubernetes/api-gateway-config.yaml
COPY --chown=65532:65532 --from=builder /build/api/app/            /app/api/app/
COPY --chown=65532:65532 --from=builder /build/api/app/middleware/ /app/api/app/middleware/
COPY --chown=65532:65532 --from=builder /build/api/app/utils/ /app/api/app/utils/
COPY --chown=65532:65532 --from=builder /build/api/app/schemas/ /app/api/app/schemas
COPY --chown=65532:65532 --from=builder /build/api/app/routers/  /app/api/app/routers/
COPY --chown=65532:65532 --from=builder /build/api/app/routes/          /app/api/app/routes/
COPY --chown=65532:65532 --from=builder /build/api/app/models/ /app/api/app/models/
COPY --chown=65532:65532 --from=builder /build/api/app/database/ /app/api/app/database/
COPY --chown=65532:65532 --from=builder /build/api/app/routes/          /app/api/app/routes/

# api level directories
COPY --chown=65532:65532 --from=builder /build/services/            /app/services/
COPY --chown=65532:65532 --from=builder /build/database/            /app/database/
COPY --chown=65532:65532 --from=builder /build/models/              /app/models/
COPY --chown=65532:65532 --from=builder /build/config/              /app/config/
COPY --chown=65532:65532 --from=builder /build/endpoints/           /app/endpoints/

# Verify packages were properly copied to runtime stage (distroless-compatible - no shell)
RUN ["/app/usr/bin/python3.11", "-c", "import os, sys; site_packages = '/app/usr/local/lib/python3.11/site-packages'; marker_file = os.path.join(site_packages, '.keep'); app_dirs = ['/app/api','/app/api/app/', '/app/api/app/db', '/app/api/app/database', '/app/api/app/utils', '/app/api/app/models', '/app/api/app/routes', '/app/api/app/schemas', '/app/api/app/services', '/app/api/app/middleware', '/app/api/app/scripts', '/app/api/app/security', '/app/endpoints', '/app/database', '/app/models', '/app/gateway', '/app/config', '/app/sessions', '/app/sidecar']; checks = [os.path.isdir(site_packages), os.path.isfile(marker_file), os.path.isdir('/app/usr/local/bin'), os.path.isfile('/app/usr/local/bin/.keep')] + [os.path.isdir(d) for d in app_dirs]; assert all(checks), f'Verification failed: site_packages={os.path.isdir(site_packages)}, marker={os.path.isfile(marker_file)}, bin={os.path.isdir(\"/app/usr/local/bin\")}, bin_marker={os.path.isfile(\"/app/usr/local/bin/.keep \")}, app_dirs={[os.path.isdir(d) for d in app_dirs]}'; print('✅ All package and application directories verified in runtime stage')"]


EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["/app/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('api-gateway', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/usr/bin/tini", "--"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "app.api.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
