#!/usr/bin/env bash
# Path: 02-network-security/tor/scripts/check_tor_bootstrap.sh
# Verify Tor bootstrap status inside container

set -euo pipefail

log() { printf '[check_tor_bootstrap] %s\n' "$*"; }
die() { printf '[check_tor_bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

TOR_CONTROL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_DATA_DIR="${TOR_DATA_DIR:-/run/lucid/tor}"
COOKIE="${TOR_DATA_DIR}/control_auth_cookie"

# Check if tor process is running
if ! pgrep -x tor >/dev/null 2>&1; then
  die "Tor is not running"
fi
log "Tor process is running"

# Verify cookie file exists
[ -f "$COOKIE" ] || die "Cookie file not found: $COOKIE"

# Read cookie hex for control port authentication
COOKIE_HEX=$(xxd -p "$COOKIE" | tr -d '\n')

# Query bootstrap phase via control port
STATUS=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n' "$COOKIE_HEX" \
  | nc -q 1 "$TOR_CONTROL_HOST" "$TOR_CONTROL_PORT" 2>/dev/null \
  | grep -i "bootstrap-phase" | head -n 1 || true)

if echo "$STATUS" | grep -q "PROGRESS=100"; then
  log "SUCCESS: Tor is fully bootstrapped"
  exit 0
elif [ -n "$STATUS" ]; then
  log "WAITING: $STATUS"
  exit 1
else
  log "No bootstrap status found"
  exit 1
fi
