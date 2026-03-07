#!/usr/bin/env bash
# Path: 02-network-security/tunnels/scripts/teardown_tunnel.sh
# Remove ephemeral onion tunnel
# NOTE: This script runs inside lucid-tunnel-tools (host-side of the interop).
#       tor-proxy is distroless — no shell, no xxd, no nc inside that container.
#       Cookie is read from the shared volume mount; nc connects over Docker network.

set -euo pipefail

log() { printf '[teardown_tunnel] %s\n' "$*"; }
die() { printf '[teardown_tunnel] ERROR: %s\n' "$*" >&2; exit 1; }

# Check if docker is available
if ! command -v docker >/dev/null 2>&1; then
  die "docker command not found. This script must be run from the host."
fi

# Load defaults from environment variables
TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"
COOKIE_FILE="${COOKIE_FILE:-/run/lucid/tor/control_auth_cookie}"
CONTROL_PORT="${CONTROL_PORT:-9051}"

CONTAINER="${1:-${TOR_CONTAINER_NAME}}"
SERVICE_ID="${2:-}"

if [[ -z "$SERVICE_ID" ]]; then
  die "Usage: $0 <container_name> <service_id>"
fi

log "Tearing down onion tunnel $SERVICE_ID in $CONTAINER"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
fi

# Ensure cookie file is accessible on the shared volume mount.
# (docker exec is not used — tor-proxy is distroless and has no shell.)
if [[ ! -f "$COOKIE_FILE" ]]; then
  die "Tor control cookie not found at $COOKIE_FILE (is the volume mounted?)"
fi

# Hex-encode cookie via xxd running locally in lucid-tunnel-tools
COOKIE_HEX=$(xxd -p -c 256 "$COOKIE_FILE" | tr -d '\n')

CMD="DEL_ONION $SERVICE_ID"

# Send authenticated command over Docker network directly to tor-proxy control port.
# nc runs here in lucid-tunnel-tools — NOT via docker exec into the distroless container.
REPLY=$(printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$COOKIE_HEX" "$CMD" \
        | nc -w 5 "$CONTAINER" "$CONTROL_PORT")

echo "$REPLY" | grep -q "250 OK" || die "Failed to remove onion tunnel"

log "SUCCESS: Onion service $SERVICE_ID removed"
