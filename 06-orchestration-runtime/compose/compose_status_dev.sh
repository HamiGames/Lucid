#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/compose_status_dev.sh
# Show running services, health, ports for the dev stack.

set -euo pipefail

# Locate repo root (prefer git)
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then :; else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

COMPOSE_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/lucid-dev.yaml"

echo "[compose_status_dev] Using compose file: ${COMPOSE_FILE}"
docker compose -f "${COMPOSE_FILE}" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo
echo "[compose_status_dev] Recent logs (last 50 lines) for key services:"
for s in lucid_api lucid_tor tor-proxy; do
  if docker ps --format '{{.Names}}' | grep -q "^${s}\$"; then
    echo "---- ${s} ----"
    docker logs --tail 50 "${s}" || true
    echo
  fi
done
