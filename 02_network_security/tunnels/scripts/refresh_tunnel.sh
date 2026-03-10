#!/usr/bin/env bash
# Refresh (recreate) the onion tunnel by rotating it and verifying reachability.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROTATE="${SCRIPT_DIR}/rotate_onion.sh"
VERIFY="${SCRIPT_DIR}/verify_tunnel.sh"

# Load defaults from environment variables
CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
PORTS="${PORTS:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
ENV_FILE="${ENV_FILE:-${WRITE_ENV:-/run/lucid/onion/.onion.env}}"

"${ROTATE}" --control-host "${CONTROL_HOST}" --ports "${PORTS}"

# Reload env from the correct location
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi
ONION="${ONION:-}"

if [[ -z "${ONION}" ]]; then
  echo "[refresh_tunnel] ERROR: ONION not set after rotation" >&2
  exit 1
fi

"${VERIFY}" --onion "http://${ONION}/" || {
  echo "[refresh_tunnel] Verification failed for ${ONION}" >&2
  exit 2
}

echo "[refresh_tunnel] OK: ${ONION} reachable via SOCKS5"

