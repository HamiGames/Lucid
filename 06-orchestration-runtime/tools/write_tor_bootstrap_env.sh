#!/usr/bin/env bash
# Purpose: Write /run/lucid/onion/tor_bootstrap.env with real ONION/BLOCK_ONION
# Notes:
# - Uses Docker volume 'lucid-dev_onion_state' (canonical HS path: <vol>/lucid/onion)
# - Generates onion keys if missing via host 'tor' (not inside a container)
# - No 'set -e' and no explicit 'exit' codes

VOL="lucid-dev_onion_state"
ENV_DIR="/run/lucid/onion"
ENV_FILE="${ENV_DIR}/tor_bootstrap.env"

# 1) Ensure the Docker volume exists and get its mountpoint
docker volume inspect "$VOL" >/dev/null 2>&1 || docker volume create "$VOL" >/dev/null
MOUNT="$(docker volume inspect -f '{{.Mountpoint}}' "$VOL" 2>/dev/null)"
[ -n "$MOUNT" ] || { echo "Cannot resolve mountpoint for volume: $VOL"; }

# 2) Canonical hidden-service dir inside the volume
HS_DIR="$MOUNT/lucid/onion"
sudo install -d -m 0700 "$HS_DIR" >/dev/null 2>&1

# 3) Ensure host Tor is available
if ! command -v tor >/dev/null 2>&1; then
  sudo apt-get update -y && sudo apt-get install -y tor
fi

# 4) If hostname missing, generate a v3 onion into HS_DIR (background tor)
if ! sudo test -s "$HS_DIR/hostname"; then
  TMP_DIR="/tmp/lucid-hostgen.$$"
  sudo install -d -m 0700 "$TMP_DIR"
  sudo tor --hush --RunAsDaemon 0 --SocksPort 0 \
    --DataDirectory "$TMP_DIR" \
    --HiddenServiceDir "$HS_DIR" \
    --HiddenServiceVersion 3 \
    --HiddenServicePort 80 127.0.0.1:80 &
  # Wait for hostname to appear
  while ! sudo test -s "$HS_DIR/hostname"; do sleep 1; done
  # Best-effort stop of the temporary tor
  sudo pkill -f "$TMP_DIR" >/dev/null 2>&1 || true
fi

# 5) Read the real onion hostname
ONION_HOST="$(sudo tr -d '\r\n' < "$HS_DIR/hostname")"

# 6) Write the bootstrap env file with *real* values (no placeholders)
sudo install -d -m 0700 "$ENV_DIR" >/dev/null 2>&1
umask 077
printf "ONION=%s\nBLOCK_ONION=%s\n" "$ONION_HOST" "$ONION_HOST" | \
  sudo tee "$ENV_FILE" >/dev/null

# 7) Show result
echo "Wrote $ENV_FILE"
sudo cat "$ENV_FILE"
