#!/bin/bash
# Lucid Tor Proxy — entrypoint for distroless runtime
# Aligned with @constants: TOR_PROXY_* env vars, CREATE_ONION=0 default, /run/lucid/onion state
# COMPLETELY REFACTORED: Fixed preload_tor_data, improved bootstrap logging, better error handling
#
# Key Improvements:
# - preload_tor_data() now correctly copies seed data before bootstrap
# - Checks source ($TOR_SEED_DIR) instead of destination
# - Critical bootstrap files verified: state, cached-consensus, cached-microdescs, cached-certs
# - Permissions applied recursively to all directories after preload
# - Removed 150+ lines of redundant/broken file checks
# - Better bootstrap progress logging
# - Improved error messages and troubleshooting guidance

set -eu

log() { printf '[tor-entrypoint] %s\n' "$*"; }

# ============================================================================
# Environment Variables & Defaults
# ============================================================================

CONTROL_HOST=${CONTROL_HOST:-lucid-tor-proxy}
# Align with @constants and compose: prefer TOR_PROXY_* then fallback
TOR_SOCKS_PORT=${TOR_PROXY_SOCKS_PORT:-${TOR_SOCKS_PORT:-9050}}
CONTROL_PORT=${TOR_PROXY_CONTROL_PORT:-${TOR_CONTROL_PORT:-9051}}
COOKIE_FILE=${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}
UPSTREAM_SERVICE=${UPSTREAM_SERVICE:-}
UPSTREAM_PORT=${UPSTREAM_PORT:-8081}
# Foundation default: don't create onions unless explicitly enabled
CREATE_ONION=${CREATE_ONION:-0}
TOR_SEED_DIR=${TOR_SEED_DIR:-/seed/tor-data}
TOR_DATA_DIR=${TOR_DATA_DIR:-/var/lib/tor}
# Bridge configuration (ISP port blocking workaround)
TOR_USE_BRIDGES=${TOR_USE_BRIDGES:-0}
TOR_BRIDGES=${TOR_BRIDGES:-}

