#!/usr/bin/env bash
# Collect Tunnel Tools Metrics Script
# Path: 02_network_security/tunnels/scripts/collect-metrics.sh
# Layout: 02_network_security/tunnels/Dockerfile (metrics under /app/run/lucid/...)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

METRICS_JSON_PATH="${METRICS_JSON_PATH:-/app/run/lucid/tunnels/metrics.json}"
STATUS_JSON_PATH="${STATUS_JSON_PATH:-/app/run/lucid/onion/tunnel_status.json}"
METRICS_ENABLED="${METRICS_ENABLED:-true}"

lucid_python_bin() {
  local p
  for p in /app/usr/local/bin/python3.11 python3.11 python3; do
    if [[ -x "$p" ]]; then
      printf '%s' "$p"
      return 0
    fi
    if command -v "$p" >/dev/null 2>&1; then
      command -v "$p"
      return 0
    fi
  done
  return 1
}

if [[ "${METRICS_ENABLED}" != "true" ]]; then
  echo "[collect-metrics] Metrics collection disabled"
  exit 0
fi

mkdir -p "$(dirname "$METRICS_JSON_PATH")" 2>/dev/null || true

PY="$(lucid_python_bin || true)"

if [[ -z "$PY" ]]; then
  echo "[collect-metrics] WARNING: Python not found, using basic metrics collection"
  CURRENT_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +%s)"
  ONION_ADDRESS=""
  if [[ -f "$WRITE_ENV" ]]; then
    ONION_ADDRESS="$(grep "^ONION=" "$WRITE_ENV" 2>/dev/null | cut -d'=' -f2- || true)"
  fi
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
    if command -v jq >/dev/null 2>&1; then
      jq ".last_updated = \"$CURRENT_TIME\"" "$METRICS_JSON_PATH" > "${METRICS_JSON_PATH}.tmp" && \
        mv "${METRICS_JSON_PATH}.tmp" "$METRICS_JSON_PATH"
    fi
  fi
  echo "[collect-metrics] Basic metrics updated"
  exit 0
fi

METRICS_PY="/app/tunnels/tunnel_metrics.py"
if [[ -f "$METRICS_PY" ]]; then
  if "$PY" -c "
import sys
sys.path.insert(0, '/app/tunnels')
from tunnel_metrics import get_metrics
import json
m = get_metrics()
print(json.dumps(m.get_summary(), indent=2))
" >/dev/null 2>&1; then
    echo "[collect-metrics] Metrics collected via Python module"
  else
    echo "[collect-metrics] WARNING: Failed to collect metrics via Python module"
  fi
else
  echo "[collect-metrics] WARNING: tunnel_metrics.py not found at $METRICS_PY"
fi

exit 0
