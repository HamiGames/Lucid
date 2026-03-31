#!/bin/bash
# Path: infrastructure/docker/common/scripts/server-tools/db-backup.sh
set -euo pipefail

readonly BACKUP_DIR="${LUCID_BACKUP_DIR:-/app/var/log/lucid/backups}"
readonly KEEP_BACKUPS="${LUCID_BACKUP_KEEP:-5}"

timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="lucid_backup_${timestamp}.gz"

mkdir -p "$BACKUP_DIR"
mongodump --uri="${MONGO_URL:-mongodb://localhost:27017}" --archive="$BACKUP_DIR/$backup_file" --gzip
echo "Backup: $BACKUP_DIR/$backup_file"

if ls -t "$BACKUP_DIR"/lucid_backup_*.gz >/dev/null 2>&1; then
    ls -t "$BACKUP_DIR"/lucid_backup_*.gz | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm -f
fi
