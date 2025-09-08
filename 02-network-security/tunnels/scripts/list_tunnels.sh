#!/usr/bin/env bash
# List active onion tunnels known to this dev stack.
# Ephemeral onions won't write /var/lib/tor/hidden_service/hostname; we surface current ONION from .env.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/.env"

ONION_ENV=""
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  ONION_ENV="${ONION:-}"
fi

echo "==> Tunnels"
if [[ -n "${ONION_ENV}" ]]; then
  echo "type=ephemeral; onion=${ONION_ENV}"
else
  echo "type=unknown; onion=(none found in ${ENV_FILE})"
fi

echo "==> Tor container"
if docker ps --format '{{.Names}} {{.Status}}' | grep -q '^lucid_tor '; then
  docker ps --format 'name={{.Names}} status={{.Status}} ports={{.Ports}}' | grep '^name=lucid_tor '
else
  echo "lucid_tor=(not running)"
fi

