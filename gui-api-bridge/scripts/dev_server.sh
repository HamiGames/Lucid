#!/usr/bin/env bash
# Start the GUI API Bridge in development mode with reload
# File: gui-api-bridge/scripts/dev_server.sh
# No hardcoded values - all from environment variables or defaults
# Safe PYTHONPATH and optional PORT configuration

set -euo pipefail

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=========================================="
echo "Starting Lucid GUI API Bridge (DEV MODE)"
echo "=========================================="
echo "Script Dir: $SCRIPT_DIR"
echo "Project Dir: $PROJECT_DIR"
echo "Workspace Dir: $WORKSPACE_DIR"
echo ""

# Load .env if it exists
if [ -f "$WORKSPACE_DIR/.env" ]; then
    echo "Loading environment from $WORKSPACE_DIR/.env"
    set -a
    source "$WORKSPACE_DIR/.env"
    set +a
fi

# Configuration (from environment or defaults)
export PYTHONPATH="${PYTHONPATH:-$WORKSPACE_DIR}"
PORT="${PORT:-8102}"
HOST="${HOST:-0.0.0.0}"
ENVIRONMENT="${ENVIRONMENT:-development}"
LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
DEBUG="${DEBUG:-true}"

# Database configuration (from environment or defaults)
MONGODB_URL="${MONGODB_URL:-mongodb://lucid:lucid@localhost:27017/?authSource=admin}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "Configuration:"
echo "  PORT: $PORT"
echo "  HOST: $HOST"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  ENVIRONMENT: $ENVIRONMENT"
echo "  LOG_LEVEL: $LOG_LEVEL"
echo "  MONGODB_URL: ${MONGODB_URL:0:50}..."
echo "  REDIS_URL: ${REDIS_URL:0:50}..."
echo ""

# Set environment variables
export PORT
export HOST
export PYTHONPATH
export ENVIRONMENT
export LOG_LEVEL
export DEBUG
export MONGODB_URL
export REDIS_URL

# Verify guicorn/uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn is not installed"
    echo "Install it with: pip install -r $PROJECT_DIR/requirements.txt"
    exit 1
fi

echo "Starting server..."
echo ""

# Start uvicorn with reload and the correct app module
# Navigate to workspace for correct module imports
cd "$WORKSPACE_DIR"

exec uvicorn gui_api_bridge.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-dir "$PROJECT_DIR" \
    --log-level "${LOG_LEVEL,,}"
