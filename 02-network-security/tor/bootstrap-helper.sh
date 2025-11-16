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

# Container paths (inside docker)
CONTAINER_TOR_DATA="/var/lib/tor"
CONTAINER_TOR_LOGS="/var/log/tor"
CONTAINER_TOR_RUN="/run"
CONTAINER_TOR_CONFIG="/etc/tor"
CONTAINER_ONION_DIR="${CONTAINER_TOR_RUN}/lucid/onion"
CONTAINER_COOKIE_FILE="${CONTAINER_TOR_DATA}/control_auth_cookie"

# Required Tor files (Tor creates these automatically)
TOR_FILES=(
  "control_auth_cookie"
  "tor.lock"
  "state"
  "cached-certs"
  "cached-consensus"
  "cached-descriptors"
  "cached-descriptors.new"
  "cached-microdesc-consensus"
  "cached-microdescs"
)

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

# Verify Tor data directory is writable
log "Verifying Tor data directory is ready..."
if [ ! -d "$HOST_TOR_DATA" ]; then
  log "ERROR: Tor data directory does not exist: $HOST_TOR_DATA"
  exit 1
fi

if sudo -u "#${TOR_UID}" test -w "$HOST_TOR_DATA" 2>/dev/null; then
  log "  Tor data directory is writable"
else
  log "  WARNING: Tor data directory may not be writable - fixing permissions..."
  sudo chown -R "${TOR_UID}:${TOR_GID}" "$HOST_TOR_DATA" || true
  sudo chmod 700 "$HOST_TOR_DATA" || true
fi

# Check which Tor files already exist
log "Checking existing Tor files in $HOST_TOR_DATA..."
EXISTING_FILES=()
MISSING_FILES=()
for file in "${TOR_FILES[@]}"; do
  if [ -f "${HOST_TOR_DATA}/${file}" ] || [ -d "${HOST_TOR_DATA}/${file}" ]; then
    EXISTING_FILES+=("$file")
    log "  Found: $file"
  else
    MISSING_FILES+=("$file")
  fi
done

if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
  log "Found ${#EXISTING_FILES[@]} existing file(s), ${#MISSING_FILES[@]} missing"
fi

# Check if cookie file exists, if not start Tor to create it
COOKIE_FILE="${HOST_TOR_DATA}/control_auth_cookie"
if [ -s "$COOKIE_FILE" ]; then
  log "Cookie file found at $COOKIE_FILE (reusing existing)"
  if [ -r "$COOKIE_FILE" ]; then
    log "Cookie file is readable, proceeding..."
  else
    log "WARNING: Cookie file exists but not readable, will regenerate"
    rm -f "$COOKIE_FILE" || true
  fi
else
  log "Cookie file not found at $COOKIE_FILE - will start Tor to create it"
fi

# Run tor in temporary container (will create missing files)
log "Starting Tor in temporary container..."
CONTAINER_ID=$(docker run -d --rm \
  --name tor-bootstrap-temp \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.tor-proxy \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets \
  --network lucid-pi-network --ip 172.20.0.9 \
  --cap-drop=ALL --security-opt no-new-privileges:true \
  --tmpfs /tmp:noexec,nosuid,size=64m \
  -v "${HOST_TOR_DATA}:${CONTAINER_TOR_DATA}:rw" \
  -v "${HOST_TOR_LOGS}:${CONTAINER_TOR_LOGS}:rw" \
  -v "${HOST_TOR_RUN}:${CONTAINER_TOR_RUN}:rw" \
  -v "${HOST_TOR_CONFIG}:${CONTAINER_TOR_CONFIG}:ro" \
  --entrypoint /usr/bin/tini \
  "$IMAGE" -- /usr/local/bin/entrypoint.sh)

log "Container started: $CONTAINER_ID"

# Wait for Tor to create required files
log "Waiting for Tor to create required files..."
MAX_WAIT=120
for i in $(seq 1 $MAX_WAIT); do
  ALL_EXIST=true
  for file in "${TOR_FILES[@]}"; do
    if ! docker exec tor-bootstrap-temp test -e "${CONTAINER_TOR_DATA}/${file}" 2>/dev/null; then
      ALL_EXIST=false
      break
    fi
  done
  
  if [ "$ALL_EXIST" = true ]; then
    log "All required Tor files created"
    break
  fi
  
  sleep 1
  [ $((i % 10)) -eq 0 ] && log "  Still waiting for Tor files... (${i}s)"
