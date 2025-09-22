#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

./seed_env.sh
docker buildx ls >/dev/null 2>&1 || docker buildx create --use --name lucid-builder

DOCKER_DEFAULT_PLATFORM=linux/arm64 \
docker compose \
  -f "${here}/lucid-dev.yaml" \
  -f "${here}/lucid-dev.local.yaml" \
  --profile dev up -d --build

docker compose -f "${here}/lucid-dev.yaml" -f "${here}/lucid-dev.local.yaml" ps
