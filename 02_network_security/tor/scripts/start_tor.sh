#!/usr/bin/env bash
# Path: 02_network_security/tor/scripts/start_tor.sh
# Ensure Tor is running — intended for lucid tor-proxy container (Dockerfile.tor-proxy-02).
#
# Terminal DIR when exec'd in container: WORKDIR /app (USER debian-tor).

set -euo pipefail

log() { printf '[start_tor] %s\n' "$*"; }
die() { printf '[start_tor] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ -d /app/usr/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/usr/bin:"* ]] && PATH="/app/usr/bin:${PATH:-}"
fi
if [[ -d /app/bin ]]; then
  [[ ":${PATH:-}:" != *":/app/bin:"* ]] && PATH="/app/bin:${PATH:-}"
fi
export PATH

TORRC="${TORRC:-/app/run/lucid/tor/torrc}"
TOR_BIN="tor"
command -v tor >/dev/null 2>&1 || TOR_BIN="/app/usr/bin/tor"
[[ -x "$TOR_BIN" ]] || die "tor binary not found (expected PATH or /app/usr/bin/tor)"

BB="${BUSYBOX:-}"
[[ -z "$BB" && -x /app/bin/busybox ]] && BB="/app/bin/busybox"
[[ -z "$BB" && -x /bin/busybox ]] && BB="/bin/busybox"
[[ -z "$BB" ]] && BB="busybox"

_tor_running() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -x tor >/dev/null 2>&1
    return
  fi
  "${BB}" ps 2>/dev/null | "${BB}" grep -q '[t]or' || return 1
  return 0
}

if _tor_running; then
  log "Tor is already running"
  exit 0
fi

log "Tor is not running — starting..."
"${TOR_BIN}" -f "$TORRC" || die "Failed to start Tor"
log "Tor process started"
