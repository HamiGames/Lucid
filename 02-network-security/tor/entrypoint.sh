#!/usr/bin/env bash
# Lucid Tor Proxy — robust entrypoint with DNS resolution for ADD_ONION

set -Eeuo pipefail

log() { printf '[tor-entrypoint] %s\n' "$*"; }

CONTROL_HOST=127.0.0.1
CONTROL_PORT=${CONTROL_PORT:-9051}
COOKIE_FILE=${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}
UPSTREAM_SERVICE=${UPSTREAM_SERVICE:-lucid_api}
UPSTREAM_PORT=${UPSTREAM_PORT:-8081}
CREATE_ONION=${CREATE_ONION:-1}   # set 0 to skip onion creation (diagnostics mode)

ensure_runtime() {
  mkdir -p /run
  chown -R tor:tor /var/lib/tor
  chmod 700 /var/lib/tor
}

start_tor() {
  log "Starting Tor as 'tor'..."
  su-exec tor tor -f /etc/tor/torrc &
  echo $! > /run/tor.pid
}

wait_for_file() {
  # wait_for_file <path> <seconds>
  local f="$1" ; local timeout="${2:-120}"
  log "Waiting for file ${f} (timeout ${timeout}s)..."
  local i=0
  while [ $i -lt "$timeout" ]; do
    if [ -s "$f" ]; then
      log "Found ${f}"
      return 0
    fi
    sleep 1; i=$((i+1))
  done
  log "ERROR: file not present: ${f}"
  return 1
}

ctl() {
  local cmd="$1"
  local cookie_hex
  cookie_hex=$(xxd -p "$COOKIE_FILE" | tr -d '\n')
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" \
    | nc -w 5 "$CONTROL_HOST" "$CONTROL_PORT"
}

resolve_upstream_ip() {
  # Try getent first (if present via busybox); fallback to nslookup (bind-tools)
  local ip=""
  if command -v getent >/dev/null 2>&1; then
    ip=$(getent hosts "$UPSTREAM_SERVICE" 2>/dev/null | awk '{print $1}' | head -1 || true)
  fi
  if [ -z "$ip" ]; then
    ip=$(nslookup -timeout=2 "$UPSTREAM_SERVICE" 2>/dev/null | awk '/^Address: /{print $2; exit}' || true)
  fi
  printf '%s' "$ip"
}

wait_for_bootstrap() {
  log "Waiting for Tor bootstrap to reach 100%..."
  local i=0
  while [ $i -lt 180 ]; do
    if ctl "GETINFO status/bootstrap-phase" 2>/dev/null | grep -q 'PROGRESS=100'; then
      log "Bootstrap complete."
      return 0
    fi
    sleep 2; i=$((i+1))
  done
  log "ERROR: Tor did not reach PROGRESS=100"
  return 1
}

create_ephemeral_onion() {
  [ "$CREATE_ONION" = "1" ] || { log "CREATE_ONION=0 — skipping onion creation"; return 0; }

  # Resolve service to IP for ADD_ONION (some Tor builds reject hostnames)
  local ip=""
  local tries=30
  while [ $tries -gt 0 ]; do
    ip=$(resolve_upstream_ip)
    if [ -n "$ip" ]; then
      break
    fi
    sleep 2; tries=$((tries-1))
  done
  if [ -z "$ip" ]; then
    log "ERROR: unable to resolve ${UPSTREAM_SERVICE}"
    return 1
  fi

  # Optional: quick connectivity probe (doesn't block onion creation if it fails)
  nc -z -w 2 "$ip" "$UPSTREAM_PORT" >/dev/null 2>&1 || log "WARN: upstream $ip:$UPSTREAM_PORT not reachable yet"

  local add_onion="ADD_ONION NEW:ED25519-V3 Port=80,${ip}:${UPSTREAM_PORT}"
  log "Creating ephemeral onion: 80 -> ${ip}:${UPSTREAM_PORT}"
  local out
  out=$(ctl "$add_onion" || true)
  echo "$out" | grep -q '250-ServiceID=' && {
    local onion
    onion=$(echo "$out" | awk -F= '/250-ServiceID=/{print $2}').onion
    log "ONION=${onion}"
    return 0
  }
  log "ERROR creating onion"
  # Print exact control error for diagnosis
  printf '%s\n' "$out"
  return 1
}

main() {
  ensure_runtime
  start_tor
  wait_for_file "$COOKIE_FILE" 120
  wait_for_bootstrap || true
  create_ephemeral_onion || true
  wait "$(cat /run/tor.pid)"
}

main "$@"
