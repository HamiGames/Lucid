#!/usr/bin/env bash
# Lucid Tor Proxy — robust entrypoint aligned with plan/constants/
# Distroless-compatible, runs as debian-tor user

set -Eeuo pipefail

log() { printf '[tor-entrypoint] %s\n' "$*"; }

# Environment variables from .env.tor-proxy, .env.secrets, .env.foundation
CONTROL_HOST=${CONTROL_HOST:-127.0.0.1}
CONTROL_PORT=${TOR_CONTROL_PORT:-9051}
COOKIE_FILE=${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}
UPSTREAM_SERVICE=${UPSTREAM_SERVICE:-}
UPSTREAM_PORT=${UPSTREAM_PORT:-8081}
CREATE_ONION=${CREATE_ONION:-1}
ONION_COUNT=${ONION_COUNT:-5}

# Network configuration from constants (lucid-pi-network: 172.20.0.0/16)
TOR_SOCKS_PORT=${TOR_SOCKS_PORT:-9050}
TOR_DATA_DIR=${TOR_DATA_DIR:-/var/lib/tor}

ensure_runtime() {
  # Ensure runtime directories exist (already owned by debian-tor from Dockerfile)
  mkdir -p /run /var/lib/tor /var/log/tor || true
  
  # Only chown if needed (usually already correct from Dockerfile COPY --chown)
  if [ -d /var/lib/tor ] && [ "$(stat -c '%U:%G' /var/lib/tor 2>/dev/null)" != "debian-tor:debian-tor" ]; then
    chown -R debian-tor:debian-tor /var/lib/tor 2>/dev/null || true
  fi
  
  chmod 700 /var/lib/tor 2>/dev/null || true
}

start_tor() {
  log "Starting Tor as debian-tor user..."
  # Run tor directly - we're already debian-tor user (no su-exec needed)
  tor -f /etc/tor/torrc &
  echo $! > /run/tor.pid || true
  log "Tor started with PID: $(cat /run/tor.pid 2>/dev/null || echo 'unknown')"
}

wait_for_file() {
  local f="$1"
  local timeout="${2:-120}"
  log "Waiting for file ${f} (timeout ${timeout}s)..."
  local i=0
  while [ $i -lt "$timeout" ]; do
    if [ -s "$f" ] 2>/dev/null; then
      log "Found ${f}"
      return 0
    fi
    sleep 1
    i=$((i+1))
  done
  log "ERROR: file not present: ${f}"
  return 1
}

ctl() {
  local cmd="$1"
  local cookie_hex
  if [ ! -f "$COOKIE_FILE" ]; then
    log "ERROR: Cookie file not found: $COOKIE_FILE"
    return 1
  fi
  cookie_hex=$(xxd -p "$COOKIE_FILE" 2>/dev/null | tr -d '\n' || echo "")
  if [ -z "$cookie_hex" ]; then
    log "ERROR: Failed to read cookie file"
    return 1
  fi
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" \
    | nc -w 5 "$CONTROL_HOST" "$CONTROL_PORT" 2>/dev/null
}

resolve_upstream_ip() {
  local ip=""
  local service="$1"
  
  if [ -z "$service" ]; then
    return 0
  fi
  
  # Try getent first
  if command -v getent >/dev/null 2>&1; then
    ip=$(getent hosts "$service" 2>/dev/null | awk '{print $1}' | head -1 || true)
  fi
  
  # Fallback to nslookup
  if [ -z "$ip" ] && command -v nslookup >/dev/null 2>&1; then
    ip=$(nslookup -timeout=2 "$service" 2>/dev/null | awk '/^Address: /{print $2; exit}' || true)
  fi
  
  printf '%s' "$ip"
}

wait_for_bootstrap() {
  log "Waiting for Tor bootstrap to reach 100%..."
  local i=0
  local max_attempts=180
  
  while [ $i -lt "$max_attempts" ]; do
    local status
    status=$(ctl "GETINFO status/bootstrap-phase" 2>/dev/null | grep -o 'PROGRESS=100' || true)
    
    if [ -n "$status" ]; then
      log "Bootstrap complete (100%)"
      return 0
    fi
    
    sleep 2
    i=$((i+1))
    
    # Log progress every 30 seconds
    if [ $((i % 15)) -eq 0 ]; then
      log "Bootstrap in progress... (attempt $i/$max_attempts)"
    fi
  done
  
  log "WARNING: Tor bootstrap did not reach 100% within timeout"
  return 1
}

create_ephemeral_onion() {
  # Skip if CREATE_ONION is disabled
  [ "$CREATE_ONION" = "1" ] || { log "CREATE_ONION=0 — skipping onion creation"; return 0; }
  
  # Skip if no upstream service configured (foundation phase)
  if [ -z "$UPSTREAM_SERVICE" ]; then
    log "No UPSTREAM_SERVICE configured — skipping onion creation (foundation phase)"
    return 0
  fi
  
  log "Resolving upstream service: $UPSTREAM_SERVICE"
  local ip=""
  local tries=30
  
  while [ $tries -gt 0 ]; do
    ip=$(resolve_upstream_ip "$UPSTREAM_SERVICE")
    if [ -n "$ip" ]; then
      log "Resolved $UPSTREAM_SERVICE to $ip"
      break
    fi
    log "Waiting for DNS resolution... ($tries attempts remaining)"
    sleep 2
    tries=$((tries-1))
  done
  
  if [ -z "$ip" ]; then
    log "ERROR: unable to resolve ${UPSTREAM_SERVICE} — skipping onion creation"
    return 1
  fi
  
  # Optional connectivity check
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 2 "$ip" "$UPSTREAM_PORT" >/dev/null 2>&1 || \
      log "WARN: upstream $ip:$UPSTREAM_PORT not reachable yet"
  fi
  
  local add_onion="ADD_ONION NEW:ED25519-V3 Port=80,${ip}:${UPSTREAM_PORT}"
  log "Creating ephemeral onion: 80 -> ${ip}:${UPSTREAM_PORT}"
  
  local out
  out=$(ctl "$add_onion" 2>/dev/null || true)
  
  if echo "$out" | grep -q '250-ServiceID='; then
    local onion
    onion=$(echo "$out" | awk -F= '/250-ServiceID=/{print $2}').onion
    log "ONION created: ${onion}"
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
  
  # Wait for bootstrap (non-fatal for foundation phase)
  wait_for_bootstrap || log "Continuing despite bootstrap warning..."
  
  # Create onion if configured (non-fatal)
  create_ephemeral_onion || log "Onion creation skipped or failed"
  
  log "Tor proxy ready - waiting for process..."
  
  # Wait for tor process
  if [ -f /run/tor.pid ]; then
    wait "$(cat /run/tor.pid)" 2>/dev/null || true
  else
    # Fallback: wait for any tor process
    wait || true
  fi
}

main "$@"