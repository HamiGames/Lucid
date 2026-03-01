#!/usr/bin/env bash
# Path: setup_pytest.sh
# Fix pytest integration for Lucid RDP project

set -euo pipefail

log() { printf '[setup_pytest] %s\n' "$*"; }

# --- Ensure __init__.py exists in api directory ---
API_DIR="03-api-gateway/api"
if [ ! -d "$API_DIR" ]; then
  log "ERROR: $API_DIR does not exist."
  exit 1
fi

if [ ! -f "$API_DIR/__init__.py" ]; then
  echo "# Marks api directory as a package" > "$API_DIR/__init__.py"
  log "Created $API_DIR/__init__.py"
else
  log "$API_DIR/__init__.py already exists"
fi

# --- Create pytest.ini at repo root ---
PYTEST_INI="pytest.ini"
cat > "$PYTEST_INI" <<'INI'
# Path: pytest.ini
[pytest]
minversion = 6.0
addopts = -ra -q
testpaths = tests
pythonpath = 03-api-gateway/api
INI
log "Created/updated $PYTEST_INI"

# --- Ensure tests directory exists ---
TESTS_DIR="tests"
mkdir -p "$TESTS_DIR"

# --- Add basic health check test ---
TEST_FILE="$TESTS_DIR/test_health.py"
if [ ! -f "$TEST_FILE" ]; then
  cat > "$TEST_FILE" <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "lucid_api"
PY
  log "Created $TEST_FILE"
else
  log "$TEST_FILE already exists"
fi

log "✅ Pytest setup complete. You can now run: pytest"
