#!/usr/bin/env bash
# Pi-side watcher: pull main & (re)deploy with docker compose.
# Intended to be called by systemd service/timer created by install_watcher.sh.

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/lucid}"
if [ ! -d "$REPO_DIR" ] && [ -d "/workspaces/Lucid" ]; then
  REPO_DIR="/workspaces/Lucid"
fi

log() { printf '[pi_watcher] %s\n' "$*"; }

cd "${REPO_DIR}"
log "git fetch --all --prune"
git fetch --all --prune
log "git reset --hard origin/main"
git reset --hard origin/main

log "docker compose -f ${COMPOSE_FILE} --profile ${PROFILE} up -d --build"
docker compose -f "${COMPOSE_FILE}" --profile "${PROFILE}" up -d --build

log "docker compose -f ${COMPOSE_FILE} ps"
docker compose -f "${COMPOSE_FILE}" ps
