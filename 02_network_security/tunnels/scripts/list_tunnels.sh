#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

FORMAT="${1:-text}"
load_env
if [[ "$FORMAT" == "json" ]]; then
  printf '{"onion":"%s"}\n' "${ONION:-}"
else
  echo "ONION=${ONION:-}"
fi
