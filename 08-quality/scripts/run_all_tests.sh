#!/usr/bin/env bash
set -euo pipefail
echo "==> Lucid RDP quality gate"
echo "==> Formatting (black)"
black --check . || (echo "Reformatting..." && black .)
echo "==> Lint (ruff)"
ruff check .
echo "==> Tests (pytest)"
pytest -q
