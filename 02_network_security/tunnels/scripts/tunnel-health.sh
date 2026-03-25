#!/usr/bin/env bash
# Tunnel Tools Health Check Script
# Path: 02_network_security/tunnels/scripts/tunnel-health.sh
# See: 02_network_security/tunnels/Dockerfile ENV (CONTROL_*, COOKIE_FILE, WRITE_ENV)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

STATUS_JSON_PATH="${STATUS_JSON_PATH:-/app/run/lucid/onion/tunnel_status.json}"
OUTDIR="${OUTDIR:-/app/run/lucid/onion}"

HEALTH_STATUS="unknown"
HEALTH_MESSAGE=""
EXIT_CODE=1

if [[ ! -s "$COOKIE_FILE" ]]; then
  HEALTH_STATUS="unhealthy"
  HEALTH_MESSAGE="Cookie file missing or empty at $COOKIE_FILE"
  EXIT_CODE=1
else
  HEX=""
  if command -v xxd >/dev/null 2>&1; then
    HEX="$(xxd -p "$COOKIE_FILE" | tr -d '\n' 2>/dev/null || true)"
  elif command -v hexdump >/dev/null 2>&1; then
    HEX="$(hexdump -v -e '1/1 "%02x"' "$COOKIE_FILE" 2>/dev/null || true)"
  else
    HEALTH_STATUS="unhealthy"
    HEALTH_MESSAGE="No hexdump tool available (xxd or hexdump)"
    EXIT_CODE=1
  fi

  if [[ -z "${HEX:-}" && "$HEALTH_STATUS" == "unknown" ]]; then
    HEALTH_STATUS="unhealthy"
    HEALTH_MESSAGE="Failed to read cookie file"
    EXIT_CODE=1
  elif [[ -n "${HEX:-}" ]]; then
    REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO version\r\nQUIT\r\n' "$HEX")
    OUT="$(printf '%s' "$REQ" | nc -w 3 "$CONTROL_HOST" "$CONTROL_PORT" 2>/dev/null || true)"

    if echo "$OUT" | grep -q "^250 OK"; then
      VERSION="$(echo "$OUT" | sed -n 's/^250-version=//p' | tr -d '\r' || true)"
      if [[ -f "$STATUS_JSON_PATH" ]]; then
        HEALTH_STATUS="healthy"
        HEALTH_MESSAGE="Tunnel tools operational (Tor ${VERSION:-ok})"
        EXIT_CODE=0
      else
        HEALTH_STATUS="degraded"
        HEALTH_MESSAGE="Tor connected but status file not found at $STATUS_JSON_PATH"
        EXIT_CODE=0
      fi
    else
      HEALTH_STATUS="unhealthy"
      HEALTH_MESSAGE="Tor control port authentication failed"
      EXIT_CODE=1
    fi
  fi
fi

STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "$(date +%s)")"
mkdir -p "$OUTDIR" 2>/dev/null || true

cat > "$OUTDIR/tunnel_health.json" <<EOF
{
  "status": "$HEALTH_STATUS",
  "message": "$HEALTH_MESSAGE",
  "timestamp": "$STAMP",
  "checks": {
    "cookie_file": {
      "path": "$COOKIE_FILE",
      "exists": $([ -s "$COOKIE_FILE" ] && echo "true" || echo "false")
    },
    "tor_control": {
      "host": "$CONTROL_HOST",
      "port": $CONTROL_PORT,
      "reachable": $([ "$HEALTH_STATUS" != "unhealthy" ] && echo "true" || echo "false")
    },
    "status_file": {
      "path": "$STATUS_JSON_PATH",
      "exists": $([ -f "$STATUS_JSON_PATH" ] && echo "true" || echo "false")
    }
  }
}
EOF

cat > "$OUTDIR/tunnel_health.env" <<EOF
TUNNEL_HEALTH_STATUS=$HEALTH_STATUS
TUNNEL_HEALTH_MESSAGE=$HEALTH_MESSAGE
TUNNEL_HEALTH_TIMESTAMP=$STAMP
EOF

echo "[hc] $HEALTH_MESSAGE"
exit "$EXIT_CODE"