# ============================================================================
# FUNCTION: preload_tor_data
# Purpose: Copy seed Tor data from /seed/tor-data to /var/lib/tor if needed
# This includes consensus documents, cached descriptors, and onion service keys
# to speed up bootstrap and improve reliability
# ============================================================================
preload_tor_data() {
  log "Checking for Tor seed data..."

  # 1️⃣ Verify seed directory exists
  if [ ! -d "$TOR_SEED_DIR" ]; then
    log "INFO: No seed directory found at $TOR_SEED_DIR — will bootstrap from scratch"
    return 0
  fi

  # 2️⃣ Prevent corruption: don't copy if Tor already has a lock file
  # This indicates Tor is running or was interrupted mid-operation
  if [ -f "$TOR_DATA_DIR/lock" ]; then
    log "WARNING: Tor lock file present at $TOR_DATA_DIR/lock — skipping preload to avoid corruption"
    return 1
  fi

  # 3️⃣ Define critical files needed for bootstrap
  # These files are REQUIRED for Tor to bootstrap efficiently
  # Without them, Tor must download from directory authorities (slower, unreliable)
  local required_files=(
    "state"                        # Tor state file with identity keys
    "cached-consensus"             # Current directory consensus
    "cached-microdescs"            # Descriptor summaries
    "cached-certs"                 # Directory authority certificates
    "control_auth_cookie"          # Control port authentication
  )

  log "Verifying critical seed files in $TOR_SEED_DIR..."
  local missing_count=0
  local found_count=0

  # Check each critical file in the SOURCE directory
  for file in "${required_files[@]}"; do
    if [ -f "$TOR_SEED_DIR/$file" ] && [ -s "$TOR_SEED_DIR/$file" ]; then
      log "  ✓ Found: $file"
      found_count=$((found_count + 1))
    else
      log "  ✗ Missing: $file"
      missing_count=$((missing_count + 1))
    fi
  done

  # If too many critical files are missing, skip preload
  # Tor can still bootstrap from scratch, but will be slower
  if [ $missing_count -ge 3 ]; then
    log "WARNING: Only $found_count/$((${#required_files[@]})) critical files found in seed — skipping preload"
    log "INFO: Tor will bootstrap from directory authorities (may take 2-5 minutes)"
    return 0
  fi

  # 4️⃣ Check if destination already has valid state
  # If so, don't overwrite existing working configuration
  if [ -f "$TOR_DATA_DIR/state" ] && [ -s "$TOR_DATA_DIR/state" ]; then
    log "INFO: Existing Tor state detected at $TOR_DATA_DIR/state — not overwriting"
    return 0
  fi

  # 5️⃣ Ensure destination directory exists
  if ! mkdir -p "$TOR_DATA_DIR" 2>/dev/null; then
    log "ERROR: Failed to create $TOR_DATA_DIR"
    return 1
  fi

  # 6️⃣ Copy seed data to destination
  log "Copying seed data from $TOR_SEED_DIR to $TOR_DATA_DIR..."
  
  if ! /bin/busybox cp -a "$TOR_SEED_DIR/." "$TOR_DATA_DIR/" 2>/dev/null; then
    log "ERROR: Failed to copy Tor seed data — bootstrap will proceed from scratch"
    return 1
  fi

  log "SUCCESS: Tor seed data preload complete"

  # 7️⃣ Fix permissions and ownership
  # Critical: Tor must have proper permissions to read its data directory
  log "Correcting file permissions and ownership..."

  # Fix main data directory
  if [ -d "$TOR_DATA_DIR" ]; then
    # Set directory permissions (rwx------)
    if ! chmod 700 "$TOR_DATA_DIR" 2>/dev/null; then
      log "WARNING: Failed to set permissions on $TOR_DATA_DIR"
    else
      log "  ✓ Set $TOR_DATA_DIR to 700"
    fi

    # Try to fix ownership to debian-tor user if available
    # Note: In some environments (distroless), chown may not be available
    if command -v chown >/dev/null 2>&1; then
      if chown -R debian-tor:debian-tor "$TOR_DATA_DIR" 2>/dev/null; then
        log "  ✓ Set ownership to debian-tor:debian-tor"
      else
        log "WARNING: Failed to set ownership (running as $(id -u), may not be root)"
      fi
    fi

    # Fix all subdirectories (especially important for onion service keys)
    log "Fixing subdirectory permissions..."
    find "$TOR_DATA_DIR" -type d -exec chmod 700 {} \; 2>/dev/null || true
    
    if command -v chown >/dev/null 2>&1; then
      find "$TOR_DATA_DIR" -type d -exec chown debian-tor:debian-tor {} \; 2>/dev/null || true
    fi

    # Fix all regular files (should be 600 for sensitive files like keys)
    log "Fixing file permissions..."
    find "$TOR_DATA_DIR" -type f -exec chmod 600 {} \; 2>/dev/null || true
    
    # Except control_auth_cookie which needs to be readable
    if [ -f "$TOR_DATA_DIR/control_auth_cookie" ]; then
      chmod 644 "$TOR_DATA_DIR/control_auth_cookie" 2>/dev/null || true
    fi

    log "SUCCESS: Permissions and ownership corrected"
  fi

  return 0
}

# ============================================================================
# FUNCTION: configure_bridges
# Purpose: Add Tor bridge configuration for ISP port blocking workaround
# Bridges allow Tor to connect when standard Tor ports are blocked
# ============================================================================
configure_bridges() {
  [ "$TOR_USE_BRIDGES" = "1" ] || return 0
  
  if [ -z "$TOR_BRIDGES" ]; then
    log "ERROR: TOR_USE_BRIDGES=1 but TOR_BRIDGES not configured"
    log "Set TOR_BRIDGES environment variable with bridge addresses"
    return 1
  fi
  
  local torrc_path="/etc/tor/torrc"
  log "Configuring Tor bridges for ISP port blocking workaround..."
  
  if [ ! -f "$torrc_path" ]; then
    log "ERROR: torrc file not found at $torrc_path"
    return 1
  fi

  # Add bridge configuration to torrc if not already present
  if ! grep -q "^UseBridges" "$torrc_path"; then
    log "Adding bridge configuration to torrc..."
    {
      echo ""
      echo "# Bridge configuration (added by entrypoint for port blocking workaround)"
      echo "UseBridges 1"
      echo "ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy"
      echo "ReachableAddresses *:80,*:443"
      echo ""
      echo "# Bridge addresses from TOR_BRIDGES environment variable"
      echo "$TOR_BRIDGES"
    } >> "$torrc_path"
    log "Bridge configuration added to torrc"
  else
    log "Bridge configuration already present in torrc"
  fi

  return 0
}

