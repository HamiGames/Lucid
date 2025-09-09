#!/usr/bin/env bash
# [compose_build_tor] Build the Tor proxy service image for the Lucid dev stack.
# Path: 06-orchestration-runtime/compose/compose_build_tor.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/lucid-dev.yaml"
SERVICE="tor-proxy"

usage() {
  cat <<USAGE
Usage: $0 [--help] [--build]

Options:
  --help    Show this help and exit.
  --build   Run docker compose build for ${SERVICE}.
  
If no option is provided, the script will print usage and exit.
This allows quick tests (e.g. pytest subprocess checks) to run fast.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

case "$1" in
  --help)
    usage
    ;;
  --build)
    echo "[compose_build_tor] Building service: ${SERVICE}"
    docker compose -f "${COMPOSE_FILE}" build "${SERVICE}"
    ;;
  *)
    echo "[compose_build_tor] ERROR: Unknown argument $1" >&2
    usage
    exit 1
    ;;
esac
