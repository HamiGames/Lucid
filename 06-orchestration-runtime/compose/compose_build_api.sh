#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/compose_build_api.sh
# Build API container only.

set -euo pipefail

if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then :; else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

COMPOSE_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/lucid-dev.yaml"

echo "[compose_build_api] Building service: lucid_api"
docker compose -f "${COMPOSE_FILE}" build lucid_api
