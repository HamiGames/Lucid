#!/usr/bin/env bash
# Lucid RDP — lint OpenAPI contract
# File: /app/03_api_gateway/scripts/lint_contract.sh
# x-lucid-file-path: /app/03_api_gateway/scripts/lint_contract.sh
# x-lucid-file-directory: /app/03_api_gateway/scripts
# x-lucid-file-type: shell
# Path: 03-api-gateway/scripts/lint_contract.sh

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")/../.." && pwd)")"
cd "$ROOT_DIR"

SPEC_FILE="03-api-gateway/gateway/openapi.yaml"

echo "[lint_contract] Linting with Redocly CLI…"
npx --yes @redocly/cli@latest lint "$SPEC_FILE"
