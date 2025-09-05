#!/usr/bin/env bash
# Lucid RDP — seed .env file for compose
# Path: 06-orchestration-runtime/compose/seed_env.sh

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
env_file="${script_dir}/.env"

if [[ -f "$env_file" ]]; then
  echo "[seed_env] OK: $env_file already exists"
  exit 0
fi

cat > "$env_file" <<'EOF'
# Lucid RDP — Dev environment variables
BLOCK_ONION=
BLOCK_RPC_URL=
EOF

echo "[seed_env] Created $env_file"
