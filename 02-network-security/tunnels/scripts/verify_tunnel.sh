#!/usr/bin/env bash
# Lucid RDP — verify Tor tunnel reachability
# Path: 02-network-security/tunnels/scripts/verify_tunnel.sh

set -euo pipefail

usage() {
  echo "Usage: $0 --onion <onion_url> [--socks5 127.0.0.1:9050]"
  exit 1
}

ONION_URL=""
SOCKS5_ADDR="127.0.0.1:9050"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --onion)
      ONION_URL="$2"
      shift 2
      ;;
    --socks5)
      SOCKS5_ADDR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown arg: $1"
      usage
      ;;
  esac
done

if [[ -z "$ONION_URL" ]]; then
  echo "[verify_tunnel] ERROR: --onion <onion_url> required"
  usage
fi

echo "[verify_tunnel] Testing reachability of $ONION_URL via SOCKS5 at $SOCKS5_ADDR"

# Use curl through Tor SOCKS5 proxy
if curl -s --socks5-hostname "$SOCKS5_ADDR" --max-time 15 "$ONION_URL" >/dev/null; then
  echo "[verify_tunnel] SUCCESS: Onion service is reachable"
  exit 0
else
  echo "[verify_tunnel] FAIL: Could not connect to onion service"
  exit 1
fi
