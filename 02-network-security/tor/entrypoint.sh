#!/usr/bin/env bash
# Custom entrypoint for Lucid Tor Proxy

set -euo pipefail

log() { printf '[tor-entrypoint] %s\n' "$*"; }

CONTROL_HOST=127.0.0.1
CONTROL_PORT=9051
COOKIE_FILE=/var/lib/tor/control_auth_cookie
UPSTREAM_SERVICE=${UPSTREAM_SERVICE:-lucid_api}
UPSTREAM_PORT=${UPSTREAM_PORT:-8081}   # match API internal port

ensure_dirs() {
  mkdir -p /run
  chown -R tor:tor /var/lib/tor
  chmod 700 /var/lib/tor
}

start_tor() {
  log "Starting Tor as user 'tor'..."
  su-exec tor tor -f /etc/tor/torrc &
  TOR_PID=$!
  echo "$TOR_PID" > /run/tor.pid
}

wait_for_cookie() {
  log "Waiting for control cookie at $COOKIE_FILE ..."
  for _ in $(seq 1 120); do
    [[ -s "$COOKIE_FILE" ]] && return 0
    sleep 1
  done
  log "ERROR: control cookie not created at $COOKIE_FILE"
  exit 1
}

ctl() {
  local cmd="$1"
  local cookie_hex
  cookie_hex=$(xxd -p "$COOKIE_FILE" | tr -d '\n')
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" \
    | nc -w 3 "$CONTROL_HOST" "$CONTROL_PORT"
}

wait_for_bootstrap() {
  log "Waiting for Tor bootstrap (GETINFO status/bootstrap-phase)..."
  for _ in $(seq 1 120); do
    if ctl "GETINFO status/bootstrap-phase" 2>/dev/null | grep -q 'PROGRESS=100'; then
      log "Tor bootstrap complete."
      return 0
    fi
    sleep 2
  done
  log "ERROR: Tor did not reach PROGRESS=100"
  exit 1
}

create_ephemeral_onion() {
  local add_onion="ADD_ONION NEW:ED25519-V3 Port=80,${UPSTREAM_SERVICE}:${UPSTREAM_PORT}"
  log "Creating ephemeral onion for 80 -> ${UPSTREAM_SERVICE}:${UPSTREAM_PORT} ..."
  local out
  out=$(ctl "$add_onion" || true)
  echo "$out" | grep -q '250-ServiceID=' || { log "ERROR creating onion"; echo "$out"; exit 1; }
  local onion
  onion=$(echo "$out" | awk -F= '/250-ServiceID=/{print $2}').onion
  log "ONION=${onion}"

  # Optional: export to env file for other services/tools
  if [[ -d /scripts ]]; then
    echo "ONION=${onion}" > /scripts/.onion.env || true
  fi
}

main() {
  ensure_dirs
  start_tor
  wait_for_cookie
  wait_for_bootstrap
  create_ephemeral_onion
  wait "$(cat /run/tor.pid)"
}

main "$@"
