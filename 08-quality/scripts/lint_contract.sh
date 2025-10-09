#!/usr/bin/env bash
# Lint & validate OpenAPI contract with Redocly + OpenAPI Generator.
# Matches the tooling you've been using in logs.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC="${ROOT_DIR}/03-api-gateway/gateway/openapi.yaml"

echo "==> [lint_contract] Linting with Redocly CLI…"
npx --yes @redocly/cli@latest lint "${SPEC}"

echo "==> [lint_contract] Validating with OpenAPI Generator…"
npx --yes @openapitools/openapi-generator-cli@latest validate -i "${SPEC}"

echo "==> [lint_contract] Done"
