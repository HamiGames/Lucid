#!/usr/bin/env bash
# Path: 02-network-security/tunnels/scripts/create_tunnel.sh
# Create an ephemeral onion tunnel mapping container ports
# NOTE: This script is designed to run from the host (uses docker exec)

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

CONTAINER="${1:-${TOR_CONTAINER_NAME}}"
PORTS="${2:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"

# Ensure container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
fi

log "Creating onion tunnel in $CONTAINER for ports: $PORTS"

# Load Tor control configuration
COOKIE_FILE="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
CONTROL_PORT="${CONTROL_PORT:-9051}"

# Ensure cookie file exists
if ! docker exec "$CONTAINER" test -f "$COOKIE_FILE"; then
  die "Tor control cookie not found at $COOKIE_FILE"
fi

# Hex-encode cookie (remove newlines)
COOKIE=$(docker exec "$CONTAINER" xxd -p -c 256 "$COOKIE_FILE" | tr -d '\n')

# Build ADD_ONION command
CMD="ADD_ONION NEW:ED25519-V3 Port=$PORTS"

# Send authenticated command (use CONTROL_PORT from environment)
REPLY=$(docker exec "$CONTAINER" sh -c "printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' '$COOKIE' '$CMD' | nc 127.0.0.1 $CONTROL_PORT")

SERVICE_ID=$(echo "$REPLY" | grep "250-ServiceID" | awk '{print $2}' || true)

if [ -z "$SERVICE_ID" ]; then
  die "Failed to create onion tunnel"
fi

ONION_ADDR="${SERVICE_ID}.onion"

log "SUCCESS: Onion service created at $ONION_ADDR"
echo "$ONION_ADDR"
