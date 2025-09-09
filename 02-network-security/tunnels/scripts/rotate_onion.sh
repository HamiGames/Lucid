#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

CONTAINER="lucid_tor"
HOST="127.0.0.1"
PORTS="80 lucid_api_gateway:8080"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --ports) PORTS="$2"; shift 2 ;;
    --container) CONTAINER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

load_env
wait_bootstrap "$CONTAINER"

COOKIE="${COOKIE:-}"
if [[ -z "$COOKIE" ]]; then
  COOKIE="$(hex_from_cookie_in_container "$CONTAINER")"
  [[ -n "$COOKIE" ]] && save_env_var "COOKIE" "$COOKIE"
fi
AUTH="AUTHENTICATE \"$COOKIE\"\r\n"

# delete old
if [[ -n "${ONION:-}" ]]; then
  SID="${ONION%.onion}"
  tor_ctl "$CONTAINER" "${AUTH}DEL_ONION ${SID}\r\nQUIT\r\n" >/dev/null || true
fi

# recreate
PORT_LINES=""
while read -r v; do
  [[ -z "$v" ]] && continue
  VPORT="$(echo "$v" | awk '{print $1}')"
  TGT="$(echo "$v" | awk '{print $2}')"
  PORT_LINES="${PORT_LINES}Port=${VPORT},${TGT}\r\n"
done < <(echo "$PORTS" | tr ',' '\n')

RESP="$(tor_ctl "$CONTAINER" "${AUTH}ADD_ONION NEW:ED25519-V3\r\n${PORT_LINES}QUIT\r\n")"
SERVICE_ID="$(echo "$RESP" | awk -F= '/250-ServiceID=/{print $2}' | tr -d '\r')"
[[ -z "$SERVICE_ID" ]] && { echo "[rotate_onion] failed:\n$RESP" >&2; exit 3; }

ONION_ADDR="${SERVICE_ID}.onion"
save_env_var "ONION" "$ONION_ADDR"
echo "$ONION_ADDR"
