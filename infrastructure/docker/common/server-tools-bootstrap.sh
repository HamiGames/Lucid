#!/bin/bash
set -euo pipefail

if [[ $# -gt 0 ]]; then
    exec "$@"
fi

echo "[lucid-server-tools] $(date -u +'%Y-%m-%dT%H:%M:%SZ') :: ready. Waiting for exec commands."
exec tail -f /dev/null