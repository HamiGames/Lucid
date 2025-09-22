#!/usr/bin/env bash
# Lucid RDP — run ruff linter across the repo
# Path: 00-foundation/workspace/tasks/lint_all.sh

set -euo pipefail

# --- Locate repo root (git) or fallback ---
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
cd "$ROOT_DIR"

echo "==> Linting all Python files with ruff"
ruff check . --exclude .venv --exclude .git --exclude .pre-commit-cache --exclude .tmp
