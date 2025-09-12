#!/usr/bin/env bash
# Tunnels manager — creates (and optionally rotates) Tor v3 *ephemeral* onion(s)
# EXPECTED RUNTIME TOPOLOGY (Compose):
#   - This container MUST share the network namespace with tor-proxy:
#       network_mode: "service:tor-proxy"
#   - This container MUST mount the same tor_data volume as tor-proxy at /var/lib/tor
#       volumes:
#         - tor_data:/var/lib/tor
#   → This allows reaching ControlPort 127.0.0.1:9051 and reading the auth cookie.
#
# ENV knobs (with safe defaults):
#   CONTROL_HOST=127.0.0.1
#   CONTROL_PORT=9051
#   COOKIE_FILE=/var/lib/tor/control_auth_cookie
#   ONION_PORTS="80 lucid_api:8081"     # space/comma separated pairs: "VPORT HOST:TPORT[, 443 svc:8443]"
#   WRITE_ENV=/scripts/.onion.env       # optional; writable path to export ONION=<addr>
#   ROTATE_INTERVAL=0                   # minutes. 0 = create once and sleep forever.

set -Eeuo pipefail

log() { printf '[tunnels] %s\n' "$*"; }
die() { printf '[tunnels][ERROR] %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"; }

CONTROL_HOST="${CONTROL_HOST:-127.0.0.1}"
CONTROL_PORT="${CONTROL_PORT:-9051}"
COOKIE_FILE="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
ONION_PORTS="${ONION_PORTS:-80 lucid_api:8081}"
WRITE_ENV="${WRITE_ENV:-/scripts/.onion.env}"
ROTATE_INTERVAL="${ROTATE_INTERVAL:-0}"

CREATE_SCRIPT="/app/scripts/create_ephemeral_onion.sh"

wait_for_file() {
  # wait_for_file <path> <seconds>
  local f="$1" ; local timeout="${2:-120}"
  log "Waiting for file ${f} (timeout ${timeout}s)..."
  local i=0
  while [ $i -lt "$timeout" ]; do
    [ -s "$f" ] && { log "Found ${f}"; return 0; }
    sleep 1; i=$((i+1))
  done
  die "file not present: ${f}"
}

ctl_ping() {
  # quick AUTH ping to verify control connectivity
  local cookie_hex
  cookie_hex="$(xxd -p "$COOKIE_FILE" | tr -d '\n')"
  printf 'AUTHENTICATE %s\r\nGETINFO version\r\nQUIT\r\n' "$cookie_hex" \
    | nc -w 5 "$CONTROL_HOST" "$CONTROL_PORT" | grep -q '^250 OK'
}

create_once() {
  log "Creating ephemeral onion(s) for: ${ONION_PORTS}"
  "$CREATE_SCRIPT" \
    --control-host "$CONTROL_HOST" \
    --control-port "$CONTROL_PORT" \
    --cookie-file  "$COOKIE_FILE" \
    --ports        "$ONION_PORTS" \
    --write-env    "$WRITE_ENV"
}

main() {
  need nc; need xxd
  [ -x "$CREATE_SCRIPT" ] || die "script not executable: $CREATE_SCRIPT"

  # Preconditions: same volume + same netns as tor-proxy
  wait_for_file "$COOKIE_FILE" 120

  # Verify ControlPort
  ctl_ping || die "cannot authenticate to Tor ControlPort at ${CONTROL_HOST}:${CONTROL_PORT}"

  if [ "${ROTATE_INTERVAL}" = "0" ]; then
    create_once
    log "Sleeping indefinitely (ROTATE_INTERVAL=0)"
    tail -f /dev/null
    exit 0
  fi

  # Rotation loop
  while true; do
    create_once || log "create failed; will retry after ${ROTATE_INTERVAL}m"
    sleep "$(( ROTATE_INTERVAL * 60 ))"
  done
}

main "$@"
