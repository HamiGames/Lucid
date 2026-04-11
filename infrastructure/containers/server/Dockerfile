# syntax=docker/dockerfile:1.5
# File: infrastructure/containers/server/Dockerfile
#
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

ARG BUILD_DATE=
ARG VCS_REF=
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

############################
# Stage 1 – Builder
############################
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.12-slim

FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

WORKDIR /build
# LUCID_IMAGE_CONFIG: host registry (builder)
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
        python3.11-wheel \
        python3.11-dev \
        python3-pip \
        python3.11-setuptools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# LUCID_LIB_SKELETON_BEGIN
# Generated: FHS dirs for builder (from final-stage COPY --from, excluding /build/ sources;
# ancestor dirs collapsed; see collect_skeleton_paths_from_dockerfile).
RUN set -eux; \
  mkdir -p \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/usr/lib' \
    '/var/lib' \
    '/var/run' \
    '/usr/local/bin' \
    '/usr/lib/python3/dist-packages' \
    '/usr/local/lib/python3.11/site-packages'; \
  for d in \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/usr/lib' \
    '/var/lib' \
    '/var/run' \
    '/usr/local/bin' \
    '/usr/lib/python3/dist-packages' \
    '/usr/local/lib/python3.11/site-packages'; \
  do \
    printf 'LUCID_LIB_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_LIB_SKELETON_END

COPY RDP/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    printf "LUCID_SERVER_CORE_WHEELS_$(date +%s)" > /build/wheels/.keep && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r ./requirements.txt
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './common' './configs' './server' './service_mesh' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/env' './configs/environment' './configs/integration' './configs/kubernetes' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './server/__pycache__' './service_mesh/__pycache__' './service_mesh/communication' './service_mesh/config' './service_mesh/controller' './service_mesh/discovery' './service_mesh/security' './service_mesh/sidecar' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/pi/ssh' './service_mesh/communication/__pycache__' './service_mesh/config/policies' './service_mesh/config/services' './service_mesh/controller/__pycache__' './service_mesh/discovery/__pycache__' './service_mesh/security/__pycache__' './service_mesh/sidecar/envoy' './service_mesh/sidecar/proxy' './service_mesh/sidecar/envoy/__pycache__' './service_mesh/sidecar/envoy/config' './service_mesh/sidecar/proxy/__pycache__'; \
    for d in \
      '.' \
      './common' \
      './configs' \
      './server' \
      './service_mesh' \
      './common/__pycache__' \
      './common/governance' \
      './common/security' \
      './common/server-tools' \
      './common/templates' \
      './common/tor' \
      './configs/.ssh' \
      './configs/container' \
      './configs/database' \
      './configs/docker' \
      './configs/env' \
      './configs/environment' \
      './configs/integration' \
      './configs/kubernetes' \
      './configs/logging' \
      './configs/pi' \
      './configs/secrets' \
      './configs/security' \
      './configs/tor' \
      './server/__pycache__' \
      './service_mesh/__pycache__' \
      './service_mesh/communication' \
      './service_mesh/config' \
      './service_mesh/controller' \
      './service_mesh/discovery' \
      './service_mesh/security' \
      './service_mesh/sidecar' \
      './common/governance/__pycache__' \
      './common/security/__pycache__' \
      './common/server-tools/__pycache__' \
      './common/tor/__pycache__' \
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
      './configs/pi/ssh' \
      './service_mesh/communication/__pycache__' \
      './service_mesh/config/policies' \
      './service_mesh/config/services' \
      './service_mesh/controller/__pycache__' \
      './service_mesh/discovery/__pycache__' \
      './service_mesh/security/__pycache__' \
      './service_mesh/sidecar/envoy' \
      './service_mesh/sidecar/proxy' \
      './service_mesh/sidecar/envoy/__pycache__' \
      './service_mesh/sidecar/envoy/config' \
      './service_mesh/sidecar/proxy/__pycache__' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN
