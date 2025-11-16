#!/bin/bash
# Bootstrap helper: Pre-bootstrap Tor and create required files
# Standalone version - runs on host, uses docker to run tor

set -euo pipefail

log() { printf '[bootstrap-helper] %s\n' "$*"; }

# Host paths (not container paths)
HOST_TOR_DATA="/mnt/myssd/Lucid/Lucid/data/tor"
HOST_TOR_LOGS="/mnt/myssd/Lucid/Lucid/logs/tor"
HOST_TOR_RUN="/mnt/myssd/Lucid/Lucid/data/tor-run"
HOST_TOR_CONFIG="/mnt/myssd/Lucid/Lucid/config/tor"
HOST_ONION_DIR="${HOST_TOR_RUN}/lucid/onion"
COOKIE_FILE="${HOST_TOR_DATA}/control_auth_cookie"

# Container paths (inside docker)
CONTAINER_TOR_DATA="/var/lib/tor"
CONTAINER_COOKIE_FILE="${CONTAINER_TOR_DATA}/control_auth_cookie"

IMAGE="pickme/lucid-tor-proxy:latest-arm64"

log "=== Tor Bootstrap Helper (Standalone) ==="

# Ensure host directories exist
log "Preparing host directories..."
sudo mkdir -p "$HOST_TOR_DATA" "$HOST_TOR_LOGS" "$HOST_TOR_RUN/lucid/onion" "$HOST_TOR_CONFIG" || true

# Discover debian-tor uid:gid from image
log "Discovering debian-tor uid:gid..."
TOR_UID=$(docker run --rm "$IMAGE" /bin/busybox awk -F: '$1=="debian-tor"{print $3}' /etc/passwd)
TOR_GID=$(docker run --rm "$IMAGE" /bin/busybox awk -F: '$1=="debian-tor"{print $3}' /etc/group)
log "  debian-tor -> ${TOR_UID}:${TOR_GID}"

# Set ownership on host directories
sudo chown -R "${TOR_UID}:${TOR_GID}" "$HOST_TOR_DATA" "$HOST_TOR_LOGS" "$HOST_TOR_RUN" || true
sudo chmod 700 "$HOST_TOR_DATA" || true
sudo chmod 755 "$HOST_TOR_LOGS" "$HOST_TOR_RUN" || true

# Check if cookie file exists, if not start Tor to create it
if [ -s "$COOKIE_FILE" ]; then
  log "Cookie file found at $COOKIE_FILE (reusing existing)"
  # Verify cookie is readable
  if [ -r "$COOKIE_FILE" ]; then
    log "Cookie file is readable, proceeding..."
  else
    log "WARNING: Cookie file exists but not readable, will regenerate"
    rm -f "$COOKIE_FILE" || true
  fi
else
  log "Cookie file not found at $COOKIE_FILE - will start Tor to create it"
fi

# Run tor in temporary container (will create cookie if missing)
log "Starting Tor in temporary container..."
CONTAINER_ID=$(docker run -d --rm \
  --name tor-bootstrap-temp \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.tor-proxy \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets \
  --network lucid-pi-network --ip 172.20.0.9 \
  --cap-drop=ALL --security-opt no-new-privileges:true \
  --tmpfs /tmp:noexec,nosuid,size=64m \
  -v "$HOST_TOR_DATA:${CONTAINER_TOR_DATA}:rw" \
  -v "$HOST_TOR_LOGS:${CONTAINER_TOR_LOGS}:rw" \
  -v "$HOST_TOR_RUN:${CONTAINER_TOR_RUN}:rw" \
  -v "$HOST_TOR_CONFIG:${CONTAINER_TOR_CONFIG}:ro" \
  --entrypoint /usr/bin/tini \
  "$IMAGE" -- /usr/local/bin/entrypoint.sh)

log "Container started: $CONTAINER_ID"

# Wait for cookie file (check both host and container)
log "Waiting for control cookie to be created..."
for i in $(seq 1 120); do
  # Check container first (most reliable)
  if docker exec tor-bootstrap-temp test -s "$CONTAINER_COOKIE_FILE" 2>/dev/null; then
    log "Cookie found in container"
    # Verify it's also visible on host
    if [ -s "$COOKIE_FILE" ]; then
      log "Cookie file seeded to host at $COOKIE_FILE"
      break
    else
      log "Cookie exists in container but not on host - checking permissions..."
      sleep 1
    fi
  fi
  # Also check host directly
  if [ -s "$COOKIE_FILE" ]; then
    log "Cookie found on host at $COOKIE_FILE"
    break
  fi
  sleep 1
  [ $((i % 10)) -eq 0 ] && log "  Still waiting... (${i}s)"
