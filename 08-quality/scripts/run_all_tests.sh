#!/usr/bin/env bash
# Lucid RDP — unified quality gate
# Path: 08-quality/scripts/run_all_tests.sh

set -euo pipefail

# --- Locate repo root ---
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
cd "$ROOT_DIR"

: "${COVERAGE_MIN:=70}"

FORMAT_SCRIPT="00-foundation/workspace/tasks/format_all.sh"
LINT_SCRIPT="00-foundation/workspace/tasks/lint_all.sh"
TEST_SCRIPT="00-foundation/workspace/tasks/test_all.sh"

echo "==> Lucid RDP quality gate"

"$FORMAT_SCRIPT"
"$LINT_SCRIPT"
COVERAGE_MIN="$COVERAGE_MIN" "$TEST_SCRIPT"
