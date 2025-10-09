# LUCID TOR PROXY - SPEC-4 Stage 0 Beta Sidecar
# Professional multi-platform Tor proxy for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base + inherent Tor system

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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid

# Create Tor system directories with proper ownership
RUN install -d -o debian-tor -g debian-tor -m 700 /var/lib/tor \
    && install -d -o debian-tor -g debian-tor -m 755 /run/lucid/onion \
    && install -d -o root -g root -m 755 /usr/local/bin

# =============================================================================
# STAGE 2: Distroless Runtime with Inherent Tor System
# =============================================================================
FROM gcr.io/distroless/base-debian12:latest

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="2.0.0-distroless-tor" \
      description="Distroless with inherent Tor system for Lucid core support" \
      com.lucid.plane="ops" \
      com.lucid.service="tor-proxy" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.tor.inherent="true" \
      com.lucid.tor.system="built-in" \
      com.lucid.expose="9050,9051,8888"

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

# Copy Tor system libraries (architecture-aware paths for multi-platform support)
# Note: distroless handles library path resolution automatically
COPY --from=tor-builder /lib/*/libc.so.6 /lib/
COPY --from=tor-builder /lib/*/libcrypto.so.3 /lib/
COPY --from=tor-builder /lib/*/libssl.so.3 /lib/
COPY --from=tor-builder /lib/*/libevent-2.1.so.7 /lib/
COPY --from=tor-builder /lib/*/libzstd.so.1 /lib/
COPY --from=tor-builder /lib/*/liblzma.so.5 /lib/
COPY --from=tor-builder /lib/*/libz.so.1 /lib/
COPY --from=tor-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy Tor system data and GeoIP databases (inherent Tor network data)
COPY --from=tor-builder /usr/share/tor /usr/share/tor
COPY --from=tor-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy user and directory structure (Tor system integration)
COPY --from=tor-builder --chown=debian-tor:debian-tor /var/lib/tor /var/lib/tor
COPY --from=tor-builder --chown=debian-tor:debian-tor /run/lucid/onion /run/lucid/onion
COPY --from=tor-builder /etc/passwd /etc/passwd
COPY --from=tor-builder /etc/group /etc/group

# Copy Lucid Tor configuration and scripts with distroless-compatible permissions
COPY --chmod=644 torrc /etc/tor/torrc
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 tor-health.sh /usr/local/bin/tor-health
COPY --chmod=755 tor-show-onion.sh /usr/local/bin/tor-show-onion
COPY --chmod=755 scripts/create_ephemeral_onion.sh /usr/local/bin/create-ephemeral-onion

# Environment variables for distroless Tor system
ENV TOR_SOCKS_PORT=9050 \
    TOR_CONTROL_PORT=9051 \
    TOR_DATA_DIR=/var/lib/tor \
    LUCID_ENV=dev \
    ONION_COUNT=5 \
    CREATE_ONION=1 \
    TOR_INHERENT=true \
    PATH=/usr/local/bin:/usr/bin:/bin

# Health check for distroless Tor system
HEALTHCHECK --interval=10s --timeout=5s --start-period=25s --retries=3 \
    CMD ["/usr/local/bin/tor-health"]

# Expose all Tor ports (SPEC-4 compliant)
EXPOSE 9050 9051 8888

# Run as debian-tor user with inherent Tor system
USER debian-tor
WORKDIR /var/lib/tor
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
