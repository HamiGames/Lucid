#!/usr/bin/env bash
# Path: 02_network_security/tunnels/scripts/create_tunnel.sh
# Create an ephemeral onion tunnel (ADD_ONION) via Tor ControlPort.
# Works in lucid-tunnel-tools (Dockerfile) or on a host with docker; delegates to
# create_ephemeral_onion.sh for valid Tor Port= lines.
#
# See: 02_network_security/tunnels/Dockerfile, 02_network_security/tor/Dockerfile.tor-proxy-02

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

log() { printf '[create_tunnel] %s\n' "$*"; }
die() { printf '[create_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
CONTROL_HOST_RESOLVE="${1:-${CONTROL_HOST:-$TOR_CONTAINER_NAME}}"
PORTS="${2:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
COOKIE_HOST_FILE="${COOKIE_HOST_FILE:-${COOKIE_FILE}}"

if command -v docker >/dev/null 2>&1; then
  if ! docker ps --format '{{.Names}}' | grep -q "^${TOR_CONTAINER_NAME}\$"; then
    die "Container ${TOR_CONTAINER_NAME} not running (docker)"
  fi
  log "Docker: ${TOR_CONTAINER_NAME} is running"
else
  log "Docker not available — assuming ${CONTROL_HOST_RESOLVE} reachable on network"
fi

if [[ ! -f "$COOKIE_HOST_FILE" ]]; then
  die "Tor control cookie not found at $COOKIE_HOST_FILE (set COOKIE_FILE / volume mount per tunnels/Dockerfile)"
fi
log "Tor control cookie found at $COOKIE_HOST_FILE"

log "Creating onion tunnel via ControlPort ${CONTROL_HOST_RESOLVE}:${CONTROL_PORT} for ports: $PORTS"
exec "$SCRIPT_DIR/create_ephemeral_onion.sh" \
  --control-host "$CONTROL_HOST_RESOLVE" \
  --control-port "${CONTROL_PORT:-9051}" \
  --cookie-file "$COOKIE_HOST_FILE" \
  --ports "$PORTS" \
  ${WRITE_ENV:+--write-env "$WRITE_ENV"}
