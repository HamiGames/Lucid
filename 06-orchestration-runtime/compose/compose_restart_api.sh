#!/usr/bin/env bash
# Restart only the API service in the Lucid dev stack
# Path: 06-orchestration-runtime/compose/compose_restart_api.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
compose_file="${script_dir}/lucid-dev.yaml"

log() { printf '[compose_restart_api] %s\n' "$*"; }
die() { printf '[compose_restart_api] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "${compose_file}" ]] || die "missing compose file: ${compose_file}"

log "Rebuilding and restarting lucid_api service..."
docker compose -f "${compose_file}" up -d --build lucid_api

log "lucid_api restarted."
