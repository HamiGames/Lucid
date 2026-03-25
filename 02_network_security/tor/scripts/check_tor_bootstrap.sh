#!/usr/bin/env bash
# Path: 02_network_security/tor/scripts/check_tor_bootstrap.sh
# Verify Tor bootstrap status (Dockerfile.tor-proxy-02 distroless: busybox + nc + xxd under /app).
#
# Terminal DIR when exec'd in container: WORKDIR /app (USER debian-tor).

set -euo pipefail

log() { printf '[check_tor_bootstrap] %s\n' "$*"; }
die() { printf '[check_tor_bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ -d /app/usr/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/usr/bin:"* ]] && PATH="/app/usr/bin:${PATH:-}"
fi
if [[ -d /app/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/bin:"* ]] && PATH="/app/bin:${PATH:-}"
fi
export PATH

BB="${BUSYBOX:-}"
[[ -z "$BB" && -x /app/bin/busybox ]] && BB="/app/bin/busybox"
[[ -z "$BB" && -x /bin/busybox ]] && BB="/bin/busybox"
[[ -z "$BB" ]] && BB="busybox"

TOR_CONTROL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_DATA_DIR="${TOR_DATA_DIR:-/app/run/lucid/tor}"
COOKIE="${TOR_DATA_DIR}/control_auth_cookie"

_tor_process_running() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -x tor >/dev/null 2>&1
    return
  fi
  "${BB}" ps 2>/dev/null | "${BB}" grep -q '[t]or' || return 1
  return 0
}

if ! _tor_process_running; then
  die "Tor is not running"
fi
log "Tor process is running"

[[ -f "$COOKIE" ]] || die "Cookie file not found: $COOKIE"

if command -v xxd >/dev/null 2>&1; then
  COOKIE_HEX="$(xxd -p "$COOKIE" | "${BB}" tr -d '\n')"
else
  die "xxd not found (expected /app/usr/bin/xxd in tor-proxy-02)"
fi

NC_BIN="nc"
if ! command -v nc >/dev/null 2>&1; then
  [[ -x /app/usr/bin/nc ]] && NC_BIN="/app/usr/bin/nc"
fi

STATUS="$(
  printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n' "$COOKIE_HEX" \
    | "${NC_BIN}" -w 5 "$TOR_CONTROL_HOST" "$TOR_CONTROL_PORT" 2>/dev/null \
    | "${BB}" grep -i "bootstrap-phase" | "${BB}" head -n 1 || true
)"

if echo "$STATUS" | "${BB}" grep -q "PROGRESS=100"; then
  log "SUCCESS: Tor is fully bootstrapped"
  exit 0
elif [[ -n "$STATUS" ]]; then
  log "WAITING: $STATUS"
  exit 1
else
  log "No bootstrap status found"
  exit 1
fi