# ============================================================================
# FUNCTION: ensure_runtime
# Purpose: Create necessary runtime directories and set base permissions
# ============================================================================
ensure_runtime() {
  log "Setting up runtime directories..."
  
  mkdir -p /run /var/lib/tor /var/log/tor 2>/dev/null || {
    log "WARNING: Failed to create some runtime directories"
  }

  # CRITICAL: Clean the cookie file before Tor starts
  # This ensures Tor writes a fresh, uncorrupted cookie
  local cookie_file="/var/lib/tor/control_auth_cookie"
  
  if [ -f "$cookie_file" ]; then
    log "Removing old control_auth_cookie to ensure clean write..."
    rm -f "$cookie_file" 2>/dev/null || true
    
    # Verify it's deleted
    if [ -f "$cookie_file" ]; then
      log "WARNING: Could not remove old cookie file"
    else
      log "✓ Old cookie file removed"
    fi
  fi

  # Set base permissions on tor directory
  chmod 755 /var/lib/tor 2>/dev/null || true

  # Try to fix ownership if possible
  if command -v chown >/dev/null 2>&1; then
    chown debian-tor:debian-tor /var/lib/tor 2>/dev/null || {
      log "WARNING: Could not set ownership (may be running as non-root)"
    }
  fi

  log "Runtime directories ready"
}

# ============================================================================
# FUNCTION: start_tor
# Purpose: Start the Tor daemon as a background process
# ============================================================================
start_tor() {
  log "Starting Tor daemon..."
  
  if ! command -v tor >/dev/null 2>&1; then
    log "ERROR: tor binary not found in PATH"
    return 1
  fi

  # Start Tor in background and capture PID
  tor -f /etc/tor/torrc &
  local tor_pid=$!

  # Save PID for monitoring
  /bin/busybox sh -c "echo $tor_pid > '${TOR_DATA_DIR}/tor.pid'" 2>/dev/null || true

  log "Tor started with PID: $tor_pid"
  
  # Give Tor a moment to initialize
  sleep 1
  
  # Verify process is still running
  if ! /bin/busybox kill -0 $tor_pid 2>/dev/null; then
    log "ERROR: Tor process exited immediately after start (check logs)"
    return 1
  fi

  log "Tor process verified running"
  return 0
}

# ============================================================================
# FUNCTION: wait_for_file
# Purpose: Wait for a file to be created (with timeout)
# Used to wait for control cookie and other key files
# ============================================================================
wait_for_file() {
  local filepath="$1"
  local timeout="${2:-120}"
  
  log "Waiting for file: $filepath (timeout: ${timeout}s)"
  
  local elapsed=0
  while [ $elapsed -lt "$timeout" ]; do
    # Check if file EXISTS AND has content (not just created empty)
    if [ -f "$filepath" ] && [ -s "$filepath" ]; then
      local size
      size=$(wc -c < "$filepath" 2>/dev/null)
      log "✓ File ready: $filepath ($size bytes)"
      return 0
    fi
    
    sleep 1
    elapsed=$((elapsed + 1))
    
    # Log progress every 30 seconds
    if [ $((elapsed % 30)) -eq 0 ]; then
      log "Still waiting for $filepath... ($elapsed/${timeout}s elapsed)"
    fi
  done

  log "ERROR: Timeout waiting for file: $filepath"
  return 1
}

