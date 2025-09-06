#!/usr/bin/env bash
set -euo pipefail

APP_MODULE="api.app.main:app"
HOST="0.0.0.0"
PORT="${PORT:-8080}"
RELOAD="--reload"

echo "[dev_server] Starting Lucid API on http://${HOST}:${PORT} ..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" $RELOAD