# alignment-mat lucid-server-core_manifest.json: compose_service='lucid-server-core' — explicit manifest paths → 40 builder COPY line(s) (dockerfile_layout_structure.json section #10 COPY_DIRECTORIES).
COPY _gen_host_config.py ./_gen_host_config.py
COPY common/__init__.py ./common/__init__.py
COPY common/contact_profile_env.py ./common/contact_profile_env.py
COPY common/governance/__init__.py ./common/governance/__init__.py
COPY common/governance/lucid_governor.py ./common/governance/lucid_governor.py
COPY common/governance/param_registry.py ./common/governance/param_registry.py
COPY common/governance/timelock.py ./common/governance/timelock.py
COPY common/load_host_config.py ./common/load_host_config.py
COPY common/security/__init__.py ./common/security/__init__.py
COPY common/security/input_controller.py ./common/security/input_controller.py
COPY common/security/policy_validator.py ./common/security/policy_validator.py
COPY common/security/privacy_shield.py ./common/security/privacy_shield.py
COPY common/security/session_validator.py ./common/security/session_validator.py
COPY common/security/trust_nothing_engine.py ./common/security/trust_nothing_engine.py
COPY common/server-tools/__init__.py ./common/server-tools/__init__.py
COPY common/tor/__init__.py ./common/tor/__init__.py
COPY common/tor/onion_service.py ./common/tor/onion_service.py
COPY common/tor/socks_proxy.py ./common/tor/socks_proxy.py
COPY common/tor/tor_manager.py ./common/tor/tor_manager.py
COPY configs/container/blockchain/docker-compose.chain.yml ./configs/container/blockchain/docker-compose.chain.yml
COPY configs/container/server/docker-compose.server-external.yml ./configs/container/server/docker-compose.server-external.yml
COPY configs/container/server/docker-compose.server-images.yml ./configs/container/server/docker-compose.server-images.yml
COPY infrastructure/containers/_sync_dockerfile_lucid_env.py ./infrastructure/containers/_sync_dockerfile_lucid_env.py
COPY infrastructure/containers/blockchain/docker-compose.chain.yml ./infrastructure/containers/blockchain/docker-compose.chain.yml
COPY infrastructure/containers/config-listings.json ./infrastructure/containers/config-listings.json
COPY infrastructure/containers/dockerfile_recalibration_map.json ./infrastructure/containers/dockerfile_recalibration_map.json
COPY infrastructure/containers/dockerfile_recalibration_map_REPAIRED.json ./infrastructure/containers/dockerfile_recalibration_map_REPAIRED.json
COPY infrastructure/containers/host-config.yml ./infrastructure/containers/host-config.yml
COPY infrastructure/containers/server/docker-compose.server-external.yml ./infrastructure/containers/server/docker-compose.server-external.yml
COPY infrastructure/containers/server/docker-compose.server-images.yml ./infrastructure/containers/server/docker-compose.server-images.yml
COPY infrastructure/containers/services/middle-ware/master-endpoint.yml ./infrastructure/containers/services/middle-ware/master-endpoint.yml
COPY infrastructure/containers/services/server/lucid-server-core.yml ./infrastructure/containers/services/server/lucid-server-core.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.json ./infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.json
COPY infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/core-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/core-cluster-host-alignment.yml
COPY infrastructure/service_mesh/service_mesh_translator.py ./infrastructure/service_mesh/service_mesh_translator.py
COPY server/__init__.py ./server/__init__.py
COPY server/host_context.py ./server/host_context.py
COPY server/run_server.py ./server/run_server.py
COPY infrastructure/service_mesh/service_mesh_translator.py ./service_mesh/service_mesh_translator.py
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY

# Stack compose: use docker-compose.server-images.yml / server-external.yml (copied above). No server-core / server-manager files in repo.

RUN rm -rf configs/environment 2>/dev/null || true



RUN mkdir -p /usr/local/lib/python3.11/site-packages /usr/local/bin && \
    printf "LUCID_SERVER_CORE_RUNTIME" > /var/run/.keep && \
    printf "LUCID_SERVER_CORE_LIB" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib && \
    chmod 644 /var/run/.keep /var/lib/.keep

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links /build/wheels -r ./requirements.txt

