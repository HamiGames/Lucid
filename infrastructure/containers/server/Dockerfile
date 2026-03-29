# syntax=docker/dockerfile:1.5
# LUCID SERVER CORE — Distroless Python (shared server-tier foundation)
# Aligned with 03_api_gateway/Dockerfile (builder wheels, /app runtime layout, tini)
# Image: pickme/lucid-server-core:latest-arm64
# Build context: repository root (.)
#
# host-config.yml (services.lucid_server_core):
#   service_name: lucid-server-core, port: 8100, host_ip: 172.20.10.4
#   http_path: http://lucid-server-core:8100/app
#
# This container hosts the server core structure: RDP server modules, protocol, shared
# common code, and RDP config — the HTTP surface is server.xrdp_integration (FastAPI).
#
# Control plane (separate images; they orchestrate or specialize this tier):
#   • infrastructure/containers/server/Dockerfile.server-manager
#       → Lucid Server Operations (full handler bundles + server_manager/entrypoint.py; host-config lucid_server_manager :8081)
#   • infrastructure/containers/rdp/Dockerfile.rdp-server-manager
#       → RDP-focused manager slice (flat app layout, uvicorn xrdp_integration:app; host-config rdp_server_manager HTTP :8090)
#
# Admin UI backend (infrastructure/containers/admin/Dockerfile.admin-ui-backend) should
# reach this tier via compose DNS, e.g. LUCID_SERVER_CORE_URL=http://lucid-server-core:8100
# alongside API_GATEWAY_URL and other Lucid services.

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
# LUCID_IMAGE_CONFIG: .env.secrets + .env.master + host registry (builder)
COPY configs/ ./configs/
RUN rm -rf ./configs/environment && \
    echo ".env.* files removed"
COPY configs/environment/.env.secrets ./configs/.env.secrets
COPY master-env-config.txt ./configs/.env.master
COPY infrastructure/containers/host-config.yml /build/configs/host-config.yml


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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /usr/local/lib/python3.11/site-packages /usr/local/bin && \
    printf "LUCID_SERVER_CORE_RUNTIME" > /var/run/.keep && \
    printf "LUCID_SERVER_CORE_LIB" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib && \
    chmod 644 /var/run/.keep /var/lib/.keep

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY RDP/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    printf "LUCID_SERVER_CORE_WHEELS_$(date +%s)" > /build/wheels/.keep && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r ./requirements.txt
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './common' './config' './configs' './protocol' './server' './service_configs' './common/governance' './common/security' './common/server-tools' './common/tor' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/environment' './configs/integration' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './service_configs/blockchain' './service_configs/distroless' './service_configs/logging' './service_configs/multi-stage' './service_configs/node' './service_configs/payment_services' './service_configs/rdp' './service_configs/security' './service_configs/service_mesh' './service_configs/sessions' './service_configs/x_lucid_cluster_calibration' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/environment/development' './configs/environment/pi' './configs/environment/production' './configs/environment/staging' './configs/pi/ssh'; \
    for d in \
      '.' \
      './common' \
      './config' \
      './configs' \
      './protocol' \
      './server' \
      './service_configs' \
      './common/governance' \
      './common/security' \
      './common/server-tools' \
      './common/tor' \
      './configs/.ssh' \
      './configs/container' \
      './configs/database' \
      './configs/docker' \
      './configs/environment' \
      './configs/integration' \
      './configs/logging' \
      './configs/pi' \
      './configs/secrets' \
      './configs/security' \
      './configs/tor' \
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
      './configs/container/admin' \
      './configs/container/auth' \
      './configs/container/base' \
      './configs/container/blockchain' \
      './configs/container/database' \
      './configs/container/electron_gui' \
      './configs/container/gui' \
      './configs/container/node' \
      './configs/container/payment_systems' \
      './configs/container/rdp' \
      './configs/container/server' \
      './configs/container/sessions' \
      './configs/container/storage' \
      './configs/container/tor' \
      './configs/database/elasticsearch' \
      './configs/database/redis' \
      './configs/docker/distroless' \
      './configs/docker/docs' \
      './configs/docker/multi-stage' \
      './configs/environment/development' \
      './configs/environment/pi' \
      './configs/environment/production' \
      './configs/environment/staging' \
      './configs/pi/ssh' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links /build/wheels -r ./requirements.txt

RUN printf "LUCID_SERVER_CORE_PACKAGES_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.lucid-marker && \
    chown 65532:65532 /usr/local/lib/python3.11/site-packages/.lucid-marker

RUN python3.11 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, aiofiles, httpx, aiohttp, structlog, prometheus_client, psutil; print('server core packages OK')"


COPY infrastructure/containers/server/docker-compose.server-core.yml ./docker-compose.server-core.yml
COPY infrastructure/containers/server/docker-compose.server-manager.yml ./docker-compose.server-manager.yml

COPY infrastructure/containers/services/ ./service_configs/
COPY infrastructure/containers/services/x_lucid_cluster_calibration/core-cluster-host-alignment.yml ./service_configs/x_lucid_cluster_calibration/core-cluster-host-alignment.yml
COPY master-env-config.txt ./configs/.env.master
COPY configs/environment/.env.secrets ./configs/.env.secrets
COPY configs/environment/.env.server-core ./configs/.env.server-core
COPY configs/environment/.env.server-manager ./configs/.env.server-manager

