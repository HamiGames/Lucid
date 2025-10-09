#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
API_DIR="$REPO_ROOT/03-api-gateway/api"

echo "[fix] ensuring FastAPI/Pydantic/etc are installed…"
if [[ -f "$API_DIR/requirements.txt" ]]; then
  pip install -r "$API_DIR/requirements.txt"
else
  pip install "fastapi>=0.111,<1.0" "uvicorn[standard]>=0.30" "pydantic>=2.5,<3.0" "python-dotenv>=1.0"
fi

echo "[fix] writing pyproject.toml for editable install…"
cat > "$API_DIR/pyproject.toml" <<'TOML'
[project]
name = "lucid-api"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111,<1.0",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.5,<3.0",
  "python-dotenv>=1.0",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["app"]
TOML

echo "[fix] installing api package in editable mode…"
pip install -e "$API_DIR"

echo "[fix] configuring VS Code/Pylance extraPaths…"
mkdir -p "$REPO_ROOT/.vscode"
cat > "$REPO_ROOT/.vscode/settings.json" <<'JSON'
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/03-api-gateway/api"
  ],
  "python.analysis.typeCheckingMode": "basic",
  "python.defaultInterpreterPath": "/usr/local/bin/python"
}
JSON

echo "[fix] verifying imports…"
python - <<'PY'
import sys; print("[python]", sys.executable)
import fastapi, pydantic
print("[ok] fastapi", fastapi.__version__, "pydantic", pydantic.__version__)
PY

echo "==> Done. In VS Code: Command Palette → “Developer: Reload Window”, then Problems will clear."
