# Lucid RDP — Tor proxy image
# Path: 02-network-security/tor/Dockerfile

FROM alpine:3.20

# Install required packages
RUN apk add --no-cache tor tini ca-certificates \
    && getent group tor || addgroup -S tor \
    && getent passwd tor || adduser -S -D -H -s /sbin/nologin -G tor tor \
    && install -d -m 700 -o tor -g tor /var/lib/tor \
    && install -d -m 755 -o tor -g tor /etc/tor

# Copy torrc
COPY --chown=tor:tor torrc /etc/tor/torrc

# Expose SOCKS and Control ports
EXPOSE 9050 9051

USER tor

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["tor", "-f", "/etc/tor/torrc"]
