#!/usr/bin/env bash
# Bring up logs for the Lucid dev stack
# Path: 06-orchestration-runtime/compose/compose_logs_dev.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
compose_file="${script_dir}/lucid-dev.yaml"

log() { printf '[compose_logs_dev] %s\n' "$*"; }
die() { printf '[compose_logs_dev] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "${compose_file}" ]] || die "missing compose file: ${compose_file}"

log "Tailing logs for dev stack..."
exec docker compose -f "${compose_file}" logs -f