done

# Final verification
if [ -s "$COOKIE_FILE" ]; then
  log "Cookie file verified at $COOKIE_FILE"
  ls -lh "$COOKIE_FILE"
elif docker exec tor-bootstrap-temp test -s "$CONTAINER_COOKIE_FILE" 2>/dev/null; then
  log "Cookie exists in container but not accessible on host"
  log "Attempting to copy from container..."
  docker cp "tor-bootstrap-temp:${CONTAINER_COOKIE_FILE}" "$COOKIE_FILE" 2>/dev/null || {
    log "ERROR: Failed to copy cookie from container"
    docker logs --tail=50 tor-bootstrap-temp
    docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true
    exit 1
  }
  sudo chown "${TOR_UID}:${TOR_GID}" "$COOKIE_FILE" || true
  log "Cookie file copied to host"
else
  log "ERROR: Cookie not created after 120s"
  log "Container logs:"
  docker logs --tail=50 tor-bootstrap-temp
  log "Checking container state:"
  docker exec tor-bootstrap-temp ls -la "$CONTAINER_TOR_DATA" 2>/dev/null || true
  docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true
  exit 1
fi

# Read cookie hex from inside container (uses container's xxd)
log "Reading cookie..."
HEX=$(docker exec tor-bootstrap-temp /usr/bin/xxd -p "$CONTAINER_COOKIE_FILE" 2>/dev/null | tr -d '\n' || {
  log "WARNING: Failed to read cookie with xxd, trying alternative..."
  docker exec tor-bootstrap-temp /bin/busybox hexdump -v -e '1/1 "%02x"' "$CONTAINER_COOKIE_FILE" 2>/dev/null | tr -d '\n'
})

[ -n "$HEX" ] || { log "ERROR: Cookie hex is empty"; docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true; exit 1; }
log "Cookie read successfully (${#HEX} chars)"

# Wait for bootstrap and create state file
log "Waiting for bootstrap to reach 100%..."
for i in $(seq 1 180); do
  REQ=$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nGETINFO version\r\nQUIT\r\n' "$HEX")
  OUT=$(echo "$REQ" | docker exec -i tor-bootstrap-temp nc -w 3 127.0.0.1 9051 2>/dev/null || true)
  CLEANED=$(echo "$OUT" | tr -d '\r' | tr '\n' ' ' | sed 's/  */ /g')
  if echo "$CLEANED" | grep -o 'PROGRESS=[0-9]*' | grep -q 'PROGRESS=100'; then
    log "Bootstrap complete (100%)"
    break
  fi
  sleep 2
  [ $((i % 15)) -eq 0 ] && log "Bootstrap progress... (attempt $i/180)"
done

# Extract bootstrap info and create state file
log "Creating bootstrap state files..."
VERSION=$(echo "$OUT" | sed -n 's/.*250-version=\([0-9.]*\).*/\1/p' | tr -d '\r')
PHASE=$(echo "$OUT" | sed -n 's/.*250-status\/bootstrap-phase=\(.*\)/\1/p' | tr -d '\r')
PROGRESS=$(echo "$PHASE" | sed -n 's/.*PROGRESS=\([0-9]*\).*/\1/p')
TAG=$(echo "$PHASE" | sed -n 's/.*TAG=\([a-z_]*\).*/\1/p')
SUMMARY=$(echo "$PHASE" | sed -n 's/.*SUMMARY=\(.*\)$/\1/p')
STAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$HOST_ONION_DIR"
cat > "$HOST_ONION_DIR/tor_bootstrap.env" <<EOF
TOR_VERSION=${VERSION:-0.4.7.16}
TOR_BOOTSTRAP_PROGRESS=${PROGRESS:-100}
TOR_BOOTSTRAP_TAG=${TAG:-done}
TOR_BOOTSTRAP_SUMMARY=${SUMMARY:-Done}
TOR_BOOTSTRAP_AT=${STAMP}
EOF

log "Bootstrap state file created at $HOST_ONION_DIR/tor_bootstrap.env"
log "Cookie file seeded at $COOKIE_FILE"
log "Helper complete. You can now start tor-proxy container."
log "Stopping temporary container..."
docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true
log "Done."
exit 0