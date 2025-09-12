# Tunnel tools — Alpine pinned to 3.22.1 (no pip; use distro packages)
FROM alpine:3.22.1

# OS + Python + required tools
#   - py3-requests provides requests
#   - py3-pysocks provides the "socks" module used by requests[socks]
RUN apk update && apk upgrade --no-cache \
 && apk add --no-cache \
      python3 py3-requests py3-pysocks \
      bash netcat-openbsd xxd curl socat bind-tools tini ca-certificates \
 && addgroup -S app && adduser -S -D -H -s /sbin/nologin -G app app

WORKDIR /app

# (no pip install step needed anymore)

# App files
COPY entrypoint.sh /app/entrypoint.sh
COPY scripts/create_ephemeral_onion.sh /app/scripts/create_ephemeral_onion.sh
RUN chmod +x /app/entrypoint.sh /app/scripts/create_ephemeral_onion.sh

USER app

EXPOSE 7000
ENTRYPOINT ["/sbin/tini","--","/app/entrypoint.sh"]
