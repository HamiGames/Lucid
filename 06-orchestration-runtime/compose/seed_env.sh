#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/seed_env.sh
# Seeds .env with required Tor variables

set -euo pipefail
env_file="$(dirname "$0")/.env"

log() { printf '[seed_env] %s\n' "$*"; }

touch "$env_file"

# Add defaults if not already present
grep -q '^ONION=' "$env_file" 2>/dev/null || echo "ONION=" >> "$env_file"
grep -q '^COOKIE=' "$env_file" 2>/dev/null || echo "COOKIE=" >> "$env_file"
grep -q '^HEX=' "$env_file" 2>/dev/null || echo "HEX=" >> "$env_file"

log "Seeded environment file: $env_file"