# ============================================================================
# FUNCTION: ctl
# Purpose: Send a command to Tor control port (localhost:9051)
# Uses cookie authentication for security
# ============================================================================
ctl() {
  local cmd="$1"
  
  # Verify cookie file exists and is readable
  if [ ! -f "$COOKIE_FILE" ]; then
    log "ERROR: Cookie file not found: $COOKIE_FILE"
    return 1
  fi

  if [ ! -r "$COOKIE_FILE" ]; then
    log "ERROR: Cookie file not readable: $COOKIE_FILE"
    return 1
  fi

  if [ ! -s "$COOKIE_FILE" ]; then
    log "ERROR: Cookie file is empty: $COOKIE_FILE"
    return 1
  fi

  # Extract cookie hex with proper spacing cleanup
  # od outputs hex bytes with spacing, we need to clean it up properly
  local cookie_hex
  cookie_hex=$(/bin/busybox od -A n -t x1 "$COOKIE_FILE" 2>/dev/null | \
    /bin/busybox sed 's/[[:space:]]\+/ /g' | \
    /bin/busybox sed 's/^ //; s/ $//' | \
    /bin/busybox tr -d ' \n')

  if [ -z "$cookie_hex" ]; then
    log "ERROR: Failed to extract valid hex from cookie file"
    return 1
  fi

  # Validate hex format (should be 60-80 hex characters for 32-byte cookie)
  if ! echo "$cookie_hex" | /bin/busybox grep -qE '^[0-9a-fA-F]{60,80}$'; then
    log "ERROR: Invalid cookie hex format (got ${#cookie_hex} chars)"
    return 1
  fi

  # Send command to Tor control port with proper authentication
  # Format: AUTHENTICATE <hex_cookie>\r\n<command>\r\nQUIT\r\n
  {
    printf 'AUTHENTICATE %s\r\n' "$cookie_hex"
    printf '%s\r\n' "$cmd"
    printf 'QUIT\r\n'
  } | timeout 5 /usr/bin/nc -w 3 "$CONTROL_HOST" "$CONTROL_PORT" 2>/dev/null

  return $?
}

# ============================================================================
# FUNCTION: resolve_upstream_ip
# Purpose: Resolve upstream service hostname to IP address
# Used when creating ephemeral onion services
# ============================================================================
resolve_upstream_ip() {
  local svc="$1"
  local ip=""

  # Return empty if no service specified
  [ -z "$svc" ] && { echo ""; return 0; }

  # Try getent first (preferred, more reliable)
  if command -v getent >/dev/null 2>&1; then
    ip=$(getent hosts "$svc" 2>/dev/null | awk '{print $1}' | head -1 || true)
    [ -n "$ip" ] && { echo "$ip"; return 0; }
  fi

  # Fallback to nslookup
  if command -v nslookup >/dev/null 2>&1; then
    ip=$(nslookup -timeout=2 "$svc" 2>/dev/null | awk '/^Address: /{print $2; exit}' || true)
    [ -n "$ip" ] && { echo "$ip"; return 0; }
  fi

  # No resolution succeeded
  echo ""
  return 1
}

