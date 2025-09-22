#!/bin/sh
set -e
COOKIE="/var/lib/tor/control_auth_cookie"
CTRL_HOST="127.0.0.1"
CTRL_PORT="${TOR_CONTROL_PORT:-9051}"

[ -s "$COOKIE" ] || { echo "[hc] cookie missing or empty at $COOKIE"; exit 1; }

if command -v xxd >/dev/null 2>&1; then
  HEX="$(xxd -p "$COOKIE" | tr -d '\n')"
else
  HEX="$(hexdump -v -e '1/1 \"%02x\"' "$COOKIE")"
fi

REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n' "$HEX")
OUT="$(echo "$REQ" | nc -w 3 "$CTRL_HOST" "$CTRL_PORT" || true)"

echo "$OUT" | grep -q "^250 OK" || { echo "[hc] auth failed"; exit 1; }
echo "$OUT" | grep -q "Bootstrapped=100" || { echo "[hc] not bootstrapped yet"; exit 1; }
echo "[hc] bootstrapped"
