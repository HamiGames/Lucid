#!/bin/sh
set -e

TOR_CONTROL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_COOKIE_PATH="${TOR_COOKIE_PATH:-/var/lib/tor/control_auth_cookie}"
OUTDIR="${ONION_DIR:-/run/lucid/onion}"
# Target: map port 80 of onion to container-local 8080 (adjust if needed)
TARGET_HOST="${TARGET_HOST:-127.0.0.1}"
TARGET_PORT="${TARGET_PORT:-8080}"

# Check cookie
if [ ! -s "$TOR_COOKIE_PATH" ]; then
  echo "[onion] control cookie missing or empty at $TOR_COOKIE_PATH" >&2
  exit 2
fi

# Cookie -> hex
if command -v xxd >/dev/null 2>&1; then
  COOKIE_HEX="$(xxd -p "$TOR_COOKIE_PATH" | tr -d '\n')"
else
  COOKIE_HEX="$(hexdump -v -e '1/1 "%02x"' "$TOR_COOKIE_PATH")"
fi

# Build control sequence (ED25519 v3 onion)
CONTROL_CMDS=$(printf 'AUTHENTICATE %s\r\nADD_ONION NEW:ED25519-V3 Port=80,%s:%s\r\nQUIT\r\n' "$COOKIE_HEX" "$TARGET_HOST" "$TARGET_PORT")

# Send via netcat
RESP="$(printf "%s" "$CONTROL_CMDS" | nc -w 5 "$TOR_CONTROL_HOST" "$TOR_CONTROL_PORT" || true)"

# Parse ServiceID
echo "$RESP" | grep -qE '^250(-| )ServiceID=' || {
  echo "[onion] failed to create onion" >&2
  echo "$RESP" | sed -n '1,20p' >&2
  exit 3
}

SERVICE_ID="$(echo "$RESP" | awk -F= '/^250(-| )ServiceID=/{id=$2} END{if(id!="")print id}' | tr -d '\r')"

# Persist for other services (optional but useful)
mkdir -p "$OUTDIR"
echo "${SERVICE_ID}.onion" > "$OUTDIR/onion.txt"

echo "[onion] ServiceID=$SERVICE_ID"
echo "[onion] wrote ${SERVICE_ID}.onion to $OUTDIR/onion.txt"
