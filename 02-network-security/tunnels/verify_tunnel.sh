#!/usr/bin/env bash
# Verify onion tunnel reachability via Tor SOCKS5 proxy
# Path: 02-network-security/tunnels/verify_tunnel.sh

set -euo pipefail

HOSTNAME_FILE="/var/lib/tor/hidden_service/hostname"
SOCKS_PROXY="${SOCKS_PROXY:-socks5h://tor-proxy:9050}"

log() { printf '[verify_tunnel] %s\n' "$*"; }

# Read onion address from tor-proxy volume
if [[ ! -f "$HOSTNAME_FILE" ]]; then
  log "ERROR: Onion hostname file not found: $HOSTNAME_FILE"
  exit 1
fi

ONION_ADDR=$(tr -d '\r\n' < "$HOSTNAME_FILE")
ONION_URL="http://${ONION_ADDR}/"

log "Testing reachability of $ONION_URL via SOCKS5 proxy $SOCKS_PROXY"
if curl -s --max-time 20 --proxy "$SOCKS_PROXY" "$ONION_URL" >/dev/null; then
  log "SUCCESS: Onion service is reachable"
  exit 0
else
  log "FAIL: Could not connect to onion service"
  exit 1
fi
