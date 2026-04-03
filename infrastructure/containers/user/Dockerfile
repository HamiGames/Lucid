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
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

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
# Generated: FHS dirs for builder (from final-stage COPY --from, excluding /build/ sources;
# ancestor dirs collapsed; see collect_skeleton_paths_from_dockerfile).
RUN set -eux; \
  mkdir -p \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/usr/lib' \
    '/etc/ssl/certs' \
    '/usr/lib/python3/dist-packages'; \
  for d in \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/usr/lib' \
    '/etc/ssl/certs' \
    '/usr/lib/python3/dist-packages'; \
  do \
    printf 'LUCID_LIB_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
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
    mkdir -p '.' './03_api_gateway' './common' './configs' './scripts' './service_configs' './tmp' './03_api_gateway/__pycache__' './03_api_gateway/api' './03_api_gateway/certs' './03_api_gateway/config' './03_api_gateway/database' './03_api_gateway/docs' './03_api_gateway/endpoints' './03_api_gateway/gateway' './03_api_gateway/legacy' './03_api_gateway/logs' './03_api_gateway/middleware' './03_api_gateway/models' './03_api_gateway/repositories' './03_api_gateway/scripts' './03_api_gateway/services' './03_api_gateway/utils' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './configs/.ssh' './configs/alignment-mats' './configs/container' './configs/database' './configs/docker' './configs/env' './configs/environment' './configs/gui-alignment' './configs/integration' './configs/kubernetes' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './scripts/__pycache__' './scripts/auth_sm_realignment' './scripts/build' './scripts/compliance' './scripts/config' './scripts/contracts' './scripts/database' './scripts/deployment' './scripts/devcontainer' './scripts/docs' './scripts/foundation' './scripts/gui' './scripts/gui_auth_realignment' './scripts/hardware' './scripts/integration' './scripts/lib' './scripts/load' './scripts/logging' './scripts/maintenance' './scripts/migration' './scripts/monitoring' './scripts/network' './scripts/re-build' './scripts/registry' './scripts/secrets' './scripts/security' './scripts/services' './scripts/testing' './scripts/validation' './scripts/verification' './03_api_gateway/api/__pycache__' './03_api_gateway/api/app' './03_api_gateway/api/lucid_api.egg-info' './03_api_gateway/api/tests' './03_api_gateway/config/__pycache__' './03_api_gateway/database/__pycache__' './03_api_gateway/docs/swagger' './03_api_gateway/endpoints/__pycache__' './03_api_gateway/legacy/api' './03_api_gateway/legacy/gateway' './03_api_gateway/middleware/__pycache__' './03_api_gateway/models/__pycache__' './03_api_gateway/repositories/__pycache__' './03_api_gateway/services/__pycache__' './03_api_gateway/utils/__pycache__' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/environment/development' './configs/environment/pi' './configs/environment/production' './configs/environment/staging' './configs/pi/ssh' './configs/secrets/runtime' './scripts/auth_sm_realignment/.cache' './scripts/auth_sm_realignment/lib' './scripts/build/__pycache__' './scripts/build/components' './scripts/build/core' './scripts/build/distroless' './scripts/build/utils' './scripts/compliance/distroless' './scripts/compliance/general' './scripts/deployment/devcontainer' './scripts/deployment/distroless' './scripts/deployment/pi' './scripts/deployment/utils' './scripts/gui_auth_realignment/.cache' './scripts/gui_auth_realignment/lib' './scripts/maintenance/cleanup' './scripts/maintenance/optimization' './scripts/maintenance/recovery' './scripts/network/diagnostics' './scripts/network/security' './scripts/network/setup' './scripts/testing/integration' './scripts/testing/unit' './scripts/testing/utils' './scripts/validation/__pycache__' './scripts/verification/__pycache__' './03_api_gateway/api/app/__pycache__' './03_api_gateway/api/app/database' './03_api_gateway/api/app/db' './03_api_gateway/api/app/middleware' './03_api_gateway/api/app/models' './03_api_gateway/api/app/routers' './03_api_gateway/api/app/routes' './03_api_gateway/api/app/schemas' './03_api_gateway/api/app/scripts' './03_api_gateway/api/app/security' './03_api_gateway/api/app/services' './03_api_gateway/api/app/utils' './03_api_gateway/api/tests/__pycache__' './03_api_gateway/api/tests/integration' './03_api_gateway/docs/swagger/dist' './configs/secrets/runtime/compose' './03_api_gateway/api/app/database/__pycache__' './03_api_gateway/api/app/db/__pycache__' './03_api_gateway/api/app/db/models' './03_api_gateway/api/app/middleware/__pycache__' './03_api_gateway/api/app/models/__pycache__' './03_api_gateway/api/app/routers/__pycache__' './03_api_gateway/api/app/routes/__pycache__' './03_api_gateway/api/app/schemas/__pycache__' './03_api_gateway/api/app/scripts/__pycache__' './03_api_gateway/api/app/security/__pycache__' './03_api_gateway/api/app/services/__pycache__' './03_api_gateway/api/app/utils/__pycache__' './03_api_gateway/api/tests/integration/__pycache__'; \
    for d in \
      '.' \
      './03_api_gateway' \
      './common' \
      './configs' \
      './scripts' \
      './service_configs' \
      './tmp' \
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
      './common/__pycache__' \
      './common/governance' \
      './common/security' \
      './common/server-tools' \
      './common/templates' \
      './common/tor' \
      './configs/.ssh' \
      './configs/alignment-mats' \
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
      './configs/environment/development' \
      './configs/environment/pi' \
      './configs/environment/production' \
      './configs/environment/staging' \
      './configs/pi/ssh' \
      './configs/secrets/runtime' \
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
      './configs/secrets/runtime/compose' \
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
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN
# alignment-mat api-gateway_manifest.json: compose_service='api-gateway' — manifest py/yml/yaml/json → builder COPY (#10).
COPY common/ ./common/
COPY configs/ ./configs/
COPY infrastructure/containers/ ./infrastructure/containers/
COPY infrastructure/service_mesh/config/ ./infrastructure/service_mesh/config/
COPY infrastructure/service_mesh/sidecar/envoy/config/ ./infrastructure/service_mesh/sidecar/envoy/config/
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './03_api_gateway' './common' './configs' './scripts' './service_configs' './tmp' './03_api_gateway/__pycache__' './03_api_gateway/api' './03_api_gateway/certs' './03_api_gateway/config' './03_api_gateway/database' './03_api_gateway/docs' './03_api_gateway/endpoints' './03_api_gateway/gateway' './03_api_gateway/legacy' './03_api_gateway/logs' './03_api_gateway/middleware' './03_api_gateway/models' './03_api_gateway/repositories' './03_api_gateway/scripts' './03_api_gateway/services' './03_api_gateway/utils' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/env' './configs/integration' './configs/kubernetes' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './scripts/__pycache__' './scripts/build' './scripts/compliance' './scripts/config' './scripts/contracts' './scripts/database' './scripts/deployment' './scripts/devcontainer' './scripts/docs' './scripts/foundation' './scripts/gui' './scripts/hardware' './scripts/integration' './scripts/lib' './scripts/load' './scripts/logging' './scripts/maintenance' './scripts/migration' './scripts/monitoring' './scripts/network' './scripts/registry' './scripts/secrets' './scripts/security' './scripts/services' './scripts/testing' './scripts/validation' './scripts/verification' './service_configs/blockchain' './service_configs/distroless' './service_configs/logging' './service_configs/multi-stage' './service_configs/node' './service_configs/payment_services' './service_configs/rdp' './service_configs/security' './service_configs/service_mesh' './service_configs/services' './service_configs/sessions' './service_configs/tor' './service_configs/x_lucid_cluster_calibration' './03_api_gateway/api/__pycache__' './03_api_gateway/api/app' './03_api_gateway/api/lucid_api.egg-info' './03_api_gateway/api/tests' './03_api_gateway/config/__pycache__' './03_api_gateway/database/__pycache__' './03_api_gateway/docs/swagger' './03_api_gateway/endpoints/__pycache__' './03_api_gateway/legacy/api' './03_api_gateway/legacy/gateway' './03_api_gateway/middleware/__pycache__' './03_api_gateway/models/__pycache__' './03_api_gateway/repositories/__pycache__' './03_api_gateway/services/__pycache__' './03_api_gateway/utils/__pycache__' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/pi/ssh' './scripts/build/__pycache__' './scripts/build/components' './scripts/build/core' './scripts/build/distroless' './scripts/build/utils' './scripts/compliance/distroless' './scripts/compliance/general' './scripts/deployment/devcontainer' './scripts/deployment/distroless' './scripts/deployment/pi' './scripts/deployment/utils' './scripts/maintenance/cleanup' './scripts/maintenance/optimization' './scripts/maintenance/recovery' './scripts/network/diagnostics' './scripts/network/security' './scripts/network/setup' './scripts/testing/integration' './scripts/testing/unit' './scripts/testing/utils' './scripts/validation/__pycache__' './scripts/verification/__pycache__' './service_configs/x_lucid_cluster_calibration/__pycache__' './03_api_gateway/api/app/__pycache__' './03_api_gateway/api/app/database' './03_api_gateway/api/app/db' './03_api_gateway/api/app/middleware' './03_api_gateway/api/app/models' './03_api_gateway/api/app/routers' './03_api_gateway/api/app/routes' './03_api_gateway/api/app/schemas' './03_api_gateway/api/app/scripts' './03_api_gateway/api/app/security' './03_api_gateway/api/app/services' './03_api_gateway/api/app/utils' './03_api_gateway/api/tests/__pycache__' './03_api_gateway/api/tests/integration' './03_api_gateway/docs/swagger/dist' './03_api_gateway/api/app/database/__pycache__' './03_api_gateway/api/app/db/__pycache__' './03_api_gateway/api/app/db/models' './03_api_gateway/api/app/middleware/__pycache__' './03_api_gateway/api/app/models/__pycache__' './03_api_gateway/api/app/routers/__pycache__' './03_api_gateway/api/app/routes/__pycache__' './03_api_gateway/api/app/schemas/__pycache__' './03_api_gateway/api/app/scripts/__pycache__' './03_api_gateway/api/app/security/__pycache__' './03_api_gateway/api/app/services/__pycache__' './03_api_gateway/api/app/utils/__pycache__' './03_api_gateway/api/tests/integration/__pycache__'; \
    for d in \
      '.' \
      './03_api_gateway' \
      './common' \
      './configs' \
      './scripts' \
      './service_configs' \
      './tmp' \
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
      './configs/integration' \
      './configs/kubernetes' \
      './configs/logging' \
      './configs/pi' \
      './configs/secrets' \
      './configs/security' \
      './configs/tor' \
      './scripts/__pycache__' \
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
      './scripts/hardware' \
      './scripts/integration' \
      './scripts/lib' \
      './scripts/load' \
      './scripts/logging' \
      './scripts/maintenance' \
      './scripts/migration' \
      './scripts/monitoring' \
      './scripts/network' \
      './scripts/registry' \
      './scripts/secrets' \
      './scripts/security' \
      './scripts/services' \
      './scripts/testing' \
      './scripts/validation' \
      './scripts/verification' \
      './service_configs/blockchain' \
      './service_configs/distroless' \
      './service_configs/logging' \
      './service_configs/multi-stage' \
      './service_configs/node' \
      './service_configs/payment_services' \
      './service_configs/rdp' \
      './service_configs/security' \
      './service_configs/service_mesh' \
      './service_configs/services' \
      './service_configs/sessions' \
      './service_configs/tor' \
      './service_configs/x_lucid_cluster_calibration' \
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
      './service_configs/x_lucid_cluster_calibration/__pycache__' \
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
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done


