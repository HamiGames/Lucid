# LUCID TOR PROXY - SPEC-4 Stage 0 Beta Sidecar
# Professional multi-platform Tor proxy for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base + inherent Tor system
# Aligned with plan/constants/ requirements
# Configuration: All values from .env.tor-proxy, .env.secrets, .env.foundation via docker-compose
# Build Context: 02-network-security/tor (relative paths used in COPY commands)

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Tor System Builder (Debian 12 with full Tor installation)
# =============================================================================
FROM debian:12-slim AS tor-builder

# Install complete Tor system with all dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        tor \
        tor-geoipdb \
        obfs4proxy \
        tini \
        bash \
        netcat-openbsd \
        xxd \
        gosu \
        ca-certificates \
        dnsutils \
        curl \
        jq \
        coreutils \
        adduser \
        libevent-2.1-7 \
        libssl3 \
        libzstd1 \
        liblzma5 \
        libtinfo6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid \
    && adduser --system --no-create-home --uid 65532 --gid 65532 --group tor-nonroot || true

# Create Tor system directories with proper ownership
RUN install -d -o debian-tor -g debian-tor -m 700 /var/lib/tor \
    && install -d -o debian-tor -g debian-tor -m 755 /run/lucid/onion \
    && install -d -o root -g root -m 755 /usr/local/bin \
    && install -d -o 65532 -g 65532 -m 755 /var/lib/tor-alt || true

# =============================================================================
# STAGE 2: Distroless Runtime with Inherent Tor System
# =============================================================================
FROM gcr.io/distroless/base-debian12:latest

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

# Metadata for professional container management (aligned with constants)
LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless with inherent Tor system for Lucid core support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Tor Proxy" \
      org.opencontainers.image.description="Distroless Tor proxy for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="tor-proxy" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.tor.inherent="true" \
      com.lucid.tor.system="built-in" \
      com.lucid.expose="9050,9051,8888" \
      com.lucid.cluster="foundation"

# Copy complete Tor system from builder
COPY --from=tor-builder /usr/bin/tor /usr/bin/tor
COPY --from=tor-builder /usr/bin/obfs4proxy /usr/bin/obfs4proxy
COPY --from=tor-builder /usr/bin/tini /usr/bin/tini
COPY --from=tor-builder /bin/bash /bin/bash
COPY --from=tor-builder /bin/nc /bin/nc
COPY --from=tor-builder /usr/bin/xxd /usr/bin/xxd
COPY --from=tor-builder /usr/bin/curl /usr/bin/curl
COPY --from=tor-builder /usr/bin/jq /usr/bin/jq
COPY --from=tor-builder /usr/sbin/gosu /usr/sbin/gosu

# Copy Tor system libraries
COPY --from=tor-builder /lib/*/libc.so.6 /lib/
COPY --from=tor-builder /lib/*/libcrypto.so.3 /lib/
COPY --from=tor-builder /lib/*/libssl.so.3 /lib/
COPY --from=tor-builder /lib/*/libevent-2.1.so.7 /lib/
COPY --from=tor-builder /lib/*/libzstd.so.1 /lib/
COPY --from=tor-builder /lib/*/liblzma.so.5 /lib/
COPY --from=tor-builder /lib/*/libz.so.1 /lib/
COPY --from=tor-builder /lib*/ld-linux-*.so.2 /lib64/
COPY --from=tor-builder /lib/*/libtinfo.so.6 /

# Copy Tor system data and GeoIP databases
COPY --from=tor-builder /usr/share/tor /usr/share/tor
COPY --from=tor-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy user and directory structure
COPY --from=tor-builder --chown=debian-tor:debian-tor /var/lib/tor /var/lib/tor
COPY --from=tor-builder --chown=debian-tor:debian-tor /run/lucid/onion /run/lucid/onion
COPY --from=tor-builder /etc/passwd /etc/passwd
COPY --from=tor-builder /etc/group /etc/group

# Copy Lucid Tor configuration and scripts
# Build context: 02-network-security/tor (relative paths)
COPY --chmod=644 torrc /etc/tor/torrc
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 tor-health.sh /usr/local/bin/tor-health
COPY --chmod=755 tor-show-onion.sh /usr/local/bin/tor-show-onion
COPY --chmod=755 scripts/create_ephemeral_onion.sh /usr/local/bin/create-ephemeral-onion

# =============================================================================
# ENVIRONMENT VARIABLES - MINIMAL DEFAULTS ONLY
# All configuration should come from .env.tor-proxy, .env.secrets, .env.foundation
# via docker-compose env_file directive. These are fallback defaults only.
# =============================================================================
# Essential PATH for runtime
ENV PATH=/usr/local/bin:/usr/bin:/bin

# Minimal runtime defaults (will be overridden by docker-compose env_file)
# DO NOT hardcode production values here - use .env files on Pi console
ENV TOR_SOCKS_PORT=9050 \
    TOR_CONTROL_PORT=9051 \
    TOR_DATA_DIR=/var/lib/tor

# Health check aligned with deployment-factors.md standards
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
    CMD ["/bin/bash", "/usr/local/bin/tor-health"]

# Expose all Tor ports (aligned with Port-summary.md)
EXPOSE 9050 9051 8888

# Run as debian-tor user
USER debian-tor
WORKDIR /var/lib/tor

# NOTE: No ENTRYPOINT in Dockerfile - configured in docker-compose.yml for flexibility
# This allows .env.* files to override entrypoint/command via docker-compose
# All configuration values come from:
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.tor-proxy
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
#   - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation