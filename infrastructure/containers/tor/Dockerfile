# LUCID TUNNEL TOOLS - 
# Builds pickme/lucid-tunnel-tools:latest-arm64
# Compatible with pickme/lucid-tor-proxy:latest-arm64
# Professional tunneling utilities for Pi deployment with distroless security
# Configuration: All values from .env.tunnel-tools, .env.secrets, .env.foundation via docker-compose
# Build Context: 02_network_security/tunnels (relative paths used in COPY commands)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Builder - Python 3.11 Bookworm with minimal tooling
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.11-slim-bookworm AS tunnel-builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG VERSION
ARG PYTHON_VERSION=3.11

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

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
      python3-dev \
      python3-pip \
      python3-setuptools \
      python3-wheel \
      ca-certificates \
      tini \
      bash \
      jq \
      netcat-openbsd \
      socat \
      xxd \
      rustc \
      cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid \
    && adduser --system --no-create-home --uid 65532 --gid 65532 --group tunnel-nonroot || true

WORKDIR /build
# LUCID_IMAGE_CONFIG: .env.secrets + .env.master (builder)
RUN mkdir -p ./configs && \
    printf "LUCID_TUNNEL_TOOLS_CONFIGS_$(date +%s)" > ./configs/.keep && \
    touch ./configs/.keep && \
    chown -R 65532:65532 ./configs && \
    chmod 644 ./configs/.keep && \
    echo " Marker files created to lock in directory structure"
 
COPY configs/ ./configs/
COPY configs/environment/.env.secrets ./configs/.env.secrets
COPY master-env-config.txt ./configs/.env.master

COPY infrastructure/containers/services/ ./service_configs/
COPY 02_network_security/ ./02_network_security/
COPY 03_api_gateway/ ./03_api_gateway/
COPY sessions/api-gateway/ ./sessions/api-gateway/
COPY gui_api_bridge/ ./gui_api_bridge/
COPY server/ ./server/

COPY service_mesh/ ./service_mesh/

