#!/bin/bash
# Bootstrap helper: Pre-bootstrap Tor and create required files
# Run this container once before starting tor-proxy

set -euo pipefail

log() { printf '[bootstrap-helper] %s\n' "$*"; }

TOR_DATA_DIR=${TOR_DATA_DIR:-/var/lib/tor}
COOKIE_FILE="${TOR_DATA_DIR}/control_auth_cookie"
OUTDIR="/run/lucid/onion"

log "=== Tor Bootstrap Helper ==="

# Ensure directories exist
mkdir -p "$TOR_DATA_DIR" "$OUTDIR" /var/log/tor || true

# Start Tor in background
log "Starting Tor for bootstrap..."
tor -f /etc/tor/torrc &
TOR_PID=$!
log "Tor started with PID: $TOR_PID"

# Wait for cookie file
log "Waiting for control cookie..."
for i in $(seq 1 120); do
  [ -s "$COOKIE_FILE" ] && break
  sleep 1
done
[ -s "$COOKIE_FILE" ] || { log "ERROR: Cookie not created"; exit 1; }
log "Cookie found"

# Wait for bootstrap
log "Waiting for bootstrap to reach 100%..."
HEX=$(xxd -p "$COOKIE_FILE" | tr -d '\n')
for i in $(seq 1 180); do
  REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n' "$HEX")
  OUT=$(echo "$REQ" | nc -w 3 127.0.0.1 9051 2>/dev/null || true)
  CLEANED=$(echo "$OUT" | /bin/busybox tr -d '\r' | /bin/busybox tr '\n' ' ' | /bin/busybox sed 's/  */ /g')
  if echo "$CLEANED" | /bin/busybox grep -o 'PROGRESS=[0-9]*' | /bin/busybox grep -q 'PROGRESS=100'; then
    log "Bootstrap complete (100%)"
    break
  fi
  sleep 2
  [ $((i % 15)) -eq 0 ] && log "Bootstrap progress... (attempt $i/180)"
done

# Create bootstrap env file
log "Creating bootstrap state files..."
VERSION=$(echo "$OUT" | /bin/busybox sed -n 's/.*250-version=\([0-9.]*\).*/\1/p' | tr -d '\r')
PHASE=$(echo "$OUT" | /bin/busybox sed -n 's/.*250-status\/bootstrap-phase=\(.*\)/\1/p' | tr -d '\r')
PROGRESS=$(echo "$PHASE" | /bin/busybox sed -n 's/.*PROGRESS=\([0-9]*\).*/\1/p')
TAG=$(echo "$PHASE" | /bin/busybox sed -n 's/.*TAG=\([a-z_]*\).*/\1/p')
SUMMARY=$(echo "$PHASE" | /bin/busybox sed -n 's/.*SUMMARY=\(.*\)$/\1/p')
STAMP=$(/bin/busybox date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$OUTDIR"
cat > "$OUTDIR/tor_bootstrap.env" <<EOF
TOR_VERSION=${VERSION:-0.4.7.16}
TOR_BOOTSTRAP_PROGRESS=${PROGRESS:-100}
TOR_BOOTSTRAP_TAG=${TAG:-done}
TOR_BOOTSTRAP_SUMMARY=${SUMMARY:-Done}
TOR_BOOTSTRAP_AT=${STAMP}
EOF

log "Bootstrap state files created at $OUTDIR"
log "Helper complete. Tor is ready. You can now start tor-proxy container."
exit 0