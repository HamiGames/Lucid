#!/usr/bin/env bash
# Health check for the onion tunnel via SOCKS5 (9050). Uses curl if available.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/.env"
TOR_SOCKS="${TOR_SOCKS:-127.0.0.1:9050}"
TIMEOUT="${TIMEOUT:-10}"

# shellcheck disable=SC1090
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"
ONION="${ONION:-}"

if [[ -z "${ONION}" ]]; then
  echo "[tunnel_status] ONION not set in ${ENV_FILE}"
  exit 2
fi

URL="http://${ONION}/health"
echo "[tunnel_status] Checking ${URL} via SOCKS5 ${TOR_SOCKS} (timeout=${TIMEOUT}s)"

if command -v curl >/dev/null 2>&1; then
  set +e
  BODY="$(curl -sS --max-time "${TIMEOUT}" --socks5-hostname "${TOR_SOCKS}" "${URL}")"
  CODE=$?
  set -e
  if [[ ${CODE} -eq 0 ]]; then
    echo "[tunnel_status] OK"
    echo "${BODY}"
    exit 0
  else
    echo "[tunnel_status] FAIL (curl exit=${CODE})"
    exit ${CODE}
  fi
else
  echo "[tunnel_status] curl not found; cannot test"
  exit 3
fi
