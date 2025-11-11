#!/bin/bash
set -e

COOKIE="/var/lib/tor/control_auth_cookie"
CTRL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
CTRL_PORT="${TOR_CONTROL_PORT:-9051}"
OUTDIR="/run/lucid/onion"

# 1) Ensure cookie exists and is non-empty
[ -s "$COOKIE" ] || { echo "[hc] cookie missing or empty at $COOKIE"; exit 1; }

# 2) Read cookie and convert to hex
if command -v xxd >/dev/null 2>&1; then
  HEX="$(xxd -p "$COOKIE" | tr -d '\n')"
else
  HEX="$(hexdump -v -e '1/1 "%02x"' "$COOKIE")"
fi

# 3) Query bootstrap phase and version after AUTHENTICATE
REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nGETINFO version\r\nQUIT\r\n' "$HEX")
OUT="$(echo "$REQ" | nc -w 3 "$CTRL_HOST" "$CTRL_PORT" || true)"

echo "$OUT" | grep -q "^250 OK" || { echo "[hc] auth failed"; exit 1; }
echo "$OUT" | grep -q "^250-status/bootstrap-phase=" || { echo "[hc] no bootstrap info"; exit 1; }

PHASE="$(echo "$OUT" | sed -n 's/^250-status\/bootstrap-phase=//p')"
VERSION="$(echo "$OUT" | sed -n 's/^250-version=//p' | tr -d '\r')"

# Healthy only if bootstrapped 100%
echo "$PHASE" | grep -q "PROGRESS=100" || { echo "[hc] not bootstrapped yet"; exit 1; }

# 4) Persist bootstrap vars (idempotent)
PROGRESS=$(echo "$PHASE" | sed -n 's/.*PROGRESS=\([0-9][0-9]*\).*/\1/p')
TAG=$(echo "$PHASE" | sed -n 's/.*TAG=\([A-Za-z0-9_-]*\).*/\1/p')
SUMMARY=$(echo "$PHASE" | sed -n 's/.*SUMMARY=\(.*\)$/\1/p')
STAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$OUTDIR"

# Write .env-style
{
  echo "TOR_VERSION=$VERSION"
  echo "TOR_BOOTSTRAP_PROGRESS=${PROGRESS:-0}"
  echo "TOR_BOOTSTRAP_TAG=$TAG"
  echo "TOR_BOOTSTRAP_SUMMARY=$SUMMARY"
  echo "TOR_BOOTSTRAP_AT=$STAMP"
} > "$OUTDIR/tor_bootstrap.env"

# Write JSON (no jq)
SUM_ESC=$(printf "%s" "$SUMMARY" | sed 's/\"/\\\"/g')
cat > "$OUTDIR/tor_bootstrap.json" <<EOF
{
  "version": "$VERSION",
  "progress": ${PROGRESS:-0},
  "tag": "$TAG",
  "summary": "$SUM_ESC",
  "timestamp": "$STAMP"
}
EOF

echo "[hc] bootstrapped (vars persisted)"
exit 0
