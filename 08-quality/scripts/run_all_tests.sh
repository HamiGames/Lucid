#!/usr/bin/env bash
set -euo pipefail
# File: /app/08-quality/scripts/run_all_tests.sh
# x-lucid-file-path: /app/08-quality/scripts/run_all_tests.sh
# x-lucid-file-directory: /app/08-quality/scripts
# x-lucid-file-type: shell
echo "==> Lucid RDP quality gate"
echo "==> Formatting (black)"
black --check . || (echo "Reformatting..." && black .)
echo "==> Lint (ruff)"
ruff check .
echo "==> Tests (pytest)"
pytest -q
