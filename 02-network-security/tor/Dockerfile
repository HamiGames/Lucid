# Path: 02-network-security/tor/Dockerfile
FROM alpine:3.20

# Install Tor + tini + required tools (netcat for ControlPort, xxd for cookie auth)
RUN apk add --no-cache tor tini ca-certificates busybox-extras xxd \
    && getent group tor || addgroup -S tor \
    && getent passwd tor || adduser -S -D -H -s /sbin/nologin -G tor tor \
    && install -d -m 700 -o tor -g tor /var/lib/tor \
    && install -d -m 755 -o tor -g tor /etc/tor \
    && chown -R tor:tor /var/lib/tor

# Copy Tor configuration and entrypoint
COPY --chown=tor:tor torrc /etc/tor/torrc
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
RUN chown -R tor:tor /var/lib/tor
# Expose SOCKS and ControlPort
EXPOSE 9050 9051

# Run as tor user
USER tor

# Use tini as init
ENTRYPOINT ["/sbin/tini", "--"]

# Entrypoint handles Tor startup and onion management
CMD ["/entrypoint.sh"]
