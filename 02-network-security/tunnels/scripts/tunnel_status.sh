#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

ONION_ARG=""
PATH_CHECK="/gateway/health"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --onion) ONION_ARG="$2"; shift 2 ;;
    --path) PATH_CHECK="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

load_env
ADDR="${ONION_ARG:-${ONION:-}}"
[[ -z "$ADDR" ]] && { echo "[tunnel_status] No onion address provided or found in .env"; exit 2; }

URL="http://${ADDR}${PATH_CHECK}"
echo "[tunnel_status] Testing ${URL} via SOCKS5 127.0.0.1:9050"
if curl -sS --max-time 10 --socks5-hostname 127.0.0.1:9050 "$URL" > /dev/null; then
  echo "OK"
else
  echo "FAIL"
  exit 1
fi
