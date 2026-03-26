#!/usr/bin/env bash
# Path: 02_network_security/tor/tor-show-onion.sh
# Aligned with: 02_network_security/tor/Dockerfile.tor-proxy-02 (distroless tor-proxy-02).
# Installed in image as: /app/run/lucid/tor/bin/tor-show-onion.sh
#
# Runtime: WORKDIR /app, USER debian-tor; bootstrap state from tor-health.sh (same TOR_DATA_DIR logic
# as tor_entrypoint.sh). Ports registry: ports.txt — tor_socks 9050 (TOR_SOCKS_PORT), tor_control 9051
# (TOR_CONTROL_PORT); Dockerfile EXPOSE also includes 8888 (optional HTTP/metrics).

set -euo pipefail

if [[ -d /app/usr/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/usr/bin:"* ]] && PATH="/app/usr/bin:${PATH:-}"
fi
if [[ -d /app/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/bin:"* ]] && PATH="/app/bin:${PATH:-}"
fi
export PATH

BB="${BUSYBOX:-}"
[[ -z "$BB" && -x /app/bin/busybox ]] && BB="/app/bin/busybox"
[[ -z "$BB" && -x /bin/busybox ]] && BB="/bin/busybox"
[[ -z "$BB" ]] && BB="busybox"

# Paths match Dockerfile.tor-proxy-02 COPY layout under /app (image ENV may set TOR_DATA_DIR=/run/lucid/tor;
# on-disk tree from the image is under /app/run — normalize if the env path is missing).
TOR_DATA_DIR="${TOR_DATA_DIR:-/app/run/lucid/tor}"
if [[ ! -d "$TOR_DATA_DIR" ]] && [[ -d "/app/run/lucid/tor" ]]; then
  TOR_DATA_DIR="/app/run/lucid/tor"
fi

# Hidden-service parent dir (lucid_admin, lucid_api, … scaffold under /app/run/lucid/onion in image).
DIR="${TOR_ONION_SERVICE_DIR:-${ONION_DIR:-/app/run/lucid/onion}}"
FILE="${TOR_DATA_DIR}/tor_bootstrap.env"

if [[ -d "$DIR" ]]; then
  "${BB}" ls -l "$DIR"
else
  echo "[info] $DIR does not exist"
  exit 0
fi

if [[ -f "$FILE" ]]; then
  echo "--- tor_bootstrap.env (path: $FILE) ---"
  "${BB}" head -n 200 "$FILE"
else
  echo "[info] $FILE not found"
fi
