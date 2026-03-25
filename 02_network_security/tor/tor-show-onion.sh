#!/usr/bin/env bash
# Path: 02_network_security/tor/tor-show-onion.sh
# Lists onion service dirs and bootstrap env from tor-health (Dockerfile.tor-proxy-02 paths).
# Installed in image as /app/run/lucid/tor/bin/tor-show-onion.sh
#
# Terminal DIR when exec'd in container: WORKDIR /app (USER debian-tor).

set -euo pipefail

if [[ -d /app/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/bin:"* ]] && PATH="/app/bin:${PATH:-}"
fi
export PATH

BB="${BUSYBOX:-}"
[[ -z "$BB" && -x /app/bin/busybox ]] && BB="/app/bin/busybox"
[[ -z "$BB" && -x /bin/busybox ]] && BB="/bin/busybox"
[[ -z "$BB" ]] && BB="busybox"

# ONION_DIR: hidden-service dirs (lucid_admin, lucid_api, …) — scaffold in Dockerfile under /app/run/lucid/onion
DIR="${ONION_DIR:-/app/run/lucid/onion}"
# Bootstrap env is written by tor-health.sh to TOR_DATA_DIR
FILE="${TOR_DATA_DIR:-/app/run/lucid/tor}/tor_bootstrap.env"

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
