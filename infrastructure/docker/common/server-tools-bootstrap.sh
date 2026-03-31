#!/bin/bash
set -euo pipefail
# File: /app/configs/docker//common/server-tools-bootstrap.sh
# x-lucid-file-path: /app/configs/docker//common/server-tools-bootstrap.sh
# x-lucid-file-directory: /app/configs/docker//common
# x-lucid-file-type: shell

if [[ $# -gt 0 ]]; then
    exec "$@"
fi

echo "[lucid-server-tools] $(date -u +'%Y-%m-%dT%H:%M:%SZ') :: ready. Waiting for exec commands."
exec tail -f /dev/null
