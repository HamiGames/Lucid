#!/usr/bin/env bash
# CI entrypoint for the project's unified quality gate.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="${ROOT_DIR}/08-quality/scripts/run_all_tests.sh"

echo "==> [ci_quality_gate] Running unified quality gate"
bash "${GATE}"
