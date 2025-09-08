# Path: 02-network-security/tor/Dockerfile
# Tor Proxy on Alpine (self-contained install)

FROM alpine:3.19

# Install Tor and dependencies
RUN apk add --no-cache tor tini ca-certificates netcat-openbsd bash curl socat xxd \
    # Ensure tor user & group exist (avoid "already exists" errors)
    && addgroup -S tor || true \
    && adduser -S -D -H -s /sbin/nologin -G tor tor || true \
    # Prepare directories
    && install -d -m 700 -o tor -g tor /var/lib/tor \
    && install -d -m 755 -o tor -g tor /etc/tor

# Copy torrc configuration
COPY torrc /etc/tor/torrc
RUN chown tor:tor /etc/tor/torrc

# Expose SOCKS and Control ports
EXPOSE 9050 9051

# Run as tor user
USER tor

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["tor", "-f", "/etc/tor/torrc"]
