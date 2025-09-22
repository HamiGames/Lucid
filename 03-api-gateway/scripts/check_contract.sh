#!/usr/bin/env bash
# Combined contract check (lint + validate) for Lucid RDP API
# Path: 03-api-gateway/scripts/check_contract.sh

set -euo pipefail

LINT_SCRIPT="03-api-gateway/scripts/lint_contract.sh"
VALIDATE_SCRIPT="03-api-gateway/scripts/validate_contract.sh"

log() { printf '[check_contract] %s\n' "$*"; }
die() { printf '[check_contract] ERROR: %s\n' "$*" >&2; exit 1; }

# Ensure both scripts exist
[[ -x "$LINT_SCRIPT" ]] || die "Missing or not executable: $LINT_SCRIPT"
[[ -x "$VALIDATE_SCRIPT" ]] || die "Missing or not executable: $VALIDATE_SCRIPT"

log "Running lint..."
"$LINT_SCRIPT"

log "Running validate..."
"$VALIDATE_SCRIPT"

log "All contract checks passed."
