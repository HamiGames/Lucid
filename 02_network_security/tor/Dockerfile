# LUCID TOR PROXY - SPEC-4 Stage 0 Beta Sidecar
# Distroless Tor proxy for Lucid (ARM64), aligned with project spin-up
# Build Context: project root (same as tunnel-tools)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# STAGE 1: Tor System Builder (Debian 12 with full Tor installation)
# =============================================================================
FROM debian:12-slim AS tor-builder
WORKDIR /build
ARG BUILDPLATFORM
ARG TARGETPLATFORM

ENV DEBIAN_FRONTEND=noninteractive

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
      openssl \
      ssl-cert \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && adduser --disabled-password --shell /bin/bash --gecos "" lucid \
    && adduser --system --no-create-home --uid 65532 --gid 65532 --group tor-nonroot || true

# Create runtime directories with correct ownership (including /run to avoid RUN in distroless)
RUN install -d -o debian-tor -g debian-tor -m 700 /var/lib/tor && \
    install -d -o debian-tor -g debian-tor -m 755 /run && \
    install -d -o debian-tor -g debian-tor -m 755 /run/lucid/onion && \
    install -d -o 65532       -g 65532     -m 755 /usr/local/bin && \
    install -d -o 65532       -g 65532     -m 755 /etc/tor && \
    install -d -o 65532 -g 65532 -m  755  /usr/local/share/ca-certificates && \
    install -d -o 65532 -g 65532 -m  755  /usr/local/sbin && \
    install -d -o 65532 -g 65532 -m  755  /usr/local/lib && \
    install -d -o 65532 -g 65532 -m  755  /usr/local/bin && \
    install -d -o 65532 -g 65532 -m  755  /usr/bin && \
    install -d -o 65532 -g 65532 -m  755  /usr/sbin && \
    install -d -o 65532 -g 65532 -m  755  /usr/share/tor && \
    install -d -o 65532 -g 65532 -m  755  /etc/ssl/certs && \
    install -d -o 65532 -g 65532 -m  755  /etc/tor/tunnels && \
    install -d -o 65532 -g 65532 -m  755  /tmp/lucid/tor && \
    install -d -o 65532 -g 65532 -m  755  /app/tor && \
    install -d -o 65532 -g 65532 -m  755  /run/lucid/tor && \
    install -d -o 65532 -g 65532 -m  755  /run/lucid/onion && \
    install -d -o 65532 -g 65532 -m  755  /run/lucid/tor/lucid && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_admin && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_vm && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_node && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_blockchain && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_governance && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_payment && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_session && \
    install -d -o 65532 -g 65532 -m  755  /var/lib/tor/lucid_rdp && \
    mkdir -p ./tor ./tor/scripts ./tunnels ./tunnels/scripts  && \
    printf "LUCID_TOR_PROXY_ENTRYPOINT_$(date +%s)" > ./tor/.keep && \
    touch ./tor/.keep && \
    printf "LUCID_TOR_PROXY_SCRIPTS_DIRECTORY_$(date +%s)" > ./tor/scripts/.keep && \
    touch ./tor/scripts/.keep && \
    printf "LUCID_TOR_PROXY_TUNNELS_DIRECTORY_$(date +%s)" > ./tunnels/.keep && \
    touch ./tunnels/.keep && \
    printf "LUCID_TOR_PROXY_TUNNELS_SCRIPTS_DIRECTORY_$(date +%s)" > ./tunnels/scripts/.keep && \
    touch ./tunnels/scripts/.keep && \
    chown -R 65532:65532 ./tor ./tor/scripts ./tunnels ./tunnels/scripts && \
    chmod +x ./tor/.keep ./tor/scripts/.keep ./tunnels/.keep ./tunnels/scripts/.keep


