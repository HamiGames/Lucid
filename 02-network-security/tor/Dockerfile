# LUCID TOR PROXY - SPEC-4 Stage 0 Beta Sidecar
# Professional multi-platform Tor proxy for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base + inherent Tor system
# Configuration: All values from .env.tor-proxy, .env.secrets, .env.foundation via docker-compose
# Build Context: 02-network-security/tor (relative paths used in COPY commands)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Tor System Builder (Debian 12 with full Tor installation)
# =============================================================================
FROM debian:12-slim AS tor-builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM

RUN apt-get update && apt-get install -y --no-install-recommends \
        tor \
        tor-geoipdb \
        obfs4proxy \
        tini \
        bash \
        busybox \
        coreutils \
        netcat-openbsd \
        xxd \
        gosu \
        ca-certificates \
        dnsutils \
        curl \
        jq \
        adduser \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid \
    && adduser --system --no-create-home --uid 65532 --gid 65532 --group tor-nonroot || true

RUN install -d -o debian-tor -g debian-tor -m 700 /var/lib/tor \
    && install -d -o debian-tor -g debian-tor -m 755 /run/lucid/onion \
    && install -d -o root -g root -m 755 /usr/local/bin \
    && install -d -o 65532 -g 65532 -m 755 /var/lib/tor-alt || true

# =============================================================================
# STAGE 2: Distroless Runtime with Inherent Tor System
# =============================================================================
FROM gcr.io/distroless/base-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

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

ENV PATH=/usr/local/bin:/usr/bin:/bin

# Core binaries and tools
COPY --from=tor-builder /usr/bin/tor /usr/bin/tor
COPY --from=tor-builder /usr/bin/obfs4proxy /usr/bin/obfs4proxy
COPY --from=tor-builder /usr/bin/tini /usr/bin/tini
COPY --from=tor-builder /bin/bash /bin/bash
COPY --from=tor-builder /bin/busybox /bin/busybox
COPY --from=tor-builder /bin/mkdir /bin/mkdir
COPY --from=tor-builder /bin/sleep /bin/sleep
COPY --from=tor-builder /bin/chmod /bin/chmod
COPY --from=tor-builder /bin/chown /bin/chown
COPY --from=tor-builder /bin/rm /bin/rm
COPY --from=tor-builder /usr/bin/nc /usr/bin/nc
COPY --from=tor-builder /usr/bin/xxd /usr/bin/xxd
COPY --from=tor-builder /usr/bin/curl /usr/bin/curl
COPY --from=tor-builder /usr/bin/jq /usr/bin/jq
COPY --from=tor-builder /usr/sbin/gosu /usr/sbin/gosu

# Required libraries
COPY --from=tor-builder /lib/*/libc.so.6 /lib/
COPY --from=tor-builder /lib/*/libcrypto.so.3 /lib/
COPY --from=tor-builder /lib/*/libssl.so.3 /lib/
COPY --from=tor-builder /lib/*/libevent-2.1.so.7 /lib/
COPY --from=tor-builder /lib/*/libzstd.so.1 /lib/
COPY --from=tor-builder /lib/*/liblzma.so.5 /lib/
COPY --from=tor-builder /lib/*/libz.so.1 /lib/
COPY --from=tor-builder /lib/*/libtinfo.so.6 /lib/
COPY --from=tor-builder /lib/*/libsystemd.so.0 /lib/
COPY --from=tor-builder /lib/*/libselinux.so.1 /lib/
COPY --from=tor-builder /lib/*/libcap.so.2 /lib/
COPY --from=tor-builder /lib/*/libnsl.so.1 /lib/
COPY --from=tor-builder /lib/*/libcrypt.so.1 /lib/
COPY --from=tor-builder /lib*/ld-linux-*.so.2 /lib64/

# Tor data/config
COPY --from=tor-builder /usr/share/tor /usr/share/tor
COPY --from=tor-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=tor-builder --chown=debian-tor:debian-tor /var/lib/tor /var/lib/tor
COPY --from=tor-builder --chown=debian-tor:debian-tor /run/lucid/onion /run/lucid/onion
COPY --from=tor-builder /etc/passwd /etc/passwd
COPY --from=tor-builder /etc/group /etc/group

# Ensure /run exists for pid file
RUN mkdir -p /run && chown debian-tor:debian-tor /run

# Lucid scripts
COPY --chmod=644 torrc /etc/tor/torrc
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 tor-health.sh /usr/local/bin/tor-health
COPY --chmod=755 tor-show-onion.sh /usr/local/bin/tor-show-onion
COPY --chmod=755 scripts/create_ephemeral_onion.sh /usr/local/bin/create-ephemeral-onion

ENV TOR_SOCKS_PORT=9050 \
    TOR_CONTROL_PORT=9051 \
    TOR_DATA_DIR=/var/lib/tor

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
    CMD ["/bin/bash", "/usr/local/bin/tor-health"]

EXPOSE 9050 9051 8888

USER debian-tor
WORKDIR /var/lib/tor