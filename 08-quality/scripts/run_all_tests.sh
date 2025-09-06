#!/usr/bin/env bash
# Lucid RDP — unified quality gate (repo-aware, no fragile paths)
# Path: 08-quality/scripts/run_all_tests.sh

set -euo pipefail

# --- Locate repo root (git) or fall back to script-relative ---
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
cd "$ROOT_DIR"

# --- Config (override via env) ---
: "${REPORT_DIR:=.reports}"
: "${DEV_REQ:=.devcontainer/requirements-dev.txt}"  # dev tools live here

FORMAT_SCRIPT="00-foundation/workspace/tasks/format_all.sh"
LINT_SCRIPT="00-foundation/workspace/tasks/lint_all.sh"
TEST_SCRIPT="00-foundation/workspace/tasks/test_all.sh"

echo "==> Lucid RDP quality gate"

# --- Run format check ---
echo "==> Running format check"
if [[ -x "$FORMAT_SCRIPT" ]]; then
  "$FORMAT_SCRIPT"
else
  echo "[format] Skipped (missing: $FORMAT_SCRIPT)"
fi

# --- Run lint check ---
echo "==> Running lint check"
if [[ -x "$LINT_SCRIPT" ]]; then
  "$LINT_SCRIPT"
else
  echo "[lint] Skipped (missing: $LINT_SCRIPT)"
fi

# --- Run API contract check ---
echo "==> Running API contract check"
if [[ -x "03-api-gateway/scripts/check_contract.sh" ]]; then
  ./03-api-gateway/scripts/check_contract.sh
else
  echo "[check_contract] Skipped (missing: 03-api-gateway/scripts/check_contract.sh)"
fi

# --- Run tests with coverage (pytest.ini controls flags) ---
echo "==> Running pytest with coverage"
if [[ -x "$TEST_SCRIPT" ]]; then
  "$TEST_SCRIPT"
else
  echo "[tests] Skipped (missing: $TEST_SCRIPT)"
  exit 1
fi

echo "==> Quality gate complete"