COPY configs/environment/.env.tunnel-tools ./configs/.env.tunnel-tools
COPY configs/environment/.env.secrets ./configs/.env.secrets
COPY master-env-config.txt ./configs/.env.master
COPY 02_network_security/tor/torrc ./configs/torrc
COPY infrastructure/containers/services/container-runtime-layout.yml ./configs/container-runtime-layout.yml
COPY infrastructure/containers/tor/docker-compose.proxy-systems.yml ./configs/docker-compose.proxy-systems.yml
RUN chmod +x ./tunnels/entrypoint.py || true && \
    ( test -f ./tunnels/__init__.py && chmod +x ./tunnels/__init__.py ) || true && \
    chmod +x ./tunnels/scripts/*.sh || true && \
    chmod +x ./tunnels/tunnel_metrics.py || true && \
    chmod +x ./tunnels/tunnel_status.py || true && \
    chmod +x ./tunnels/scripts/*.sh || true && \
    chmod +x ./tunnels/config/* || true && \
    echo "✅ Permissions set for all files"

# Pinned build artifacts: wheelhouse for supply-chain / optional offline installs (tunnel app is stdlib-first).
RUN mkdir -p /build/wheels && \
    python3.11 -m pip wheel --no-cache-dir \
      -w /build/wheels \
      "setuptools>=69.0" \
      "wheel>=0.42.0" \
    && echo "✅ Wheelhouse populated under /build/wheels"
# LUCID_X_FILES_SKELETON_BEGIN
# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY
RUN set -eux; \
    mkdir -p '.' './02_network_security' './03_api_gateway' './configs' './gui_api_bridge' './server' './service_configs' './service_mesh' './sessions' './02_network_security/docs' './02_network_security/tor' './02_network_security/tunnels' './03_api_gateway/api' './03_api_gateway/certs' './03_api_gateway/config' './03_api_gateway/database' './03_api_gateway/docs' './03_api_gateway/endpoints' './03_api_gateway/gateway' './03_api_gateway/legacy' './03_api_gateway/logs' './03_api_gateway/middleware' './03_api_gateway/models' './03_api_gateway/repositories' './03_api_gateway/scripts' './03_api_gateway/services' './03_api_gateway/utils' './configs/.ssh' './configs/container' './configs/database' './configs/docker' './configs/environment' './configs/integration' './configs/logging' './configs/pi' './configs/secrets' './configs/security' './configs/tor' './configs/torrc' './gui_api_bridge/config' './gui_api_bridge/gui_api_bridge' './gui_api_bridge/scripts' './service_configs/blockchain' './service_configs/distroless' './service_configs/logging' './service_configs/multi-stage' './service_configs/node' './service_configs/payment_services' './service_configs/rdp' './service_configs/security' './service_configs/service_mesh' './service_configs/sessions' './service_configs/x_lucid_cluster_calibration' './service_mesh/communication' './service_mesh/config' './service_mesh/controller' './service_mesh/discovery' './service_mesh/security' './service_mesh/sidecar' './sessions/api' './sessions/api-gateway' './sessions/core' './sessions/encryption' './sessions/integration' './sessions/pipeline' './sessions/processor' './sessions/recorder' './sessions/security' './sessions/session_systems_control' './sessions/storage' './02_network_security/tor/scripts' './02_network_security/tunnels/config' './02_network_security/tunnels/scripts' './03_api_gateway/api/app' './03_api_gateway/api/lucid_api.egg-info' './03_api_gateway/api/tests' './03_api_gateway/docs/swagger' './03_api_gateway/legacy/api' './03_api_gateway/legacy/gateway' './configs/container/admin' './configs/container/auth' './configs/container/base' './configs/container/blockchain' './configs/container/database' './configs/container/electron_gui' './configs/container/gui' './configs/container/node' './configs/container/payment_systems' './configs/container/rdp' './configs/container/server' './configs/container/sessions' './configs/container/storage' './configs/container/tor' './configs/database/elasticsearch' './configs/database/redis' './configs/docker/distroless' './configs/docker/docs' './configs/docker/multi-stage' './configs/environment/development' './configs/environment/pi' './configs/environment/production' './configs/environment/staging' './configs/pi/ssh' './gui_api_bridge/gui_api_bridge/config' './gui_api_bridge/gui_api_bridge/integration' './gui_api_bridge/gui_api_bridge/middleware' './gui_api_bridge/gui_api_bridge/models' './gui_api_bridge/gui_api_bridge/routers' './gui_api_bridge/gui_api_bridge/services' './gui_api_bridge/gui_api_bridge/utils' './gui_api_bridge/gui_api_bridge/{config,middleware,routers,services,integration,models,utils}' './service_mesh/sidecar/envoy' './service_mesh/sidecar/proxy' './sessions/api/integration' './sessions/pipeline/integration' './sessions/processor/integration' './sessions/recorder/integration' './03_api_gateway/api/app/database' './03_api_gateway/api/app/db' './03_api_gateway/api/app/middleware' './03_api_gateway/api/app/models' './03_api_gateway/api/app/routers' './03_api_gateway/api/app/routes' './03_api_gateway/api/app/schemas' './03_api_gateway/api/app/scripts' './03_api_gateway/api/app/security' './03_api_gateway/api/app/services' './03_api_gateway/api/app/utils' './03_api_gateway/api/tests/integration' './03_api_gateway/docs/swagger/dist' './03_api_gateway/api/app/db/models'; \
    for d in \
      '.' \
      './02_network_security' \
      './03_api_gateway' \
      './configs' \
      './gui_api_bridge' \
      './server' \
      './service_configs' \
      './service_mesh' \
      './sessions' \
      './02_network_security/docs' \
      './02_network_security/tor' \
      './02_network_security/tunnels' \
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
      './configs/torrc' \
      './gui_api_bridge/config' \
      './gui_api_bridge/gui_api_bridge' \
      './gui_api_bridge/scripts' \
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
      './service_mesh/communication' \
      './service_mesh/config' \
      './service_mesh/controller' \
      './service_mesh/discovery' \
      './service_mesh/security' \
      './service_mesh/sidecar' \
      './sessions/api' \
      './sessions/api-gateway' \
      './sessions/core' \
      './sessions/encryption' \
      './sessions/integration' \
      './sessions/pipeline' \
      './sessions/processor' \
      './sessions/recorder' \
      './sessions/security' \
      './sessions/session_systems_control' \
      './sessions/storage' \
      './02_network_security/tor/scripts' \
      './02_network_security/tunnels/config' \
      './02_network_security/tunnels/scripts' \
      './03_api_gateway/api/app' \
      './03_api_gateway/api/lucid_api.egg-info' \
      './03_api_gateway/api/tests' \
      './03_api_gateway/docs/swagger' \
      './03_api_gateway/legacy/api' \
      './03_api_gateway/legacy/gateway' \
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
      './gui_api_bridge/gui_api_bridge/config' \
      './gui_api_bridge/gui_api_bridge/integration' \
      './gui_api_bridge/gui_api_bridge/middleware' \
      './gui_api_bridge/gui_api_bridge/models' \
      './gui_api_bridge/gui_api_bridge/routers' \
      './gui_api_bridge/gui_api_bridge/services' \
      './gui_api_bridge/gui_api_bridge/utils' \
      './gui_api_bridge/gui_api_bridge/{config,middleware,routers,services,integration,models,utils}' \
      './service_mesh/sidecar/envoy' \
      './service_mesh/sidecar/proxy' \
      './sessions/api/integration' \
      './sessions/pipeline/integration' \
      './sessions/processor/integration' \
      './sessions/recorder/integration' \
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
      './03_api_gateway/api/tests/integration' \
      './03_api_gateway/docs/swagger/dist' \
      './03_api_gateway/api/app/db/models' \
    ; do \
      printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
      touch "$d/.keep"; \
    done
# LUCID_X_FILES_SKELETON_END

# Builder stage verification: Verify Python

RUN python3.11 --version && \
    which python3.11 && \
    test -f ./tunnels/entrypoint.py && \
    python3.11 -m py_compile ./tunnels/entrypoint.py && \
    python3.11 -m py_compile ./tunnels/tunnel_metrics.py && \
    python3.11 -m py_compile ./tunnels/tunnel_status.py && \
    ( test ! -f ./tunnels/__init__.py || python3.11 -m py_compile ./tunnels/__init__.py ) && \
    test -n "$(ls -A /build/wheels 2>/dev/null)" && \
    echo "✅ Builder stage verification passed - All Python files compile successfully"

# =============================================================================
# STAGE 2: Distroless Runtime with Python3 (Debian 12)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:latest

WORKDIR /app

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless tunnel tools for Lucid core support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Tunnel Tools" \
      org.opencontainers.image.description="Distroless tunnel tools for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="tunnel-tools" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="7000" \
      com.lucid.cluster="foundation" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.tunnel-tools,.env.secrets,.env.foundation"

# Minimal, safe PATH and Python settings
ENV PATH=/app/usr/local/bin:/app/usr/bin:/app/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LUCID_SERVICE_NAME=tunnel-tools \
    LUCID_SERVICE_PORT=7000 \
    LUCID_SERVICE_PROTOCOL=http \
    LUCID_SERVICE_HOST_IP=172.20.10.66 \
    LUCID_SERVICE_HTTP_PATH=http://tunnel-tools:7000/app

# LUCID_IMAGE_CONFIG: .env.secrets + .env.master (runtime)
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.secrets /app/configs/.env.secrets
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.master /app/configs/.env.master
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.tunnel-tools /app/configs/.env.tunnel-tools
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/torrc /app/configs/torrc
COPY --from=tunnel-builder --chown=65532:65532 /build/02_network_security/tunnels/scripts/ /app/02_network_security/tunnels/scripts/
COPY --from=tunnel-builder --chown=65532:65532 /build/02_network_security/tunnels/config/ /app/02_network_security/tunnels/config/

COPY --from=tunnel-builder --chown=65532:65532 /usr/local/bin/ /app/usr/local/bin/
COPY --from=tunnel-builder --chown=65532:65532 /var/lib/ /app/var/lib/
COPY --from=tunnel-builder --chown=65532:65532 /var/run/ /app/var/run/
COPY --from=tunnel-builder --chown=65532:65532 /run/lucid/onion/ /app/run/lucid/onion/
COPY --from=tunnel-builder --chown=65532:65532 /run/lucid/tunnel/ /app/run/lucid/tunnel/
COPY --from=tunnel-builder --chown=65532:65532 /run/lucid/tunnels/ /app/run/lucid/tunnels/
COPY --from=tunnel-builder --chown=65532:65532 /run/lucid/tor/ /app/run/lucid/tor/
COPY --from=tunnel-builder --chown=65532:65532 /run/lucid/tor/lucid_admin/ /app/run/lucid/tor/lucid_admin/

COPY --from=tunnel-builder --chown=65532:65532 /run/ /app/run/
COPY --from=tunnel-builder --chown=65532:65532 /tmp/ /app/tmp/
COPY --from=tunnel-builder --chown=65532:65532 /etc/ /app/etc/
COPY --from=tunnel-builder --chown=65532:65532 /lib/ /app/lib/
COPY --from=tunnel-builder --chown=65532:65532 /usr/lib/ /app/usr/lib/
COPY --from=tunnel-builder --chown=65532:65532 /usr/sbin/ /app/usr/sbin/
COPY --from=tunnel-builder --chown=65532:65532 /usr/share/ /app/usr/share/
COPY --from=tunnel-builder --chown=65532:65532 /usr/local/share/ /app/usr/local/share/
COPY --from=tunnel-builder --chown=65532:65532 /etc/ssl/certs/ /app/etc/ssl/certs/
COPY --from=tunnel-builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=tunnel-builder --chown=65532:65532 /etc/passwd /app/etc/passwd
COPY --from=tunnel-builder --chown=65532:65532 /etc/group /app/etc/group
COPY --from=tunnel-builder --chown=65532:65532 /etc/hosts /app/etc/hosts
COPY --from=tunnel-builder --chown=65532:65532 /etc/hostname /app/etc/hostname
COPY --from=tunnel-builder --chown=65532:65532 /etc/resolv.conf /app/etc/resolv.conf
COPY --from=tunnel-builder --chown=65532:65532 /etc/hosts.allow /app/etc/hosts.allow
COPY --from=tunnel-builder --chown=65532:65532 /etc/hosts.deny /app/etc/hosts.deny
COPY --from=tunnel-builder --chown=65532:65532 /etc/motd /app/etc/motd
COPY --from=tunnel-builder --chown=65532:65532 /usr/bin/ /app/usr/bin/
COPY --from=tunnel-builder --chown=65532:65532 /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=tunnel-builder --chown=65532:65532 /build/wheels/ /app/wheels/
COPY --from=tunnel-builder --chown=65532:65532 /build/




# Runtime verification: Verify entrypoint exists and modules can be imported (distroless base Python)
RUN ["/usr/bin/python3.11", "-c", "import os, sys; \
sys.path.insert(0, '/app/tunnels'); \
entrypoint_path = '/app/tunnels/entrypoint.py'; \
assert os.path.isfile(entrypoint_path), 'CRITICAL: /app/tunnels/entrypoint.py missing'; \
import entrypoint; import tunnel_metrics; import tunnel_status; \
print('✅ All tunnel-tools modules verified')"]


ENV CONTROL_HOST=tor-proxy \
    CONTROL_PORT=9051 \
    COOKIE_FILE=/app/run/lucid/tor/control_auth_cookie \
    ONION_PORTS="80 api-gateway:8080" \
    WRITE_ENV=/app/run/lucid/tunnels/.onion.env \
    ROTATE_INTERVAL=0 \
    TUNNEL_PORT=7000 \
    TUNNEL_MODE=client \
    TOR_PROXY=tor-proxy:9050 \
    LUCID_ENV=production \
    LUCID_PLATFORM=arm64
# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN
# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).
COPY --from=tunnel-builder --chown=65532:65532 /build/02_network_security/ /app/02_network_security/
COPY --from=tunnel-builder --chown=65532:65532 /build/03_api_gateway/ /app/03_api_gateway/
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/ /app/configs/
COPY --from=tunnel-builder --chown=65532:65532 /build/gui_api_bridge/ /app/gui_api_bridge/
COPY --from=tunnel-builder --chown=65532:65532 /build/server/ /app/server/
COPY --from=tunnel-builder --chown=65532:65532 /build/service_configs/ /app/service_configs/
COPY --from=tunnel-builder --chown=65532:65532 /build/service_mesh/ /app/service_mesh/
COPY --from=tunnel-builder --chown=65532:65532 /build/sessions/ /app/sessions/
# LUCID_RUNTIME_COPY_FROM_BUILD_END

# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).
COPY --from=tunnel-builder --chown=65532:65532 /usr/lib/*/libffi.so* /app/usr/lib/
COPY --from=tunnel-builder --chown=65532:65532 /usr/lib/*/libssl.so* /app/usr/lib/
COPY --from=tunnel-builder --chown=65532:65532 /usr/lib/*/ossl-modules/ /app/usr/lib/
COPY --from=tunnel-builder --chown=65532:65532 /usr/lib/*/libcurl.so* /app/usr/lib/
COPY --from=tunnel-builder --chown=65532:65532 /bin/ /app/bin/
COPY --from=tunnel-builder --chown=65532:65532 /dev/null)"/ /app/dev/null)"/
COPY --from=tunnel-builder --chown=65532:65532 /etc/ssl/ /app/etc/ssl/
COPY --from=tunnel-builder --chown=65532:65532 /usr/ /app/usr/
# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END




# Health check: control port reachability (matches distroless capabilities)
# Uses CONTROL_HOST and CONTROL_PORT environment variables (aligned with tor-proxy service)
# Improved error handling with settimeout and connect_ex per data-chain-design.md
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD ["/usr/bin/python3.11", "-c", "import os, socket; \
host = os.getenv('CONTROL_HOST', 'tor-proxy'); \
port = int(os.getenv('CONTROL_PORT', '9051')); \
s = socket.socket(); \
s.settimeout(2); \
result = s.connect_ex((host, port)); \
s.close(); \
exit(0 if result == 0 else 1)"]

EXPOSE 7000

# Run as non-root (distroless default)
USER 65532:65532


# Use tini for correct signal handling; run Python entrypoint directly (no shell)
# Clear ENTRYPOINT pattern per dockerfile-design.md: tini in ENTRYPOINT, Python in CMD
ENTRYPOINT ["/app/usr/bin/tini", "--"]
CMD ["/usr/bin/python3.11", "/app/tunnels/entrypoint.py"]

# NOTES:
#   Configuration files are expected at:
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.tunnel-tools
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
#   Loaded via docker-compose env_file directive; no hardcoded secrets here.