COPY 02_network_security/tor/entrypoint.sh ./tor/entrypoint.sh
COPY 02_network_security/tor/tor-entrypoint.sh ./tor/tor-entrypoint.sh
COPY 02_network_security/tor/t_entrypoint.sh ./tor/t_entrypoint.sh
COPY 02_network_security/tor/tor-health.sh ./tor/tor-health.sh
COPY 02_network_security/tor/tor-show-onion.sh ./tor/tor-show-onion.sh
COPY config/tor/torrc ./tor/torrc



COPY 02_network_security/tor/scripts/create_ephemeral_onion.sh ./tor/scripts/create_ephemeral_onion.sh
COPY 02_network_security/tor/scripts/start_tor.sh ./tor/scripts/start_tor.sh
COPY 02_network_security/tor/scripts/check_tor_bootstrap.sh ./tor/scripts/check_tor_bootstrap.sh
COPY 02_network_security/tor/scripts/create_dynamic_onion.sh ./tor/scripts/create_dynamic_onion.sh

COPY 02_network_security/tunnels/scripts/ ./tunnels/scripts/



RUN echo "=== Checking if tor/ was copied ===" && \
    ls -la ./tor/ && \
    ls -d ./tor/* && \
    chmod +x ./tor/* && \
    echo "tor/ was copied"

COPY 02_network_security/tor/scripts/ ./tor/scripts/
RUN echo "=== Checking if tor/scripts/ was copied ===" && \
    ls -la ./tor/scripts/ && \
    ls -d ./tor/scripts/* && \
    chmod +x ./tor/scripts/* && \
    echo "tor/scripts/ was copied"

#=============================================================================
# STAGE 2: Distroless Runtime with Inherent Tor System
# =============================================================================
FROM gcr.io/distroless/base-debian12:latest
WORKDIR /app

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Tor proxy for Lucid project" \
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

ENV PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:/app/etc:/app/usr/share:/app/lib:$PATH

# Core binaries and helpers
COPY --from=tor-builder /build/usr/bin/tor/         /app/usr/bin/tor/
COPY --from=tor-builder /build/usr/bin/obfs4proxy/  /app/usr/bin/obfs4proxy/
COPY --from=tor-builder /build/usr/bin/tini/        /app/usr/bin/tini/
COPY --from=tor-builder /build/usr/sbin/gosu/       /app/usr/sbin/gosu/
COPY --from=tor-builder /build/bin/bash/            /app/bin/bash/
COPY --from=tor-builder /build/bin/busybox/         /app/bin/busybox/
COPY --from=tor-builder /build/bin/mkdir/           /app/bin/mkdir/
COPY --from=tor-builder /build/bin/sleep/           /app/bin/sleep/
COPY --from=tor-builder /build/bin/tail/            /app/bin/tail/
COPY --from=tor-builder /build/bin/chmod/           /app/bin/chmod/
COPY --from=tor-builder /build/bin/chown/           /app/bin/chown/
COPY --from=tor-builder /build/bin/rm/              /app/bin/rm/
COPY --from=tor-builder /build/usr/bin/nc/          /app/usr/bin/nc/
COPY --from=tor-builder /build/usr/bin/xxd/         /app/usr/bin/xxd/
COPY --from=tor-builder /build/usr/bin/curl/        /app/usr/bin/curl/
COPY --from=tor-builder /build/usr/bin/jq/          /app/usr/bin/jq/

# Required libraries (include systemd/selinux/cap and loader)
COPY --from=tor-builder /lib/*/libc.so.6         /app/lib/
COPY --from=tor-builder /lib/*/libcrypto.so.3   /app/lib/
COPY --from=tor-builder /lib/*/libssl.so.3      /app/lib/
COPY --from=tor-builder /lib/*/libevent-2.1.so.7 /app/lib/
COPY --from=tor-builder /lib/*/libzstd.so.1     /app/lib/
COPY --from=tor-builder /lib/*/liblzma.so.5     /app/lib/
COPY --from=tor-builder /lib/*/libz.so.1        /app/lib/
COPY --from=tor-builder /lib/*/libtinfo.so.6    /app/lib/
COPY --from=tor-builder /lib/*/libsystemd.so.0  /app/lib/
COPY --from=tor-builder /lib/*/libselinux.so.1  /app/lib/
COPY --from=tor-builder /lib/*/libcap.so.2      /app/lib/
COPY --from=tor-builder /lib/*/libnsl.so.1      /app/lib/
COPY --from=tor-builder /lib/*/libcrypt.so.1    /app/lib/
# Dynamic linker and arch-specific libs for ARM64 (required by coreutils/tor)
COPY --from=tor-builder /lib/ld-linux-aarch64.so.1 /app/lib/ld-linux-aarch64.so.1
COPY --from=tor-builder /lib/aarch64-linux-gnu     /app/lib/aarch64-linux-gnu