# ============================================================================
# FUNCTION: wait_for_bootstrap
# Purpose: Wait for Tor to complete bootstrap (reach 100%)
# Monitors bootstrap phase via control port
# ============================================================================
wait_for_bootstrap() {
  log "Waiting for Tor to bootstrap..."
  log "This may take 30 seconds to 5 minutes depending on network conditions"
  
  local i=0
  local max_attempts=300  # 10 minutes maximum
  local last_progress=""
  local cookie_failed=0

  # Validate cookie before starting
  if [ ! -s "$COOKIE_FILE" ]; then
    log "ERROR: Cookie file is missing or empty before bootstrap"
    return 1
  fi

  # Try to extract cookie hex for validation
  local test_hex
  test_hex=$(/bin/busybox od -A n -t x1 "$COOKIE_FILE" 2>/dev/null | \
    /bin/busybox sed 's/[[:space:]]\+/ /g' | \
    /bin/busybox sed 's/^ //; s/ $//' | \
    /bin/busybox tr -d ' \n')

  if [ -z "$test_hex" ] || ! echo "$test_hex" | /bin/busybox grep -qE '^[0-9a-fA-F]{60,80}$'; then
    log "ERROR: Cookie file contains invalid hex data"
    log "Cookie file size: $(wc -c < "$COOKIE_FILE") bytes"
    log "Cookie hex length: ${#test_hex} chars"
    return 1
  fi

  log "DEBUG: Cookie validation passed (${#test_hex} hex chars)"

  while [ $i -lt "$max_attempts" ]; do
    # Query bootstrap status from Tor
    local response
    response=$(ctl "GETINFO status/bootstrap-phase" 2>/dev/null || true)

    # Check if response is empty (indicates ctl command failed)
    if [ -z "$response" ]; then
      cookie_failed=$((cookie_failed + 1))
      
      # Log every 30 seconds if control connection keeps failing
      if [ $((i % 15)) -eq 0 ]; then
        log "WARNING: Control port not responding (attempt $((cookie_failed)))... retrying"
      fi
      
      # If cookie problems persist, something is very wrong
      if [ $cookie_failed -gt 20 ]; then
        log "FATAL: Cannot reach Tor control port after many attempts"
        log "Cookie file exists: $([ -f "$COOKIE_FILE" ] && echo 'yes' || echo 'no')"
        log "Cookie file size: $(wc -c < "$COOKIE_FILE") bytes"
        return 1
      fi
      
      sleep 2
      i=$((i + 1))
      continue
    fi

    # Reset cookie failure counter on successful response
    cookie_failed=0

    # Normalize response: remove CR/LF, convert newlines to spaces, collapse whitespace
    local cleaned
    cleaned=$(printf '%s' "$response" | \
      /bin/busybox tr -d '\r' | \
      /bin/busybox tr '\n' ' ' | \
      /bin/busybox sed 's/  */ /g')

    # Verify we got a valid response (should contain "PROGRESS")
    if ! echo "$cleaned" | /bin/busybox grep -q 'PROGRESS'; then
      if [ $((i % 15)) -eq 0 ]; then
        log "WARNING: Invalid response from control port"
      fi
      sleep 2
      i=$((i + 1))
      continue
    fi

    # Extract progress percentage (safely handle extraction)
    local progress
    progress=$(/bin/busybox printf '%s' "$cleaned" | \
      /bin/busybox grep -o 'PROGRESS=[0-9]*' | \
      /bin/busybox head -1)
    
    # Fallback if extraction failed
    if [ -z "$progress" ]; then
      progress="PROGRESS=unknown"
    fi

    # Check if bootstrap is complete (PROGRESS=100)
    if /bin/busybox printf '%s' "$cleaned" | /bin/busybox grep -q 'PROGRESS=100'; then
      log "✓ Bootstrap complete (100%)"
      
      # Also log the summary for debugging
      local tag
      tag=$(/bin/busybox printf '%s' "$cleaned" | \
        /bin/busybox grep -o 'TAG=[^ ]*' | \
        /bin/busybox head -1)
      
      if [ -n "$tag" ]; then
        log "  Final status: $progress, $tag"
      else
        log "  Final status: $progress"
      fi
      
      return 0
    fi

    # Log progress every 15 attempts (30 seconds) to avoid log spam
    if [ $((i % 15)) -eq 0 ] && [ $i -gt 0 ]; then
      # Extract tag (phase description)
      local tag
      tag=$(/bin/busybox printf '%s' "$cleaned" | \
        /bin/busybox grep -o 'TAG=[^ ]*' | \
        /bin/busybox head -1)
      
      local display_tag=""
      if [ -n "$tag" ]; then
        display_tag=", $tag"
      fi
      
      # Only log if progress changed
      if [ "$progress" != "$last_progress" ]; then
        log "Bootstrap in progress: $progress$display_tag (attempt $i/$max_attempts)"
        last_progress="$progress"
      fi
    fi

    sleep 2
    i=$((i + 1))
  done

  log "ERROR: Tor bootstrap did not reach 100% within timeout ($max_attempts attempts = 10 minutes)"
  log "Last known status: $progress"
  log "This usually means:"
  log "  1. ISP is blocking Tor ports (configure bridges)"
  log "  2. Network connectivity issues"
  log "  3. Tor consensus is unavailable"
  return 1
}

