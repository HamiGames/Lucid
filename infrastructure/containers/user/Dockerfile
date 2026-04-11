# syntax=docker/dockerfile:1.5
# File: infrastructure/containers/user/Dockerfile
#
# LUCID API GATEWAY - Distroless Python Service
# Aligned with dockerfile-design.md and Dockerfile-copy-pattern.md
# Image: pickme/lucid-api-gateway:latest-arm64
# Port: 8080

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
        python3.11-wheel \
        python3.11-dev \
        python3-pip \
        python3.11-setuptools \
        rustc \
        cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# LUCID_LIB_SKELETON_BEGIN
# (no non-/build/ FHS COPY --from paths under /app/ found; no directories to create.)
# LUCID_LIB_SKELETON_END


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

RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    printf "LUCID_API_GATEWAY_BUILD_WHEELS_$(date +%s)" > /build/wheels/.keep && \
    touch /build/wheels/.keep && \
    echo "upgrading pip and setuptools" && \
    pip install --upgrade pip setuptools wheel &&\
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r ./requirements.txt
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './02_network_security' './03_api_gateway' './admin' './api' './auth' './blockchain' './common' './configs' './database' './gui' './gui_api_bridge' './gui_docker_manager' './gui_hardware_manager' './node' './rdp' './scripts' './server' './service_configs' './service_mesh' './sessions' './tmp' './02_network_security/__pycache__' './02_network_security/docs' './02_network_security/tor' './02_network_security/tunnels' './03_api_gateway/__pycache__' './03_api_gateway/api' './03_api_gateway/certs' './03_api_gateway/config' './03_api_gateway/database' './03_api_gateway/docs' './03_api_gateway/endpoints' './03_api_gateway/gateway' './03_api_gateway/legacy' './03_api_gateway/logs' './03_api_gateway/middleware' './03_api_gateway/models' './03_api_gateway/repositories' './03_api_gateway/scripts' './03_api_gateway/services' './03_api_gateway/utils' './admin/__pycache__' './admin/admin_ui' './admin/api' './admin/audit' './admin/config' './admin/emergency' './admin/governance' './admin/key_rotation' './admin/over_lord' './admin/rbac' './admin/services' './admin/system' './admin/ui' './admin/utils' './api/__pycache__' './api/app' './api/cluster' './api/lucid_api.egg-info' './api/tests' './auth/__pycache__' './auth/api' './auth/config' './auth/docs' './auth/middleware' './auth/models' './auth/services' './auth/utils' './blockchain/__pycache__' './blockchain/anchoring' './blockchain/api' './blockchain/chain_client' './blockchain/config' './blockchain/contracts' './blockchain/core' './blockchain/data' './blockchain/deployment' './blockchain/docs' './blockchain/evm' './blockchain/governance' './blockchain/manager' './blockchain/on_system_chain' './blockchain/scripts' './blockchain/tests' './blockchain/utils' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/env' './configs/environment' './configs/gui-alignment' './configs/integration' './configs/kubernetes' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './database/__pycache__' './database/admin' './database/api' './database/config' './database/elasticsearch' './database/models' './database/mongodb' './database/redis' './database/repositories' './database/schema' './database/schemas' './database/services' './gui/__pycache__' './gui/admin' './gui/build' './gui/config' './gui/core' './gui/node' './gui/requirements' './gui/shared' './gui/tests' './gui/user' './gui/wallet' './gui_api_bridge/__pycache__' './gui_api_bridge/config' './gui_api_bridge/gui_api_bridge' './gui_api_bridge/integration' './gui_api_bridge/middleware' './gui_api_bridge/models' './gui_api_bridge/routers' './gui_api_bridge/scripts' './gui_api_bridge/services' './gui_api_bridge/utils' './gui_docker_manager/gui_docker_manager' './gui_hardware_manager/__pycache__' './gui_hardware_manager/gui_hardware_manager' './legacy_files/tests' './node/__pycache__' './node/api' './node/config' './node/consensus' './node/dht_crdt' './node/economy' './node/flags' './node/governance' './node/models' './node/over_lord' './node/payouts' './node/pools' './node/poot' './node/registration' './node/repositories' './node/resources' './node/service_configs' './node/shards' './node/sync' './node/tor' './node/validation' './node/worker' './rdp/__pycache__' './rdp/client' './rdp/common' './rdp/config' './rdp/database' './rdp/monitoring' './rdp/protocol' './rdp/recorder' './rdp/resource_monitor' './rdp/scripts' './rdp/security' './rdp/server' './rdp/server_manager' './rdp/session_controller' './rdp/xrdp' './scripts/__pycache__' './scripts/auth_sm_realignment' './scripts/build' './scripts/compliance' './scripts/config' './scripts/contracts' './scripts/database' './scripts/deployment' './scripts/devcontainer' './scripts/docs' './scripts/foundation' './scripts/gui' './scripts/gui_auth_realignment' './scripts/hardware' './scripts/integration' './scripts/lib' './scripts/load' './scripts/logging' './scripts/maintenance' './scripts/migration' './scripts/monitoring' './scripts/network' './scripts/re-build' './scripts/registry' './scripts/secrets' './scripts/security' './scripts/services' './scripts/testing' './scripts/validation' './scripts/verification' './server/__pycache__' './service_mesh/__pycache__' './service_mesh/communication' './service_mesh/config' './service_mesh/controller' './service_mesh/discovery' './service_mesh/security' './service_mesh/sidecar' './sessions/__pycache__' './sessions/api' './sessions/config' './sessions/core' './sessions/encryption' './sessions/integration' './sessions/pipeline' './sessions/processor' './sessions/recorder' './sessions/security' './sessions/session_systems_control' './sessions/storage' './tests/load' './tests/performance' './tests/security' './tests/validation' './02_network_security/tor/scripts' './02_network_security/tunnels/__pycache__' './02_network_security/tunnels/config' './02_network_security/tunnels/scripts' './03_api_gateway/api/__pycache__' './03_api_gateway/api/app' './03_api_gateway/api/lucid_api.egg-info' './03_api_gateway/api/tests' './03_api_gateway/config/__pycache__' './03_api_gateway/database/__pycache__' './03_api_gateway/docs/swagger' './03_api_gateway/endpoints/__pycache__' './03_api_gateway/legacy/api' './03_api_gateway/legacy/gateway' './03_api_gateway/middleware/__pycache__' './03_api_gateway/models/__pycache__' './03_api_gateway/repositories/__pycache__' './03_api_gateway/services/__pycache__' './03_api_gateway/utils/__pycache__' './admin/admin_ui/__pycache__' './admin/api/__pycache__' './admin/audit/__pycache__' './admin/config/__pycache__' './admin/emergency/__pycache__' './admin/governance/__pycache__' './admin/key_rotation/__pycache__' './admin/rbac/__pycache__' './admin/services/__pycache__' './admin/system/__pycache__' './admin/ui/__pycache__' './admin/ui/static' './admin/ui/templates' './admin/utils/__pycache__' './api/app/__pycache__' './api/app/crypto' './api/app/database' './api/app/db' './api/app/middleware' './api/app/models' './api/app/repo' './api/app/routers' './api/app/routes' './api/app/schemas' './api/app/scripts' './api/app/security' './api/app/services' './api/app/utils' './api/cluster/__pycache__' './api/tests/__pycache__' './api/tests/integration' './auth/api/__pycache__' './auth/config/__pycache__' './auth/middleware/__pycache__' './auth/models/__pycache__' './auth/services/__pycache__' './auth/utils/__pycache__' './blockchain/anchoring/__pycache__' './blockchain/api/app' './blockchain/chain_client/__pycache__' './blockchain/config/__pycache__' './blockchain/contracts/__pycache__' './blockchain/core/__pycache__' './blockchain/data/__pycache__' './blockchain/data/api' './blockchain/deployment/__pycache__' './blockchain/evm/__pycache__' './blockchain/governance/__pycache__' './blockchain/manager/__pycache__' './blockchain/on_system_chain/__pycache__' './blockchain/scripts/__pycache__' './blockchain/tests/__pycache__' './blockchain/utils/__pycache__' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/pi/ssh' './database/admin/__pycache__' './database/api/__pycache__' './database/config/__pycache__' './database/elasticsearch/__pycache__' './database/models/__pycache__' './database/mongodb/__pycache__' './database/redis/__pycache__' './database/repositories/__pycache__' './database/schema/__pycache__' './database/services/__pycache__' './database/services/backup' './database/services/migration' './database/services/monitoring' './gui/admin/__pycache__' './gui/build/__pycache__' './gui/config/__pycache__' './gui/core/__pycache__' './gui/node/__pycache__' './gui/requirements/__pycache__' './gui/shared/__pycache__' './gui/tests/__pycache__' './gui/user/__pycache__' './gui/wallet/wallet_gui' './gui_api_bridge/gui_api_bridge/__pycache__' './gui_api_bridge/gui_api_bridge/config' './gui_api_bridge/gui_api_bridge/integration' './gui_api_bridge/gui_api_bridge/middleware' './gui_api_bridge/gui_api_bridge/models' './gui_api_bridge/gui_api_bridge/routers' './gui_api_bridge/gui_api_bridge/services' './gui_api_bridge/gui_api_bridge/utils' './gui_docker_manager/gui_docker_manager/__pycache__' './gui_docker_manager/gui_docker_manager/config' './gui_docker_manager/gui_docker_manager/integration' './gui_docker_manager/gui_docker_manager/middleware' './gui_docker_manager/gui_docker_manager/models' './gui_docker_manager/gui_docker_manager/routers' './gui_docker_manager/gui_docker_manager/services' './gui_docker_manager/gui_docker_manager/utils' './gui_hardware_manager/gui_hardware_manager/__pycache__' './gui_hardware_manager/gui_hardware_manager/integration' './gui_hardware_manager/gui_hardware_manager/middleware' './gui_hardware_manager/gui_hardware_manager/models' './gui_hardware_manager/gui_hardware_manager/routers' './gui_hardware_manager/gui_hardware_manager/services' './gui_hardware_manager/gui_hardware_manager/utils' './node/api/__pycache__' './node/consensus/__pycache__' './node/dht_crdt/__pycache__' './node/economy/__pycache__' './node/flags/__pycache__' './node/governance/__pycache__' './node/models/__pycache__' './node/payouts/__pycache__' './node/pools/__pycache__' './node/poot/__pycache__' './node/registration/__pycache__' './node/repositories/__pycache__' './node/resources/__pycache__' './node/service_configs/x_lucid_cluster_calibration' './node/shards/__pycache__' './node/sync/__pycache__' './node/tor/__pycache__' './node/validation/__pycache__' './node/worker/__pycache__' './rdp/client/__pycache__' './rdp/common/__pycache__' './rdp/monitoring/grafana' './rdp/protocol/__pycache__' './rdp/recorder/__pycache__' './rdp/resource_monitor/__pycache__' './rdp/resource_monitor/config' './rdp/security/__pycache__' './rdp/server/__pycache__' './rdp/server_manager/__pycache__' './rdp/server_manager/config' './rdp/session_controller/__pycache__' './rdp/session_controller/config' './rdp/session_controller/integration' './rdp/xrdp/__pycache__' './rdp/xrdp/config' './scripts/auth_sm_realignment/.cache' './scripts/auth_sm_realignment/lib' './scripts/build/__pycache__' './scripts/build/components' './scripts/build/core' './scripts/build/distroless' './scripts/build/utils' './scripts/compliance/distroless' './scripts/compliance/general' './scripts/deployment/devcontainer' './scripts/deployment/distroless' './scripts/deployment/pi' './scripts/deployment/utils' './scripts/gui_auth_realignment/.cache' './scripts/gui_auth_realignment/lib' './scripts/maintenance/cleanup' './scripts/maintenance/optimization' './scripts/maintenance/recovery' './scripts/network/diagnostics' './scripts/network/security' './scripts/network/setup' './scripts/testing/integration' './scripts/testing/unit' './scripts/testing/utils' './scripts/validation/__pycache__' './scripts/verification/__pycache__' './service_mesh/communication/__pycache__' './service_mesh/config/policies' './service_mesh/config/services' './service_mesh/controller/__pycache__' './service_mesh/discovery/__pycache__' './service_mesh/security/__pycache__' './service_mesh/sidecar/envoy' './service_mesh/sidecar/proxy' './sessions/api/__pycache__' './sessions/api/config' './sessions/api/integration' './sessions/core/__pycache__' './sessions/encryption/__pycache__' './sessions/integration/__pycache__' './sessions/pipeline/__pycache__' './sessions/pipeline/integration' './sessions/processor/__pycache__' './sessions/processor/config' './sessions/processor/integration' './sessions/recorder/__pycache__' './sessions/recorder/config' './sessions/recorder/integration' './sessions/security/__pycache__' './sessions/session_systems_control/__pycache__' './sessions/storage/__pycache__' './sessions/storage/config' './tests/integration/phase2' './tests/integration/phase4' './03_api_gateway/api/app/__pycache__' './03_api_gateway/api/app/database' './03_api_gateway/api/app/db' './03_api_gateway/api/app/middleware' './03_api_gateway/api/app/models' './03_api_gateway/api/app/routers' './03_api_gateway/api/app/routes' './03_api_gateway/api/app/schemas' './03_api_gateway/api/app/scripts' './03_api_gateway/api/app/security' './03_api_gateway/api/app/services' './03_api_gateway/api/app/utils' './03_api_gateway/api/tests/__pycache__' './03_api_gateway/api/tests/integration' './03_api_gateway/docs/swagger/dist' './admin/ui/static/css' './admin/ui/static/js' './api/app/crypto/__pycache__' './api/app/database/__pycache__' './api/app/database/repositories' './api/app/db/__pycache__' './api/app/db/models' './api/app/middleware/__pycache__' './api/app/models/__pycache__' './api/app/repo/__pycache__' './api/app/routers/__pycache__' './api/app/routes/__pycache__' './api/app/schemas/__pycache__' './api/app/scripts/__pycache__' './api/app/security/__pycache__' './api/app/services/__pycache__' './api/app/utils/__pycache__' './api/tests/integration/__pycache__' './blockchain/api/app/__pycache__' './blockchain/api/app/crypto' './blockchain/api/app/database' './blockchain/api/app/db' './blockchain/api/app/middleware' './blockchain/api/app/models' './blockchain/api/app/repo' './blockchain/api/app/routers' './blockchain/api/app/routes' './blockchain/api/app/schemas' './blockchain/api/app/services' './blockchain/data/api/__pycache__' './database/services/backup/__pycache__' './database/services/migration/__pycache__' './database/services/monitoring/__pycache__' './gui_docker_manager/gui_docker_manager/integration/__pycache__' './gui_docker_manager/gui_docker_manager/middleware/__pycache__' './gui_docker_manager/gui_docker_manager/models/__pycache__' './gui_docker_manager/gui_docker_manager/routers/__pycache__' './gui_docker_manager/gui_docker_manager/services/__pycache__' './gui_docker_manager/gui_docker_manager/utils/__pycache__' './gui_hardware_manager/gui_hardware_manager/integration/__pycache__' './gui_hardware_manager/gui_hardware_manager/middleware/__pycache__' './gui_hardware_manager/gui_hardware_manager/models/__pycache__' './gui_hardware_manager/gui_hardware_manager/routers/__pycache__' './gui_hardware_manager/gui_hardware_manager/services/__pycache__' './gui_hardware_manager/gui_hardware_manager/utils/__pycache__' './rdp/monitoring/grafana/dashboards' './rdp/monitoring/grafana/datasources' './rdp/session_controller/integration/__pycache__' './service_mesh/sidecar/envoy/__pycache__' './service_mesh/sidecar/envoy/config' './service_mesh/sidecar/proxy/__pycache__' './sessions/api/integration/__pycache__' './sessions/pipeline/integration/__pycache__' './sessions/processor/integration/__pycache__' './sessions/recorder/integration/__pycache__' './03_api_gateway/api/app/database/__pycache__' './03_api_gateway/api/app/db/__pycache__' './03_api_gateway/api/app/db/models' './03_api_gateway/api/app/middleware/__pycache__' './03_api_gateway/api/app/models/__pycache__' './03_api_gateway/api/app/routers/__pycache__' './03_api_gateway/api/app/routes/__pycache__' './03_api_gateway/api/app/schemas/__pycache__' './03_api_gateway/api/app/scripts/__pycache__' './03_api_gateway/api/app/security/__pycache__' './03_api_gateway/api/app/services/__pycache__' './03_api_gateway/api/app/utils/__pycache__' './03_api_gateway/api/tests/integration/__pycache__' './api/app/database/repositories/__pycache__' './api/app/db/models/__pycache__' './blockchain/api/app/crypto/__pycache__' './blockchain/api/app/database/__pycache__' './blockchain/api/app/database/repositories' './blockchain/api/app/db/__pycache__' './blockchain/api/app/middleware/__pycache__' './blockchain/api/app/models/__pycache__' './blockchain/api/app/repo/__pycache__' './blockchain/api/app/routers/__pycache__' './blockchain/api/app/routes/__pycache__' './blockchain/api/app/schemas/__pycache__' './blockchain/api/app/services/__pycache__' './legacy_files/tests/tests/integration/phase2' './legacy_files/tests/tests/integration/phase4'; \
    for d in \
      '.' \
      './02_network_security' \
      './03_api_gateway' \
      './admin' \
      './api' \
      './auth' \
      './blockchain' \
      './common' \
      './configs' \
      './database' \
      './gui' \
      './gui_api_bridge' \
      './gui_docker_manager' \
      './gui_hardware_manager' \
      './node' \
      './rdp' \
      './scripts' \
      './server' \
      './service_configs' \
      './service_mesh' \
      './sessions' \
      './tmp' \
      './02_network_security/__pycache__' \
      './02_network_security/docs' \
      './02_network_security/tor' \
      './02_network_security/tunnels' \
      './03_api_gateway/__pycache__' \
      './03_api_gateway/api' \
      './03_api_gateway/certs' \
      './03_api_gateway/config' \
      './03_api_gateway/database' \
      './03_api_gateway/docs' \
      './03_api_gateway/endpoints' \
      './03_api_gateway/gateway' \
      './03_api_gateway/legacy' \
      './03_api_gateway/logs' \
      './03_api_gateway/middleware' \
      './03_api_gateway/models' \
      './03_api_gateway/repositories' \
      './03_api_gateway/scripts' \
      './03_api_gateway/services' \
      './03_api_gateway/utils' \
      './admin/__pycache__' \
      './admin/admin_ui' \
      './admin/api' \
      './admin/audit' \
      './admin/config' \
      './admin/emergency' \
      './admin/governance' \
      './admin/key_rotation' \
      './admin/over_lord' \
      './admin/rbac' \
      './admin/services' \
      './admin/system' \
      './admin/ui' \
      './admin/utils' \
      './api/__pycache__' \
      './api/app' \
      './api/cluster' \
      './api/lucid_api.egg-info' \
      './api/tests' \
      './auth/__pycache__' \
      './auth/api' \
      './auth/config' \
      './auth/docs' \
      './auth/middleware' \
      './auth/models' \
      './auth/services' \
      './auth/utils' \
      './blockchain/__pycache__' \
      './blockchain/anchoring' \
      './blockchain/api' \
      './blockchain/chain_client' \
      './blockchain/config' \
      './blockchain/contracts' \
      './blockchain/core' \
      './blockchain/data' \
      './blockchain/deployment' \
      './blockchain/docs' \
      './blockchain/evm' \
      './blockchain/governance' \
      './blockchain/manager' \
      './blockchain/on_system_chain' \
      './blockchain/scripts' \
      './blockchain/tests' \
      './blockchain/utils' \
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
      './configs/gui-alignment' \
      './configs/integration' \
      './configs/kubernetes' \
      './configs/logging' \
      './configs/pi' \
      './configs/secrets' \
      './configs/security' \
      './configs/tor' \
      './database/__pycache__' \
      './database/admin' \
      './database/api' \
      './database/config' \
      './database/elasticsearch' \
      './database/models' \
      './database/mongodb' \
      './database/redis' \
      './database/repositories' \
      './database/schema' \
      './database/schemas' \
      './database/services' \
      './gui/__pycache__' \
      './gui/admin' \
      './gui/build' \
      './gui/config' \
      './gui/core' \
      './gui/node' \
      './gui/requirements' \
      './gui/shared' \
      './gui/tests' \
      './gui/user' \
      './gui/wallet' \
      './gui_api_bridge/__pycache__' \
      './gui_api_bridge/config' \
      './gui_api_bridge/gui_api_bridge' \
      './gui_api_bridge/integration' \
      './gui_api_bridge/middleware' \
      './gui_api_bridge/models' \
      './gui_api_bridge/routers' \
      './gui_api_bridge/scripts' \
      './gui_api_bridge/services' \
      './gui_api_bridge/utils' \
      './gui_docker_manager/gui_docker_manager' \
      './gui_hardware_manager/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager' \
      './legacy_files/tests' \
      './node/__pycache__' \
      './node/api' \
      './node/config' \
      './node/consensus' \
      './node/dht_crdt' \
      './node/economy' \
      './node/flags' \
      './node/governance' \
      './node/models' \
      './node/over_lord' \
      './node/payouts' \
      './node/pools' \
      './node/poot' \
      './node/registration' \
      './node/repositories' \
      './node/resources' \
      './node/service_configs' \
      './node/shards' \
      './node/sync' \
      './node/tor' \
      './node/validation' \
      './node/worker' \
      './rdp/__pycache__' \
      './rdp/client' \
      './rdp/common' \
      './rdp/config' \
      './rdp/database' \
      './rdp/monitoring' \
      './rdp/protocol' \
      './rdp/recorder' \
      './rdp/resource_monitor' \
      './rdp/scripts' \
      './rdp/security' \
      './rdp/server' \
      './rdp/server_manager' \
      './rdp/session_controller' \
      './rdp/xrdp' \
      './scripts/__pycache__' \
      './scripts/auth_sm_realignment' \
      './scripts/build' \
      './scripts/compliance' \
      './scripts/config' \
      './scripts/contracts' \
      './scripts/database' \
      './scripts/deployment' \
      './scripts/devcontainer' \
      './scripts/docs' \
      './scripts/foundation' \
      './scripts/gui' \
      './scripts/gui_auth_realignment' \
      './scripts/hardware' \
      './scripts/integration' \
      './scripts/lib' \
      './scripts/load' \
      './scripts/logging' \
      './scripts/maintenance' \
      './scripts/migration' \
      './scripts/monitoring' \
      './scripts/network' \
      './scripts/re-build' \
      './scripts/registry' \
      './scripts/secrets' \
      './scripts/security' \
      './scripts/services' \
      './scripts/testing' \
      './scripts/validation' \
      './scripts/verification' \
      './server/__pycache__' \
      './service_mesh/__pycache__' \
      './service_mesh/communication' \
      './service_mesh/config' \
      './service_mesh/controller' \
      './service_mesh/discovery' \
      './service_mesh/security' \
      './service_mesh/sidecar' \
      './sessions/__pycache__' \
      './sessions/api' \
      './sessions/config' \
      './sessions/core' \
      './sessions/encryption' \
      './sessions/integration' \
      './sessions/pipeline' \
      './sessions/processor' \
      './sessions/recorder' \
      './sessions/security' \
      './sessions/session_systems_control' \
      './sessions/storage' \
      './tests/load' \
      './tests/performance' \
      './tests/security' \
      './tests/validation' \
      './02_network_security/tor/scripts' \
      './02_network_security/tunnels/__pycache__' \
      './02_network_security/tunnels/config' \
      './02_network_security/tunnels/scripts' \
      './03_api_gateway/api/__pycache__' \
      './03_api_gateway/api/app' \
      './03_api_gateway/api/lucid_api.egg-info' \
      './03_api_gateway/api/tests' \
      './03_api_gateway/config/__pycache__' \
      './03_api_gateway/database/__pycache__' \
      './03_api_gateway/docs/swagger' \
      './03_api_gateway/endpoints/__pycache__' \
      './03_api_gateway/legacy/api' \
      './03_api_gateway/legacy/gateway' \
      './03_api_gateway/middleware/__pycache__' \
      './03_api_gateway/models/__pycache__' \
      './03_api_gateway/repositories/__pycache__' \
      './03_api_gateway/services/__pycache__' \
      './03_api_gateway/utils/__pycache__' \
      './admin/admin_ui/__pycache__' \
      './admin/api/__pycache__' \
      './admin/audit/__pycache__' \
      './admin/config/__pycache__' \
      './admin/emergency/__pycache__' \
      './admin/governance/__pycache__' \
      './admin/key_rotation/__pycache__' \
      './admin/rbac/__pycache__' \
      './admin/services/__pycache__' \
      './admin/system/__pycache__' \
      './admin/ui/__pycache__' \
      './admin/ui/static' \
      './admin/ui/templates' \
      './admin/utils/__pycache__' \
      './api/app/__pycache__' \
      './api/app/crypto' \
      './api/app/database' \
      './api/app/db' \
      './api/app/middleware' \
      './api/app/models' \
      './api/app/repo' \
      './api/app/routers' \
      './api/app/routes' \
      './api/app/schemas' \
      './api/app/scripts' \
      './api/app/security' \
      './api/app/services' \
      './api/app/utils' \
      './api/cluster/__pycache__' \
      './api/tests/__pycache__' \
      './api/tests/integration' \
      './auth/api/__pycache__' \
      './auth/config/__pycache__' \
      './auth/middleware/__pycache__' \
      './auth/models/__pycache__' \
      './auth/services/__pycache__' \
      './auth/utils/__pycache__' \
      './blockchain/anchoring/__pycache__' \
      './blockchain/api/app' \
      './blockchain/chain_client/__pycache__' \
      './blockchain/config/__pycache__' \
      './blockchain/contracts/__pycache__' \
      './blockchain/core/__pycache__' \
      './blockchain/data/__pycache__' \
      './blockchain/data/api' \
      './blockchain/deployment/__pycache__' \
      './blockchain/evm/__pycache__' \
      './blockchain/governance/__pycache__' \
      './blockchain/manager/__pycache__' \
      './blockchain/on_system_chain/__pycache__' \
      './blockchain/scripts/__pycache__' \
      './blockchain/tests/__pycache__' \
      './blockchain/utils/__pycache__' \
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
      './database/admin/__pycache__' \
      './database/api/__pycache__' \
      './database/config/__pycache__' \
      './database/elasticsearch/__pycache__' \
      './database/models/__pycache__' \
      './database/mongodb/__pycache__' \
      './database/redis/__pycache__' \
      './database/repositories/__pycache__' \
      './database/schema/__pycache__' \
      './database/services/__pycache__' \
      './database/services/backup' \
      './database/services/migration' \
      './database/services/monitoring' \
      './gui/admin/__pycache__' \
      './gui/build/__pycache__' \
      './gui/config/__pycache__' \
      './gui/core/__pycache__' \
      './gui/node/__pycache__' \
      './gui/requirements/__pycache__' \
      './gui/shared/__pycache__' \
      './gui/tests/__pycache__' \
      './gui/user/__pycache__' \
      './gui/wallet/wallet_gui' \
      './gui_api_bridge/gui_api_bridge/__pycache__' \
      './gui_api_bridge/gui_api_bridge/config' \
      './gui_api_bridge/gui_api_bridge/integration' \
      './gui_api_bridge/gui_api_bridge/middleware' \
      './gui_api_bridge/gui_api_bridge/models' \
      './gui_api_bridge/gui_api_bridge/routers' \
      './gui_api_bridge/gui_api_bridge/services' \
      './gui_api_bridge/gui_api_bridge/utils' \
      './gui_docker_manager/gui_docker_manager/__pycache__' \
      './gui_docker_manager/gui_docker_manager/config' \
      './gui_docker_manager/gui_docker_manager/integration' \
      './gui_docker_manager/gui_docker_manager/middleware' \
      './gui_docker_manager/gui_docker_manager/models' \
      './gui_docker_manager/gui_docker_manager/routers' \
      './gui_docker_manager/gui_docker_manager/services' \
      './gui_docker_manager/gui_docker_manager/utils' \
      './gui_hardware_manager/gui_hardware_manager/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/integration' \
      './gui_hardware_manager/gui_hardware_manager/middleware' \
      './gui_hardware_manager/gui_hardware_manager/models' \
      './gui_hardware_manager/gui_hardware_manager/routers' \
      './gui_hardware_manager/gui_hardware_manager/services' \
      './gui_hardware_manager/gui_hardware_manager/utils' \
      './node/api/__pycache__' \
      './node/consensus/__pycache__' \
      './node/dht_crdt/__pycache__' \
      './node/economy/__pycache__' \
      './node/flags/__pycache__' \
      './node/governance/__pycache__' \
      './node/models/__pycache__' \
      './node/payouts/__pycache__' \
      './node/pools/__pycache__' \
      './node/poot/__pycache__' \
      './node/registration/__pycache__' \
      './node/repositories/__pycache__' \
      './node/resources/__pycache__' \
      './node/service_configs/x_lucid_cluster_calibration' \
      './node/shards/__pycache__' \
      './node/sync/__pycache__' \
      './node/tor/__pycache__' \
      './node/validation/__pycache__' \
      './node/worker/__pycache__' \
      './rdp/client/__pycache__' \
      './rdp/common/__pycache__' \
      './rdp/monitoring/grafana' \
      './rdp/protocol/__pycache__' \
      './rdp/recorder/__pycache__' \
      './rdp/resource_monitor/__pycache__' \
      './rdp/resource_monitor/config' \
      './rdp/security/__pycache__' \
      './rdp/server/__pycache__' \
      './rdp/server_manager/__pycache__' \
      './rdp/server_manager/config' \
      './rdp/session_controller/__pycache__' \
      './rdp/session_controller/config' \
      './rdp/session_controller/integration' \
      './rdp/xrdp/__pycache__' \
      './rdp/xrdp/config' \
      './scripts/auth_sm_realignment/.cache' \
      './scripts/auth_sm_realignment/lib' \
      './scripts/build/__pycache__' \
      './scripts/build/components' \
      './scripts/build/core' \
      './scripts/build/distroless' \
      './scripts/build/utils' \
      './scripts/compliance/distroless' \
      './scripts/compliance/general' \
      './scripts/deployment/devcontainer' \
      './scripts/deployment/distroless' \
      './scripts/deployment/pi' \
      './scripts/deployment/utils' \
      './scripts/gui_auth_realignment/.cache' \
      './scripts/gui_auth_realignment/lib' \
      './scripts/maintenance/cleanup' \
      './scripts/maintenance/optimization' \
      './scripts/maintenance/recovery' \
      './scripts/network/diagnostics' \
      './scripts/network/security' \
      './scripts/network/setup' \
      './scripts/testing/integration' \
      './scripts/testing/unit' \
      './scripts/testing/utils' \
      './scripts/validation/__pycache__' \
      './scripts/verification/__pycache__' \
      './service_mesh/communication/__pycache__' \
      './service_mesh/config/policies' \
      './service_mesh/config/services' \
      './service_mesh/controller/__pycache__' \
      './service_mesh/discovery/__pycache__' \
      './service_mesh/security/__pycache__' \
      './service_mesh/sidecar/envoy' \
      './service_mesh/sidecar/proxy' \
      './sessions/api/__pycache__' \
      './sessions/api/config' \
      './sessions/api/integration' \
      './sessions/core/__pycache__' \
      './sessions/encryption/__pycache__' \
      './sessions/integration/__pycache__' \
      './sessions/pipeline/__pycache__' \
      './sessions/pipeline/integration' \
      './sessions/processor/__pycache__' \
      './sessions/processor/config' \
      './sessions/processor/integration' \
      './sessions/recorder/__pycache__' \
      './sessions/recorder/config' \
      './sessions/recorder/integration' \
      './sessions/security/__pycache__' \
      './sessions/session_systems_control/__pycache__' \
      './sessions/storage/__pycache__' \
      './sessions/storage/config' \
      './tests/integration/phase2' \
      './tests/integration/phase4' \
      './03_api_gateway/api/app/__pycache__' \
      './03_api_gateway/api/app/database' \
      './03_api_gateway/api/app/db' \
      './03_api_gateway/api/app/middleware' \
      './03_api_gateway/api/app/models' \
      './03_api_gateway/api/app/routers' \
      './03_api_gateway/api/app/routes' \
      './03_api_gateway/api/app/schemas' \
      './03_api_gateway/api/app/scripts' \
      './03_api_gateway/api/app/security' \
      './03_api_gateway/api/app/services' \
      './03_api_gateway/api/app/utils' \
      './03_api_gateway/api/tests/__pycache__' \
      './03_api_gateway/api/tests/integration' \
      './03_api_gateway/docs/swagger/dist' \
      './admin/ui/static/css' \
      './admin/ui/static/js' \
      './api/app/crypto/__pycache__' \
      './api/app/database/__pycache__' \
      './api/app/database/repositories' \
      './api/app/db/__pycache__' \
      './api/app/db/models' \
      './api/app/middleware/__pycache__' \
      './api/app/models/__pycache__' \
      './api/app/repo/__pycache__' \
      './api/app/routers/__pycache__' \
      './api/app/routes/__pycache__' \
      './api/app/schemas/__pycache__' \
      './api/app/scripts/__pycache__' \
      './api/app/security/__pycache__' \
      './api/app/services/__pycache__' \
      './api/app/utils/__pycache__' \
      './api/tests/integration/__pycache__' \
      './blockchain/api/app/__pycache__' \
      './blockchain/api/app/crypto' \
      './blockchain/api/app/database' \
      './blockchain/api/app/db' \
      './blockchain/api/app/middleware' \
      './blockchain/api/app/models' \
      './blockchain/api/app/repo' \
      './blockchain/api/app/routers' \
      './blockchain/api/app/routes' \
      './blockchain/api/app/schemas' \
      './blockchain/api/app/services' \
      './blockchain/data/api/__pycache__' \
      './database/services/backup/__pycache__' \
      './database/services/migration/__pycache__' \
      './database/services/monitoring/__pycache__' \
      './gui_docker_manager/gui_docker_manager/integration/__pycache__' \
      './gui_docker_manager/gui_docker_manager/middleware/__pycache__' \
      './gui_docker_manager/gui_docker_manager/models/__pycache__' \
      './gui_docker_manager/gui_docker_manager/routers/__pycache__' \
      './gui_docker_manager/gui_docker_manager/services/__pycache__' \
      './gui_docker_manager/gui_docker_manager/utils/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/integration/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/middleware/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/models/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/routers/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/services/__pycache__' \
      './gui_hardware_manager/gui_hardware_manager/utils/__pycache__' \
      './rdp/monitoring/grafana/dashboards' \
      './rdp/monitoring/grafana/datasources' \
      './rdp/session_controller/integration/__pycache__' \
      './service_mesh/sidecar/envoy/__pycache__' \
      './service_mesh/sidecar/envoy/config' \
      './service_mesh/sidecar/proxy/__pycache__' \
      './sessions/api/integration/__pycache__' \
      './sessions/pipeline/integration/__pycache__' \
      './sessions/processor/integration/__pycache__' \
      './sessions/recorder/integration/__pycache__' \
      './03_api_gateway/api/app/database/__pycache__' \
      './03_api_gateway/api/app/db/__pycache__' \
      './03_api_gateway/api/app/db/models' \
      './03_api_gateway/api/app/middleware/__pycache__' \
      './03_api_gateway/api/app/models/__pycache__' \
      './03_api_gateway/api/app/routers/__pycache__' \
      './03_api_gateway/api/app/routes/__pycache__' \
      './03_api_gateway/api/app/schemas/__pycache__' \
      './03_api_gateway/api/app/scripts/__pycache__' \
      './03_api_gateway/api/app/security/__pycache__' \
      './03_api_gateway/api/app/services/__pycache__' \
      './03_api_gateway/api/app/utils/__pycache__' \
      './03_api_gateway/api/tests/integration/__pycache__' \
      './api/app/database/repositories/__pycache__' \
      './api/app/db/models/__pycache__' \
      './blockchain/api/app/crypto/__pycache__' \
      './blockchain/api/app/database/__pycache__' \
      './blockchain/api/app/database/repositories' \
      './blockchain/api/app/db/__pycache__' \
      './blockchain/api/app/middleware/__pycache__' \
      './blockchain/api/app/models/__pycache__' \
      './blockchain/api/app/repo/__pycache__' \
      './blockchain/api/app/routers/__pycache__' \
      './blockchain/api/app/routes/__pycache__' \
      './blockchain/api/app/schemas/__pycache__' \
      './blockchain/api/app/services/__pycache__' \
      './legacy_files/tests/tests/integration/phase2' \
      './legacy_files/tests/tests/integration/phase4' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN
