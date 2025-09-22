#!/usr/bin/env bash
# Bring up the Lucid dev stack using lucid-dev.yaml
set -euo pipefail
here="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose="$here/lucid-dev.yaml"
envfile="$here/.env"

log(){ printf '[compose_up_dev] %s\n' "$*"; }
die(){ printf '[compose_up_dev] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "$compose" ]] || die "missing compose file: $compose"

# seed env
if [[ -x "$here/seed_env.sh" ]]; then
  "$here/seed_env.sh" "$envfile"
fi

# buildx for arm64
docker buildx create --use --name lucid-builder >/dev/null 2>&1 || true
docker buildx use lucid-builder
docker buildx inspect --bootstrap >/dev/null

DOCKER_DEFAULT_PLATFORM=linux/arm64 \
docker compose -f "$compose" --profile dev up -d --build

docker compose -f "$compose" ps
log "Done."
