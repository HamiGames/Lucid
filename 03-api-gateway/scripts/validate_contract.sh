#!/usr/bin/env bash
# Validate Lucid RDP API contract (OpenAPI 3.0+)
# Path: 03-api-gateway/scripts/validate_contract.sh

set -euo pipefail

API_SPEC="03-api-gateway/gateway/openapi.yaml"

log() { printf '[validate_contract] %s\n' "$*"; }
die() { printf '[validate_contract] ERROR: %s\n' "$*" >&2; exit 1; }

# Ensure OpenAPI spec exists
[[ -f "$API_SPEC" ]] || die "Spec not found: $API_SPEC"

# Run validation with OpenAPI Generator CLI
log "Validating $API_SPEC..."
npx --yes @openapitools/openapi-generator-cli@latest validate -i "$API_SPEC"

log "Validation complete."
