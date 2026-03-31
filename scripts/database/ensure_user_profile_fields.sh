#!/usr/bin/env bash
# Path: scripts/database/ensure_user_profile_fields.sh
# File: /app/scripts/database/ensure_user_profile_fields.sh
# x-lucid-file-path: /app/scripts/database/ensure_user_profile_fields.sh
# x-lucid-file-directory: /app/scripts/database
# x-lucid-file-type: shell
# Ensures MongoDB users have contact_profile / lucid_env fields (see ensure_user_profile_fields.js).
#
# Usage (Pi / local):
#   PROJECT_ROOT=/app bash scripts/database/ensure_user_profile_fields.sh
#
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
JS_FILE="${PROJECT_ROOT}/scripts/database/ensure_user_profile_fields.js"
CONTAINER="${MONGODB_CONTAINER:-lucid-mongodb}"

if [[ ! -f "$JS_FILE" ]]; then
  echo "Missing $JS_FILE" >&2
  exit 1
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  echo "Running via docker exec $CONTAINER ..."
  docker exec -i "$CONTAINER" mongosh lucid <"$JS_FILE"
else
  if ! command -v mongosh >/dev/null 2>&1; then
    echo "mongosh not found and container $CONTAINER not running. Start MongoDB or run:" >&2
    echo "  mongosh \"\$MONGODB_URL\" < scripts/database/ensure_user_profile_fields.js" >&2
    exit 1
  fi
  URI="${MONGODB_URL:-mongodb://127.0.0.1:27017/lucid}"
  echo "Running mongosh against $URI ..."
  mongosh "$URI" <"$JS_FILE"
fi

echo "ensure_user_profile_fields: done."
