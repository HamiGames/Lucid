#!/usr/bin/env bash
# Refresh (recreate) the onion tunnel by rotating it and verifying reachability.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ROTATE="${ROOT_DIR}/02-network-security/tunnels/scripts/rotate_onion.sh"
VERIFY="${ROOT_DIR}/02-network-security/tunnels/scripts/verify_tunnel.sh"

HOST_IP="${HOST_IP:-127.0.0.1}"
PORTS="${PORTS:-80 lucid_api:8080}"

"${ROTATE}" --host "${HOST_IP}" --ports "${PORTS}"

# Reload env
# shellcheck disable=SC1090
source "${ROOT_DIR}/06-orchestration-runtime/compose/.env"
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

