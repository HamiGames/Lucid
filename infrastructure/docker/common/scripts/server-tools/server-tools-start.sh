#!/bin/bash
# Path: infrastructure/docker/common/scripts/server-tools/server-tools-start.sh
# Installed on builder as /usr/local/bin/server-tools-start.sh; runtime CMD.
set -euo pipefail

echo "[server-tools] env=${LUCID_ENV:-dev}"
sleep 10
/app/lucid/scripts/health-check.sh || true
exec tail -f /dev/null