# alignment-mat api-gateway_manifest.json: compose_service='api-gateway' — explicit manifest paths → 338 builder COPY line(s) (dockerfile_layout_structure.json section #10 COPY_DIRECTORIES).
COPY 02_network_security/tunnels/entrypoint.py ./02_network_security/tunnels/entrypoint.py
COPY 03_api_gateway/__init__.py ./03_api_gateway/__init__.py
COPY 03_api_gateway/api/__init__.py ./03_api_gateway/api/__init__.py
COPY 03_api_gateway/api/app/__init__.py ./03_api_gateway/api/app/__init__.py
COPY 03_api_gateway/api/app/config.py ./03_api_gateway/api/app/config.py
COPY 03_api_gateway/api/app/database/__init__.py ./03_api_gateway/api/app/database/__init__.py
COPY 03_api_gateway/api/app/database/connection.py ./03_api_gateway/api/app/database/connection.py
COPY 03_api_gateway/api/app/db/__init__.py ./03_api_gateway/api/app/db/__init__.py
COPY 03_api_gateway/api/app/db/connection.py ./03_api_gateway/api/app/db/connection.py
COPY 03_api_gateway/api/app/db/models/__init__.py ./03_api_gateway/api/app/db/models/__init__.py
COPY 03_api_gateway/api/app/db/models/session.py ./03_api_gateway/api/app/db/models/session.py
COPY 03_api_gateway/api/app/db/models/user.py ./03_api_gateway/api/app/db/models/user.py
COPY 03_api_gateway/api/app/db/users_repo.py ./03_api_gateway/api/app/db/users_repo.py
COPY 03_api_gateway/api/app/deps.py ./03_api_gateway/api/app/deps.py
COPY 03_api_gateway/api/app/main.py ./03_api_gateway/api/app/main.py
COPY 03_api_gateway/api/app/middleware/__init__.py ./03_api_gateway/api/app/middleware/__init__.py
COPY 03_api_gateway/api/app/middleware/auth.py ./03_api_gateway/api/app/middleware/auth.py
COPY 03_api_gateway/api/app/middleware/cors.py ./03_api_gateway/api/app/middleware/cors.py
COPY 03_api_gateway/api/app/middleware/logging.py ./03_api_gateway/api/app/middleware/logging.py
COPY 03_api_gateway/api/app/middleware/rate_limit.py ./03_api_gateway/api/app/middleware/rate_limit.py
COPY 03_api_gateway/api/app/models/__init__.py ./03_api_gateway/api/app/models/__init__.py
COPY 03_api_gateway/api/app/models/common.py ./03_api_gateway/api/app/models/common.py
COPY 03_api_gateway/api/app/routers/__init__.py ./03_api_gateway/api/app/routers/__init__.py
COPY 03_api_gateway/api/app/routers/auth.py ./03_api_gateway/api/app/routers/auth.py
COPY 03_api_gateway/api/app/routers/chain.py ./03_api_gateway/api/app/routers/chain.py
COPY 03_api_gateway/api/app/routers/gui.py ./03_api_gateway/api/app/routers/gui.py
COPY 03_api_gateway/api/app/routers/gui_docker.py ./03_api_gateway/api/app/routers/gui_docker.py
COPY 03_api_gateway/api/app/routers/gui_hardware.py ./03_api_gateway/api/app/routers/gui_hardware.py
COPY 03_api_gateway/api/app/routers/gui_tor.py ./03_api_gateway/api/app/routers/gui_tor.py
COPY 03_api_gateway/api/app/routers/manifests.py ./03_api_gateway/api/app/routers/manifests.py
COPY 03_api_gateway/api/app/routers/meta.py ./03_api_gateway/api/app/routers/meta.py
COPY 03_api_gateway/api/app/routers/sessions.py ./03_api_gateway/api/app/routers/sessions.py
COPY 03_api_gateway/api/app/routers/tron_support.py ./03_api_gateway/api/app/routers/tron_support.py
COPY 03_api_gateway/api/app/routers/trust.py ./03_api_gateway/api/app/routers/trust.py
COPY 03_api_gateway/api/app/routers/users.py ./03_api_gateway/api/app/routers/users.py
COPY 03_api_gateway/api/app/routers/wallets.py ./03_api_gateway/api/app/routers/wallets.py
COPY 03_api_gateway/api/app/routes/__init__.py ./03_api_gateway/api/app/routes/__init__.py
COPY 03_api_gateway/api/app/routes/auth.py ./03_api_gateway/api/app/routes/auth.py
COPY 03_api_gateway/api/app/routes/chain_proxy.py ./03_api_gateway/api/app/routes/chain_proxy.py
COPY 03_api_gateway/api/app/routes/db_health.py ./03_api_gateway/api/app/routes/db_health.py
COPY 03_api_gateway/api/app/routes/health.py ./03_api_gateway/api/app/routes/health.py
COPY 03_api_gateway/api/app/routes/init.py ./03_api_gateway/api/app/routes/init.py
COPY 03_api_gateway/api/app/routes/manifests.py ./03_api_gateway/api/app/routes/manifests.py
COPY 03_api_gateway/api/app/routes/meta.py ./03_api_gateway/api/app/routes/meta.py
COPY 03_api_gateway/api/app/routes/sessions.py ./03_api_gateway/api/app/routes/sessions.py
COPY 03_api_gateway/api/app/routes/trust_policy.py ./03_api_gateway/api/app/routes/trust_policy.py
COPY 03_api_gateway/api/app/routes/users.py ./03_api_gateway/api/app/routes/users.py
COPY 03_api_gateway/api/app/routes/wallets_proxy.py ./03_api_gateway/api/app/routes/wallets_proxy.py
COPY 03_api_gateway/api/app/schemas/__init__.py ./03_api_gateway/api/app/schemas/__init__.py
COPY 03_api_gateway/api/app/schemas/auth.py ./03_api_gateway/api/app/schemas/auth.py
COPY 03_api_gateway/api/app/schemas/errors.py ./03_api_gateway/api/app/schemas/errors.py
COPY 03_api_gateway/api/app/schemas/meta.py ./03_api_gateway/api/app/schemas/meta.py
COPY 03_api_gateway/api/app/schemas/sessions.py ./03_api_gateway/api/app/schemas/sessions.py
COPY 03_api_gateway/api/app/schemas/users.py ./03_api_gateway/api/app/schemas/users.py
COPY 03_api_gateway/api/app/scripts/__init__.py ./03_api_gateway/api/app/scripts/__init__.py
COPY 03_api_gateway/api/app/scripts/ensure_indexes.py ./03_api_gateway/api/app/scripts/ensure_indexes.py
COPY 03_api_gateway/api/app/scripts/seed_dev.py ./03_api_gateway/api/app/scripts/seed_dev.py
COPY 03_api_gateway/api/app/security/__init__.py ./03_api_gateway/api/app/security/__init__.py
COPY 03_api_gateway/api/app/security/jwt.py ./03_api_gateway/api/app/security/jwt.py
COPY 03_api_gateway/api/app/services/__init__.py ./03_api_gateway/api/app/services/__init__.py
COPY 03_api_gateway/api/app/services/access_orchestrator.py ./03_api_gateway/api/app/services/access_orchestrator.py
COPY 03_api_gateway/api/app/services/gui_alignment.py ./03_api_gateway/api/app/services/gui_alignment.py
COPY 03_api_gateway/api/app/services/gui_bridge_service.py ./03_api_gateway/api/app/services/gui_bridge_service.py
COPY 03_api_gateway/api/app/services/gui_docker_manager_service.py ./03_api_gateway/api/app/services/gui_docker_manager_service.py
COPY 03_api_gateway/api/app/services/gui_hardware_manager_service.py ./03_api_gateway/api/app/services/gui_hardware_manager_service.py
COPY 03_api_gateway/api/app/services/gui_tor_manager_service.py ./03_api_gateway/api/app/services/gui_tor_manager_service.py
COPY 03_api_gateway/api/app/services/mongo_service.py ./03_api_gateway/api/app/services/mongo_service.py
COPY 03_api_gateway/api/app/services/session_service.py ./03_api_gateway/api/app/services/session_service.py
COPY 03_api_gateway/api/app/services/tron_support_service.py ./03_api_gateway/api/app/services/tron_support_service.py
COPY 03_api_gateway/api/app/utils/__init__.py ./03_api_gateway/api/app/utils/__init__.py
COPY 03_api_gateway/api/app/utils/config.py ./03_api_gateway/api/app/utils/config.py
COPY 03_api_gateway/api/app/utils/logger.py ./03_api_gateway/api/app/utils/logger.py
COPY 03_api_gateway/api/app/utils/logging.py ./03_api_gateway/api/app/utils/logging.py
COPY 03_api_gateway/api/tests/integration/test_session_lifecycle.py ./03_api_gateway/api/tests/integration/test_session_lifecycle.py
COPY 03_api_gateway/api/tests/test_sessions_router.py ./03_api_gateway/api/tests/test_sessions_router.py
COPY 03_api_gateway/config/load_host_config.py ./03_api_gateway/config/load_host_config.py
COPY 03_api_gateway/database/__init__.py ./03_api_gateway/database/__init__.py
COPY 03_api_gateway/database/connection.py ./03_api_gateway/database/connection.py
COPY 03_api_gateway/endpoints/__init__.py ./03_api_gateway/endpoints/__init__.py
COPY 03_api_gateway/endpoints/auth.py ./03_api_gateway/endpoints/auth.py
COPY 03_api_gateway/endpoints/chain.py ./03_api_gateway/endpoints/chain.py
COPY 03_api_gateway/endpoints/manifests.py ./03_api_gateway/endpoints/manifests.py
COPY 03_api_gateway/endpoints/meta.py ./03_api_gateway/endpoints/meta.py
COPY 03_api_gateway/endpoints/sessions.py ./03_api_gateway/endpoints/sessions.py
COPY 03_api_gateway/endpoints/trust.py ./03_api_gateway/endpoints/trust.py
COPY 03_api_gateway/endpoints/users.py ./03_api_gateway/endpoints/users.py
COPY 03_api_gateway/middleware/__init__.py ./03_api_gateway/middleware/__init__.py
COPY 03_api_gateway/models/__init__.py ./03_api_gateway/models/__init__.py
COPY 03_api_gateway/models/auth.py ./03_api_gateway/models/auth.py
COPY 03_api_gateway/models/common.py ./03_api_gateway/models/common.py
COPY 03_api_gateway/models/session.py ./03_api_gateway/models/session.py
COPY 03_api_gateway/models/user.py ./03_api_gateway/models/user.py
COPY 03_api_gateway/repositories/__init__.py ./03_api_gateway/repositories/__init__.py
COPY 03_api_gateway/repositories/session_repository.py ./03_api_gateway/repositories/session_repository.py
COPY 03_api_gateway/repositories/user_repository.py ./03_api_gateway/repositories/user_repository.py
COPY 03_api_gateway/services/__init__.py ./03_api_gateway/services/__init__.py
COPY 03_api_gateway/services/auth_service.py ./03_api_gateway/services/auth_service.py
COPY 03_api_gateway/services/gui_bridge_service.py ./03_api_gateway/services/gui_bridge_service.py
COPY 03_api_gateway/services/gui_docker_manager_service.py ./03_api_gateway/services/gui_docker_manager_service.py
COPY 03_api_gateway/services/gui_hardware_manager_service.py ./03_api_gateway/services/gui_hardware_manager_service.py
COPY 03_api_gateway/services/gui_tor_manager_service.py ./03_api_gateway/services/gui_tor_manager_service.py
COPY 03_api_gateway/services/proxy_service.py ./03_api_gateway/services/proxy_service.py
COPY 03_api_gateway/services/rate_limit_service.py ./03_api_gateway/services/rate_limit_service.py
COPY 03_api_gateway/services/session_service.py ./03_api_gateway/services/session_service.py
COPY 03_api_gateway/services/tron_support_service.py ./03_api_gateway/services/tron_support_service.py
COPY 03_api_gateway/services/user_service.py ./03_api_gateway/services/user_service.py
COPY 03_api_gateway/utils/__init__.py ./03_api_gateway/utils/__init__.py
COPY 03_api_gateway/utils/security.py ./03_api_gateway/utils/security.py
COPY 03_api_gateway/utils/validation.py ./03_api_gateway/utils/validation.py
COPY 03_api_gateway/verify_files.py ./03_api_gateway/verify_files.py
COPY 03_api_gateway/verify_runtime.py ./03_api_gateway/verify_runtime.py
COPY _gen_host_config.py ./_gen_host_config.py
COPY _normalise_lucid_headers.py ./_normalise_lucid_headers.py
COPY admin/admin_ui/api_handlers.py ./admin/admin_ui/api_handlers.py
COPY admin/admin_ui/provisioning_manager.py ./admin/admin_ui/provisioning_manager.py
COPY admin/config.py ./admin/config.py
COPY admin/services/service_client.py ./admin/services/service_client.py
COPY admin/services/service_discovery.py ./admin/services/service_discovery.py
COPY api/cluster/api-gateway.py ./api/cluster/api-gateway.py
COPY auth/api/auth_routes.py ./auth/api/auth_routes.py
COPY auth/config.py ./auth/config.py
COPY auth/middleware/auth_middleware.py ./auth/middleware/auth_middleware.py
COPY auth/models/permissions.py ./auth/models/permissions.py
COPY blockchain/utils/set_host_config.py ./blockchain/utils/set_host_config.py
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
COPY configs/container/admin/docker-compose.admin.yml ./configs/container/admin/docker-compose.admin.yml
COPY configs/container/auth/docker-compose.auth.yml ./configs/container/auth/docker-compose.auth.yml
COPY configs/container/base/docker-compose.base.yml ./configs/container/base/docker-compose.base.yml
COPY configs/container/blockchain/docker-compose.block-system.yml ./configs/container/blockchain/docker-compose.block-system.yml
COPY configs/container/blockchain/docker-compose.chain.yml ./configs/container/blockchain/docker-compose.chain.yml
COPY configs/container/blockchain/docker-compose.manager.yml ./configs/container/blockchain/docker-compose.manager.yml
COPY configs/container/database/docker-compose.database-system.yml ./configs/container/database/docker-compose.database-system.yml
COPY configs/container/electron_gui/docker-compose.electron-gui.yml ./configs/container/electron_gui/docker-compose.electron-gui.yml
COPY configs/container/gui/docker-compose.node-gui.yml ./configs/container/gui/docker-compose.node-gui.yml
COPY configs/container/node/docker-compose.node-data-system.yml ./configs/container/node/docker-compose.node-data-system.yml
COPY configs/container/node/docker-compose.node-gui.yml ./configs/container/node/docker-compose.node-gui.yml
COPY configs/container/node/docker-compose.node-images.yml ./configs/container/node/docker-compose.node-images.yml
COPY configs/container/node/docker-compose.node-sessions.yml ./configs/container/node/docker-compose.node-sessions.yml
COPY configs/container/payment_systems/docker-compose.payment-externals.yml ./configs/container/payment_systems/docker-compose.payment-externals.yml
COPY configs/container/payment_systems/docker-compose.payment-internal.yml ./configs/container/payment_systems/docker-compose.payment-internal.yml
COPY configs/container/rdp/docker-compose.rdp-system.yml ./configs/container/rdp/docker-compose.rdp-system.yml
COPY configs/container/server/docker-compose.server-external.yml ./configs/container/server/docker-compose.server-external.yml
COPY configs/container/server/docker-compose.server-images.yml ./configs/container/server/docker-compose.server-images.yml
COPY configs/container/sessions/docker-compose.session-images.yml ./configs/container/sessions/docker-compose.session-images.yml
COPY configs/container/tor/docker-compose.proxy-systems.yml ./configs/container/tor/docker-compose.proxy-systems.yml
COPY configs/docker/docker-compose.all.yml ./configs/docker/docker-compose.all.yml
COPY configs/docker/docker-compose.application.yml ./configs/docker/docker-compose.application.yml
COPY configs/docker/docker-compose.core.yml ./configs/docker/docker-compose.core.yml
COPY configs/docker/docker-compose.foundation-02.yml ./configs/docker/docker-compose.foundation-02.yml
COPY configs/docker/docker-compose.foundation.yml ./configs/docker/docker-compose.foundation.yml
COPY configs/docker/docker-compose.gui-integration.yml ./configs/docker/docker-compose.gui-integration.yml
COPY configs/docker/docker-compose.support.yml ./configs/docker/docker-compose.support.yml
COPY configs/gui-alignment/admin-interface.json ./configs/gui-alignment/admin-interface.json
COPY configs/gui-alignment/gui-api-bridge.json ./configs/gui-alignment/gui-api-bridge.json
COPY configs/gui-alignment/gui-docker-manager.json ./configs/gui-alignment/gui-docker-manager.json
COPY configs/gui-alignment/gui-hardware-manager.json ./configs/gui-alignment/gui-hardware-manager.json
COPY configs/gui-alignment/gui-tor-manager.json ./configs/gui-alignment/gui-tor-manager.json
COPY configs/gui-alignment/node-interface.json ./configs/gui-alignment/node-interface.json
COPY configs/gui-alignment/user-interface.json ./configs/gui-alignment/user-interface.json
COPY configs/integration/master-integration-config.yml ./configs/integration/master-integration-config.yml
COPY infrastructure/containers/services/admin/admin-interface.yml ./service_configs/admin-interface.yml
COPY infrastructure/containers/services/api-gateway.yml ./service_configs/api-gateway.yml
COPY infrastructure/containers/services/beta-sidecar.yml ./service_configs/beta-sidecar.yml
COPY infrastructure/containers/services/blockchain/blockchain-core.yml ./service_configs/blockchain-core.yml
COPY infrastructure/containers/services/database/database.yml ./service_configs/database.yml
COPY infrastructure/containers/services/gui/gui-api-bridge.yml ./service_configs/gui-api-bridge.yml
COPY infrastructure/containers/services/gui/gui-docker-manager-service-groups.yml ./service_configs/gui-docker-manager-service-groups.yml
COPY infrastructure/containers/services/gui/gui-docker-manager.yml ./service_configs/gui-docker-manager.yml
COPY infrastructure/containers/services/gui/gui-hardware-manager.yml ./service_configs/gui-hardware-manager.yml
COPY infrastructure/containers/services/node/node-management.yml ./service_configs/node-management.yml
COPY infrastructure/containers/services/rdp/rdp-services.yml ./service_configs/rdp-services.yml
COPY infrastructure/containers/services/service-discovery.yml ./service_configs/service-discovery.yml
COPY infrastructure/containers/services/service-registry.json ./service_configs/service-registry.json
COPY infrastructure/containers/services/sessions/session-management.yml ./service_configs/session-management.yml
COPY configs/x-files.json ./configs/x-files.json
COPY database/admin/admin_connection.py ./database/admin/admin_connection.py
COPY gui/admin/bootstrap_wizard.py ./gui/admin/bootstrap_wizard.py
COPY gui/config/config.py ./gui/config/config.py
COPY gui/config/load_host_config.py ./gui/config/load_host_config.py
COPY gui_api_bridge/gui_api_bridge/config.py ./gui_api_bridge/gui_api_bridge/config.py
COPY gui_api_bridge/gui_api_bridge/gui_api_bridge_service.py ./gui_api_bridge/gui_api_bridge/gui_api_bridge_service.py
COPY gui_api_bridge/gui_api_bridge/healthcheck.py ./gui_api_bridge/gui_api_bridge/healthcheck.py
COPY gui_api_bridge/gui_api_bridge/integration/api_gateway_client.py ./gui_api_bridge/gui_api_bridge/integration/api_gateway_client.py
COPY gui_api_bridge/gui_api_bridge/integration/integration_manager.py ./gui_api_bridge/gui_api_bridge/integration/integration_manager.py
COPY gui_api_bridge/gui_api_bridge/main.py ./gui_api_bridge/gui_api_bridge/main.py
COPY gui_api_bridge/gui_api_bridge/middleware/gateway_forward.py ./gui_api_bridge/gui_api_bridge/middleware/gateway_forward.py
COPY gui_api_bridge/gui_api_bridge/routers/admin.py ./gui_api_bridge/gui_api_bridge/routers/admin.py
COPY gui_api_bridge/gui_api_bridge/services/discovery_service.py ./gui_api_bridge/gui_api_bridge/services/discovery_service.py
COPY gui_api_bridge/gui_api_bridge/services/routing_service.py ./gui_api_bridge/gui_api_bridge/services/routing_service.py
COPY gui_docker_manager/gui_docker_manager/routers/events.py ./gui_docker_manager/gui_docker_manager/routers/events.py
COPY gui_docker_manager/gui_docker_manager/routers/services.py ./gui_docker_manager/gui_docker_manager/routers/services.py
COPY gui_hardware_manager/gui_hardware_manager/config.py ./gui_hardware_manager/gui_hardware_manager/config.py
COPY infrastructure/containers/.devcontainer/devcontainer.yaml ./infrastructure/containers/.devcontainer/devcontainer.yaml
COPY infrastructure/containers/.devcontainer/docker-compose.dev.yml ./infrastructure/containers/.devcontainer/docker-compose.dev.yml
COPY infrastructure/containers/_gen_x_lucid_cluster_calibration.py ./infrastructure/containers/_gen_x_lucid_cluster_calibration.py
COPY infrastructure/containers/_sync_dockerfile_lucid_env.py ./infrastructure/containers/_sync_dockerfile_lucid_env.py
COPY infrastructure/containers/admin/admin-system-gateway/entrypoint.py ./infrastructure/containers/admin/admin-system-gateway/entrypoint.py
COPY infrastructure/containers/admin/admin-system-gateway/verify_runtime.py ./infrastructure/containers/admin/admin-system-gateway/verify_runtime.py
COPY infrastructure/containers/admin/config/admin-system-gateway.connections.json ./infrastructure/containers/admin/config/admin-system-gateway.connections.json
COPY infrastructure/containers/admin/docker-compose.admin.yml ./infrastructure/containers/admin/docker-compose.admin.yml
COPY infrastructure/containers/allocate_x_lucid_cluster_calibration.py ./infrastructure/containers/allocate_x_lucid_cluster_calibration.py
COPY infrastructure/containers/auth/docker-compose.auth.yml ./infrastructure/containers/auth/docker-compose.auth.yml
COPY infrastructure/containers/blockchain/docker-compose.chain.yml ./infrastructure/containers/blockchain/docker-compose.chain.yml
COPY infrastructure/containers/config-listings.json ./infrastructure/containers/config-listings.json
COPY infrastructure/containers/database/docker-compose.database-system.yml ./infrastructure/containers/database/docker-compose.database-system.yml
COPY infrastructure/containers/dockerfile_recalibration_map.json ./infrastructure/containers/dockerfile_recalibration_map.json
COPY infrastructure/containers/dockerfile_recalibration_map_REPAIRED.json ./infrastructure/containers/dockerfile_recalibration_map_REPAIRED.json
COPY infrastructure/containers/electron_gui/docker-compose.electron-gui.yml ./infrastructure/containers/electron_gui/docker-compose.electron-gui.yml
COPY infrastructure/containers/gui/docker-compose.node-gui.yml ./infrastructure/containers/gui/docker-compose.node-gui.yml
COPY infrastructure/containers/host-config.yml ./infrastructure/containers/host-config.yml
COPY infrastructure/containers/node/config/node-system-gateway.connections.json ./infrastructure/containers/node/config/node-system-gateway.connections.json
COPY infrastructure/containers/node/docker-compose.node-gui.yml ./infrastructure/containers/node/docker-compose.node-gui.yml
COPY infrastructure/containers/node/docker-compose.node-sessions.yml ./infrastructure/containers/node/docker-compose.node-sessions.yml
COPY infrastructure/containers/node/node-system-gateway/entrypoint.py ./infrastructure/containers/node/node-system-gateway/entrypoint.py
COPY infrastructure/containers/node/node-system-gateway/verify_files.py ./infrastructure/containers/node/node-system-gateway/verify_files.py
COPY infrastructure/containers/node/node-system-gateway/verify_runtime.py ./infrastructure/containers/node/node-system-gateway/verify_runtime.py
COPY infrastructure/containers/payment_systems/docker-compose.payment-externals.yml ./infrastructure/containers/payment_systems/docker-compose.payment-externals.yml
COPY infrastructure/containers/server/docker-compose.server-external.yml ./infrastructure/containers/server/docker-compose.server-external.yml
COPY infrastructure/containers/server/docker-compose.server-images.yml ./infrastructure/containers/server/docker-compose.server-images.yml
COPY infrastructure/containers/services/admin/admin-interface.yml ./infrastructure/containers/services/admin/admin-interface.yml
COPY infrastructure/containers/services/api-gateway.yml ./infrastructure/containers/services/api-gateway.yml
COPY infrastructure/containers/services/base/base.yml ./infrastructure/containers/services/base/base.yml
COPY infrastructure/containers/services/beta-sidecar.yml ./infrastructure/containers/services/beta-sidecar.yml
COPY infrastructure/containers/services/blockchain/blockchain-core.yml ./infrastructure/containers/services/blockchain/blockchain-core.yml
COPY infrastructure/containers/services/blockchain/blockchain-engine.yml ./infrastructure/containers/services/blockchain/blockchain-engine.yml
COPY infrastructure/containers/services/database/database.yml ./infrastructure/containers/services/database/database.yml
COPY infrastructure/containers/services/database/lucid-mongodb.yml ./infrastructure/containers/services/database/lucid-mongodb.yml
COPY infrastructure/containers/services/database/lucid-redis.yml ./infrastructure/containers/services/database/lucid-redis.yml
COPY infrastructure/containers/services/gui/gui-api-bridge.yml ./infrastructure/containers/services/gui/gui-api-bridge.yml
COPY infrastructure/containers/services/gui/gui-docker-manager-service-groups.yml ./infrastructure/containers/services/gui/gui-docker-manager-service-groups.yml
COPY infrastructure/containers/services/gui/gui-docker-manager.yml ./infrastructure/containers/services/gui/gui-docker-manager.yml
COPY infrastructure/containers/services/gui/gui-hardware-manager.yml ./infrastructure/containers/services/gui/gui-hardware-manager.yml
COPY infrastructure/containers/services/middle-ware/auth-service.yml ./infrastructure/containers/services/middle-ware/auth-service.yml
COPY infrastructure/containers/services/middle-ware/container-runtime-layout.yml ./infrastructure/containers/services/middle-ware/container-runtime-layout.yml
COPY infrastructure/containers/services/middle-ware/lucid-auth-service.yml ./infrastructure/containers/services/middle-ware/lucid-auth-service.yml
COPY infrastructure/containers/services/middle-ware/master-endpoint.yml ./infrastructure/containers/services/middle-ware/master-endpoint.yml
COPY infrastructure/containers/services/multi-stage/multi-stage-build-config.yml ./infrastructure/containers/services/multi-stage/multi-stage-build-config.yml
COPY infrastructure/containers/services/multi-stage/multi-stage-config.yml ./infrastructure/containers/services/multi-stage/multi-stage-config.yml
COPY infrastructure/containers/services/multi-stage/multi-stage-development-config.yml ./infrastructure/containers/services/multi-stage/multi-stage-development-config.yml
COPY infrastructure/containers/services/multi-stage/multi-stage-runtime-config.yml ./infrastructure/containers/services/multi-stage/multi-stage-runtime-config.yml
COPY infrastructure/containers/services/multi-stage/multi-stage-testing-config.yml ./infrastructure/containers/services/multi-stage/multi-stage-testing-config.yml
COPY infrastructure/containers/services/node/node-management-config.yaml ./infrastructure/containers/services/node/node-management-config.yaml
COPY infrastructure/containers/services/node/node-management.yml ./infrastructure/containers/services/node/node-management.yml
COPY infrastructure/containers/services/payment_services/payment-services-host-alignment.yml ./infrastructure/containers/services/payment_services/payment-services-host-alignment.yml
COPY infrastructure/containers/services/payment_services/payout-security-policies.yaml ./infrastructure/containers/services/payment_services/payout-security-policies.yaml
COPY infrastructure/containers/services/payment_services/tron-payment-service.yml ./infrastructure/containers/services/payment_services/tron-payment-service.yml
COPY infrastructure/containers/services/payment_services/tron-payment.yml ./infrastructure/containers/services/payment_services/tron-payment.yml
COPY infrastructure/containers/services/rdp/controller-config.yaml ./infrastructure/containers/services/rdp/controller-config.yaml
COPY infrastructure/containers/services/rdp/monitor-config.yaml ./infrastructure/containers/services/rdp/monitor-config.yaml
COPY infrastructure/containers/services/rdp/rdp-services.yml ./infrastructure/containers/services/rdp/rdp-services.yml
COPY infrastructure/containers/services/rdp/server-manager-config.yaml ./infrastructure/containers/services/rdp/server-manager-config.yaml
COPY infrastructure/containers/services/rdp/xrdp-config.yaml ./infrastructure/containers/services/rdp/xrdp-config.yaml
COPY infrastructure/containers/services/server/lucid-server-manager.yml ./infrastructure/containers/services/server/lucid-server-manager.yml
COPY infrastructure/containers/services/service-discovery.yml ./infrastructure/containers/services/service-discovery.yml
COPY infrastructure/containers/services/service-registry.json ./infrastructure/containers/services/service-registry.json
COPY infrastructure/containers/services/service_mesh/health-checks.json ./infrastructure/containers/services/service_mesh/health-checks.json
COPY infrastructure/containers/services/service_mesh/mtls.json ./infrastructure/containers/services/service_mesh/mtls.json
COPY infrastructure/containers/services/service_mesh/network.json ./infrastructure/containers/services/service_mesh/network.json
COPY infrastructure/containers/services/service_mesh/policies.yaml ./infrastructure/containers/services/service_mesh/policies.yaml
COPY infrastructure/containers/services/service_mesh/services.yaml ./infrastructure/containers/services/service_mesh/services.yaml
COPY infrastructure/containers/services/sessions/api-config.yaml ./infrastructure/containers/services/sessions/api-config.yaml
COPY infrastructure/containers/services/sessions/session-anchoring.yml ./infrastructure/containers/services/sessions/session-anchoring.yml
COPY infrastructure/containers/services/sessions/session-management.yml ./infrastructure/containers/services/sessions/session-management.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.json ./infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.json
COPY infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/core-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/core-cluster-host-alignment.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/gui-integration-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/gui-integration-cluster-host-alignment.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/monitoring-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/monitoring-cluster-host-alignment.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/processing-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/processing-cluster-host-alignment.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/storage-cluster-host-alignment.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/storage-cluster-host-alignment.yml
COPY infrastructure/containers/user/docker-compose.user-services.yml ./infrastructure/containers/user/docker-compose.user-services.yml
COPY infrastructure/service_mesh/communication/grpc_client.py ./infrastructure/service_mesh/communication/grpc_client.py
COPY infrastructure/service_mesh/config/service-mesh.yaml ./infrastructure/service_mesh/config/service-mesh.yaml
COPY infrastructure/service_mesh/controller/health_checker.py ./infrastructure/service_mesh/controller/health_checker.py
COPY infrastructure/service_mesh/controller/http_server.py ./infrastructure/service_mesh/controller/http_server.py
COPY infrastructure/service_mesh/discovery/dns_resolver.py ./infrastructure/service_mesh/discovery/dns_resolver.py
COPY infrastructure/service_mesh/service_mesh_translator.py ./infrastructure/service_mesh/service_mesh_translator.py
COPY infrastructure/service_mesh/sidecar/envoy/config/bootstrap.yaml ./infrastructure/service_mesh/sidecar/envoy/config/bootstrap.yaml
COPY infrastructure/service_mesh/sidecar/envoy/config/cluster.yaml ./infrastructure/service_mesh/sidecar/envoy/config/cluster.yaml
COPY infrastructure/service_mesh/verify_files.py ./infrastructure/service_mesh/verify_files.py
COPY legacy_files/tests/conftest.py ./legacy_files/tests/conftest.py
COPY legacy_files/tests/tests/integration/phase2/conftest.py ./legacy_files/tests/tests/integration/phase2/conftest.py
COPY legacy_files/tests/tests/integration/phase4/conftest.py ./legacy_files/tests/tests/integration/phase4/conftest.py
COPY node/config.py ./node/config.py
COPY infrastructure/containers/node/config/load_host_config.py ./node/config/load_host_config.py
COPY node/database_adapter.py ./node/database_adapter.py
COPY node/tor/onion_service.py ./node/tor/onion_service.py
COPY RDP/server_manager/config.py ./RDP/server_manager/config.py
COPY RDP/server_manager/main.py ./RDP/server_manager/main.py
COPY RDP/xrdp/config.py ./RDP/xrdp/config.py
COPY repair_dockerfile_standardization.py ./repair_dockerfile_standardization.py
COPY scripts/database/ensure_user_profile_fields.py ./scripts/database/ensure_user_profile_fields.py
COPY scripts/gui_auth_realignment/align_tor_tunnel_gui_systems.py ./scripts/gui_auth_realignment/align_tor_tunnel_gui_systems.py
COPY scripts/re-build/gui_scrub_python_env_secrets.py ./scripts/re-build/gui_scrub_python_env_secrets.py
COPY scripts/validation/repair-validation-failures.py ./scripts/validation/repair-validation-failures.py
COPY scripts/validation/validate-electron-gui-alignment.py ./scripts/validation/validate-electron-gui-alignment.py
COPY scripts/validation/validate-python-build-alignment.py ./scripts/validation/validate-python-build-alignment.py
COPY server/host_context.py ./server/host_context.py
COPY infrastructure/service_mesh/service_mesh_translator.py ./service_mesh/service_mesh_translator.py
COPY sessions/api/config.py ./sessions/api/config.py
COPY sessions/pipeline/config.py ./sessions/pipeline/config.py
COPY sessions/pipeline/integration/api_gateway_client.py ./sessions/pipeline/integration/api_gateway_client.py
COPY sessions/pipeline/integration/integration_manager.py ./sessions/pipeline/integration/integration_manager.py
COPY sessions/processor/config.py ./sessions/processor/config.py
COPY sessions/processor/integration/integration_manager.py ./sessions/processor/integration/integration_manager.py
COPY sessions/recorder/integration/integration_manager.py ./sessions/recorder/integration/integration_manager.py
COPY tests/integration/phase2/test_gateway_auth.py ./tests/integration/phase2/test_gateway_auth.py
COPY tests/integration/phase2/test_gateway_blockchain.py ./tests/integration/phase2/test_gateway_blockchain.py
COPY tests/integration/phase2/test_rate_limiting.py ./tests/integration/phase2/test_rate_limiting.py
COPY tests/integration/phase2/test_service_mesh.py ./tests/integration/phase2/test_service_mesh.py
COPY tests/integration/phase4/test_emergency_controls.py ./tests/integration/phase4/test_emergency_controls.py
COPY tests/integration/phase4/test_full_system.py ./tests/integration/phase4/test_full_system.py
COPY tests/load/__init__.py ./tests/load/__init__.py
COPY tests/performance/__init__.py ./tests/performance/__init__.py
COPY tests/performance/test_api_gateway_throughput.py ./tests/performance/test_api_gateway_throughput.py
COPY tests/security/test_input_validation.py ./tests/security/test_input_validation.py
COPY tests/security/test_rate_limiting.py ./tests/security/test_rate_limiting.py
COPY tests/validation/test_all_apis_responding.py ./tests/validation/test_all_apis_responding.py
COPY tests/validation/test_all_containers_running.py ./tests/validation/test_all_containers_running.py
COPY tests/validation/test_all_integrations.py ./tests/validation/test_all_integrations.py
COPY tests/validation/test_all_services_healthy.py ./tests/validation/test_all_services_healthy.py
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
COPY scripts/ ./scripts/
COPY 03_api_gateway/ ./03_api_gateway/

