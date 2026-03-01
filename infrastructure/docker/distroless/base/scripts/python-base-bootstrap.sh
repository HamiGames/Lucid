#!/bin/bash
set -euo pipefail

LOG_DIR="${PYTHON_BASE_LOG_DIR:-/var/log/python-base}"
LOG_FILE="${LOG_DIR}/bootstrap.log"

log() {
  local level="$1"; shift
  mkdir -p "$LOG_DIR"
  printf '[python-base][%s] %s\n' "$level" "$*" | tee -a "$LOG_FILE"
}

if [[ $# -gt 0 ]]; then
  log INFO "Executing custom command: $*"
  exec "$@"
fi

log INFO "Python base container idle. Override with docker exec as needed."
exec tail -f /dev/null