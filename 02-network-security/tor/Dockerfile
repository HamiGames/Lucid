# LUCID TOR PROXY - SPEC-4 Stage 0 Beta Sidecar
# Professional multi-platform Tor proxy for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture

FROM alpine:3.22.1

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0" \
      description="Tor proxy service for Lucid core support" \
      com.lucid.plane="ops" \
      com.lucid.service="tor-proxy" \
      com.lucid.expose="9050,9051"

# Security and performance optimizations
RUN apk update && apk upgrade --no-cache \
    && apk add --no-cache \
       tor \
       tini \
       bash \
       netcat-openbsd \
       xxd \
       su-exec \
       ca-certificates \
       bind-tools \
       curl \
       jq \
    && rm -rf /var/cache/apk/* \
    && adduser -D -s /bin/bash lucid

# Tor configuration directory setup
RUN install -d -o tor -g tor -m 700 /var/lib/tor \
    && install -d -o tor -g tor -m 755 /run/lucid/onion \
    && install -d -o root -g root -m 755 /usr/local/bin

# Copy Tor configuration and scripts
COPY torrc /etc/tor/torrc
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY tor-health.sh /usr/local/bin/tor-health
COPY tor-show-onion.sh /usr/local/bin/tor-show-onion
COPY scripts/create_ephemeral_onion.sh /usr/local/bin/create-ephemeral-onion

# Set proper permissions
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/tor-health \
    && chmod +x /usr/local/bin/tor-show-onion \
    && chmod +x /usr/local/bin/create-ephemeral-onion \
    && chown -R tor:tor /var/lib/tor

# Environment variables for configuration
ENV TOR_SOCKS_PORT=9050 \
    TOR_CONTROL_PORT=9051 \
    TOR_DATA_DIR=/var/lib/tor \
    LUCID_ENV=dev

# Health check script
HEALTHCHECK --interval=10s --timeout=5s --start-period=25s --retries=3 \
    CMD /usr/local/bin/tor-health || exit 1

# Expose Tor ports
EXPOSE 9050 9051

# Use non-root user and tini for proper signal handling
USER tor
WORKDIR /var/lib/tor
ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/entrypoint.sh"]