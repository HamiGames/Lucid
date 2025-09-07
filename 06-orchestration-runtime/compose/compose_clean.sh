#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/compose_clean.sh
# Prune containers/images/networks. Use --force to skip prompt.

set -euo pipefail

FORCE="${1:-}"

confirm() {
  if [[ "${FORCE}" == "--force" ]]; then return 0; fi
  read -r -p "[compose_clean] Prune dangling containers/images/networks? [y/N] " ans
  [[ "${ans:-N}" =~ ^[Yy]$ ]]
}

if confirm; then
  echo "[compose_clean] Removing stopped containers..."
  docker container prune -f
  echo "[compose_clean] Removing dangling images..."
  docker image prune -f
  echo "[compose_clean] Removing unused networks..."
  docker network prune -f
  echo "[compose_clean] Removing unused volumes (optional)..."
  docker volume prune -f || true
  echo "[compose_clean] Done."
else
  echo "[compose_clean] Aborted."
fi
