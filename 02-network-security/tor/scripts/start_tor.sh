#!/usr/bin/env bash
# Path: 02-network-security/tor/scripts/start_tor.sh
# Ensure Tor is running — runs inside the lucid_tor container

set -euo pipefail

log() { printf '[start_tor] %s\n' "$*"; }
die() { printf '[start_tor] ERROR: %s\n' "$*" >&2; exit 1; }

TORRC="${TORRC:-/opt/lucid/tor/bin/torrc}"

# Check if tor is already running — if not, start it
if pgrep -x tor >/dev/null 2>&1; then
  log "Tor is already running"
  exit 0
else
  log "Tor is not running — starting..."
  tor -f "$TORRC" || die "Failed to start Tor"
  log "Tor process started"
fi
