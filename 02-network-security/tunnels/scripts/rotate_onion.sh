#!/usr/bin/env bash
# Rotate the ephemeral Onion address by invoking the project's creator script.
# Cross-refs: create_ephemeral_onion.sh, verify_tunnel.sh
# Requirements: docker running, lucid_tor container healthy, curl installed for checks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TOR_SOCKS="127.0.0.1:9050"
CREATE_SCRIPT="${ROOT_DIR}/02-network-security/tor/scripts/create_ephemeral_onion.sh"
ENV_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/.env"

usage() {
  cat <<USAGE
Usage: $0 --host <HOST_IP> [--ports "80 lucid_api:8080,443 lucid_api:8443"]
Rotates the ephemeral onion by re-running the canonical creator script, then writes ONION into ${ENV_FILE}.
USAGE
}

HOST_IP=""
PORTS="80 lucid_api:8080"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST_IP="$2"; shift 2 ;;
    --ports) PORTS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[rotate_onion] Unknown arg: $1" >&2; usage; exit 2 ;;
  case_esac_done
done

[[ -n "${HOST_IP}" ]] || { echo "[rotate_onion] --host required"; exit 2; }
[[ -x "${CREATE_SCRIPT}" ]] || { echo "[rotate_onion] Missing ${CREATE_SCRIPT}"; exit 2; }

echo "[rotate_onion] Rotating onion via ${CREATE_SCRIPT} ..."
ONION_ADDR="$("${CREATE_SCRIPT}" --host "${HOST_IP}" --ports "${PORTS}" | awk '/\[create_ephemeral_onion\] ONION=/{print $NF}' | tail -1)"

if [[ -z "${ONION_ADDR}" ]]; then
  echo "[rotate_onion] ERROR: Could not obtain new onion address" >&2
  exit 1
fi

mkdir -p "$(dirname "${ENV_FILE}")"
touch "${ENV_FILE}"
if grep -q '^ONION=' "${ENV_FILE}"; then
  sed -i.bak "s|^ONION=.*$|ONION=${ONION_ADDR}|" "${ENV_FILE}"
else
  echo "ONION=${ONION_ADDR}" >> "${ENV_FILE}"
fi

echo "[rotate_onion] New ONION=${ONION_ADDR}"
echo "[rotate_onion] Env updated at ${ENV_FILE}"
