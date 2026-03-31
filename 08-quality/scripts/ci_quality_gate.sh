#!/bin/bash
# CI entrypoint for the project's unified quality gate.
# File: /app/08-quality/scripts/ci_quality_gate.sh
# x-lucid-file-path: /app/08-quality/scripts/ci_quality_gate.sh
# x-lucid-file-directory: /app/08-quality/scripts
# x-lucid-file-type: shell

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="${ROOT_DIR}/08-quality/scripts/run_all_tests.sh"

echo "==> [ci_quality_gate] Running unified quality gate"
bash "${GATE}"
