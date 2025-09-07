#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/compose_build_tor.sh
# Build Tor container only (service typically named tor-proxy).

set -euo pipefail

if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then :; else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

COMPOSE_FILE="${ROOT_DIR}/06-orchestration-runtime/compose/lucid-dev.yaml"

SERVICE="${1:-tor-proxy}"
echo "[compose_build_tor] Building service: ${SERVICE}"
docker compose -f "${COMPOSE_FILE}" build "${SERVICE}"
