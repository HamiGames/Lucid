#!/usr/bin/env bash
# Verify onion tunnel reachability via Tor SOCKS5 proxy
# Path: 02-network-security/tunnels/verify_tunnel.sh

set -euo pipefail

ONION_URL="${1:-${ONION_URL:-}}"
SOCKS_PROXY="${SOCKS_PROXY:-socks5h://tor-proxy:9050}"

log() { printf '[verify_tunnel] %s\n' "$*"; }

if [[ -z "$ONION_URL" ]]; then
  log "ERROR: No onion URL provided. Usage: verify_tunnel.sh <onion_url>"
  exit 1
fi

log "Testing reachability of $ONION_URL via SOCKS5 proxy $SOCKS_PROXY"
if curl -s --max-time 20 --proxy "$SOCKS_PROXY" "$ONION_URL" >/dev/null; then
  log "SUCCESS: Onion service is reachable"
  exit 0
else
  log "FAIL: Could not connect to onion service"
  exit 1
fi
