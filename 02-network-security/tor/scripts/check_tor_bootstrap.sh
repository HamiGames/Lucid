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
