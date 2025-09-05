#!/usr/bin/env bash
# Lucid RDP — run pytest across the repo with coverage
# Path: 00-foundation/workspace/tasks/test_all.sh

set -euo pipefail

# --- Locate repo root (git) or fallback ---
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
cd "$ROOT_DIR"

: "${COVERAGE_MIN:=70}"   # default coverage threshold

echo "==> Running pytest with coverage (min: ${COVERAGE_MIN}%)"

if [ -d "tests" ]; then
  pytest --cov=src --cov-report=term-missing --cov-fail-under="${COVERAGE_MIN}" tests
else
  echo "WARN: No tests/ directory found. Running pytest on src/ only."
  pytest --cov=src --cov-report=term-missing --cov-fail-under="${COVERAGE_MIN}" src || true
fi
