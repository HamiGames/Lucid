#!/bin/bash
set -e
# File: /app/02_network_security/tor/tor-health.sh
# x-lucid-file-path: /app/02_network_security/tor/tor-health.sh
# x-lucid-file-directory: /app/02_network_security/tor
# x-lucid-file-type: shell

COOKIE="${TOR_DATA_DIR:-/app/var/lib/tor}/control_auth_cookie"
CTRL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
CTRL_PORT="${TOR_CONTROL_PORT:-9051}"
# Aligned with Dockerfile.tor-proxy-02: TOR_DATA_DIR=/app/var/lib/tor (torrc CookieAuthFile)
OUTDIR="${TOR_DATA_DIR:-/app/var/lib/tor}"

BB="/app/bin/busybox"
[ -x "$BB" ] || BB="/bin/busybox"

[ -s "$COOKIE" ] || { echo "[hc] cookie missing or empty at $COOKIE"; exit 1; }

if command -v xxd >/dev/null 2>&1; then
  HEX="$(xxd -p "$COOKIE" | "${BB}" tr -d '\n')"
else
  HEX="$(hexdump -v -e '1/1 "%02x"' "$COOKIE")"
fi

REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nGETINFO version\r\nQUIT\r\n' "$HEX")
OUT="$(echo "$REQ" | nc -w 3 "$CTRL_HOST" "$CTRL_PORT" || true)"

# Use busybox grep explicitly (distroless: /app/bin/busybox)
echo "$OUT" | "${BB}" grep -q "^250 OK" || { echo "[hc] auth failed"; exit 1; }
echo "$OUT" | "${BB}" grep -q "^250-status/bootstrap-phase=" || { echo "[hc] no bootstrap info"; exit 1; }

PHASE="$(echo "$OUT" | "${BB}" sed -n 's/^250-status\/bootstrap-phase=//p')"
VERSION="$(echo "$OUT" | "${BB}" sed -n 's/^250-version=//p' | "${BB}" tr -d '\r')"

echo "$PHASE" | "${BB}" grep -q "PROGRESS=100" || { echo "[hc] not bootstrapped yet"; exit 1; }

PROGRESS=$(echo "$PHASE" | "${BB}" sed -n 's/.*PROGRESS=\([0-9][0-9]*\).*/\1/p')
TAG=$(echo "$PHASE" | "${BB}" sed -n 's/.*TAG=\([A-Za-z0-9_-]*\).*/\1/p')
SUMMARY=$(echo "$PHASE" | "${BB}" sed -n 's/.*SUMMARY=\(.*\)$/\1/p')
STAMP=$("${BB}" date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$OUTDIR" 2>/dev/null || true

{
  echo "TOR_VERSION=$VERSION"
  echo "TOR_BOOTSTRAP_PROGRESS=${PROGRESS:-0}"
  echo "TOR_BOOTSTRAP_TAG=$TAG"
  echo "TOR_BOOTSTRAP_SUMMARY=$SUMMARY"
  echo "TOR_BOOTSTRAP_AT=$STAMP"
} > "$OUTDIR/tor_bootstrap.env" 2>/dev/null || true

SUM_ESC=$(printf "%s" "$SUMMARY" | "${BB}" sed 's/\"/\\\"/g')
"${BB}" cat > "$OUTDIR/tor_bootstrap.json" <<EOF 2>/dev/null || true
{
  "version": "$VERSION",
  "progress": ${PROGRESS:-0},
  "tag": "$TAG",
  "summary": "$SUM_ESC",
  "timestamp": "$STAMP"
}
EOF

echo "[hc] bootstrapped (health check passed)"
exit 0
