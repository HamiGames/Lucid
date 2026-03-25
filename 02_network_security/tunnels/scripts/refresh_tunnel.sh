#!/usr/bin/env bash
# Refresh (recreate) the onion tunnel by rotating it and verifying reachability.
# Path: 02_network_security/tunnels/scripts/refresh_tunnel.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

ROTATE="${SCRIPT_DIR}/rotate_onion.sh"
VERIFY="${SCRIPT_DIR}/verify_tunnel.sh"

UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
PORTS="${PORTS:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
ENV_FILE="${ENV_FILE:-${WRITE_ENV}}"

"${ROTATE}" --control-host "${CONTROL_HOST}" --ports "${PORTS}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
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
