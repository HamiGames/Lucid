#!/bin/bash
# Lucid Tor Proxy — entrypoint for distroless runtime
# Aligned with @constants: TOR_PROXY_* env vars, CREATE_ONION=0 default, /run/lucid/onion state

set -eu

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
    local out
    out=$(ctl "GETINFO status/bootstrap-phase" 2>/dev/null || true)
    # Robust detection: strip CR/LF, normalize whitespace, check for PROGRESS=100
    local cleaned
    cleaned=$(echo "$out" | /bin/busybox tr -d '\r' | /bin/busybox tr '\n' ' ' | /bin/busybox sed 's/  */ /g')
    # Check for PROGRESS=100 pattern (handles both "PROGRESS=100" and "250-status/bootstrap-phase=...PROGRESS=100")
    if echo "$cleaned" | /bin/busybox grep -o 'PROGRESS=[0-9]*' | /bin/busybox grep -q 'PROGRESS=100'; then
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

copy_cookie_to_shared() {
  local cookie_src="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
  local cookie_dest="${COOKIE_FILE_SHARED:-/run/lucid/onion/control_auth_cookie}"
  local max_wait=60
  local waited=0
  
  log "Copying cookie to shared volume for tunnel-tools access..."
  
  # Wait for cookie file if it doesn't exist yet
  while [ ! -f "$cookie_src" ] && [ $waited -lt $max_wait ]; do
    sleep 1
    waited=$((waited + 1))
  done
  
  if [ ! -f "$cookie_src" ]; then
    log "WARNING: Cookie file not found: $cookie_src"
    return 1
  fi
  
  # Get destination directory using pure bash parameter expansion (distroless-compatible)
  # ${cookie_dest%/*} removes the shortest match of /* from the end
  # This is pure bash - no external commands required
  local dest_dir="${cookie_dest%/*}"
  
  # Ensure destination directory exists and is writable (best-effort)
  if ! mkdir -p "$dest_dir" 2>/dev/null; then
    log "WARNING: Cannot create destination directory: $dest_dir (continuing anyway)"
  fi
  
  # Check if directory is writable (best-effort)
  if [ ! -w "$dest_dir" ]; then
    log "WARNING: Destination directory is not writable: $dest_dir (continuing anyway)"
  fi
  
  # Copy with world-readable permissions so tunnel-tools (UID 65532) can read it
  # Use busybox cp (distroless doesn't have cp in PATH)
  if /bin/busybox cp "$cookie_src" "$cookie_dest" 2>/dev/null; then
    # Set permissions: owner read/write, group read, others read (644)
    if chmod 644 "$cookie_dest" 2>/dev/null; then
      log "Cookie copied to $cookie_dest (readable by tunnel-tools)"
      return 0
    else
      log "WARNING: Cookie copied but chmod failed - tunnel-tools may not be able to read it"
      return 0  # Still return success as copy worked
    fi
  else
    log "ERROR: Failed to copy cookie using busybox cp, trying cat method..."
    # Fallback to cat method (busybox cat with redirection)
    if /bin/busybox cat "$cookie_src" > "$cookie_dest" 2>/dev/null; then
      chmod 644 "$cookie_dest" 2>/dev/null || true
      log "Cookie copied using cat method to $cookie_dest"
      return 0
    else
      log "WARNING: Failed to copy cookie to shared volume (both cp and cat methods failed)"
      log "Source: $cookie_src (exists: $([ -f "$cookie_src" ] && echo 'yes' || echo 'no'))"
      log "Destination: $cookie_dest (dir writable: $([ -w "$dest_dir" ] && echo 'yes' || echo 'no'))"
      log "Continuing anyway - tunnel-tools will try to access direct mount"
      return 0  # Non-fatal: allow tor-proxy to continue
    fi
  fi
}

monitor_and_copy_cookie() {
  local cookie_src="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
  local cookie_dest="${COOKIE_FILE_SHARED:-/run/lucid/onion/control_auth_cookie}"
  
  log "Starting cookie monitor (background)..."
  while true; do
    if [ -f "$cookie_src" ]; then
      # Get destination directory using pure bash parameter expansion (distroless-compatible)
      local dest_dir="${cookie_dest%/*}"
      
      # Ensure directory exists and is writable
      if mkdir -p "$dest_dir" 2>/dev/null && [ -w "$dest_dir" ]; then
        # Only copy if source is newer or destination doesn't exist
        if [ ! -f "$cookie_dest" ] || [ "$cookie_src" -nt "$cookie_dest" ]; then
          # Use busybox cp (distroless doesn't have cp in PATH)
          if /bin/busybox cp "$cookie_src" "$cookie_dest" 2>/dev/null; then
            chmod 644 "$cookie_dest" 2>/dev/null || true
            log "Updated cookie in shared volume"
          else
            # Fallback to cat method
            if /bin/busybox cat "$cookie_src" > "$cookie_dest" 2>/dev/null; then
              chmod 644 "$cookie_dest" 2>/dev/null || true
              log "Updated cookie in shared volume (using cat method)"
            else
              log "ERROR: Failed to update cookie in shared volume"
            fi
          fi
        fi
      fi
    fi
    sleep 10  # Check every 10 seconds
  done
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

  # Copy cookie to shared volume for tunnel-tools access
  copy_cookie_to_shared || log "WARNING: Cookie copy failed, tunnel-tools may not have access"
  
  # Start background monitor to keep cookie updated
  monitor_and_copy_cookie &

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