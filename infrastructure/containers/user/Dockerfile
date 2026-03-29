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
# Host registry + service fragments (infrastructure/containers/host-config.yml → main_lucid_gateway)
COPY infrastructure/containers/host-config.yml /build/configs/host-config.yml
COPY infrastructure/containers/services/ /build/service_configs/
# System packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        bash \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
        tini \
        python3-wheel \
        python3-dev \
        python3-pip \
        python3-setuptools \
        rustc \
        cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /root /root/.rustup /root/.cargo && \
    printf "LUCID_API_GATEWAY_RUST_$(date +%s)" > /root/.keep && \
    touch /root/.keep && \
    printf "LUCID_API_GATEWAY_RUSTUP_$(date +%s)" > /root/.rustup/.keep && \
    touch /root/.rustup/.keep && \
    printf "LUCID_API_GATEWAY_CARGO_$(date +%s)" > /root/.cargo/.keep && \
    touch /root/.cargo/.keep && \
    chown -R 65532:65532 /root /root/.cargo /root/.rustup && \
    chmod +x /root/.keep  /root/.rustup/.keep  /root/.cargo/.keep


RUN apt-get remove -y rustc cargo && \
    rm -rf /root/.cargo /root/.rustup && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

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
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './api' './common' './config' './configs' './database' './endpoints' './models' './service_configs' './services' './tmp' './utils' './api/app' './api/cluster' './api/lucid_api.egg-info' './api/tests' './common/governance' './common/security' './common/server-tools' './common/tor' './configs/docker' './database/api' './database/config' './database/elasticsearch' './database/models' './database/mongodb' './database/redis' './database/repositories' './database/schema' './database/services' './service_configs/blockchain' './service_configs/distroless' './service_configs/logging' './service_configs/multi-stage' './service_configs/node' './service_configs/payment_services' './service_configs/rdp' './service_configs/security' './service_configs/service_mesh' './service_configs/sessions' './service_configs/x_lucid_cluster_calibration' './api/app/database' './api/app/db' './api/app/middleware' './api/app/models' './api/app/routers' './api/app/routes' './api/app/schemas' './api/app/scripts' './api/app/security' './api/app/services' './api/app/utils' './api/tests/integration' './database/services/backup' './database/services/migration' './database/services/monitoring' './api/app/db/models'; \
    for d in \
      '.' \
      './api' \
      './common' \
      './config' \
      './configs' \
      './database' \
      './endpoints' \
      './models' \
      './service_configs' \
      './services' \
      './tmp' \
      './utils' \
      './api/app' \
      './api/cluster' \
      './api/lucid_api.egg-info' \
      './api/tests' \
      './common/governance' \
      './common/security' \
      './common/server-tools' \
      './common/tor' \
      './configs/docker' \
      './database/api' \
      './database/config' \
      './database/elasticsearch' \
      './database/models' \
      './database/mongodb' \
      './database/redis' \
      './database/repositories' \
      './database/schema' \
      './database/services' \
      './service_configs/blockchain' \
      './service_configs/distroless' \
      './service_configs/logging' \
      './service_configs/multi-stage' \
      './service_configs/node' \
      './service_configs/payment_services' \
      './service_configs/rdp' \
      './service_configs/security' \
      './service_configs/service_mesh' \
      './service_configs/sessions' \
      './service_configs/x_lucid_cluster_calibration' \
      './api/app/database' \
      './api/app/db' \
      './api/app/middleware' \
      './api/app/models' \
      './api/app/routers' \
      './api/app/routes' \
      './api/app/schemas' \
      './api/app/scripts' \
      './api/app/security' \
      './api/app/services' \
      './api/app/utils' \
      './api/tests/integration' \
      './database/services/backup' \
      './database/services/migration' \
      './database/services/monitoring' \
      './api/app/db/models' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

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
    
