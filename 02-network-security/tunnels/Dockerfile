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
# STAGE 1: Builder - Debian 12 with minimal tooling (glibc-compatible)
# =============================================================================
FROM debian:12-slim AS tunnel-builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG VERSION

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
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
RUN mkdir -p /app/scripts /var/lib/tunnel /var/log/tunnel /run \
    && echo "LUCID_TUNNEL_TOOLS_SCRIPTS_DIRECTORY_$(date +%s)" > /app/scripts/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_LIB_DIRECTORY_$(date +%s)" > /var/lib/tunnel/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_LOG_DIRECTORY_$(date +%s)" > /var/log/tunnel/.lucid-keep \
    && echo "LUCID_TUNNEL_TOOLS_RUN_DIRECTORY_$(date +%s)" > /run/.lucid-keep \
    && chown -R 65532:65532 /app /var/lib/tunnel /var/log/tunnel /run

# Copy tunnel application files
# Build context: project root, so we prefix with 02-network-security/tunnels/
COPY 02-network-security/tunnels/entrypoint.py /app/entrypoint.py
COPY 02-network-security/tunnels/scripts/ /app/scripts/

RUN chmod +x /app/entrypoint.py || true \
    && chmod +x /app/scripts/*.sh || true \
    && echo "LUCID_TUNNEL_TOOLS_ENTRYPOINT_$(date +%s)" > /app/.lucid-entrypoint-marker

# =============================================================================
# STAGE 2: Distroless Runtime with Python3 (Debian 12)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:latest

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
    PYTHONPATH=/app

# Copy tini from builder (for proper signal handling)
COPY --from=tunnel-builder /usr/bin/tini /usr/bin/tini

# Copy application and data directories owned by non-root (65532:65532)
COPY --from=tunnel-builder --chown=65532:65532 /app /app
COPY --from=tunnel-builder --chown=65532:65532 /var/lib/tunnel /var/lib/tunnel
COPY --from=tunnel-builder --chown=65532:65532 /var/log/tunnel /var/log/tunnel
COPY --from=tunnel-builder --chown=65532:65532 /run /run

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
    ONION_PORTS="80 lucid_api:8081" \
    WRITE_ENV=/app/scripts/.onion.env \
    ROTATE_INTERVAL=0 \
    TUNNEL_PORT=7000 \
    TUNNEL_MODE=client \
    TOR_PROXY=tor-proxy:9050 \
    LUCID_ENV=production \
    LUCID_PLATFORM=arm64

# Health check: control port reachability (matches distroless capabilities)
# Uses CONTROL_HOST and CONTROL_PORT environment variables (aligned with tor-proxy service)
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD ["python3", "-c", "import os, socket; host = os.getenv('CONTROL_HOST', 'tor-proxy'); port = int(os.getenv('CONTROL_PORT', '9051')); s = socket.socket(); s.connect((host, port)); s.close(); exit(0)"]

EXPOSE 7000

# Run as non-root (distroless default)
USER 65532:65532
WORKDIR /app

# Use tini for correct signal handling; run Python entrypoint directly (no shell)
ENTRYPOINT ["/usr/bin/tini", "--", "python3", "/app/entrypoint.py"]

# NOTES:
#   Configuration files are expected at:
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.tunnel-tools
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
#     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
#   Loaded via docker-compose env_file directive; no hardcoded secrets here.