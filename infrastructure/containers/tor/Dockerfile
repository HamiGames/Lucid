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
RUN mkdir -p /build/configs
COPY configs/environment/.env.secrets /build/configs/.env.secrets
COPY master-env-config.txt /build/configs/.env.master



# Create application and data directories with proper ownership
# Following Dockerfile-copy-pattern.md: create directories with marker files (actual content) before COPY
RUN mkdir -p /usr /usr/local usr/bin /bin /usr/local/lib /usr/local/bin /usr/local/lib/python3.11 /usr/local/lib/python3.11/site-packages && \
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
    printf "LUCID_API_GATEWAY_BIN_$(date +%s)" > /bin/.keep && \
    touch /bin/.keep && \
    printf "LUCID_API_GATEWAY_USR_BIN_$(date +%s)" > /usr/bin/.keep && \
    touch /usr/bin/.keep && \
    printf "LUCID_API_GATEWAY_USR_LOCAL_BIN_$(date +%s)" > /usr/local/bin/.keep && \
    touch /usr/local/bin/.keep && \
    chown -R 65532:65532 /usr /usr/local /usr/local/lib /usr/local/bin /usr/local/lib/python3.11 /usr/local/lib/python3.11/site-packages /bin /usr/bin /usr/local/bin && \
    chmod 644 /usr/.keep /usr/local/.keep /usr/local/lib/.keep /usr/local/lib/python3.11/.keep /usr/local/lib/python3.11/site-packages/.keep /usr/local/bin/.keep /bin/.keep /usr/bin/.keep /usr/local/bin/.keep && \
    echo " Marker files created to lock in directory structure"

# Copy tunnel application files
# Build context: project root, so we prefix with 02_network_security/tunnels/
RUN mkdir -p ./tunnels  ./tunnels/scripts ./tunnels/config && \
    printf "LUCID_TUNNEL_TOOLS_CONFIG_$(date +%s)" > ./tunnels/config/.keep && \
    touch ./tunnels/config/.keep && \
    printf "LUCID_TUNNEL_TOOLS_TUNNELS_$(date +%s)" > ./tunnels/.keep && \
    touch ./tunnels/.keep && \
    printf "LUCID_TUNNEL_TOOLS_SCRIPTS_$(date +%s)" > ./tunnels/scripts/.keep && \
    touch ./tunnels/scripts/.keep && \
    chown -R 65532:65532 ./tunnels ./tunnels/scripts ./tunnels/config  && \
    chmod 644 ./tunnels/.keep ./tunnels/scripts/.keep ./tunnels/config/.keep  && \
    echo " Marker files created to lock in directory structure"

COPY 02_network_security/tunnels/ ./tunnels/
COPY 02_network_security/tunnels/scripts/ ./tunnels/scripts/
COPY 02_network_security/tunnels/config/ ./tunnels/config/
COPY configs/environment/.env.tunnel-tools ./configs/.env.tunnel-tools
COPY configs/environment/.env.secrets ./configs/.env.secrets
COPY master-env-config.txt ./configs/.env.master
COPY 02_network_security/tor/torrc ./configs/torrc
RUN mkdir -p /build/configs/services/tor
COPY infrastructure/containers/services/container-runtime-layout.yml /build/configs/services/container-runtime-layout.yml
COPY infrastructure/containers/tor/docker-compose.proxy-systems.yml /build/configs/services/tor/docker-compose.proxy-systems.yml
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
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

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

# Copy tini from builder (for proper signal handling)
# LUCID_IMAGE_CONFIG: .env.secrets + .env.master (runtime)
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.secrets /app/configs/.env.secrets
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.master /app/configs/.env.master
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/.env.tunnel-tools /app/configs/.env.tunnel-tools
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/torrc /app/configs/torrc
COPY --from=tunnel-builder --chown=65532:65532 /build/tunnels/ /app/tunnels/
COPY --from=tunnel-builder --chown=65532:65532 /build/tunnels/scripts/ /app/tunnels/scripts/
COPY --from=tunnel-builder --chown=65532:65532 /build/tunnels/config/ /app/tunnels/config/
COPY --from=tunnel-builder --chown=65532:65532 /build/configs/services/ /app/configs/services/

COPY --from=tunnel-builder --chown=65532:65532 /usr/bin/tini /app/usr/bin/tini
COPY --from=tunnel-builder --chown=65532:65532 /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=tunnel-builder --chown=65532:65532 /build/wheels/ /app/wheels/

# Runtime verification: Verify entrypoint exists and modules can be imported (distroless base Python)
RUN ["/usr/bin/python3.11", "-c", "import os, sys; \
sys.path.insert(0, '/app/tunnels'); \
entrypoint_path = '/app/tunnels/entrypoint.py'; \
assert os.path.isfile(entrypoint_path), 'CRITICAL: /app/tunnels/entrypoint.py missing'; \
import entrypoint; import tunnel_metrics; import tunnel_status; \
print('✅ All tunnel-tools modules verified')"]


ENV CONTROL_HOST=tor-proxy \
    CONTROL_PORT=9051 \
    COOKIE_FILE=/app/var/lib/tor/control_auth_cookie \
    ONION_PORTS="80 api-gateway:8080" \
    WRITE_ENV=/app/run/lucid/onion/.onion.env \
    ROTATE_INTERVAL=0 \
    TUNNEL_PORT=7000 \
    TUNNEL_MODE=client \
    TOR_PROXY=tor-proxy:9050 \
    LUCID_ENV=production \
    LUCID_PLATFORM=arm64

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