# Application source COPY (only directories that exist with content)
COPY 03_api_gateway/verify_files.py ./tmp/verify_files.py
RUN echo "=== Checking if verify_files.py was copied ===" && \
    ls -la ./tmp/* && echo "(ls -la ./tmp/* || echo "./tmp/ directory not found")" && \
    ls -la /build/tmp/* && echo "(ls -la /build/tmp/* || echo "/build/tmp/ directory not found")" && \
    echo "verify_files.py was copied"
COPY 03_api_gateway/verify_runtime.py ./tmp/verify_runtime.py


COPY common/__init__.py ./common/__init__.py
RUN echo "=== Checking if common/__init__.py was copied ===" && \
    ls -la ./common/* && echo "(ls -la ./common/* || echo "./common/ directory not found")" && \
    ls -la /build/common/* && echo "(ls -la /build/common/* || echo "/build/common/ directory not found")" && \
    echo "common/ was copied"

COPY common/tor/ ./common/tor/
RUN echo "=== Checking if common/tor/ was copied ===" && \
    ls -la ./common/tor/* && echo "(ls -la ./common/tor/* || echo "./common/tor/ directory not found")" && \
    ls -la /build/common/tor/* && echo "(ls -la /build/common/tor/* || echo "/build/common/tor/ directory not found")" && \
    echo "common/tor/ was copied"

COPY 03_api_gateway/api/ ./api/
RUN echo "=== Checking if api/ was copied ===" && \
    ls -la ./api/* && \
    ls -la /build/api/* && \
    echo "api/ was copied"
COPY 03_api_gateway/utils/ ./utils/
COPY service_configs/kubernetes/01_configmaps/ ./configs/
COPY 03_api_gateway/api/app/ ./api/app/
RUN echo "=== Checking if api/app/ was copied ===" && \
    ls -la ./api/app/* && \
    ls -la /build/api/app/* && \
    echo "api/app/ was copied"

COPY 03_api_gateway/api/app/db/ ./api/app/db/
RUN echo "=== Checking if api/app/db/ was copied ===" && \
    ls -la ./api/app/db/*.py && \
    echo "api/app/db/ was copied"

COPY 03_api_gateway/api/app/db/models/ ./api/app/db/models/
RUN echo "=== Checking if api/app/db/models/ was copied ===" && \
    ls -la ./api/app/db/models/*.py && \
    echo "api/app/db/models/ was copied"

COPY 03_api_gateway/api/app/database/ ./api/app/database/
COPY 03_api_gateway/api/app/schemas/ ./api/app/schemas/
COPY 03_api_gateway/api/app/routers/ ./api/app/routers/

RUN echo "=== Checking if api/app/routers/ was copied ===" && \
    ls -la ./api/app/routers/ && \
    echo "api/app/routers/ was copied"

COPY 03_api_gateway/api/app/routes/ ./api/app/routes/
RUN echo "=== Checking if api/app/routes/ was copied ===" && \
    ls -la ./api/app/routes/ && \
    echo "api/app/routes/ was copied"


COPY 03_api_gateway/api/app/services/ ./api/app/services/
COPY 03_api_gateway/api/app/utils/ ./api/app/utils/
RUN echo "=== Checking if api/app/utils/ was copied ===" && \
    ls -la ./api/app/utils/ && \
    echo "api/app/utils/ was copied"

COPY 03_api_gateway/api/app/scripts/ ./api/app/scripts/
COPY 03_api_gateway/api/app/security/ ./api/app/security/
COPY 03_api_gateway/api/app/middleware/ ./api/app/middleware/
RUN echo "=== Checking if api/app/middleware/ was copied ===" && \
    ls -la ./api/app/middleware/ && \
    echo "api/app/middleware/ was copied"
# copy .services
COPY 03_api_gateway/services/ ./services/
RUN echo "=== Checking if services/ was copied ===" && \
    ls -la ./services/ && \
    echo "services/ was copied"
# copy .database
COPY 03_api_gateway/database/ ./database/
COPY 03_api_gateway/models/ ./models/
COPY 03_api_gateway/utils/ ./utils/
# copy .endpoints
COPY 03_api_gateway/endpoints/ ./endpoints/
COPY 03_api_gateway/config/ ./config/
  
RUN echo "## changing permission on verify_files.py ##" && \
    chmod +x ./tmp/verify_files.py && \
    echo "verify_files.py permission changed" && \
    /usr/bin/python3.11 ./tmp/verify_files.py && \
    echo "All files verified successfully"

# Stage 2 – Runtime (Distroless)

FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest 

WORKDIR /app

















COPY --from=builder --chown=65532:65532 /build/service_configs/x_lucid_cluster_calibration/core-cluster-host-alignment.yml /app/service_configs/x_lucid_cluster_calibration/core-cluster-host-alignment.yml

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
      com.lucid.security="distroless" \
      com.lucid.expose="8080" \
      com.lucid.plane="ops"

# ENV aligned with host-config.yml services.main_lucid_gateway (api-gateway:8080, 172.20.10.1)
ENV PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/api:/app:/app/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LUCID_HOST_CONFIG_PATH=/app/configs/host-config.yml \
    LUCID_HOST_CONFIG_SERVICE_KEY=main_lucid_gateway \
    LUCID_SERVICES_CONFIG_DIR=/app/service_configs \
    LUCID_SERVICE_NAME=api-gateway \
    LUCID_SERVICE_HOST_IP=172.20.10.1 \
    LUCID_SERVICE_HTTP_PATH=http://api-gateway:8080/app \
    API_GATEWAY_PORT=8080 \
    API_GATEWAY_HOST=api-gateway
# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/api/ /app/api/
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/config/ /app/config/
COPY --from=builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=builder --chown=65532:65532 /build/database/ /app/database/
COPY --from=builder --chown=65532:65532 /build/endpoints/ /app/endpoints/
COPY --from=builder --chown=65532:65532 /build/models/ /app/models/
COPY --from=builder --chown=65532:65532 /build/service_configs/ /app/service_configs/
COPY --from=builder --chown=65532:65532 /build/services/ /app/services/
COPY --from=builder --chown=65532:65532 /build/tmp/ /app/tmp/
COPY --from=builder --chown=65532:65532 /build/utils/ /app/utils/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /root/ /app/root/
COPY --from=builder --chown=65532:65532 /usr/ /app/usr/
COPY --from=builder --chown=65532:65532 /var/lib/ /app/var/lib/
COPY --from=builder --chown=65532:65532 /var/run/ /app/var/run/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END




# System directories & certificates
COPY --from=builder /root/.rustup/        /app/rust/
COPY --from=builder /root/.cargo/        /app/cargo/
COPY --from=builder /var/run/          /app/var/run/
COPY --from=builder /var/lib/           /app/var/lib/
COPY --from=builder /etc/ssl/certs/ca-certificates.crt     /app/etc/ssl/certs/ca-certificates.crt
COPY --from=builder /usr/local/lib/python3.11/site-packages/   /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/              /app/usr/local/bin/
COPY --from=builder /usr/bin/ /app/usr/bin/
COPY --from=builder /usr/sbin/ /app/usr/sbin/




# Bake Python packages into distroless image - explicit COPY with verification
COPY --from=builder --chown=65532:65532 /build/wheels/         /app/wheels/
COPY --from=builder --chown=65532:65532 /build/common/__init__.py         /app/common/__init__.py
COPY --from=builder --chown=65532:65532 /build/common/tor/         /app/common/tor/
#kubernetes configmaps
COPY --from=builder --chown=65532:65532 /build/configs/api-gateway-config.yaml /app/configs/api-gateway-config.yaml
COPY --from=builder --chown=65532:65532 /build/api/app/            /app/api/app/
COPY --from=builder --chown=65532:65532 /build/api/app/middleware/ /app/api/app/middleware/
COPY --from=builder --chown=65532:65532 /build/api/app/utils/ /app/api/app/utils/
COPY --from=builder --chown=65532:65532 /build/api/app/schemas/ /app/api/app/schemas/
COPY --from=builder --chown=65532:65532 /build/api/app/models/ /app/api/app/models/
COPY --from=builder --chown=65532:65532 /build/api/app/services/ /app/api/app/services/
COPY --from=builder --chown=65532:65532 /build/api/app/db/ /app/api/app/db/
COPY --from=builder --chown=65532:65532 /build/api/app/db/models/ /app/api/app/db/models/


COPY --from=builder --chown=65532:65532 /build/api/app/routers/  /app/api/app/routers/
COPY --from=builder --chown=65532:65532 /build/api/app/database/ /app/api/app/database/
COPY --from=builder --chown=65532:65532 /build/api/app/routes/          /app/api/app/routes/


# api level directories
COPY --from=builder --chown=65532:65532 /build/tmp/verify_runtime.py /app/tmp/verify_runtime.py

RUN ["/app/usr/bin/python3.11", "/app/tmp/verify_runtime.py"]
RUN ["rm", "-f", "/app/tmp/verify_runtime.py"]



EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["/app/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('api-gateway', 8080)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/usr/bin/tini", "--"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "app.api.app.main:app", "--host", "api-gateway", "--port", "8080"]