# ============================================================================
# FUNCTION: copy_cookie_to_shared
# Purpose: Copy Tor control cookie to shared volume for other services
# Allows tunnel-tools and other components to communicate with Tor control port
# ============================================================================
copy_cookie_to_shared() {
  local cookie_src="${COOKIE_FILE:-/var/lib/tor/control_auth_cookie}"
  local cookie_dest="${COOKIE_FILE_SHARED:-/run/lucid/onion/control_auth_cookie}"

  log "Preparing to copy control cookie to shared volume..."

  # Get destination directory
  local dest_dir="${cookie_dest%/*}"

  # Create destination directory
  mkdir -p "$dest_dir" 2>/dev/null || true

  # CRITICAL: Wait for source cookie file to be CREATED AND WRITTEN
  # Tor creates the file first, then writes content to it
  log "Waiting for source cookie file to be created and written..."
  local waited=0
  local max_wait=120
  
  while [ $waited -lt $max_wait ]; do
    # Check if file exists AND has content (not just created empty)
    if [ -f "$cookie_src" ] && [ -s "$cookie_src" ]; then
      local size
      size=$(wc -c < "$cookie_src" 2>/dev/null)
      log "✓ Cookie file ready: $cookie_src ($size bytes)"
      break
    fi
    
    # Show progress every 10 seconds
    if [ $((waited % 10)) -eq 0 ] && [ $waited -gt 0 ]; then
      log "Waiting for cookie... ($waited/${max_wait}s)"
    fi
    
    sleep 1
    waited=$((waited + 1))
  done

  # Check if we actually got a valid source file
  if [ ! -f "$cookie_src" ] || [ ! -s "$cookie_src" ]; then
    log "ERROR: Source cookie file did not appear or is empty after ${max_wait}s"
    return 1
  fi

  # Verify source is readable
  if [ ! -r "$cookie_src" ]; then
    log "ERROR: Source cookie file not readable: $cookie_src"
    return 1
  fi

  # Get source file size
  local src_size
  src_size=$(wc -c < "$cookie_src" 2>/dev/null)

  log "Copying cookie ($src_size bytes) to shared volume..."

  # Copy with multiple fallback methods
  if /bin/busybox cp "$cookie_src" "$cookie_dest" 2>/dev/null; then
    # Method 1 worked, verify destination
    local dst_size
    dst_size=$(wc -c < "$cookie_dest" 2>/dev/null || echo 0)
    
    if [ "$dst_size" -gt 0 ] && [ "$dst_size" -eq "$src_size" ]; then
      chmod 644 "$cookie_dest" 2>/dev/null || true
      log "✓ Cookie copied successfully: $cookie_dest ($dst_size bytes)"
      return 0
    fi
  fi

  # Method 2: Try cat
  if /bin/busybox cat "$cookie_src" > "$cookie_dest" 2>/dev/null; then
    local dst_size
    dst_size=$(wc -c < "$cookie_dest" 2>/dev/null || echo 0)
    
    if [ "$dst_size" -gt 0 ] && [ "$dst_size" -eq "$src_size" ]; then
      chmod 644 "$cookie_dest" 2>/dev/null || true
      log "✓ Cookie copied with cat: $cookie_dest ($dst_size bytes)"
      return 0
    fi
  fi

  # Method 3: Try dd
  if /bin/busybox dd if="$cookie_src" of="$cookie_dest" 2>/dev/null; then
    local dst_size
    dst_size=$(wc -c < "$cookie_dest" 2>/dev/null || echo 0)
    
    if [ "$dst_size" -gt 0 ] && [ "$dst_size" -eq "$src_size" ]; then
      chmod 644 "$cookie_dest" 2>/dev/null || true
      log "✓ Cookie copied with dd: $cookie_dest ($dst_size bytes)"
      return 0
    fi
  fi

  log "ERROR: Failed to copy cookie using all methods"
  return 1
}

