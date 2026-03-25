#!/usr/bin/env bash
# Path: 02_network_security/tunnels/scripts/teardown_tunnel.sh
# Remove ephemeral onion (DEL_ONION) via Tor ControlPort.
# See: 02_network_security/tunnels/Dockerfile, 02_network_security/tor/Dockerfile.tor-proxy-02

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

log() { printf '[teardown_tunnel] %s\n' "$*"; }
die() { printf '[teardown_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"
CONTROL_HOST_TARGET="${1:-${CONTROL_HOST:-$TOR_CONTAINER_NAME}}"
SERVICE_ID="${2:-}"

[[ -n "$SERVICE_ID" ]] || die "Usage: $0 [control_host] <service_id>"

if command -v docker >/dev/null 2>&1; then
  if ! docker ps --format '{{.Names}}' | grep -q "^${TOR_CONTAINER_NAME}\$"; then
    die "Container ${TOR_CONTAINER_NAME} not running (docker)"
  fi
else
  log "Docker not available — sending DEL_ONION to ${CONTROL_HOST_TARGET}:${CONTROL_PORT}"
fi

[[ -f "$COOKIE_FILE" ]] || die "Tor control cookie not found at $COOKIE_FILE"

COOKIE_HEX=$(xxd -p -c 256 "$COOKIE_FILE" | tr -d '\n')
REPLY=$(printf 'AUTHENTICATE %s\r\nDEL_ONION %s\r\nQUIT\r\n' "$COOKIE_HEX" "$SERVICE_ID" \
        | nc -w 5 "$CONTROL_HOST_TARGET" "${CONTROL_PORT:-9051}")

echo "$REPLY" | grep -q "250 OK" || die "Failed to remove onion tunnel"

log "SUCCESS: Onion service $SERVICE_ID removed"
