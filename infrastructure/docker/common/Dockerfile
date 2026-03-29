# infrastructure/docker/common/Dockerfile
# syntax=docker/dockerfile:1.5
# Lucid server-tools style image: Debian builder → distroless runtime (Pi-friendly multi-arch).
# Build context: repository root (.)
#
# Layout registry: infrastructure/containers/host-config.yml → canonical runtime /app/service_configs/host-config.yml
# Service config root: infrastructure/containers/services/container-runtime-layout.yml

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# Stage 1 – Builder (apt, pip wheels, app trees, helper scripts)
# =============================================================================
FROM --platform=$TARGETPLATFORM debian:12-slim AS builder

ARG TARGETARCH
ARG BUILDPLATFORM
ARG TARGETPLATFORM

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
        curl \
        wget \
        jq \
        python3 \
        python3-venv \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-dev \
        dnsutils \
        iputils-ping \
        inetutils-traceroute \
        netcat-openbsd \
        socat \
        nmap \
        tcpdump \
        iperf3 \
        openssl \
        ca-certificates \
        gnupg \
        htop \
        procps \
        lsof \
        strace \
        rsync \
        unzip \
        tar \
        gzip \
        git \
        vim \
        nano \
        tree \
        util-linux \
        gosu \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pip + pinned wheelhouse (offline / supply-chain friendly); yq not in bookworm main — wheel + script wrapper
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    pip3 install --break-system-packages --upgrade pip setuptools wheel && \
    pip3 install --break-system-packages yq && \
    pip3 wheel --no-cache-dir --wheel-dir /build/wheels \
        "pip>=24.0" \
        "setuptools>=69.0" \
        "wheel>=0.42.0" \
        "yq>=3.0"

# MongoDB shell + database tools (arch-aware; builder TARGETARCH from BuildKit)
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

RUN useradd --system --create-home --shell /bin/bash lucid

RUN mkdir -p /opt/lucid/tools /opt/lucid/scripts /var/log/lucid \
    && chown -R lucid:lucid /opt/lucid /var/log/lucid

WORKDIR /build

# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './admin' './node' './rdp' './tools' './admin/admin_ui' './admin/api' './admin/audit' './admin/config' './admin/emergency' './admin/governance' './admin/key_rotation' './admin/rbac' './admin/services' './admin/system' './admin/ui' './admin/utils' './node/api' './node/config' './node/consensus' './node/dht_crdt' './node/economy' './node/flags' './node/governance' './node/models' './node/payouts' './node/pools' './node/poot' './node/registration' './node/repositories' './node/resources' './node/shards' './node/sync' './node/tor' './node/validation' './node/worker' './rdp/client' './rdp/common' './rdp/config' './rdp/protocol' './rdp/recorder' './rdp/resource_monitor' './rdp/security' './rdp/server' './rdp/server_manager' './rdp/session_controller' './rdp/xrdp' './tools/build' './tools/dev' './tools/ops' './rdp/session_controller/integration' './tools/ops/backup' './tools/ops/monitoring' './tools/ops/ota'; \
    for d in \
      '.' \
      './admin' \
      './node' \
      './rdp' \
      './tools' \
      './admin/admin_ui' \
      './admin/api' \
      './admin/audit' \
      './admin/config' \
      './admin/emergency' \
      './admin/governance' \
      './admin/key_rotation' \
      './admin/rbac' \
      './admin/services' \
      './admin/system' \
      './admin/ui' \
      './admin/utils' \
      './node/api' \
      './node/config' \
      './node/consensus' \
      './node/dht_crdt' \
      './node/economy' \
      './node/flags' \
      './node/governance' \
      './node/models' \
      './node/payouts' \
      './node/pools' \
      './node/poot' \
      './node/registration' \
      './node/repositories' \
      './node/resources' \
      './node/shards' \
      './node/sync' \
      './node/tor' \
      './node/validation' \
      './node/worker' \
      './rdp/client' \
      './rdp/common' \
      './rdp/config' \
      './rdp/protocol' \
      './rdp/recorder' \
      './rdp/resource_monitor' \
      './rdp/security' \
      './rdp/server' \
      './rdp/server_manager' \
      './rdp/session_controller' \
      './rdp/xrdp' \
      './tools/build' \
      './tools/dev' \
      './tools/ops' \
      './rdp/session_controller/integration' \
      './tools/ops/backup' \
      './tools/ops/monitoring' \
      './tools/ops/ota' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

COPY tools/ ./tools/
COPY infrastructure/service_mesh/ ./infrastructure/service_mesh/
COPY node/config/ ./node/config/
COPY RDP/config/ ./RDP/config/
COPY admin/config/ ./admin/config/

COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap

RUN cat > /opt/lucid/scripts/health-check.sh <<'EOF' && chmod +x /opt/lucid/scripts/health-check.sh
#!/bin/bash
# Comprehensive health check for core support services
set -euo pipefail

echo "[health-check] Lucid Core Support Health Check"
echo "============================================"

if curl -fsS --max-time 5 --socks5 tor-proxy:9050 http://check.torproject.org >/dev/null 2>&1; then
    echo "✅ Tor proxy: HEALTHY"
else
    echo "❌ Tor proxy: UNHEALTHY"