# ============================================================================
# FUNCTION: create_ephemeral_onion
# Purpose: Create an ephemeral Tor hidden service
# Maps localhost port to upstream service via onion address
# ============================================================================
create_ephemeral_onion() {
  [ "$CREATE_ONION" = "1" ] || {
    log "INFO: CREATE_ONION disabled (CREATE_ONION=$CREATE_ONION)"
    return 0
  }

  if [ -z "$UPSTREAM_SERVICE" ]; then
    log "INFO: No UPSTREAM_SERVICE configured — skipping onion creation"
    return 0
  fi

  log "Creating ephemeral onion service for: $UPSTREAM_SERVICE"

  # Resolve upstream service hostname to IP
  log "Resolving upstream service: $UPSTREAM_SERVICE"
  local ip=""
  local tries=30

  while [ $tries -gt 0 ]; do
    ip=$(resolve_upstream_ip "$UPSTREAM_SERVICE")
    if [ -n "$ip" ]; then
      log "✓ Resolved $UPSTREAM_SERVICE to $ip"
      break
    fi
    log "  Waiting for DNS resolution... ($tries attempts remaining)"
    sleep 2
    tries=$((tries - 1))
  done

  if [ -z "$ip" ]; then
    log "ERROR: Unable to resolve $UPSTREAM_SERVICE"
    return 1
  fi

  # Test connectivity to upstream (best-effort, don't fail)
  if command -v nc >/dev/null 2>&1; then
    log "Testing connectivity to $ip:$UPSTREAM_PORT..."
    if nc -z -w 2 "$ip" "$UPSTREAM_PORT" >/dev/null 2>&1; then
      log "✓ Upstream service is reachable"
    else
      log "WARNING: Could not reach upstream service at $ip:$UPSTREAM_PORT"
    fi
  fi

  # Build ADD_ONION command
  # NEW:ED25519-V3 creates a new ED25519 v3 onion address
  # Port=80,$ip:$UPSTREAM_PORT maps port 80 to upstream service
  local add_onion="ADD_ONION NEW:ED25519-V3 Port=80,${ip}:${UPSTREAM_PORT}"
  log "Creating ephemeral onion: 80 → ${ip}:${UPSTREAM_PORT}"

  # Send command to Tor control port
  local response
  response=$(ctl "$add_onion" 2>/dev/null || true)

  # Check if onion was created successfully
  if echo "$response" | /bin/busybox grep -q '250-ServiceID='; then
    # Extract onion address from response
    local onion
    onion=$(echo "$response" | awk -F= '/250-ServiceID=/{print $2}').onion
    
    log "✓ ONION SERVICE CREATED: ${onion}"
    log "  Access via: http://${onion}/"
    log "  Backend: ${ip}:${UPSTREAM_PORT}"

    # Persist onion address to shared state
    echo "ONION=${onion}" > /run/lucid/onion/current.onion 2>/dev/null || {
      log "WARNING: Could not write onion state file"
    }

    return 0
  fi

  # Creation failed
  log "ERROR: Failed to create ephemeral onion service"
  log "Tor response:"
  printf '%s\n' "$response" | head -10
  
  return 1
}

