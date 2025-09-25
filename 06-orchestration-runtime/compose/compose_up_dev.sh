#!/usr/bin/env bash
# Bring up the Lucid dev stack using lucid-dev.yaml on the Raspberry Pi daemon.
# Uses Buildx builder "lucidbx" and Docker context "lucid-pi".
# Ensures required volumes and network exist; validates .env for tor-proxy keys.
# FILE: ./06-orchestration-runtime/compose/compose_up_dev.sh
# RUN FROM DIR: ./06-orchestration-runtime/compose

set -Eeuo pipefail

here="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose="$here/lucid-dev.yaml"
envfile="$here/.env"

# fixed project-scoped names
builder_name="lucidbx"
context_name="lucid-pi"
platform="linux/arm64"
output_mode="--load"                  # use --push only with registry-tagged images
project_name="lucid-dev"              # ensures compose resources use this prefix

# resources (as requested)
volumes=( "lucid-dev_tor_data" "lucid-dev_onion_state" "mongo_data" )
network_name="lucid-dev_lucid_net"

log(){ printf '[compose_up_dev] %s\n' "$*"; }
die(){ printf '[compose_up_dev] ERROR: %s\n' "$*" >&2; exit 1; }

ensure_volume(){
  local v="$1"
  if ! docker --context "$context_name" volume inspect "$v" >/dev/null 2>&1; then
    log "creating volume: $v"
    docker --context "$context_name" volume create --name "$v" >/dev/null
  else
    log "volume exists: $v"
  fi
}

ensure_network(){
  local n="$1"
  if ! docker --context "$context_name" network inspect "$n" >/dev/null 2>&1; then
    log "creating network: $n"
    docker --context "$context_name" network create \
      --driver bridge \
      "$n" >/dev/null
  else
    log "network exists: $n"
  fi
}

# --- Preconditions -----------------------------------------------------------
command -v docker >/dev/null || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
[[ -f "$compose" ]] || die "missing compose file: $compose"

# must have the remote Pi context configured ahead of time
docker context inspect "$context_name" >/dev/null 2>&1 \
  || die "missing docker context \"$context_name\" (create once: docker context create $context_name --docker 'host=ssh://<pi-user>@<pi-host>')"

# BuildKit on; lock compose project name so resource prefixes match requests
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export COMPOSE_PROJECT_NAME="$project_name"

# --- Seed env ---------------------------------------------------------------
if [[ -x "$here/seed_env.sh" ]]; then
  "$here/seed_env.sh" "$envfile"
fi
[[ -f "$envfile" ]] || die "missing env file: $envfile"

# tor-proxy dev requirements (must exist in .env)
missing_env=0
for k in ONION COOKIE HEX; do
  if ! grep -E "^[[:space:]]*$k=" "$envfile" >/dev/null; then
    log "WARN: $k not found in $envfile"
    missing_env=1
  fi
done
(( missing_env == 0 )) || die "required tor-proxy keys not found in $envfile (run seed_env.sh to populate)"

# --- Ensure volumes & network (before any pulls/builds) ----------------------
for v in "${volumes[@]}"; do
  ensure_volume "$v"
done
ensure_network "$network_name"

# --- Buildx builder (on the Pi daemon via context) --------------------------
if ! docker --context "$context_name" buildx inspect "$builder_name" >/dev/null 2>&1; then
  log "creating buildx builder \"$builder_name\" on context \"$context_name\""
  docker --context "$context_name" buildx create \
    --driver docker-container \
    --name "$builder_name" \
    --use >/dev/null
fi
docker --context "$context_name" buildx use "$builder_name"
docker --context "$context_name" buildx inspect --bootstrap >/dev/null

# --- Pre-pull images referenced by compose (only those with image:) ----------
# (This does not build; it just pulls remote images so first up is faster.)
cd "$here"
log "pulling images on \"$context_name\" from compose"
docker --context "$context_name" compose -f "$compose" --profile dev pull

# --- Build local services (compose-as-bake; resolves build contexts correctly)
log "building images on \"$context_name\" via buildx bake (platform: $platform)"
docker --context "$context_name" buildx bake \
  -f "$compose" \
  --builder "$builder_name" \
  --set "*.platform=${platform}" \
  --pull \
  --provenance=false \
  ${output_mode}

# --- Start stack on the Pi (no rebuild here) --------------------------------
log "starting stack on \"$context_name\""
docker --context "$context_name" compose -f "$compose" --profile dev up -d --no-build

docker --context "$context_name" compose -f "$compose" ps
log "Done."