COPY scripts/ ./scripts/
COPY 03_api_gateway/ ./03_api_gateway/

RUN rm -rf configs/environment 2>/dev/null || true



COPY 03_api_gateway/verify_files.py ./tmp/verify_files.py
COPY 03_api_gateway/verify_runtime.py ./tmp/verify_runtime.py



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

ARG BUILD_DATE
ARG VCS_REF
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
COPY --from=builder --chown=65532:65532 /build/03_api_gateway/ /app/03_api_gateway/
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=builder --chown=65532:65532 /build/scripts/ /app/scripts/
COPY --from=builder --chown=65532:65532 /build/service_configs/ /app/service_configs/
COPY --from=builder --chown=65532:65532 /build/tmp/ /app/tmp/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /bin/ /app/bin/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/lib/python3/dist-packages/ /app/usr/lib/python3/dist-packages/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /build/config/ /app/config/
COPY --from=builder --chown=65532:65532 /build/database/ /app/database/
COPY --from=builder --chown=65532:65532 /build/endpoints/ /app/endpoints/
COPY --from=builder --chown=65532:65532 /build/models/ /app/models/
COPY --from=builder --chown=65532:65532 /build/services/ /app/services/
COPY --from=builder --chown=65532:65532 /build/utils/ /app/utils/

# System directories & certificates
COPY --from=builder --chown=65532:65532 /build/tmp/verify_runtime.py /app/tmp/verify_runtime.py

RUN ["/app/usr/bin/python3.11", "/app/tmp/verify_runtime.py"]
RUN ["rm", "-f", "/app/tmp/verify_runtime.py"]



EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
USER 65532:65532

# tini as PID 1: proper signal handling & zombie reaping (aligned with tunnel-tools)
ENTRYPOINT ["/app/usr/bin/tini", "--"]

  CMD ["/app/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('api-gateway', 8080)); s.close(); exit(0 if result == 0 else 1)"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "app.api.app.main:app", "--host", "api-gateway", "--port", "8080"]
