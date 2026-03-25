#!/usr/bin/env bash
# Verify onion tunnel reachability via Tor SOCKS5 proxy
# Path: 02_network_security/tunnels/scripts/verify_tunnel.sh
# Defaults: TOR_PROXY from 02_network_security/tunnels/Dockerfile (tor-proxy:9050)

set -euo pipefail

ONION_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --onion)
      ONION_URL="$2"
      shift 2
      ;;
    --url)
      ONION_URL="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: verify_tunnel.sh [--onion URL] [URL]"
      exit 0
      ;;
    *)
      ONION_URL="${ONION_URL:-$1}"
      shift
      ;;
  esac
done

if [[ -n "${TOR_PROXY:-}" ]]; then
  TOR_PROXY_HOST="${TOR_PROXY%%:*}"
  TOR_PROXY_PORT="${TOR_PROXY##*:}"
  SOCKS_PROXY="socks5h://${TOR_PROXY_HOST}:${TOR_PROXY_PORT}"
elif [[ -n "${SOCKS_PROXY:-}" ]]; then
  :
else
  SOCKS_PROXY="socks5h://tor-proxy:9050"
fi

log() { printf '[verify_tunnel] %s\n' "$*"; }

if [[ -z "$ONION_URL" ]]; then
  log "ERROR: No onion URL. Usage: verify_tunnel.sh [--onion http://xxx.onion/] [URL]"
  exit 1
fi

log "Testing reachability of $ONION_URL via SOCKS5 proxy $SOCKS_PROXY"

if ! command -v curl >/dev/null 2>&1; then
  log "WARNING: curl not available. Cannot verify tunnel reachability."
  log "Onion URL: $ONION_URL"
  log "SOCKS Proxy: $SOCKS_PROXY"
  exit 0
fi

if curl -s --max-time 20 --proxy "$SOCKS_PROXY" "$ONION_URL" >/dev/null; then
  log "SUCCESS: Onion service is reachable"
  exit 0
else
  log "FAIL: Could not connect to onion service"
  exit 1
fi
