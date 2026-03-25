#!/usr/bin/env bash
# Path: 02_network_security/tunnels/scripts/list_tunnels.sh
# Reads ONION from WRITE_ENV (see _lib.sh / tunnels/Dockerfile).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lib.sh"

FORMAT="${1:-text}"
load_env
if [[ "$FORMAT" == "json" ]]; then
  printf '{"onion":"%s"}\n' "${ONION:-}"
else
  echo "ONION=${ONION:-}"
fi
