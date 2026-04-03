# syntax=docker/dockerfile:1.5
# Lucid server-tools — Debian builder → distroless runtime (multi-arch, Pi-friendly).
# Build context: repository root (.)
# Dockerfile path: infrastructure/docker/common/Dockerfile
#
# Layout: infrastructure/containers/host-config.yml → runtime /app/configs/host-config.yml
# Service config: infrastructure/containers/services/container-runtime-layout.yml

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# -----------------------------------------------------------------------------
# Stage 1 — Builder
# -----------------------------------------------------------------------------
FROM --platform=$TARGETPLATFORM debian:12-slim AS builder

ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        dnsutils \
        g++ \
        gcc \
        git \
        gnupg \
        gosu \
        gzip \
        htop \
        inetutils-traceroute \
        iperf3 \
        iputils-ping \
        jq \
        libffi-dev \
        libpq-dev \
        libssl-dev \
        lsof \
        nano \
        netcat-openbsd \
        nmap \
        openssl \
        pkg-config \
        procps \
        python3.11 \
        python3.11-dev \
        python3-pip \
        python3.11-setuptools \
        python3-venv \
        python3.11-wheel \
        rsync \
        socat \
        strace \
        tar \
        tcpdump \
        tini \
        tree \
        unzip \
        util-linux \
        vim \
        wget \
        xxd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# LUCID_LIB_SKELETON_BEGIN
# Generated: FHS dirs for builder (from final-stage COPY --from, excluding /build/ sources;
# ancestor dirs collapsed; overlaps with builder mkdir/.keep removed — see collect_skeleton_paths_from_dockerfile).
RUN set -eux; \
  mkdir -p \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/var/log/lucid' \
    '/usr/lib/python3/dist-packages'; \
  for d in \
    '/bin' \
    '/etc/ssl' \
    '/usr/bin' \
    '/var/log/lucid' \
    '/usr/lib/python3/dist-packages'; \
  do \
    printf 'LUCID_LIB_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_LIB_SKELETON_END


RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    pip3 install --break-system-packages --upgrade pip setuptools wheel && \
    pip3 install --break-system-packages yq && \
    pip3 wheel --no-cache-dir --wheel-dir /build/wheels \
        "pip>=24.0" \
        "setuptools>=69.0" \
        "wheel>=0.42.0" \
        "yq>=3.0"

