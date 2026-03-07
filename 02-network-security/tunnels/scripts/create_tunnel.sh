#!/usr/bin/env bash
# Path: 02-network-security/tunnels/scripts/create_tunnel.sh
# Create an ephemeral onion tunnel mapping container ports
# NOTE: This script runs inside lucid-tunnel-tools (host-side of the interop).
#       tor-proxy is distroless — no shell, no xxd, no nc inside that container.
#       Cookie is read from the shared volume mount; nc connects over Docker network.

set -euo pipefail

log() { printf '[create_tunnel] %s\n' "$*"; }
die() { printf '[create_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

# Check if docker is available
if ! command -v docker >/dev/null 2>&1; then
  die "docker command not found. This script must be run from the host."
fi

# Load defaults from environment variables
TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
CONTAINER="${1:-${TOR_CONTAINER_NAME-tor-proxy}}"
PORTS="${2:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
COOKIE_HOST_DIR="${COOKIE_HOST_DIR:-/run/lucid/tor}"
COOKIE_HOST_FILE="${COOKIE_HOST_FILE:-"${COOKIE_HOST_DIR}/control_auth_cookie"}"
CONTROL_PORT="${CONTROL_PORT:-9051}"

# Ensure container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
else
  log "Creating onion tunnel in $CONTAINER for ports: $PORTS"
fi

# Ensure cookie file is accessible on the shared volume mount.
# (docker exec is not used — tor-proxy is distroless and has no shell.)
if [[ ! -f "$COOKIE_HOST_FILE" ]]; then
  die "Tor control cookie not found at $COOKIE_HOST_FILE (is the volume mounted?)"
fi
log "Tor control cookie found at $COOKIE_HOST_FILE"

# Hex-encode cookie via xxd running locally in lucid-tunnel-tools
COOKIE=$(xxd -p -c 256 "$COOKIE_HOST_FILE" | tr -d '\n')

# Build ADD_ONION command
CMD="ADD_ONION NEW:ED25519-V3 Port=$PORTS"

# Send authenticated command over Docker network directly to tor-proxy control port.
# nc runs here in lucid-tunnel-tools — NOT via docker exec into the distroless container.
REPLY=$(printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$COOKIE" "$CMD" \
        | nc -w 5 "$CONTAINER" "$CONTROL_PORT")

SERVICE_ID=$(echo "$REPLY" | grep "250-ServiceID" | awk '{print $2}' || true)

if [ -z "$SERVICE_ID" ]; then
  die "Failed to create onion tunnel"
fi

ONION_ADDR="${SERVICE_ID}.onion"

log "SUCCESS: Onion service created at $ONION_ADDR"
echo "$ONION_ADDR"