done

# Verify and seed each required file from container to host
log "Verifying and seeding Tor files to host mount point..."
SEEDED_COUNT=0
FAILED_FILES=()

for file in "${TOR_FILES[@]}"; do
  CONTAINER_FILE="${CONTAINER_TOR_DATA}/${file}"
  HOST_FILE="${HOST_TOR_DATA}/${file}"
  
  # Check if file exists in container
  if docker exec tor-bootstrap-temp test -e "$CONTAINER_FILE" 2>/dev/null; then
    # Check if file exists on host
    if [ -e "$HOST_FILE" ]; then
      log "  ✓ $file (exists on host)"
      # Ensure correct ownership
      sudo chown "${TOR_UID}:${TOR_GID}" "$HOST_FILE" 2>/dev/null || true
      SEEDED_COUNT=$((SEEDED_COUNT + 1))
    else
      # File exists in container but not on host - copy it
      log "  → Seeding $file from container to host..."
      if docker cp "tor-bootstrap-temp:${CONTAINER_FILE}" "$HOST_FILE" 2>/dev/null; then
        sudo chown "${TOR_UID}:${TOR_GID}" "$HOST_FILE" 2>/dev/null || true
        # Set appropriate permissions
        if [ -f "$HOST_FILE" ]; then
          sudo chmod 600 "$HOST_FILE" 2>/dev/null || true
        elif [ -d "$HOST_FILE" ]; then
          sudo chmod 700 "$HOST_FILE" 2>/dev/null || true
        fi
        log "    ✓ Seeded $file"
        SEEDED_COUNT=$((SEEDED_COUNT + 1))
      else
        log "    ✗ Failed to seed $file"
        FAILED_FILES+=("$file")
      fi
    fi
  else
    log "  ✗ $file (not created by Tor)"
    FAILED_FILES+=("$file")
  fi
done

# Critical files check
CRITICAL_FILES=("control_auth_cookie" "state")
for file in "${CRITICAL_FILES[@]}"; do
  HOST_FILE="${HOST_TOR_DATA}/${file}"
  if [ ! -s "$HOST_FILE" ]; then
    log "ERROR: Critical file $file is missing or empty"
    log "Container logs:"
    docker logs --tail=50 tor-bootstrap-temp
    log "Container directory contents:"
    docker exec tor-bootstrap-temp ls -la "$CONTAINER_TOR_DATA" 2>/dev/null || true
    docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true
    exit 1
  fi
done

log "Seeded ${SEEDED_COUNT}/${#TOR_FILES[@]} Tor files to host mount point"

if [ ${#FAILED_FILES[@]} -gt 0 ]; then
  log "WARNING: ${#FAILED_FILES[@]} file(s) failed to seed: ${FAILED_FILES[*]}"
  log "These may be created later by Tor or may not be required"
fi

# Read cookie hex from inside container (uses container's xxd)
log "Reading control cookie..."
HEX=$(docker exec tor-bootstrap-temp /usr/bin/xxd -p "${CONTAINER_COOKIE_FILE}" 2>/dev/null | tr -d '\n' || {
  log "WARNING: Failed to read cookie with xxd, trying alternative..."
  docker exec tor-bootstrap-temp /bin/busybox hexdump -v -e '1/1 "%02x"' "${CONTAINER_COOKIE_FILE}" 2>/dev/null | tr -d '\n'
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

# Final verification: list all seeded files
log "Final verification - Tor files in host mount point:"
ls -lh "$HOST_TOR_DATA" | grep -E "(control_auth_cookie|tor.lock|state|cached-)" || true

log "Bootstrap state file created at $HOST_ONION_DIR/tor_bootstrap.env"
log "All Tor files seeded to $HOST_TOR_DATA"
log "Helper complete. You can now start tor-proxy container."
log "Stopping temporary container..."
docker rm -f tor-bootstrap-temp >/dev/null 2>&1 || true
log "Done."
exit 0