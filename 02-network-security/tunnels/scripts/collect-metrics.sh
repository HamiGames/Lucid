#!/usr/bin/env bash
# Collect Tunnel Tools Metrics Script
# Collects operational metrics and updates metrics JSON file
# All configuration from environment variables - no hardcoded values

set -euo pipefail

# Load configuration from environment
METRICS_JSON_PATH="${METRICS_JSON_PATH:-/var/lib/tunnel/metrics.json}"
STATUS_JSON_PATH="${STATUS_JSON_PATH:-/run/lucid/onion/tunnel_status.json}"
WRITE_ENV="${WRITE_ENV:-/run/lucid/onion/.onion.env}"
METRICS_ENABLED="${METRICS_ENABLED:-true}"

# Check if metrics collection is enabled
if [[ "${METRICS_ENABLED}" != "true" ]]; then
    echo "[collect-metrics] Metrics collection disabled"
    exit 0
fi

# Create metrics directory if it doesn't exist
mkdir -p "$(dirname "$METRICS_JSON_PATH")"

# Check if Python is available (for metrics module)
if ! command -v python3 >/dev/null 2>&1; then
    echo "[collect-metrics] WARNING: python3 not available, using basic metrics collection"
    
    # Basic metrics collection without Python
    CURRENT_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +%s)"
    ONION_ADDRESS=""
    
    # Try to read onion address from env file
    if [[ -f "$WRITE_ENV" ]]; then
        ONION_ADDRESS="$(grep "^ONION=" "$WRITE_ENV" 2>/dev/null | cut -d'=' -f2- || true)"
    fi
    
    # Create basic metrics structure
    if [[ ! -f "$METRICS_JSON_PATH" ]]; then
        cat > "$METRICS_JSON_PATH" <<EOF
{
  "version": "1.0.0",
  "started_at": "$CURRENT_TIME",
  "last_updated": "$CURRENT_TIME",
  "counters": {
    "onion_creations": 0,
    "onion_rotations": 0,
    "verification_successes": 0,
    "verification_failures": 0,
    "errors": 0,
    "recoveries": 0
  },
  "current_state": {
    "onion_address": "${ONION_ADDRESS:-null}",
    "onion_created_at": null,
    "status": "unknown",
    "last_verification": null,
    "verification_status": null
  },
  "history": []
}
EOF
    else
        # Update last_updated timestamp
        if command -v jq >/dev/null 2>&1; then
            jq ".last_updated = \"$CURRENT_TIME\"" "$METRICS_JSON_PATH" > "${METRICS_JSON_PATH}.tmp" && \
            mv "${METRICS_JSON_PATH}.tmp" "$METRICS_JSON_PATH"
        fi
    fi
    
    echo "[collect-metrics] Basic metrics updated"
    exit 0
fi

# Use Python metrics module if available
if [[ -f "/app/tunnel_metrics.py" ]]; then
    python3 -c "
import sys
sys.path.insert(0, '/app')
from tunnel_metrics import get_metrics
import json

metrics = get_metrics()
print(json.dumps(metrics.get_summary(), indent=2))
" > /dev/null 2>&1 && echo "[collect-metrics] Metrics collected via Python module" || \
    echo "[collect-metrics] WARNING: Failed to collect metrics via Python module"
else
    echo "[collect-metrics] WARNING: tunnel_metrics.py not found, using basic collection"
fi

exit 0

