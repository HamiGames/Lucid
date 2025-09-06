#!/usr/bin/env bash
# Path: 02-network-security/tunnels/scripts/teardown_tunnel.sh
# Remove ephemeral onion tunnel

set -euo pipefail

log() { printf '[teardown_tunnel] %s\n' "$*"; }
die() { printf '[teardown_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

CONTAINER="${1:-lucid_tor}"
SERVICE_ID="${2:-}"

if [[ -z "$SERVICE_ID" ]]; then
  die "Usage: $0 <container_name> <service_id>"
fi

log "Tearing down onion tunnel $SERVICE_ID in $CONTAINER"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
fi

CMD="DEL_ONION $SERVICE_ID"
REPLY=$(docker exec "$CONTAINER" sh -c "echo -e 'AUTHENTICATE \"\"\n$CMD\nQUIT' | nc localhost 9051")

echo "$REPLY" | grep -q "250 OK" || die "Failed to remove onion tunnel"

log "SUCCESS: Onion service $SERVICE_ID removed"
