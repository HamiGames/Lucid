#!/usr/bin/env bash
# Restart only the Tor proxy service in the Lucid dev stack
# Path: 06-orchestration-runtime/compose/compose_restart_tor.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
compose_file="${script_dir}/lucid-dev.yaml"

log() { printf '[compose_restart_tor] %s\n' "$*"; }
die() { printf '[compose_restart_tor] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "${compose_file}" ]] || die "missing compose file: ${compose_file}"

log "Rebuilding and restarting tor-proxy service..."
docker compose -f "${compose_file}" up -d --build tor-proxy

log "tor-proxy restarted."