RUN set -eux; \
    case "$TARGETARCH" in \
        arm64) \
            MONGOSH_URL="https://downloads.mongodb.com/compass/mongosh-2.1.5-linux-arm64.tgz"; \
            DB_TOOLS_URL="https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-aarch64-100.9.4.tgz"; \
            ;; \
        amd64) \
            MONGOSH_URL="https://downloads.mongodb.com/compass/mongosh-2.1.5-linux-x64.tgz"; \
            DB_TOOLS_URL="https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.9.4.tgz"; \
            ;; \
        *) \
            echo "unsupported TARGETARCH=$TARGETARCH"; exit 1; \
            ;; \
    esac; \
    curl -fsSL "$MONGOSH_URL" | tar -xzC /tmp; \
    mv /tmp/mongosh-*/bin/* /usr/local/bin/; \
    rm -rf /tmp/mongosh-*; \
    curl -fsSL "$DB_TOOLS_URL" | tar -xzC /tmp; \
    mv /tmp/mongodb-database-tools-*/bin/* /usr/local/bin/; \
    rm -rf /tmp/mongodb-database-tools-*

RUN groupadd -g 65532 nonroot && \
    useradd --system --no-create-home --shell /usr/sbin/nologin -u 65532 -g nonroot nonroot

RUN mkdir -p /build/lucid/tools /build/lucid/scripts /var/log/lucid && \
    chown -R 65532:65532 /build/lucid /var/log/lucid

WORKDIR /build
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './admin' './common' './configs' './lucid' './node' './rdp' './scripts' './service_configs' './sessions' './tools' './admin/__pycache__' './admin/admin_ui' './admin/api' './admin/audit' './admin/config' './admin/emergency' './admin/governance' './admin/key_rotation' './admin/over_lord' './admin/rbac' './admin/services' './admin/system' './admin/ui' './admin/utils' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/env' './configs/integration' './configs/kubernetes' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './lucid/scripts' './node/__pycache__' './node/api' './node/config' './node/consensus' './node/dht_crdt' './node/economy' './node/flags' './node/governance' './node/models' './node/over_lord' './node/payouts' './node/pools' './node/poot' './node/registration' './node/repositories' './node/resources' './node/service_configs' './node/shards' './node/sync' './node/tor' './node/validation' './node/worker' './rdp/__pycache__' './rdp/client' './rdp/common' './rdp/config' './rdp/database' './rdp/monitoring' './rdp/protocol' './rdp/recorder' './rdp/resource_monitor' './rdp/scripts' './rdp/security' './rdp/server' './rdp/server_manager' './rdp/session_controller' './rdp/xrdp' './scripts/__pycache__' './scripts/build' './scripts/compliance' './scripts/config' './scripts/contracts' './scripts/database' './scripts/deployment' './scripts/devcontainer' './scripts/docs' './scripts/foundation' './scripts/gui' './scripts/hardware' './scripts/integration' './scripts/lib' './scripts/load' './scripts/logging' './scripts/maintenance' './scripts/migration' './scripts/monitoring' './scripts/network' './scripts/registry' './scripts/secrets' './scripts/security' './scripts/services' './scripts/testing' './scripts/validation' './scripts/verification' './sessions/__pycache__' './sessions/api' './sessions/config' './sessions/core' './sessions/encryption' './sessions/integration' './sessions/pipeline' './sessions/processor' './sessions/recorder' './sessions/security' './sessions/session_systems_control' './sessions/storage' './tools/__pycache__' './tools/build' './tools/dev' './tools/ops' './admin/admin_ui/__pycache__' './admin/api/__pycache__' './admin/audit/__pycache__' './admin/config/__pycache__' './admin/emergency/__pycache__' './admin/governance/__pycache__' './admin/key_rotation/__pycache__' './admin/rbac/__pycache__' './admin/services/__pycache__' './admin/system/__pycache__' './admin/ui/__pycache__' './admin/ui/static' './admin/ui/templates' './admin/utils/__pycache__' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/pi/ssh' './lucid/scripts/db-backup.sh' './lucid/scripts/health-check.sh' './lucid/scripts/network-test.sh' './node/api/__pycache__' './node/consensus/__pycache__' './node/dht_crdt/__pycache__' './node/economy/__pycache__' './node/flags/__pycache__' './node/governance/__pycache__' './node/models/__pycache__' './node/payouts/__pycache__' './node/pools/__pycache__' './node/poot/__pycache__' './node/registration/__pycache__' './node/repositories/__pycache__' './node/resources/__pycache__' './node/service_configs/x_lucid_cluster_calibration' './node/shards/__pycache__' './node/sync/__pycache__' './node/tor/__pycache__' './node/validation/__pycache__' './node/worker/__pycache__' './rdp/client/__pycache__' './rdp/common/__pycache__' './rdp/monitoring/grafana' './rdp/protocol/__pycache__' './rdp/recorder/__pycache__' './rdp/resource_monitor/__pycache__' './rdp/resource_monitor/config' './rdp/security/__pycache__' './rdp/server/__pycache__' './rdp/server_manager/__pycache__' './rdp/server_manager/config' './rdp/session_controller/__pycache__' './rdp/session_controller/config' './rdp/session_controller/integration' './rdp/xrdp/__pycache__' './rdp/xrdp/config' './scripts/build/__pycache__' './scripts/build/components' './scripts/build/core' './scripts/build/distroless' './scripts/build/utils' './scripts/compliance/distroless' './scripts/compliance/general' './scripts/deployment/devcontainer' './scripts/deployment/distroless' './scripts/deployment/pi' './scripts/deployment/utils' './scripts/maintenance/cleanup' './scripts/maintenance/optimization' './scripts/maintenance/recovery' './scripts/network/diagnostics' './scripts/network/security' './scripts/network/setup' './scripts/testing/integration' './scripts/testing/unit' './scripts/testing/utils' './scripts/validation/__pycache__' './scripts/verification/__pycache__' './sessions/api/__pycache__' './sessions/api/config' './sessions/api/integration' './sessions/core/__pycache__' './sessions/encryption/__pycache__' './sessions/integration/__pycache__' './sessions/pipeline/__pycache__' './sessions/pipeline/integration' './sessions/processor/__pycache__' './sessions/processor/config' './sessions/processor/integration' './sessions/recorder/__pycache__' './sessions/recorder/config' './sessions/recorder/integration' './sessions/security/__pycache__' './sessions/session_systems_control/__pycache__' './sessions/storage/__pycache__' './sessions/storage/config' './tools/build/__pycache__' './tools/dev/__pycache__' './tools/ops/__pycache__' './tools/ops/backup' './tools/ops/monitoring' './tools/ops/ota' './admin/ui/static/css' './admin/ui/static/js' './rdp/monitoring/grafana/dashboards' './rdp/monitoring/grafana/datasources' './rdp/session_controller/integration/__pycache__' './sessions/api/integration/__pycache__' './sessions/pipeline/integration/__pycache__' './sessions/processor/integration/__pycache__' './sessions/recorder/integration/__pycache__' './tools/ops/backup/__pycache__' './tools/ops/monitoring/__pycache__' './tools/ops/ota/__pycache__'; \
    for d in \
      '.' \
      './admin' \
      './common' \
      './configs' \
      './lucid' \
      './node' \
      './rdp' \
      './scripts' \
      './service_configs' \
      './sessions' \
      './tools' \
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
      './lucid/scripts' \
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
      './tools/__pycache__' \
      './tools/build' \
      './tools/dev' \
      './tools/ops' \
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
      './lucid/scripts/db-backup.sh' \
      './lucid/scripts/health-check.sh' \
      './lucid/scripts/network-test.sh' \
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
      './tools/build/__pycache__' \
      './tools/dev/__pycache__' \
      './tools/ops/__pycache__' \
      './tools/ops/backup' \
      './tools/ops/monitoring' \
      './tools/ops/ota' \
      './admin/ui/static/css' \
      './admin/ui/static/js' \
      './rdp/monitoring/grafana/dashboards' \
      './rdp/monitoring/grafana/datasources' \
      './rdp/session_controller/integration/__pycache__' \
      './sessions/api/integration/__pycache__' \
      './sessions/pipeline/integration/__pycache__' \
      './sessions/processor/integration/__pycache__' \
      './sessions/recorder/integration/__pycache__' \
      './tools/ops/backup/__pycache__' \
      './tools/ops/monitoring/__pycache__' \
      './tools/ops/ota/__pycache__' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

RUN rm -rf configs/environment 2>/dev/null || true

COPY sessions/ ./sessions/
COPY infrastructure/compose/./configs/compose/

COPY scripts/ ./scripts/
COPY tools/ ./tools/
COPY infrastructure/service_mesh/ ./infrastructure/service_mesh/
COPY node/config/ ./node/config/
COPY RDP/config/ ./rdp/config/
COPY admin/config/ ./admin/config/
COPY common/ ./common/

COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap

# Server-tools scripts (repo: infrastructure/docker/common/scripts/server-tools/)
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/health-check.sh ./lucid/scripts/health-check.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/network-test.sh ./lucid/scripts/network-test.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/db-backup.sh ./lucid/scripts/db-backup.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/server-tools-start.sh /usr/local/bin/server-tools-start.sh

RUN chown -R 65532:65532 ./scripts ./lucid /var/log/lucid

# -----------------------------------------------------------------------------
# Stage 2 — Distroless runtime
# -----------------------------------------------------------------------------
FROM gcr.io/distroless/base-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
# Lucid Tor egress / network isolation (PUBLIC_TOR_IP: ../../configs/environment/ ; compose: lucid-tor-egress-network)
ARG PUBLIC_TOR_IP=109.70.100.1
ARG LUCID_INTERNAL_NETWORK_NAME=lucid-pi-network
ARG LUCID_TOR_EGRESS_NETWORK_NAME=lucid-tor-egress-network

LABEL maintainer="Lucid Development Team" \
      com.lucid.network.internal="${LUCID_INTERNAL_NETWORK_NAME}" \
      com.lucid.network.tor_egress="${LUCID_TOR_EGRESS_NETWORK_NAME}" \
      com.lucid.tor.public_egress_ip="${PUBLIC_TOR_IP}" \
      version="${VERSION}" \
      description="Lucid server-tools (distroless Debian 12)" \
      org.opencontainers.image.title="Lucid Server Tools" \
      org.opencontainers.image.description="Diagnostics and maintenance toolbox" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.plane="ops" \
      com.lucid.service="server-common" \
      com.lucid.layer="0" \
      org.lucid.layer="0" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="none" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation,.env.core,.env.support,.env.server-tools"

ENV     PUBLIC_TOR_IP="${PUBLIC_TOR_IP}" \
    LUCID_INTERNAL_NETWORK_NAME="${LUCID_INTERNAL_NETWORK_NAME}" \
    LUCID_TOR_EGRESS_NETWORK_NAME="${LUCID_TOR_EGRESS_NETWORK_NAME}" \
    PATH="/usr/local/bin:/app/scripts:/app/tools:/usr/bin:/bin" \
    LOG_DIR="/var/log/lucid" \
    LUCID_ENV="dev" \
    SCRIPTS_DIR="/app/scripts" \
    SERVER_HOME_DIR="/app" \
    SERVER_LOG_DIR="/app/logs" \
    TOOLS_DIR="/app/tools"
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libpq.so.5 /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /bin/ /app/bin/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/lib/python3/dist-packages/ /app/usr/lib/python3/dist-packages/
COPY --from=builder --chown=65532:65532 /var/log/lucid/ /app/var/log/lucid/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END

# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/admin/ /app/admin/
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/

COPY --from=builder --chown=65532:65532 /build/lucid/ /app/lucid/
COPY --from=builder --chown=65532:65532 /build/node/ /app/node/
COPY --from=builder --chown=65532:65532 /build/rdp/ /app/rdp/
COPY --from=builder --chown=65532:65532 /build/scripts/ /app/scripts/
COPY --from=builder --chown=65532:65532 /build/sessions/ /app/sessions/
COPY --from=builder --chown=65532:65532 /build/tools/ /app/tools/
# LUCID_RUNTIME_COPY_FROM_BUILD_END


COPY --from=builder /bin/bash /bin/bash
COPY --from=builder /usr/bin/tini /usr/bin/tini
COPY --from=builder /usr/bin /usr/bin
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /lib /lib
COPY --from=builder --chown=65532:65532 /build/wheels/ /app/wheels/
COPY --from=builder --chown=65532:65532 /build/infrastructure/service_mesh/ /app/infrastructure/service_mesh/
COPY --from=builder --chown=65532:65532 /build/node/config/ /app/node/config/
COPY --from=builder --chown=65532:65532 /build/rdp/config/ /app/rdp/config/
COPY --from=builder --chown=65532:65532 /build/admin/config/ /app/admin/config/

COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap

COPY --from=builder /usr/local/bin/server-tools-start.sh /usr/local/bin/server-tools-start.sh

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

USER 65532:65532
WORKDIR /app/lucid

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/server-tools-start.sh"]
