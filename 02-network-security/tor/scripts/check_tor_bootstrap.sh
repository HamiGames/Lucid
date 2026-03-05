#!/usr/bin/env bash
# Path: 02-network-security/tor/scripts/check_tor_bootstrap.sh
# Verify Tor bootstrap status inside container

set -euo pipefail

log() { printf '[check_tor_bootstrap] %s\n' "$*"; }
die() { printf '[check_tor_bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

CONTAINER="${1:-lucid_tor}"

# Ensure container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  die "Container $CONTAINER not running"
else
  log "Container $CONTAINER is running"
fi
# Check if tor is already running
if docker exec "$CONTAINER" pgrep -x tor >/dev/null 2>&1; then
  log "Tor is already running inside $CONTAINER"
  exit 0
else
  log "Tor is not running inside $CONTAINER"
  exit 1
fi
log "Checking Tor bootstrap status in $CONTAINER..."

# Get the latest Bootstrapped line from logs
STATUS=$(docker logs "$CONTAINER" 2>&1 | grep "Bootstrapped" | tail -n 1 || true)

if echo "$STATUS" | grep -q "100%"; then
  log "SUCCESS: Tor is fully bootstrapped"
  exit 0
elif [ -n "$STATUS" ]; then
  log "WAITING: $STATUS"
  exit 1
else
  log "No bootstrap status found in logs yet"
  exit 1
fi
