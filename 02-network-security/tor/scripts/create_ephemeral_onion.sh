#!/usr/bin/env bash
# Path: 02-network-security/tor/scripts/create_ephemeral_onion.sh
# Creates an ephemeral onion service via Tor ControlPort

set -euo pipefail

CONTROL_PORT=9051
COOKIE_FILE=/var/lib/tor/control.authcookie
ONION_PORTS=""
HOST="127.0.0.1"
env_file="/workspaces/Lucid/06-orchestration-runtime/compose/.env"

log() { printf '[create_ephemeral_onion] %s\n' "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --ports) ONION_PORTS="$2"; shift 2 ;;
    *) log "Unknown arg: $1"; exit 1 ;;
  esac
done

[[ -z "$ONION_PORTS" ]] && { log "No ports provided"; exit 1; }

# Authenticate with Tor ControlPort
COOKIE=$(xxd -p "$COOKIE_FILE" | tr -d '\n')
AUTH="AUTHENTICATE $COOKIE\r\n"
ADD_ONION="ADD_ONION NEW:ED25519-V3 Port=$ONION_PORTS\r\n"
QUIT="QUIT\r\n"

REPLY=$(printf "$AUTH$ADD_ONION$QUIT" | nc 127.0.0.1 $CONTROL_PORT)

ONION_ADDR=$(echo "$REPLY" | grep -oE '[a-z0-9]{56}\.onion' | head -n1)

if [[ -n "$ONION_ADDR" ]]; then
  log "Ephemeral onion created: $ONION_ADDR"
  sed -i "/^ONION=/c\ONION=$ONION_ADDR" "$env_file"
else
  log "Failed to create ephemeral onion"
  exit 1
fi
