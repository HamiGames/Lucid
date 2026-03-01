#!/bin/bash
set -euo pipefail

LOG_DIR="${JAVA_BASE_LOG_DIR:-/var/log/java-base}"
LOG_FILE="${LOG_DIR}/bootstrap.log"

log() {
  local level="$1"; shift
  mkdir -p "$LOG_DIR"
  printf '[java-base][%s] %s\n' "$level" "$*" | tee -a "$LOG_FILE"
}

if [[ $# -gt 0 ]]; then
  log INFO "Launching custom command: $*"
  exec "$@"
fi

log INFO "Java base image standing by."
exec tail -f /dev/null