COPY 03_api_gateway/verify_files.py ./tmp/verify_files.py
COPY 03_api_gateway/verify_runtime.py ./tmp/verify_runtime.py



RUN rm -rf configs/environment 2>/dev/null || true



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
RUN echo "=== Checking if verify_files.py was copied ===" && \
    ls -la ./tmp/* && echo "(ls -la ./tmp/* || echo "./tmp/ directory not found")" && \
    ls -la /build/tmp/* && echo "(ls -la /build/tmp/* || echo "/build/tmp/ directory not found")" && \
    echo "verify_files.py was copied"
RUN echo "=== Checking if common/__init__.py was copied ===" && \
    ls -la ./common/* && echo "(ls -la ./common/* || echo "./common/ directory not found")" && \
    ls -la /build/common/* && echo "(ls -la /build/common/* || echo "/build/common/ directory not found")" && \
    echo "common/ was copied"


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
      org.opencontainers.image.title="Lucid API Gateway" \
      org.opencontainers.image.description="Distroless API Gateway for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.plane="ops" \
      com.lucid.service="api-gateway" \
      com.lucid.layer="1" \
      org.lucid.layer="1" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8080" \
      com.lucid.cluster="core" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation" \
      com.lucid.service_id="com.lucid.dockerfile.v1.ccb15d3adc538585.infrastructure.containers.user.Dockerfile" \
      onion.lucid.service_id="lucid-ccb15d3adc538585-infrastructure-container" \
      org.lucid.service_id="org.lucid.dockerfile.v1.ccb15d3adc538585:infrastructure/containers/user/Dockerfile" \

# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/02_network_security/ /app/02_network_security/
COPY --from=builder --chown=65532:65532 /build/03_api_gateway/ /app/03_api_gateway/
COPY --from=builder --chown=65532:65532 /build/admin/ /app/admin/
COPY --from=builder --chown=65532:65532 /build/api/ /app/api/
COPY --from=builder --chown=65532:65532 /build/auth/ /app/auth/
COPY --from=builder --chown=65532:65532 /build/blockchain/ /app/blockchain/
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=builder --chown=65532:65532 /build/database/ /app/database/
COPY --from=builder --chown=65532:65532 /build/gui/ /app/gui/
COPY --from=builder --chown=65532:65532 /build/gui_api_bridge/ /app/gui_api_bridge/
COPY --from=builder --chown=65532:65532 /build/gui_docker_manager/ /app/gui_docker_manager/
COPY --from=builder --chown=65532:65532 /build/gui_hardware_manager/ /app/gui_hardware_manager/
COPY --from=builder --chown=65532:65532 /build/node/ /app/node/
COPY --from=builder --chown=65532:65532 /build/rdp/ /app/rdp/
COPY --from=builder --chown=65532:65532 /build/scripts/ /app/scripts/
COPY --from=builder --chown=65532:65532 /build/server/ /app/server/
COPY --from=builder --chown=65532:65532 /build/service_configs/ /app/service_configs/
COPY --from=builder --chown=65532:65532 /build/service_mesh/ /app/service_mesh/
COPY --from=builder --chown=65532:65532 /build/sessions/ /app/sessions/
COPY --from=builder --chown=65532:65532 /build/tmp/ /app/tmp/
COPY --from=builder --chown=65532:65532 /build/legacy_files/tests/ /app/legacy_files/tests/
COPY --from=builder --chown=65532:65532 /build/tests/load/ /app/tests/load/
COPY --from=builder --chown=65532:65532 /build/tests/performance/ /app/tests/performance/
COPY --from=builder --chown=65532:65532 /build/tests/security/ /app/tests/security/
COPY --from=builder --chown=65532:65532 /build/tests/validation/ /app/tests/validation/
COPY --from=builder --chown=65532:65532 /build/tests/integration/phase2/ /app/tests/integration/phase2/
COPY --from=builder --chown=65532:65532 /build/tests/integration/phase4/ /app/tests/integration/phase4/
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
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).

# System directories & certificates

RUN ["/app/usr/bin/python3.11", "/app/tmp/verify_runtime.py"]
RUN ["rm", "-f", "/app/tmp/verify_runtime.py"]



EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/usr/bin/tini", "--"]

  CMD ["/app/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('api-gateway', 8080)); s.close(); exit(0 if result == 0 else 1)"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "app.api.app.main:app", "--host", "api-gateway", "--port", "8080"]
