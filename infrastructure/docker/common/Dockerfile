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
ARG TARGETARCH

FROM --platform=$TARGETPLATFORM debian:12-slim AS builder

WORKDIR /build
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN
# alignment-mat server-common_manifest.json: compose_service='server-common' — explicit manifest paths → 23 builder COPY line(s) (dockerfile_layout_structure.json section #10 COPY_DIRECTORIES).
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
COPY infrastructure/containers/apply_alignment_mat_copy_section10.py ./infrastructure/containers/apply_alignment_mat_copy_section10.py
COPY infrastructure/containers/services/common/server-common.yml ./infrastructure/containers/services/common/server-common.yml
COPY infrastructure/containers/services/middle-ware/master-endpoint.yml ./infrastructure/containers/services/middle-ware/master-endpoint.yml
COPY infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml ./infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml
COPY scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py ./scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py
# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END
COPY infrastructure/compose/./configs/compose/

COPY scripts/ ./scripts/
COPY infrastructure/service_mesh/ ./infrastructure/service_mesh/

COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap

# Server-tools scripts (repo: infrastructure/docker/common/scripts/server-tools/)
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/health-check.sh ./lucid/scripts/health-check.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/network-test.sh ./lucid/scripts/network-test.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/db-backup.sh ./lucid/scripts/db-backup.sh
COPY --chmod=755 infrastructure/docker/common/scripts/server-tools/server-tools-start.sh /usr/local/bin/server-tools-start.sh

RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    pip3 install --break-system-packages --upgrade pip setuptools wheel && \
    pip3 install --break-system-packages yq && \
    pip3 wheel --no-cache-dir --wheel-dir /build/wheels \
        "pip>=24.0" \
        "setuptools>=69.0" \
        "wheel>=0.42.0" \
        "yq>=3.0"
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './common' './lucid' './scripts' './common/__pycache__' './common/governance' './common/security' './common/server-tools' './common/templates' './common/tor' './lucid/scripts' './scripts/__pycache__' './scripts/auth_sm_realignment' './scripts/build' './scripts/compliance' './scripts/config' './scripts/contracts' './scripts/database' './scripts/deployment' './scripts/devcontainer' './scripts/docs' './scripts/foundation' './scripts/gui' './scripts/gui_auth_realignment' './scripts/hardware' './scripts/integration' './scripts/lib' './scripts/load' './scripts/logging' './scripts/maintenance' './scripts/migration' './scripts/monitoring' './scripts/network' './scripts/re-build' './scripts/registry' './scripts/secrets' './scripts/security' './scripts/services' './scripts/testing' './scripts/validation' './scripts/verification' './common/governance/__pycache__' './common/security/__pycache__' './common/server-tools/__pycache__' './common/tor/__pycache__' './lucid/scripts/db-backup.sh' './lucid/scripts/health-check.sh' './lucid/scripts/network-test.sh' './scripts/auth_sm_realignment/.cache' './scripts/auth_sm_realignment/lib' './scripts/build/__pycache__' './scripts/build/components' './scripts/build/core' './scripts/build/distroless' './scripts/build/utils' './scripts/compliance/distroless' './scripts/compliance/general' './scripts/deployment/devcontainer' './scripts/deployment/distroless' './scripts/deployment/pi' './scripts/deployment/utils' './scripts/gui_auth_realignment/.cache' './scripts/gui_auth_realignment/lib' './scripts/maintenance/cleanup' './scripts/maintenance/optimization' './scripts/maintenance/recovery' './scripts/network/diagnostics' './scripts/network/security' './scripts/network/setup' './scripts/testing/integration' './scripts/testing/unit' './scripts/testing/utils' './scripts/validation/__pycache__' './scripts/verification/__pycache__'; \
    for d in \
      '.' \
      './common' \
      './lucid' \
      './scripts' \
      './common/__pycache__' \
      './common/governance' \
      './common/security' \
      './common/server-tools' \
      './common/templates' \
      './common/tor' \
      './lucid/scripts' \
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
      './common/governance/__pycache__' \
      './common/security/__pycache__' \
      './common/server-tools/__pycache__' \
      './common/tor/__pycache__' \
      './lucid/scripts/db-backup.sh' \
      './lucid/scripts/health-check.sh' \
      './lucid/scripts/network-test.sh' \
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
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

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

RUN rm -rf configs/environment 2>/dev/null || true

RUN chown -R 65532:65532 ./scripts ./lucid /var/log/lucid

# -----------------------------------------------------------------------------
# Stage 2 — Distroless runtime
# -----------------------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

FROM gcr.io/distroless/base-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
# Lucid Tor egress / network isolation (PUBLIC_TOR_IP: ../../configs/environment/ ; compose: lucid-tor-egress-network)
ARG PUBLIC_TOR_IP=109.70.100.1
ARG LUCID_INTERNAL_NETWORK_NAME=lucid-pi-network
ARG LUCID_TOR_EGRESS_NETWORK_NAME=lucid-tor-egress-network

WORKDIR /app/lucid

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
      com.lucid.expose="0" \
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
# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/lucid/ /app/lucid/
COPY --from=builder --chown=65532:65532 /build/scripts/ /app/scripts/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=builder --chown=65532:65532 /bin/ /app/bin/
COPY --from=builder --chown=65532:65532 /dev/null/ /app/dev/null/
COPY --from=builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=builder --chown=65532:65532 /usr/lib/python3/dist-packages/ /app/usr/lib/python3/dist-packages/
COPY --from=builder --chown=65532:65532 /var/log/lucid/ /app/var/log/lucid/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=builder --chown=65532:65532 /build/wheels/ /app/wheels/
COPY --from=builder --chown=65532:65532 /build/infrastructure/service_mesh/ /app/infrastructure/service_mesh/

USER 65532:65532
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/server-tools-start.sh"]
COPY --chmod=755 infrastructure/docker/common/server-tools-bootstrap.sh /usr/local/bin/server-tools-bootstrap
COPY --chmod=755 infrastructure/docker/common/service-mesh-bootstrap.sh /usr/local/bin/service-mesh-bootstrap