RUN printf "LUCID_SERVER_CORE_PACKAGES_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.lucid-marker && \
    chown 65532:65532 /usr/local/lib/python3.11/site-packages/.lucid-marker

RUN python3.11 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, aiofiles, httpx, aiohttp, structlog, prometheus_client, psutil; print('server core packages OK')"


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

ARG BUILD_DATE=
ARG VCS_REF=
ARG VERSION=1.0.0
# Lucid Tor egress / network isolation (PUBLIC_TOR_IP: ../../configs/environment/ ; compose: lucid-tor-egress-network)
ARG PUBLIC_TOR_IP=109.70.100.1
ARG LUCID_INTERNAL_NETWORK_NAME=lucid-pi-network
ARG LUCID_TOR_EGRESS_NETWORK_NAME=lucid-tor-egress-network

WORKDIR /app

















LABEL maintainer="Lucid Development Team" \
      com.lucid.network.internal="${LUCID_INTERNAL_NETWORK_NAME}" \
      com.lucid.network.tor_egress="${LUCID_TOR_EGRESS_NETWORK_NAME}" \
      com.lucid.tor.public_egress_ip="${PUBLIC_TOR_IP}" \
      org.opencontainers.image.title="Lucid Server Core" \
      org.opencontainers.image.description="Distroless server-tier foundation (RDP server, protocol, common, config); orchestrated by server-operations and RDP manager images" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.plane="ops" \
      com.lucid.service="lucid-server-core" \
      com.lucid.layer="1" \
      org.lucid.layer="1" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8100" \
      com.lucid.cluster="core" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation" \
      com.lucid.role="server-core-foundation" \
      com.lucid.hostconfig.registry_key="lucid_server_core" \
      com.lucid.discovery.host_ip="172.20.10.4" \
      com.lucid.service_id="com.lucid.dockerfile.v1.81e12d75c5d335ef.infrastructure.containers.server.Dockerfile" \
      onion.lucid.service_id="lucid-81e12d75c5d335ef-infrastructure-container" \
      org.lucid.service_id="org.lucid.dockerfile.v1.81e12d75c5d335ef:infrastructure/containers/server/Dockerfile" \

ENV     PUBLIC_TOR_IP="${PUBLIC_TOR_IP}" \
    LUCID_INTERNAL_NETWORK_NAME="${LUCID_INTERNAL_NETWORK_NAME}" \
    LUCID_TOR_EGRESS_NETWORK_NAME="${LUCID_TOR_EGRESS_NETWORK_NAME}" \
    PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:$PATH \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONPATH="/app:/app/usr/local/lib/python3.11/site-packages" \
    PYTHONIOENCODING="utf-8" \
    LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    LUCID_HOST_CONFIG_PATH="/app/configs/host-config.yml" \
    LUCID_HOST_CONFIG_SERVICE_NAME=lucid_server_core \
    LUCID_SERVER_CORE_DNS="lucid-server-core" \
    LUCID_SERVER_CORE_HOST_IP="172.20.10.4" \
    LUCID_SERVER_CORE_PORT="8100" \
    LUCID_SERVICE_HOST_IP=172.20.10.4 \
    LUCID_SERVICE_HTTP_PATH=http://lucid-server-core:8100/app
# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=builder --chown=65532:65532 /build/server/ /app/server/
COPY --from=builder --chown=65532:65532 /build/service_mesh/ /app/service_mesh/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /bin/ /app/bin/
COPY --from=builder --chown=65532:65532 /dev/null/ /app/dev/null/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/lib/python3/dist-packages/ /app/usr/lib/python3/dist-packages/
COPY --from=builder --chown=65532:65532 /usr/local/bin/ /app/usr/local/bin/
COPY --from=builder --chown=65532:65532 /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder --chown=65532:65532 /var/lib/ /app/var/lib/
COPY --from=builder --chown=65532:65532 /var/run/ /app/var/run/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END




# LUCID_RUNTIME_COPY_FROM_BUILD_END
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
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
