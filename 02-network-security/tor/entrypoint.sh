#!/bin/bash
# Lucid Tor Proxy — entrypoint for distroless runtime
# Aligned with @constants: TOR_PROXY_* env vars, CREATE_ONION=0 default, /run/lucid/onion state

set -Eeuo pipefail

log() { printf '[tor-entrypoint] %s\n' "$*"; }

CONTROL_HOST=${CONTROL_HOST:-127.0.0.1}
# Align with @constants and compose: prefer TOR_PROXY_* then fallback
TOR_SOCKS_PORT=${TOR_PROXY_SOCKS_PORT:-${TOR_SOCKS_PORT:-9050}}
CONTROL_PORT=${TOR_PROXY_CONTROL_PORT:-${TOR_CONTROL_PORT:-9051}}
COOKIE_FILE=${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}
UPSTREAM_SERVICE=${UPSTREAM_SERVICE:-}
UPSTREAM_PORT=${UPSTREAM_PORT:-8081}
# Foundation default: don't create onions unless explicitly enabled
CREATE_ONION=${CREATE_ONION:-0}

TOR_DATA_DIR=${TOR_DATA_DIR:-/var/lib/tor}

ensure_runtime() {
  mkdir -p /run /var/lib/tor /var/log/tor || true
  # Best-effort ownership; bind mounts might not allow this, but won't fail the script
  chown -R debian-tor:debian-tor /var/lib/tor 2>/dev/null || true
  chmod 700 /var/lib/tor 2>/dev/null || true
}

start_tor() {
  log "Starting Tor as debian-tor user..."
  tor -f /etc/tor/torrc &
  echo $! > "${TOR_DATA_DIR}/tor.pid" 2>/dev/null || true
  log "Tor started with PID: $(cat "${TOR_DATA_DIR}/tor.pid" 2>/dev/null || echo 'unknown')"
}

wait_for_file() {
  local f="$1"; local timeout="${2:-120}"
  log "Waiting for file ${f} (timeout ${timeout}s)..."
  local i=0
  while [ $i -lt "$timeout" ]; do
    [ -s "$f" ] && { log "Found ${f}"; return 0; }
    sleep 1; i=$((i+1))
  done
  log "ERROR: file not present: ${f}"
  return 1
}

ctl() {
  local cmd="$1"
  [ -f "$COOKIE_FILE" ] || { log "ERROR: Cookie file not found: $COOKIE_FILE"; return 1; }
  local cookie_hex
  cookie_hex=$(xxd -p "$COOKIE_FILE" 2>/dev/null | tr -d '\n' || echo "")
  [ -n "$cookie_hex" ] || { log "ERROR: Failed to read cookie file"; return 1; }
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" | nc -w 3 "$CONTROL_HOST" "$CONTROL_PORT" 2>/dev/null
}

resolve_upstream_ip() {
  # best-effort; optional
  local svc="$1" ip=""
  [ -z "$svc" ] && { echo ""; return 0; }
  if command -v getent >/dev/null 2>&1; then
    ip=$(getent hosts "$svc" 2>/dev/null | awk '{print $1}' | head -1 || true)
  fi
  if [ -z "$ip" ] && command -v nslookup >/dev/null 2>&1; then
    ip=$(nslookup -timeout=2 "$svc" 2>/dev/null | awk '/^Address: /{print $2; exit}' || true)
  fi
  echo "$ip"
}

wait_for_bootstrap() {
  log "Waiting for Tor bootstrap to reach 100%..."
  local i=0 max_attempts=180
  while [ $i -lt "$max_attempts" ]; do
    # Use busybox grep explicitly (distroless-compatible)
    local out
    out=$(ctl "GETINFO status/bootstrap-phase" 2>/dev/null || true)
    if echo "$out" | /bin/busybox grep -q 'PROGRESS=100'; then
      log "Bootstrap complete (100%)"
      return 0
    fi
    sleep 2; i=$((i+1))
    if [ $((i % 15)) -eq 0 ]; then
      log "Bootstrap in progress... (attempt $i/$max_attempts)"
    fi
  done
  log "WARNING: Tor bootstrap did not reach 100% within timeout"
  return 1
}

create_ephemeral_onion() {
  [ "$CREATE_ONION" = "1" ] || { log "CREATE_ONION=0 — skipping onion creation"; return 0; }
  [ -n "$UPSTREAM_SERVICE" ] || { log "No UPSTREAM_SERVICE configured — skipping onion creation"; return 0; }

  log "Resolving upstream service: $UPSTREAM_SERVICE"
  local ip="" tries=30
  while [ $tries -gt 0 ]; do
    ip=$(resolve_upstream_ip "$UPSTREAM_SERVICE")
    [ -n "$ip" ] && { log "Resolved $UPSTREAM_SERVICE to $ip"; break; }
    log "Waiting for DNS resolution... ($tries attempts remaining)"
    sleep 2; tries=$((tries-1))
  done
  [ -n "$ip" ] || { log "ERROR: unable to resolve ${UPSTREAM_SERVICE} — skipping onion creation"; return 1; }

  command -v nc >/dev/null 2>&1 && nc -z -w 2 "$ip" "$UPSTREAM_PORT" >/dev/null 2>&1 || true

  local add_onion="ADD_ONION NEW:ED25519-V3 Port=80,${ip}:${UPSTREAM_PORT}"
  log "Creating ephemeral onion: 80 -> ${ip}:${UPSTREAM_PORT}"
  local out; out=$(ctl "$add_onion" 2>/dev/null || true)
  if echo "$out" | /bin/busybox grep -q '250-ServiceID='; then
    local onion; onion=$(echo "$out" | awk -F= '/250-ServiceID=/{print $2}').onion
    log "ONION created: ${onion}"
    # Persist to @constants onion-state volume
    echo "ONION=${onion}" > /run/lucid/onion/current.onion 2>/dev/null || true
    return 0
  fi
  log "ERROR creating onion"
  printf '%s\n' "$out" | head -5
  return 1
}

main() {
  log "=== Lucid Tor Proxy Starting ==="
  log "Platform: ${LUCID_PLATFORM:-arm64}"
  log "Environment: ${LUCID_ENV:-production}"
  log "SOCKS Port: ${TOR_SOCKS_PORT}"
  log "Control Port: ${CONTROL_PORT}"
  log "Upstream Service: ${UPSTREAM_SERVICE:-<not configured>}"

  ensure_runtime
  start_tor

  if ! wait_for_file "$COOKIE_FILE" 120; then
    log "FATAL: Tor control cookie not created"
    exit 1
  fi

  wait_for_bootstrap || log "Continuing despite bootstrap warning..."
  create_ephemeral_onion || log "Onion creation skipped or failed"

  log "Tor proxy ready - waiting for process..."
  if [ -f "${TOR_DATA_DIR}/tor.pid" ]; then
    wait "$(cat "${TOR_DATA_DIR}/tor.pid")" 2>/dev/null || true
  else
    wait || true
  fi
}

main "$@"