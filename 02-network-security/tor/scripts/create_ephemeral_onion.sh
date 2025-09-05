#!/usr/bin/env bash
# Lucid RDP — create ephemeral onion service
# Path: 02-network-security/tor/scripts/create_ephemeral_onion.sh

set -euo pipefail

usage() {
  echo "Usage: $0 --host <ip> --ports \"80 lucid_api:8080\""
  exit 1
}

HOST_IP=""
PORTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST_IP="$2"
      shift 2
      ;;
    --ports)
      PORTS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      ;;
  esac
done

if [[ -z "$HOST_IP" || -z "$PORTS" ]]; then
  echo "[create_ephemeral_onion] ERROR: Missing required args"
  usage
fi

echo "[create_ephemeral_onion] Checking Tor bootstrap state..."
if ! curl -s --socks5-hostname 127.0.0.1:9050 http://check.torproject.org >/dev/null; then
  echo "[create_ephemeral_onion] ERROR: Tor is not bootstrapped"
  exit 1
fi

echo "[create_ephemeral_onion] Tor bootstrap complete"

# Convert ports string into Tor control ADD_ONION format
PORT_ARGS=()
for mapping in $PORTS; do
  PORT_ARGS+=("Port=$mapping")
done

CONTROL_CMD="ADD_ONION NEW:BEST Port=${PORT_ARGS[*]}"
echo "[create_ephemeral_onion] Connecting to Tor ControlPort at 127.0.0.1:9051"

ONION_ADDR=$(printf "%s\n" "$CONTROL_CMD" | nc 127.0.0.1 9051 | awk '/ServiceID/ {print $2".onion"}')

if [[ -n "$ONION_ADDR" ]]; then
  echo "[create_ephemeral_onion] SUCCESS: Created onion service at $ONION_ADDR"
  echo "$ONION_ADDR"
else
  echo "[create_ephemeral_onion] FAIL: Could not create onion service"
  exit 1
fi