# ============================================================================
# FUNCTION: main
# Purpose: Main entrypoint - orchestrates startup and monitoring
# ============================================================================
main() {
  # Print startup banner
  log "╔════════════════════════════════════════════════════════════════╗"
  log "║          Lucid Tor Proxy - Starting                            ║"
  log "╚════════════════════════════════════════════════════════════════╝"

  # Log configuration
  log "Configuration:"
  log "  Platform: ${LUCID_PLATFORM:-arm64}"
  log "  Environment: ${LUCID_ENV:-production}"
  log "  SOCKS Port: ${TOR_SOCKS_PORT}"
  log "  Control Port: ${CONTROL_PORT}"
  log "  Control Host: ${CONTROL_HOST}"
  log "  Data Directory: ${TOR_DATA_DIR}"
  log "  Seed Directory: ${TOR_SEED_DIR}"
  log "  Upstream Service: ${UPSTREAM_SERVICE:-<not configured>}"
  log "  Create Onion: ${CREATE_ONION}"
  log "  Use Bridges: ${TOR_USE_BRIDGES}"

  # Step 1: Ensure runtime directories exist
  ensure_runtime || {
    log "ERROR: Failed to set up runtime directories"
    exit 1
  }

  # Step 2: Preload seed data if available
  log ""
  log "STEP 1: Preloading Tor seed data..."
  preload_tor_data || {
    log "WARNING: Seed data preload failed (will bootstrap from scratch)"
  }

  # Step 3: Configure bridges if needed
  log ""
  log "STEP 2: Configuring bridge support..."
  if ! configure_bridges; then
    log "WARNING: Bridge configuration failed (continuing without bridges)"
  fi

  # Step 4: Start Tor daemon
  log ""
  log "STEP 3: Starting Tor daemon..."
  if ! start_tor; then
    log "FATAL: Failed to start Tor"
    exit 1
  fi

  # Step 5: Wait for control cookie to be created
  log ""
  log "STEP 4: Waiting for Tor initialization..."
  if ! wait_for_file "$COOKIE_FILE" 120; then
    log "FATAL: Tor control cookie not created within timeout"
    log "Possible causes:"
    log "  - Tor crashed or failed to start"
    log "  - /var/lib/tor directory permission issues"
    log "  - /etc/tor/torrc configuration error"
    log "Check Tor logs for details"
    exit 1
  fi

  # Step 6: Copy cookie to shared volume
  log ""
  log "STEP 5: Sharing control cookie with other services..."
  if ! copy_cookie_to_shared; then
    log "WARNING: Cookie sharing failed (tunnel-tools may not have access)"
  fi

  # Step 7: Wait for bootstrap to complete
  log ""
  log "STEP 6: Waiting for Tor bootstrap..."
  if ! wait_for_bootstrap; then
    log "FATAL: Tor bootstrap failed"
    log ""
    log "Bootstrap Failure - Troubleshooting Guide:"
    log "============================================"
    log ""
    log "1. Check Tor daemon logs:"
    log "   docker logs <container> | grep -i 'tor\\|bootstrap\\|conn'"
    log ""
    log "2. If stuck at 'connecting to directory authorities':"
    log "   - ISP is likely blocking Tor ports 443, 9001, etc."
    log "   - Configure bridges: TOR_USE_BRIDGES=1 TOR_BRIDGES='...'"
    log "   - See: https://bridges.torproject.org/"
    log ""
    log "3. If 'consensus' phase fails:"
    log "   - Ensure seed data is present: /seed/tor-data/cached-consensus"
    log "   - Check network connectivity to Tor directory authorities"
    log "   - Try restarting container: docker restart <container>"
    log ""
    log "4. Verify Tor is running:"
    log "   docker exec <container> ps aux | grep tor"
    log ""
    log "5. Test network access:"
    log "   docker exec <container> nc -zv 128.30.39.46 443"
    log ""
    log "6. Check control port:"
    log "   docker exec <container> nc -zv 127.0.0.1 9051"
    log ""
    exit 1
  fi

  # Step 8: Create ephemeral onion if configured
  log ""
  log "STEP 7: Setting up onion services..."
  if ! create_ephemeral_onion; then
    log "WARNING: Ephemeral onion creation failed or was skipped"
  fi

  # Step 9: Run monitoring loop
  log ""
  log "╔════════════════════════════════════════════════════════════════╗"
  log "║  ✓ Tor Proxy Ready                                              ║"
  log "╚════════════════════════════════════════════════════════════════╝"
  log ""
  log "Tor is fully operational. Now monitoring for stability..."
  log "SOCKS proxy: socks5://localhost:${TOR_SOCKS_PORT}"
  log "Control port: telnet://localhost:${CONTROL_PORT}"
  log ""

  # Monitor Tor process and restart if it dies
  while true; do
    if [ -f "${TOR_DATA_DIR}/tor.pid" ]; then
      local tor_pid
      tor_pid=$(/bin/busybox cat "${TOR_DATA_DIR}/tor.pid" 2>/dev/null || echo "")

      if [ -n "$tor_pid" ] && /bin/busybox kill -0 "$tor_pid" 2>/dev/null; then
        # Tor is running - sleep and check again
        /bin/busybox sleep 30
      else
        # Tor process died, restart it
        log "⚠ WARNING: Tor process died (PID: ${tor_pid:-unknown}), restarting..."
        
        start_tor || {
          log "ERROR: Failed to restart Tor"
          sleep 10
          continue
        }

        # Wait for cookie and bootstrap again
        if wait_for_file "$COOKIE_FILE" 60; then
          if ! wait_for_bootstrap; then
            log "WARNING: Bootstrap incomplete after restart"
          fi
        else
          log "WARNING: Cookie not ready after restart"
        fi
      fi
    else
      # No PID file, sleep and retry
      /bin/busybox sleep 30
    fi
  done
}

# Execute main function
main "$@"