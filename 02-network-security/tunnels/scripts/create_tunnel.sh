#!/usr/bin/env bash
# Path: 02-network-security/tunnels/scripts/create_tunnel.sh
# Create an ephemeral onion tunnel mapping container ports

set -euo pipefail

log() { printf '[create_tunnel] %s\n' "$*"; }
die() { printf '[create_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

CONTAINER="${1:-lucid_tor}"
PORTS="${2:-80 lucid_api:4000}"

# Ensure container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
fi

log "Creating onion tunnel in $CONTAINER for ports: $PORTS"

# Grab Tor control cookie path
COOKIE_FILE="/var/lib/tor/control_auth_cookie"

# Ensure cookie file exists
if ! docker exec "$CONTAINER" test -f "$COOKIE_FILE"; then
  die "Tor control cookie not found at $COOKIE_FILE"
fi

# Hex-encode cookie
COOKIE=$(docker exec "$CONTAINER" xxd -p -c 256 "$COOKIE_FILE")

# Build ADD_ONION command
CMD="ADD_ONION NEW:BEST Flags=DiscardPK Port=$PORTS"

# Send authenticated command
REPLY=$(docker exec "$CONTAINER" sh -c "echo -e 'AUTHENTICATE $COOKIE\n$CMD\nQUIT' | nc 127.0.0.1 9051")

SERVICE_ID=$(echo "$REPLY" | grep "250-ServiceID" | awk '{print $2}' || true)

if [ -z "$SERVICE_ID" ]; then
  die "Failed to create onion tunnel"
fi

ONION_ADDR="${SERVICE_ID}.onion"

log "SUCCESS: Onion service created at $ONION_ADDR"
echo "$ONION_ADDR"
