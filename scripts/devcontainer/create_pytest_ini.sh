#!/usr/bin/env bash
# Path: create_pytest_ini.sh
# File: /app/scripts/devcontainer/create_pytest_ini.sh
# x-lucid-file-path: /app/scripts/devcontainer/create_pytest_ini.sh
# x-lucid-file-directory: /app/scripts/devcontainer
# x-lucid-file-type: shell
# Create pytest.ini at repo root for Lucid RDP project

set -euo pipefail

FILE="pytest.ini"

cat > "$FILE" <<'INI'
# Path: pytest.ini
[pytest]
minversion = 6.0
addopts = -ra -q
testpaths = tests
pythonpath =
    03-api-gateway/api
INI

echo "[create_pytest_ini] Created $FILE with pytest configuration."
