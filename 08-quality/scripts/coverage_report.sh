#!/usr/bin/env bash
# Generate coverage HTML report and terminal summary.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/.reports/coverage"
mkdir -p "${REPORT_DIR}"

echo "==> [coverage_report] Running pytest with coverage"
pytest -q --maxfail=1 --cov="${ROOT_DIR}" --cov-report=term-missing --cov-report=html:"${REPORT_DIR}/html" tests

echo "==> [coverage_report] HTML report: ${REPORT_DIR}/html/index.html"
