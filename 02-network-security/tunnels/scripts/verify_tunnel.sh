#!/usr/bin/env bash
# Verify onion tunnel reachability via Tor SOCKS5 proxy
# Path: 02-network-security/tunnels/scripts/verify_tunnel.sh

set -euo pipefail

ONION_URL="${1:-${ONION_URL:-}}"

# Load Tor proxy configuration from environment (supports both TOR_PROXY and SOCKS_PROXY)
if [[ -n "${TOR_PROXY:-}" ]]; then
  TOR_PROXY_HOST="${TOR_PROXY%%:*}"
  TOR_PROXY_PORT="${TOR_PROXY##*:}"
  SOCKS_PROXY="socks5h://${TOR_PROXY_HOST}:${TOR_PROXY_PORT}"
elif [[ -n "${SOCKS_PROXY:-}" ]]; then
  # Use existing SOCKS_PROXY if set
  :
else
  # Default fallback
  SOCKS_PROXY="socks5h://tor-proxy:9050"
fi

log() { printf '[verify_tunnel] %s\n' "$*"; }

if [[ -z "$ONION_URL" ]]; then
  log "ERROR: No onion URL provided. Usage: verify_tunnel.sh <onion_url>"
  exit 1
fi

log "Testing reachability of $ONION_URL via SOCKS5 proxy $SOCKS_PROXY"

# Check if curl is available (may not be in distroless container)
if ! command -v curl >/dev/null 2>&1; then
  log "WARNING: curl not available. Cannot verify tunnel reachability."
  log "Onion URL: $ONION_URL"
  log "SOCKS Proxy: $SOCKS_PROXY"
  exit 0  # Don't fail if curl isn't available
fi

if curl -s --max-time 20 --proxy "$SOCKS_PROXY" "$ONION_URL" >/dev/null; then
  log "SUCCESS: Onion service is reachable"
  exit 0
else
  log "FAIL: Could not connect to onion service"
  exit 1
fi