fi

if mongosh --quiet --eval "db.runCommand({ ping: 1 })" "${MONGO_URL:-mongodb://localhost:27017}" >/dev/null 2>&1; then
    echo "✅ MongoDB: HEALTHY"
else
    echo "❌ MongoDB: UNHEALTHY"
fi

if curl -fsS --max-time 5 http://lucid_api_gateway:8080/health >/dev/null 2>&1; then
    echo "✅ API Gateway: HEALTHY"
else
    echo "❌ API Gateway: UNHEALTHY"
fi

if curl -fsS --max-time 5 http://lucid_api:8081/health >/dev/null 2>&1; then
    echo "✅ API Server: HEALTHY"
else
    echo "❌ API Server: UNHEALTHY"
fi

echo "============================================"
EOF

RUN cat > /opt/lucid/scripts/network-test.sh <<'EOF' && chmod +x /opt/lucid/scripts/network-test.sh
#!/bin/bash
set -euo pipefail

echo "[network-test] Core Support Network Test"
echo "========================================"

services=("tor-proxy:9050" "lucid_mongo:27017" "lucid_api_gateway:8080" "lucid_api:8081" "lucid_tunnel_tools:7000")

for service in "${services[@]}"; do
    host=$(echo "$service" | cut -d: -f1)
    port=$(echo "$service" | cut -d: -f2)

    if nc -z "$host" "$port" 2>/dev/null; then
        echo "✅ $service: REACHABLE"
    else
        echo "❌ $service: UNREACHABLE"
    fi
done

echo "========================================"
EOF

RUN cat > /opt/lucid/scripts/db-backup.sh <<'EOF' && chmod +x /opt/lucid/scripts/db-backup.sh
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/log/lucid/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_backup_${TIMESTAMP}.gz"

echo "[db-backup] Starting MongoDB backup..."
mkdir -p "$BACKUP_DIR"

if mongodump --uri="${MONGO_URL:-mongodb://localhost:27017}" --archive="$BACKUP_DIR/$BACKUP_FILE" --gzip; then
    echo "✅ Backup completed: $BACKUP_DIR/$BACKUP_FILE"
    ls -t "$BACKUP_DIR"/lucid_backup_*.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
else
    echo "❌ Backup failed"
    exit 1
fi
EOF

RUN cat > /usr/local/bin/server-tools-start.sh <<'EOF' && chmod +x /usr/local/bin/server-tools-start.sh
#!/bin/bash
set -euo pipefail

echo "[server-tools] Lucid Server Tools starting..."
echo "[server-tools] Environment: ${LUCID_ENV:-dev}"
echo "[server-tools] Tools directory: ${TOOLS_DIR:-/opt/lucid/tools}"
echo "[server-tools] Scripts directory: ${SCRIPTS_DIR:-/opt/lucid/scripts}"

echo "[server-tools] Waiting for core services..."
sleep 10

echo "[server-tools] Running initial health check..."
/opt/lucid/scripts/health-check.sh || true

echo "[server-tools] Server tools ready."

exec tail -f /dev/null
EOF

RUN chown -R lucid:lucid /opt/lucid/scripts /var/log/lucid

# =============================================================================
# Stage 2 – Distroless runtime (COPY --from=builder)
# =============================================================================
FROM gcr.io/distroless/base-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Server utilities for Lucid core support (distroless Debian 12)" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Server Tools (common)" \
      org.opencontainers.image.description="Diagnostics and maintenance toolbox; COPY --from=builder" \
      com.lucid.plane="ops" \
      com.lucid.service="server-tools" \
      com.lucid.expose="none" \
      com.lucid.security="distroless" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation,.env.core,.env.support,.env.server-tools"

ENV PATH=/opt/lucid/scripts:/opt/lucid/tools:/usr/local/bin:/usr/bin:/bin \
    LUCID_ENV=dev \
    TOOLS_DIR=/opt/lucid/tools \
    SCRIPTS_DIR=/opt/lucid/scripts \
    LOG_DIR=/var/log/lucid \
    SERVER_TOOLS_HOME=/opt/lucid \
    SERVER_TOOLS_LOG_DIR=/opt/lucid/logs \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime support: full userland slices from builder (dynamic libs resolved)
COPY --from=builder /bin/bash /bin/bash
COPY --from=builder /usr/bin /usr/bin
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /lib /lib
COPY --from=builder /opt/lucid /opt/lucid
COPY --from=builder --chown=lucid:lucid /build/wheels/ /opt/lucid/tools/wheels/
COPY --from=builder --chown=lucid:lucid /build/infrastructure/service_mesh/ /opt/lucid/tools/infrastructure/service_mesh/
COPY --from=builder --chown=lucid:lucid /build/tools/ /opt/lucid/tools/repo-tools/
COPY --from=builder --chown=lucid:lucid /build/node/config/ /opt/lucid/tools/node/config/
COPY --from=builder --chown=lucid:lucid /build/RDP/config/ /opt/lucid/tools/RDP/config/
COPY --from=builder --chown=lucid:lucid /build/admin/config/ /opt/lucid/tools/admin/config/

COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap

COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

USER lucid:lucid
WORKDIR /opt/lucid

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/server-tools-start.sh"]
