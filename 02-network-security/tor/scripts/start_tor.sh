#!/usr/bin/env bash
# Path: 02-network-security/tor/scripts/start_tor.sh
# Ensure Tor is running inside the lucid_tor container

set -euo pipefail

log() { printf '[start_tor] %s\n' "$*"; }
die() { printf '[start_tor] ERROR: %s\n' "$*" >&2; exit 1; }

CONTAINER="${1:-lucid_tor}"

# Ensure container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
fi

# Check if tor is already running
if docker exec "$CONTAINER" pgrep -x tor >/dev/null 2>&1; then
  log "Tor is already running inside $CONTAINER"
  exit 0
fi

# Otherwise, start tor manually
log "Starting Tor in $CONTAINER..."
docker exec -d "$CONTAINER" tor -f /etc/tor/torrc || die "Failed to start Tor"

log "Tor process started inside $CONTAINER"
