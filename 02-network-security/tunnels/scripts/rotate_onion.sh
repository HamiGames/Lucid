#!/usr/bin/env bash
# Rotate the ephemeral onion: try to delete existing, then create a new one.
# Delegates creation to create_ephemeral_onion.sh in the same directory

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CREATE_SCRIPT="${SCRIPT_DIR}/create_ephemeral_onion.sh"

# Load defaults from environment variables
CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
CONTROL_PORT="${CONTROL_PORT:-9051}"
COOKIE_FILE="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
WRITE_ENV="${WRITE_ENV:-/run/lucid/onion/.onion.env}"

# Input format matches previous usage:
#   --ports "80 lucid_api:8081"
#   --ports "80 127.0.0.1:8081, 443 127.0.0.1:8443"
PORT_SPECS=""

log() { printf '[rotate_onion] %s\n' "$*"; }
die() { printf '[rotate_onion][ERROR] %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"; }

ctl_send() {
  local cmd="$1"
  local cookie_hex
  [ -r "$COOKIE_FILE" ] || die "cookie not readable: $COOKIE_FILE"
  cookie_hex="$(xxd -p "$COOKIE_FILE" | tr -d '\n')"
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" \
    | nc -w 5 "$CONTROL_HOST" "$CONTROL_PORT"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --control-host) CONTROL_HOST="$2"; shift 2;;
    --control-port) CONTROL_PORT="$2"; shift 2;;
    --cookie-file)  COOKIE_FILE="$2";  shift 2;;
    --write-env)    WRITE_ENV="$2";    shift 2;;
    --ports)        PORT_SPECS="$2";   shift 2;;
    --help|-h)
      cat <<'USAGE'
Usage:
  rotate_onion.sh [--control-host 127.0.0.1] [--control-port 9051]
                  [--cookie-file /var/lib/tor/control_auth_cookie]
                  [--write-env /scripts/.onion.env]
                  --ports "80 lucid_api:8081[, 443 lucid_api:8443]"
Notes:
 - Attempts to delete the currently active onion (if ONION is known),
   then creates a new one using create_ephemeral_onion.sh.
USAGE
      exit 0;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

need nc
need xxd

# Try to read existing ONION to delete
CURRENT_ONION=""
if [ -r "$WRITE_ENV" ]; then
  CURRENT_ONION="$(awk -F= '/^ONION=/{print $2; exit}' "$WRITE_ENV" || true)"
fi

if [ -n "$CURRENT_ONION" ]; then
  SVC_ID="${CURRENT_ONION%.onion}"
  log "Deleting existing onion: ${CURRENT_ONION}"
  DEL_REPLY="$(ctl_send "DEL_ONION ${SVC_ID}")" || true
  printf '%s\n' "$DEL_REPLY" | sed -n '1,40p'
fi

[ -x "$CREATE_SCRIPT" ] || die "creation script not executable: $CREATE_SCRIPT"

log "Creating new ephemeral onion with ports: ${PORT_SPECS:-<default>}"
exec "$CREATE_SCRIPT" \
  --control-host "$CONTROL_HOST" \
  --control-port "$CONTROL_PORT" \
  --cookie-file "$COOKIE_FILE" \
  --write-env "$WRITE_ENV" \
  ${PORT_SPECS:+--ports "$PORT_SPECS"}
