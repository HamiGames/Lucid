#!/usr/bin/env sh
set -eu

LOG_DIR="${LUCID_BASE_LOG_DIR:-/var/log/lucid-base}"
LOG_FILE="$LOG_DIR/bootstrap.log"

log() {
  level="$1"
  shift
  mkdir -p "$LOG_DIR"
  printf '[lucid-base][%s] %s\n' "$level" "$*" | tee -a "$LOG_FILE"
}

if [ "$#" -gt 0 ]; then
  log INFO "Custom command received: $*"
  exec "$@"
fi

log INFO "Lucid base runtime ready. Sleeping indefinitely."
exec tail -f /dev/null