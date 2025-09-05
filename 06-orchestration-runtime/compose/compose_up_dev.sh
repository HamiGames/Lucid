#!/usr/bin/env bash
# Lucid RDP — bring up the dev stack
# Path: 06-orchestration-runtime/compose/compose_up_dev.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
compose_file="${script_dir}/lucid-dev.yaml"
env_file="${script_dir}/.env"

log() { printf '[compose_up_dev] %s\n' "$*"; }
die() { printf '[compose_up_dev] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "${compose_file}" ]] || die "missing compose file: ${compose_file}"

if [[ -x "${script_dir}/seed_env.sh" ]]; then
  "${script_dir}/seed_env.sh"
elif [[ ! -f "${env_file}" ]]; then
  log "WARN: ${env_file} not found and seed_env.sh missing; proceeding without it"
fi

log "docker compose -f ${compose_file} --profile dev up -d --build"
docker compose -f "${compose_file}" --profile dev up -d --build

docker compose -f "${compose_file}" ps
log "Done."