COPY RDP/server/ ./server/
COPY RDP/protocol/ ./protocol/
COPY RDP/common/ ./common/
COPY RDP/config/ ./config/
COPY RDP/__init__.py ./__init__.py

RUN printf "LUCID_SERVER_CORE_SRC_$(date +%s)" > ./server/.keep && \
    printf "LUCID_SERVER_CORE_PROTOCOL_$(date +%s)" > ./protocol/.keep && \
    chown -R 65532:65532 ./server ./protocol ./common ./config ./__init__.py

RUN test -f ./server/xrdp_integration.py && \
    test -f ./server/.keep && \
    test -s ./server/.keep && \
    echo "server core source verified"

############################
# Stage 2 – Runtime (Distroless)
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

WORKDIR /app

















ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid Server Core" \
      org.opencontainers.image.description="Distroless server-tier foundation (RDP server, protocol, common, config); orchestrated by server-operations and RDP manager images" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="lucid-server-core" \
      com.lucid.role="server-core-foundation" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless" \
      com.lucid.expose="8100" \
      com.lucid.hostconfig.registry_key="lucid_server_core" \
      com.lucid.discovery.host_ip="172.20.10.4"

ENV PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LUCID_SERVER_CORE_PORT=8100 \
    LUCID_SERVER_CORE_DNS=lucid-server-core \
    LUCID_SERVER_CORE_HOST_IP=172.20.10.4 \
    LUCID_HOST_CONFIG_PATH=/app/configs/host-config.yml \
    LUCID_HOST_CONFIG_SERVICE_KEY=lucid_server_core \
    LUCID_SERVICE_HOST_IP=172.20.10.4 \
    LUCID_SERVICE_HTTP_PATH=http://lucid-server-core:8100/app
# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/config/ /app/config/
COPY --from=builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=builder --chown=65532:65532 /build/protocol/ /app/protocol/
COPY --from=builder --chown=65532:65532 /build/server/ /app/server/
COPY --from=builder --chown=65532:65532 /build/service_configs/ /app/service_configs/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/lib/python3.11/ /app/usr/lib/python3.11/
COPY --from=builder --chown=65532:65532 /usr/lib/python3/dist-packages/ /app/usr/lib/python3/dist-packages/
COPY --from=builder --chown=65532:65532 /usr/local/bin/ /app/usr/local/bin/
COPY --from=builder --chown=65532:65532 /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder --chown=65532:65532 /var/lib/ /app/var/lib/
COPY --from=builder --chown=65532:65532 /var/run/ /app/var/run/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END
# LUCID_IMAGE_CONFIG: .env.secrets + .env.master + host-config (runtime)
COPY --from=builder --chown=65532:65532 /build/configs/.env.secrets /app/configs/.env.secrets
COPY --from=builder --chown=65532:65532 /build/configs/.env.master /app/configs/.env.master
COPY --from=builder --chown=65532:65532 /build/configs/host-config.yml /app/configs/host-config.yml
COPY --from=builder --chown=65532:65532 /build/service_configs/x_lucid_cluster_calibration/core-cluster-host-alignment.yml /app/service_configs/x_lucid_cluster_calibration/core-cluster-host-alignment.yml

COPY --from=builder /var/run/ /app/var/run/
COPY --from=builder /var/lib/ /app/var/lib/
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /app/etc/ssl/certs/ca-certificates.crt
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /app/usr/local/bin/
COPY --from=builder /usr/bin/ /app/usr/bin/
COPY --from=builder /usr/sbin/ /app/usr/sbin/

COPY --from=builder --chown=65532:65532 /build/wheels/ /app/wheels/
COPY --from=builder --chown=65532:65532 /build/__init__.py /app/__init__.py

COPY --from=builder --chown=65532:65532 /build/configs/.env.server-core /app/configs/.env.server-core
COPY --from=builder --chown=65532:65532 /build/configs/.env.server-manager /app/configs/.env.server-manager
COPY --from=builder --chown=65532:65532 /build/configs/docker-compose.server-core.yml /app/configs/docker-compose.server-core.yml
COPY --from=builder --chown=65532:65532 /build/configs/docker-compose.server-manager.yml /app/configs/docker-compose.server-manager.yml


RUN ["/app/usr/bin/python3.11", "-c", "import os,sys; sp='/app/usr/local/lib/python3.11/site-packages'; sys.path.insert(0,sp); assert os.path.isdir(sp); m=os.path.join(sp,'.lucid-marker'); assert os.path.isfile(m) and os.path.getsize(m)>0; import uvicorn,fastapi,cryptography,aiofiles,psutil; print('runtime site-packages OK')"]

RUN ["/app/usr/bin/python3.11", "-c", "import os; assert os.path.isfile('/app/server/xrdp_integration.py'); assert os.path.isfile('/app/server/.keep'); print('server core app tree OK')"]

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD ["/app/usr/bin/python3.11", "-c", "import os,urllib.request,sys; p=os.environ.get('LUCID_SERVER_CORE_PORT',os.environ.get('LUCID_CORE_SERVER_PORT','8100')); urllib.request.urlopen('http://127.0.0.1:'+str(p)+'/health', timeout=10).read(); sys.exit(0)"]

USER 65532:65532

ENTRYPOINT ["/app/usr/bin/tini", "--"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "server.xrdp_integration:app", "--host", "0.0.0.0", "--port", "8100"]