# Bring in /usr/lib to satisfy Debian dynamic deps (libselinux, libcap, etc.)
COPY --from=tor-builder /usr/lib /app/usr/lib

# Ensure /etc/tor directory exists in runtime and is traversable
COPY --from=tor-builder /etc/tor /app/etc/tor

# Tor data/config and system files
COPY --from=tor-builder /usr/share/tor                                 /app/usr/share/tor
COPY --from=tor-builder /etc/ssl/certs/ca-certificates.crt             /app/etc/ssl/certs/ca-certificates.crt
COPY --from=tor-builder --chown=debian-tor:debian-tor /var/lib/tor     /app/var/lib/tor
COPY --from=tor-builder --chown=debian-tor:debian-tor /run             /app/run
COPY --from=tor-builder --chown=debian-tor:debian-tor /run/lucid/onion /app/run/lucid/onion
COPY --from=tor-builder /etc/passwd                                    /app/etc/passwd
COPY --from=tor-builder /etc/group                                     /app/etc/group

# Lucid scripts and tor configuration (torrc baked into image)
# Build context: project root, so we prefix with 02_network_security/tor/
COPY --chmod=644 --chown=debian-tor:debian-tor --from=tor-builder /build/tor/torrc                                  /app/etc/tor/torrc
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/entrypoint.sh                          /app/usr/local/bin/entrypoint.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/tor-health.sh                          /app/usr/local/bin/tor-health.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/tor-show-onion.sh                      /app/usr/local/bin/tor-show-onion.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/scripts/create_ephemeral_onion.sh      /app/usr/local/bin/create-ephemeral-onion.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/scripts/create_dynamic_onion.sh      /app/usr/local/bin/create-dynamic-onion.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/scripts/check_tor_bootstrap.sh      /app/usr/local/bin/check-tor-bootstrap.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tor/scripts/start_tor.sh      /app/usr/local/bin/start-tor.sh
COPY --chmod=755 --chown=65532:65532 --from=tor-builder /build/tunnels/scripts/ /app/usr/local/bin/scripts/

# Minimal defaults (overridden by env files/compose)
ENV TOR_SOCKS_PORT=9050 \
    TOR_CONTROL_PORT=9051 \
    TOR_DATA_DIR=/var/lib/tor \
    PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:/app/etc:/app/usr/share:$PATH \
    LD_LIBRARY_PATH=/app/lib:/app/usr/lib:/app/var/lib:/app/usr/local/lib:$LD_LIBRARY_PATH
    TOR_PROXY_SERVICE=tor-proxy 

# Healthcheck uses /bin/bash copied above
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
  CMD ["/app/bin/bash", "/app/usr/local/bin/tor-health"]

# Expose ports (SOCKS, Control, optional HTTP)
EXPOSE 9050 9051 8888

# Run as debian-tor (present from builder /etc/passwd)
USER debian-tor


# NOTE:
# - No ENTRYPOINT/CMD set intentionally to allow compose or manual `--entrypoint` to control startup.
# - For manual runs: add `--entrypoint /usr/local/bin/entrypoint.sh`.