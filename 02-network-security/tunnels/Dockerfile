# LUCID TUNNEL TOOLS - SPEC-4 Stage 0 Network Security (Distroless)
# Builds pickme/lucid-tunnel-tools:latest-arm64
# Compatible with pickme/lucid-tor-proxy:latest-arm64
# Professional tunneling utilities for Pi deployment with distroless security
# Configuration: All values from .env.tunnel-tools, .env.secrets, .env.foundation via docker-compose
# Build Context: 02-network-security/tunnels (relative paths used in COPY commands)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Builder - Python 3.11 Bookworm with minimal tooling
# =============================================================================
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS tunnel-builder

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
      ca-certificates \
      tini \
      bash \
      curl \
      jq \
      netcat-openbsd \
      socat \
      xxd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid \
    && adduser --system --no-create-home --uid 65532 --gid 65532 --group tunnel-nonroot || true

WORKDIR /app

# Create application and data directories with proper ownership
# Following Dockerfile-copy-pattern.md: create directories with marker files (actual content) before COPY
RUN sudo mkdir -p /app/scripts /data/tunnel /var/lib/tunnel /var/log/tunnel /run  \
    && echo "LUCID_TUNNEL_TOOLS_SCRIPTS_DIRECTORY_$(date +%s)" > /app/scripts/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_LIB_DIRECTORY_$(date +%s)" > /var/lib/tunnel/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_LOG_DIRECTORY_$(date +%s)" > /var/log/tunnel/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_RUN_DIRECTORY_$(date +%s)" > /run/.lucid-keep \
    && chown -R 65532:65532 /app /var/lib/tunnel /var/log/tunnel /run

# Copy tunnel application files
# Build context: project root, so we prefix with 02-network-security/tunnels/
COPY 02-network-security/tunnels/entrypoint.py /app/entrypoint.py
COPY 02-network-security/tunnels/tunnel_metrics.py /app/tunnel_metrics.py
COPY 02-network-security/tunnels/tunnel_status.py /app/tunnel_status.py
COPY 02-network-security/tunnels/scripts/ /app/scripts/
COPY 02-network-security/tunnels/config/ /app/config/

RUN chmod +x /app/entrypoint.py || true \
    && chmod +x /app/scripts/*.sh || true \
    && chmod +x /app/tunnel_metrics.py || true \
    && chmod +x /app/tunnel_status.py || true \
    && mkdir -p /app/config \
    && echo "LUCID_TUNNEL_TOOLS_ENTRYPOINT_$(date +%s)" > /app/.lucid-entrypoint-marker

# Builder stage verification: Verify Python and compile entrypoint
RUN python3 --version && \
    which python3 && \
    test -f /app/entrypoint.py && \
    python3 -m py_compile /app/entrypoint.py && \
    python3 -m py_compile /app/tunnel_metrics.py && \
    python3 -m py_compile /app/tunnel_status.py && \
    echo "✅ Builder stage verification passed - All Python files compile successfully"

# =============================================================================
# STAGE 2: Distroless Runtime with Python3 (Debian 12)
# =============================================================================
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

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
ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Copy tini from builder (for proper signal handling)
COPY --from=tunnel-builder /usr/bin/tini /usr/bin/tini

# Copy application and data directories owned by non-root (65532:65532)
COPY --from=tunnel-builder --chown=65532:65532 /app /app
COPY --from=tunnel-builder --chown=65532:65532 /var/lib/tunnel /var/lib/tunnel
COPY --from=tunnel-builder --chown=65532:65532 /var/log/tunnel /var/log/tunnel
COPY --from=tunnel-builder --chown=65532:65532 /run /run

# Runtime verification: Verify entrypoint exists and modules can be imported
RUN ["/usr/bin/python3.11", "-c", "import os, sys; \
sys.path.insert(0, '/app'); \
entrypoint_path = '/app/entrypoint.py'; \
assert os.path.exists(entrypoint_path), f'CRITICAL: Entrypoint not found at {entrypoint_path}'; \
assert os.path.isfile(entrypoint_path), f'CRITICAL: {entrypoint_path} is not a file'; \
import entrypoint; \
import tunnel_metrics; \
import tunnel_status; \
print('✅ All tunnel-tools modules verified')"]

# =============================================================================
# ENVIRONMENT VARIABLES - MINIMAL DEFAULTS ONLY
# All configuration should come from .env.tunnel-tools, .env.secrets, .env.foundation
# via docker-compose env_file directive. These are fallback defaults only.
# NOTE: These defaults align with tor-proxy service from docker-compose.foundation.yml:
#   - tor-proxy container_name: tor-proxy (line 5)
#   - TOR_CONTROL_PORT: 9051 (line 16)
#   - TOR_PROXY_SOCKS_PORT: 9050 (line 15)
# These values are overridden by docker-compose.core.yml environment section (lines 394-405)
# =============================================================================
ENV CONTROL_HOST=tor-proxy \
    CONTROL_PORT=9051 \
    COOKIE_FILE=/var/lib/tor/control_auth_cookie \
    ONION_PORTS="80 api-gateway:8080" \
    WRITE_ENV=/run/lucid/onion/.onion.env \
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
WORKDIR /app

# Use tini for correct signal handling; run Python entrypoint directly (no shell)
# Clear ENTRYPOINT pattern per dockerfile-design.md: tini in ENTRYPOINT, Python in CMD
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/bin/python3.11", "/app/entrypoint.py"]

# NOTES:
#   Configuration files are expected at:
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.tunnel-tools
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
#   Loaded via docker-compose env_file directive; no hardcoded secrets here.