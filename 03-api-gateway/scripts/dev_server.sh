#!/usr/bin/env bash
# Start the API in-dev with reload, safe PYTHONPATH, and optional PORT
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-/workspaces/Lucid}"
PORT="${PORT:-8081}"
MONGO_URL="${MONGO_URL:-mongodb://lucid:lucid@lucid_mongo:27017/?authSource=admin}"

echo "[dev_server] Starting Lucid API on http://0.0.0.0:${PORT} (MONGO_URL=${MONGO_URL}) ..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --reload
