#!/usr/bin/env bash
# Tunnel Tools Health Check Script
# Outputs JSON status for monitoring and health checks
# All configuration from environment variables - no hardcoded values
# Compatible with distroless containers

set -euo pipefail

# Load configuration from environment
COOKIE_FILE="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
CONTROL_PORT="${CONTROL_PORT:-9051}"
STATUS_JSON_PATH="${STATUS_JSON_PATH:-/run/lucid/onion/tunnel_status.json}"
WRITE_ENV="${WRITE_ENV:-/run/lucid/onion/.onion.env}"
OUTDIR="${OUTDIR:-/run/lucid/onion}"

# Health check result
HEALTH_STATUS="unknown"
HEALTH_MESSAGE=""
EXIT_CODE=1

# Check if cookie file exists and is readable
if [[ ! -s "$COOKIE_FILE" ]]; then
    HEALTH_STATUS="unhealthy"
    HEALTH_MESSAGE="Cookie file missing or empty at $COOKIE_FILE"
    EXIT_CODE=1
else
    # Try to read cookie hex
    if command -v xxd >/dev/null 2>&1; then
        HEX="$(xxd -p "$COOKIE_FILE" | tr -d '\n' 2>/dev/null || true)"
    elif command -v hexdump >/dev/null 2>&1; then
        HEX="$(hexdump -v -e '1/1 "%02x"' "$COOKIE_FILE" 2>/dev/null || true)"
    else
        HEALTH_STATUS="unhealthy"
        HEALTH_MESSAGE="No hexdump tool available (xxd or hexdump)"
        EXIT_CODE=1
    fi
    
    if [[ -n "${HEX:-}" ]]; then
        # Test Tor control port connection
        REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO version\r\nQUIT\r\n' "$HEX")
        OUT="$(printf '%s' "$REQ" | nc -w 3 "$CONTROL_HOST" "$CONTROL_PORT" 2>/dev/null || true)"
        
        if echo "$OUT" | grep -q "^250 OK"; then
            VERSION="$(echo "$OUT" | sed -n 's/^250-version=//p' | tr -d '\r' || true)"
            
            # Check if status JSON exists
            if [[ -f "$STATUS_JSON_PATH" ]]; then
                HEALTH_STATUS="healthy"
                HEALTH_MESSAGE="Tunnel tools operational"
                EXIT_CODE=0
            else
                HEALTH_STATUS="degraded"
                HEALTH_MESSAGE="Tor connected but status file not found"
                EXIT_CODE=0
            fi
        else
            HEALTH_STATUS="unhealthy"
            HEALTH_MESSAGE="Tor control port authentication failed"
            EXIT_CODE=1
        fi
    else
        HEALTH_STATUS="unhealthy"
        HEALTH_MESSAGE="Failed to read cookie file"
        EXIT_CODE=1
    fi
fi

# Get timestamp
STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "$(date +%s)")"

# Create output directory
mkdir -p "$OUTDIR"

# Write health status to JSON
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

# Write health status to .env file for shell script compatibility
cat > "$OUTDIR/tunnel_health.env" <<EOF
TUNNEL_HEALTH_STATUS=$HEALTH_STATUS
TUNNEL_HEALTH_MESSAGE=$HEALTH_MESSAGE
TUNNEL_HEALTH_TIMESTAMP=$STAMP
EOF

# Output status
echo "[hc] $HEALTH_MESSAGE"
exit $EXIT_CODE

