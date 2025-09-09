# Lucid RDP — tor-proxy container (Alpine, arm64-friendly)

FROM alpine:3.20

# Tools needed by entrypoint + healthcheck
# - tor: the daemon
# - tini: proper signal handling as PID 1
# - netcat-openbsd: for nc in healthchecks/control calls
# - bash: entrypoint is a bash script
# - xxd: to hex-encode the auth cookie
# - su-exec: drop privileges to tor user
# - ca-certificates: sane defaults
RUN apk add --no-cache tor tini ca-certificates netcat-openbsd bash xxd su-exec \
    && addgroup -S tor || true \
    && adduser -S -D -H -s /sbin/nologin -G tor tor || true \
    && install -d -m 700 -o tor -g tor /var/lib/tor \
    && install -d -m 755 -o tor -g tor /etc/tor \
    && install -d -m 755 /scripts \
    && chown tor:tor /scripts

# Config + entrypoint
COPY --chown=tor:tor torrc /etc/tor/torrc
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 9050 9051

# Use tini as PID 1
ENTRYPOINT ["/sbin/tini","--"]
CMD ["/usr/local/bin/entrypoint.sh"]
