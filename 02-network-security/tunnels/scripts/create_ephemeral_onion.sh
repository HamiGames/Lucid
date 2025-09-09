#!/usr/bin/env bash
# Create an ephemeral Onion service via Tor ControlPort.
# Works both on host (via docker exec) and inside the tor container.

set -euo pipefail

usage() {
  echo "Usage: $0 --host <HOST_IP> --ports \"80 lucid_api:8081\""
}

HOST=""
PORTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --ports) PORTS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[create_ephemeral_onion] Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$HOST" ]] || { echo "[create_ephemeral_onion] --host required" >&2; exit 1; }
[[ -n "$PORTS" ]] || { echo "[create_ephemeral_onion] --ports required" >&2; exit 1; }

IN_CONTAINER=false
[[ -f "/.dockerenv" ]] && IN_CONTAINER=true

cookie_hex_host() {
  docker exec lucid_tor xxd -p /var/lib/tor/control_auth_cookie 2>/dev/null | tr -d '\n'
}
cookie_hex_container() {
  xxd -p /var/lib/tor/control_auth_cookie 2>/dev/null | tr -d '\n'
}

build_control_cmds() {
  local cookie_hex="$1"
  local cmds="AUTHENTICATE ${cookie_hex}\nADD_ONION NEW:ED25519-V3"
  # Validate `<VIRTUAL_PORT> <HOST:PORT>` and convert to Tor's `Port=VIRTUAL,HOST:PORT`
  for p in $PORTS; do
    # split into two tokens per mapping
    local vport target
    vport=$(echo "$p" | cut -d' ' -f1)
    target=$(echo "$p" | cut -d' ' -f2-)
    [[ "$vport" =~ ^[0-9]+$ ]] || { echo "[create_ephemeral_onion] invalid VPORT in '$p'"; exit 1; }
    echo "$target" | grep -Eq '^[A-Za-z0-9_.:-]+:[0-9]+$' || { echo "[create_ephemeral_onion] invalid target in '$p'"; exit 1; }
    cmds="${cmds} Port=${vport},${target}"
  done
  printf "%b\n" "${cmds}\nQUIT\n"
}

if $IN_CONTAINER; then
  cookie=$(cookie_hex_container || true)
  [[ -n "$cookie" ]] || { echo "[create_ephemeral_onion] ERROR: no cookie in container"; exit 1; }
  CONTROL_CMDS=$(build_control_cmds "$cookie")
  OUTPUT=$(printf "%b" "$CONTROL_CMDS" | nc -w 3 127.0.0.1 9051 || true)
else
  docker ps --format '{{.Names}}' | grep -q '^lucid_tor$' || { echo "[create_ephemeral_onion] ERROR: lucid_tor not running"; exit 1; }
  cookie=$(cookie_hex_host || true)
  [[ -n "$cookie" ]] || { echo "[create_ephemeral_onion] ERROR: could not read cookie from container"; exit 1; }
  CONTROL_CMDS=$(build_control_cmds "$cookie")
  OUTPUT=$(docker exec -i lucid_tor sh -c "printf '%b' \"$CONTROL_CMDS\" | nc -w 3 127.0.0.1 9051" || true)
fi

ONION=$(echo "$OUTPUT" | awk -F= '/250-ServiceID=/{print $2}').onion
[[ "$ONION" != ".onion" ]] && [[ -n "$ONION" ]] || { echo "[create_ephemeral_onion] ERROR: Failed to create onion"; echo "$OUTPUT"; exit 1; }
echo "[create_ephemeral_onion] ONION=${ONION}"
