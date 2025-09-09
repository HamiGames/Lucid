#!/usr/bin/env bash
# Create an ephemeral Onion service via Tor ControlPort inside lucid_tor container.
# Path: 02-network-security/tor/scripts/create_ephemeral_onion.sh

set -euo pipefail

usage() {
  echo "Usage: $0 --host <HOST_IP> --ports \"80 127.0.0.1:8080,443 127.0.0.1:8443\""
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

# Ensure tor container is running
if ! docker ps --format '{{.Names}}' | grep -q '^lucid_tor$'; then
  echo "[create_ephemeral_onion] ERROR: lucid_tor container not running" >&2
  exit 1
fi

# Correct cookie file name (Tor writes control_auth_cookie, not control.authcookie)
COOKIE=$(docker exec lucid_tor xxd -p /var/lib/tor/control_auth_cookie 2>/dev/null | tr -d '\n' || true)

if [[ -z "$COOKIE" ]]; then
  echo "[create_ephemeral_onion] ERROR: Could not read /var/lib/tor/control_auth_cookie from lucid_tor" >&2
  exit 1
fi

# Build Tor control command for ephemeral onion
CONTROL_CMDS="AUTHENTICATE ${COOKIE}\nADD_ONION NEW:ED25519-V3"

# Validate and append Port mappings
for p in $PORTS; do
  if ! echo "$p" | grep -Eq '^[0-9]+ [0-9.]+:[0-9]+$'; then
    echo "[create_ephemeral_onion] ERROR: Invalid port mapping '$p'"
    echo "Use format: <VIRTUAL_PORT> <IP:PORT>, e.g. \"80 127.0.0.1:8080\""
    exit 1
  fi
  CONTROL_CMDS="${CONTROL_CMDS} Port=${p}"
done

CONTROL_CMDS="${CONTROL_CMDS}\nQUIT\n"

# Run command against Tor control port
OUTPUT=$(docker exec -i lucid_tor sh -c "printf '${CONTROL_CMDS}' | nc 127.0.0.1 9051")

# Extract onion address
ONION=$(echo "$OUTPUT" | awk '/250-ServiceID=/ {print $1}' | cut -d= -f2).onion

if [[ -z "$ONION" || "$ONION" == ".onion" ]]; then
  echo "[create_ephemeral_onion] ERROR: Failed to create onion" >&2
  echo "$OUTPUT"
  exit 1
fi

echo "[create_ephemeral_onion] ONION=${ONION}"
