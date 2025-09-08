#!/usr/bin/env bash
# Path: 02-network-security/tunnels/entrypoint.sh
# Tunnel container entrypoint — validates onion reachability

set -euo pipefail

log() { printf '[tunnel] %s\n' "$*"; }

: "${ONION:?ONION address not set}"
: "${API_ENDPOINT:?API endpoint not set}"
: "${SOCKS_PROXY:?SOCKS proxy not set}"

log "Starting tunnel container..."
log "ONION: $ONION"
log "API_ENDPOINT: $API_ENDPOINT"
log "SOCKS_PROXY: $SOCKS_PROXY"

while true; do
  # Validate onion service reachability
  if curl -s --socks5-hostname "$SOCKS_PROXY" "$ONION" >/dev/null 2>&1; then
    log "SUCCESS: Onion $ONION reachable via $SOCKS_PROXY"
  else
    log "FAIL: Onion $ONION not reachable"
  fi

  # Validate API endpoint internally
  if curl -s "$API_ENDPOINT/health" | grep -q '"status":'; then
    log "SUCCESS: API at $API_ENDPOINT is healthy"
  else
    log "FAIL: API $API_ENDPOINT failed health check"
  fi

  sleep 15
done
