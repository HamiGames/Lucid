FROM alpine:3.20

# Install required packages
RUN apk add --no-cache tor tini ca-certificates \
    && getent group tor || addgroup -S tor \
    && getent passwd tor || adduser -S -D -H -s /sbin/nologin -G tor tor \
    && install -d -m 700 -o tor -g tor /var/lib/tor \
    && install -d -m 755 -o tor -g tor /etc/tor

# Copy config and entrypoint
COPY --chown=tor:tor torrc /etc/tor/torrc
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 9050 9051

# Run as tor user
USER tor

# Use tini as init
ENTRYPOINT ["/sbin/tini", "--"]

# Entrypoint script wraps tor
CMD ["/entrypoint.sh"]
