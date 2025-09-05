#!/usr/bin/env bash
# Lucid RDP — run black formatter across the repo
# Path: 00-foundation/workspace/tasks/format_all.sh

set -euo pipefail

# --- Locate repo root (git) or fallback ---
if ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
cd "$ROOT_DIR"

echo "==> Formatting all Python files with black"
black . --exclude '(\.venv|\.git|\.pre-commit-cache|\.tmp)'
