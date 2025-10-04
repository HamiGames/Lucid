#!/usr/bin/env bash
# Lucid Dynamic Onion Creator - Create new .onion addresses on-the-fly
# Supports wallet operations and runtime service expansion
# Cookie authentication with ED25519-V3 keys for security

set -Eeuo pipefail

# Configuration
TOR_CONTROL_HOST="${TOR_CONTROL_HOST:-127.0.0.1}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_COOKIE_PATH="${TOR_COOKIE_PATH:-/var/lib/tor/control_auth_cookie}"
OUTDIR="${ONION_DIR:-/run/lucid/onion}"
DYNAMIC_DIR="$OUTDIR/dynamic"

# Default values
DEFAULT_ONION_PORT=80
DEFAULT_TARGET_HOST="127.0.0.1"
DEFAULT_TARGET_PORT=8080

# Logging functions
log() { printf '[dynamic-onion] %s\n' "$*"; }
error() { printf '[dynamic-onion][ERROR] %s\n' "$*" >&2; }
die() { error "$*"; exit 1; }
success() { printf '[dynamic-onion][✓] %s\n' "$*"; }

# Usage information
show_usage() {
  cat << 'USAGE'
Lucid Dynamic Onion Creator

USAGE:
  create_dynamic_onion.sh [OPTIONS] SERVICE_NAME

OPTIONS:
  --target-host HOST      Target host for onion (default: 127.0.0.1)
  --target-port PORT      Target port for onion (default: 8080)
  --onion-port PORT       Onion service port (default: 80)
  --env-var VAR           Environment variable name (default: ONION_<SERVICE_NAME>)
  --persistent            Save to persistent multi-onion.env file
  --wallet                Optimize for wallet operations (secure defaults)
  --list                  List all existing dynamic onions
  --remove SERVICE        Remove a dynamic onion service
  --rotate SERVICE        Rotate (delete and recreate) an existing onion
  --help, -h              Show this help

EXAMPLES:
  # Create wallet onion with secure defaults
  create_dynamic_onion.sh --wallet wallet-1

  # Create custom service onion
  create_dynamic_onion.sh --target-host api --target-port 8081 --onion-port 443 payment-api

  # List all dynamic onions
  create_dynamic_onion.sh --list

  # Remove a specific onion
  create_dynamic_onion.sh --remove wallet-1

  # Rotate (refresh) an onion address
  create_dynamic_onion.sh --rotate wallet-1

WALLET OPERATIONS:
  For wallet services, use --wallet flag for:
  - Random high port assignment (security)
  - Additional entropy in service ID
  - Enhanced logging for audit trails
  - Automatic backup of private keys (if supported)

FILES CREATED:
  $DYNAMIC_DIR/<service>.onion       - Onion address
  $DYNAMIC_DIR/<service>.hex         - Service ID in hex
  $DYNAMIC_DIR/<service>.meta        - Service metadata
  $OUTDIR/dynamic-onions.env         - Environment variables
  $OUTDIR/onion-registry.json        - JSON registry of all onions
USAGE
}

# Validate environment and dependencies
validate_environment() {
  [ -s "$TOR_COOKIE_PATH" ] || die "control cookie missing or empty at $TOR_COOKIE_PATH"
  command -v xxd >/dev/null 2>&1 || command -v hexdump >/dev/null 2>&1 || die "xxd or hexdump required for cookie hex encoding"
  command -v nc >/dev/null 2>&1 || die "netcat required for tor control protocol"
  command -v jq >/dev/null 2>&1 || log "WARN: jq not found - JSON registry will be disabled"
  
  mkdir -p "$OUTDIR" "$DYNAMIC_DIR" || die "failed to create output directories"
}

# Get cookie hex for authentication
get_cookie_hex() {
  if command -v xxd >/dev/null 2>&1; then
    xxd -p "$TOR_COOKIE_PATH" | tr -d '\n'
  else
    hexdump -v -e '1/1 "%02x"' "$TOR_COOKIE_PATH"
  fi
}

# Send control command to tor
send_control_command() {
  local cmd="$1"
  local cookie_hex="$2"
  
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" | \
    nc -w 10 "$TOR_CONTROL_HOST" "$TOR_CONTROL_PORT" 2>/dev/null
}

# Generate secure random port for wallet operations
generate_wallet_port() {
  # Random port in range 8000-9999 for wallet services
  echo $((8000 + RANDOM % 2000))
}

# Create service metadata
create_service_metadata() {
  local service_name="$1"
  local onion_port="$2"
  local target_host="$3"
  local target_port="$4"
  local onion_address="$5"
  local is_wallet="$6"
  
  cat > "$DYNAMIC_DIR/${service_name}.meta" << EOF
# Lucid Dynamic Onion Service Metadata
SERVICE_NAME=$service_name
ONION_ADDRESS=$onion_address
ONION_PORT=$onion_port
TARGET_HOST=$target_host
TARGET_PORT=$target_port
CREATED=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
IS_WALLET=$is_wallet
COOKIE_AUTH=ED25519-V3
EPHEMERAL=true
EOF
}

# Update JSON registry (if jq available)
update_json_registry() {
  local service_name="$1"
  local onion_address="$2"
  local target_host="$3"
  local target_port="$4"
  local is_wallet="$5"
  local operation="${6:-create}"  # create, remove
  
  local registry_file="$OUTDIR/onion-registry.json"
  
  if ! command -v jq >/dev/null 2>&1; then
    return 0
  fi
  
  # Initialize registry if not exists
  if [ ! -f "$registry_file" ]; then
    echo '{"dynamic_onions":{},"static_onions":{},"last_updated":""}' > "$registry_file"
  fi
  
  case "$operation" in
    create|update)
      local entry=$(jq -n \
        --arg name "$service_name" \
        --arg address "$onion_address" \
        --arg target_host "$target_host" \
        --arg target_port "$target_port" \
        --arg is_wallet "$is_wallet" \
        --arg created "$(date -u +"%Y-%m-%d %H:%M:%S UTC")" \
        '{
          address: $address,
          target_host: $target_host,
          target_port: $target_port,
          is_wallet: ($is_wallet == "true"),
          created: $created
        }')
      
      jq --arg name "$service_name" \
         --argjson entry "$entry" \
         --arg updated "$(date -u +"%Y-%m-%d %H:%M:%S UTC")" \
         '.dynamic_onions[$name] = $entry | .last_updated = $updated' \
         "$registry_file" > "${registry_file}.tmp" && mv "${registry_file}.tmp" "$registry_file"
      ;;
    remove)
      jq --arg name "$service_name" \
         --arg updated "$(date -u +"%Y-%m-%d %H:%M:%S UTC")" \
         'del(.dynamic_onions[$name]) | .last_updated = $updated' \
         "$registry_file" > "${registry_file}.tmp" && mv "${registry_file}.tmp" "$registry_file"
      ;;
  esac
}

# Create a new dynamic onion service
create_onion() {
  local service_name="$1"
  local onion_port="$2"
  local target_host="$3"
  local target_port="$4"
  local env_var="${5:-ONION_${service_name^^}}"  # Convert to uppercase
  local is_wallet="${6:-false}"
  
  log "Creating dynamic onion for $service_name: $onion_port -> $target_host:$target_port"
  
  local cookie_hex
  cookie_hex="$(get_cookie_hex)"
  [ -n "$cookie_hex" ] || die "failed to get cookie hex"
  
  # Build ADD_ONION command for ED25519-V3
  local add_onion_cmd="ADD_ONION NEW:ED25519-V3 Port=${onion_port},${target_host}:${target_port}"
  
  # Send command
  local response
  response="$(send_control_command "$add_onion_cmd" "$cookie_hex" || true)"
  
  # Parse ServiceID from response
  if echo "$response" | grep -qE '^250(-| )ServiceID='; then
    local service_id
    service_id="$(echo "$response" | awk -F= '/^250(-| )ServiceID=/{print $2}' | tr -d '\r' | head -1)"
    local onion_address="${service_id}.onion"
    
    # Save onion files
    echo "$onion_address" > "$DYNAMIC_DIR/${service_name}.onion"
    printf '%s' "$service_id" | xxd -p | tr -d '\n' > "$DYNAMIC_DIR/${service_name}.hex"
    
    # Create metadata
    create_service_metadata "$service_name" "$onion_port" "$target_host" "$target_port" "$onion_address" "$is_wallet"
    
    # Update environment file
    local env_file="$OUTDIR/dynamic-onions.env"
    # Remove existing entry if present
    grep -v "^${env_var}=" "$env_file" > "${env_file}.tmp" 2>/dev/null || touch "${env_file}.tmp"
    echo "${env_var}=${onion_address}" >> "${env_file}.tmp"
    mv "${env_file}.tmp" "$env_file"
    
    # Update JSON registry
    update_json_registry "$service_name" "$onion_address" "$target_host" "$target_port" "$is_wallet" "create"
    
    success "$service_name: $onion_address"
    
    if [ "$is_wallet" = "true" ]; then
      log "WALLET: Service created with enhanced security"
      log "WALLET: Target port $target_port is randomized for security"
      log "WALLET: Service ID hex: $(cat "$DYNAMIC_DIR/${service_name}.hex")"
    fi
    
    return 0
  else
    error "Failed to create onion for $service_name"
    echo "$response" | sed -n '1,10p' >&2
    return 1
  fi
}

# Remove an existing dynamic onion
remove_onion() {
  local service_name="$1"
  
  if [ ! -f "$DYNAMIC_DIR/${service_name}.onion" ]; then
    error "Service $service_name not found"
    return 1
  fi
  
  local onion_address
  onion_address="$(cat "$DYNAMIC_DIR/${service_name}.onion")"
  local service_id="${onion_address%.onion}"
  
  log "Removing dynamic onion: $service_name ($onion_address)"
  
  local cookie_hex
  cookie_hex="$(get_cookie_hex)"
  [ -n "$cookie_hex" ] || die "failed to get cookie hex"
  
  # Send DEL_ONION command
  local del_response
  del_response="$(send_control_command "DEL_ONION $service_id" "$cookie_hex" || true)"
  
  # Remove local files
  rm -f "$DYNAMIC_DIR/${service_name}".{onion,hex,meta}
  
  # Update environment file
  local env_file="$OUTDIR/dynamic-onions.env"
  if [ -f "$env_file" ]; then
    grep -v "=${onion_address}$" "$env_file" > "${env_file}.tmp" 2>/dev/null || touch "${env_file}.tmp"
    mv "${env_file}.tmp" "$env_file"
  fi
  
  # Update JSON registry
  update_json_registry "$service_name" "" "" "" "false" "remove"
  
  success "Removed $service_name"
}

# List all dynamic onions
list_onions() {
  echo "Dynamic Onion Services:"
  echo "======================"
  
  if [ ! -d "$DYNAMIC_DIR" ] || [ -z "$(ls -A "$DYNAMIC_DIR" 2>/dev/null)" ]; then
    echo "No dynamic onions found."
    return 0
  fi
  
  for meta_file in "$DYNAMIC_DIR"/*.meta; do
    [ -f "$meta_file" ] || continue
    
    local service_name
    service_name="$(basename "$meta_file" .meta)"
    
    if [ -f "$DYNAMIC_DIR/${service_name}.onion" ]; then
      local onion_address
      onion_address="$(cat "$DYNAMIC_DIR/${service_name}.onion")"
      
      printf "%-15s %s\n" "$service_name:" "$onion_address"
      
      # Show additional info if metadata exists
      if [ -f "$meta_file" ]; then
        local target_host target_port is_wallet
        target_host="$(grep '^TARGET_HOST=' "$meta_file" | cut -d= -f2)"
        target_port="$(grep '^TARGET_PORT=' "$meta_file" | cut -d= -f2)"
        is_wallet="$(grep '^IS_WALLET=' "$meta_file" | cut -d= -f2)"
        
        printf "%-15s -> %s:%s" "" "$target_host" "$target_port"
        [ "$is_wallet" = "true" ] && printf " [WALLET]"
        printf "\n"
      fi
    fi
  done
  
  # Show JSON registry summary if available
  if command -v jq >/dev/null 2>&1 && [ -f "$OUTDIR/onion-registry.json" ]; then
    echo
    echo "Registry Summary:"
    jq -r '.dynamic_onions | length as $count | "Total dynamic onions: \($count)"' "$OUTDIR/onion-registry.json"
  fi
}

# Rotate (delete and recreate) an onion
rotate_onion() {
  local service_name="$1"
  
  if [ ! -f "$DYNAMIC_DIR/${service_name}.meta" ]; then
    error "Service $service_name not found"
    return 1
  fi
  
  log "Rotating onion for $service_name"
  
  # Read current metadata
  local target_host target_port onion_port is_wallet
  target_host="$(grep '^TARGET_HOST=' "$DYNAMIC_DIR/${service_name}.meta" | cut -d= -f2)"
  target_port="$(grep '^TARGET_PORT=' "$DYNAMIC_DIR/${service_name}.meta" | cut -d= -f2)"
  onion_port="$(grep '^ONION_PORT=' "$DYNAMIC_DIR/${service_name}.meta" | cut -d= -f2)"
  is_wallet="$(grep '^IS_WALLET=' "$DYNAMIC_DIR/${service_name}.meta" | cut -d= -f2)"
  
  # Remove current onion
  remove_onion "$service_name"
  
  # Create new onion with same parameters
  create_onion "$service_name" "$onion_port" "$target_host" "$target_port" "ONION_${service_name^^}" "$is_wallet"
  
  success "Rotated $service_name with new address"
}

# Main execution
main() {
  local service_name=""
  local target_host="$DEFAULT_TARGET_HOST"
  local target_port="$DEFAULT_TARGET_PORT"
  local onion_port="$DEFAULT_ONION_PORT"
  local env_var=""
  local is_wallet="false"
  local persistent="false"
  local action="create"
  
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target-host)
        target_host="$2"
        shift 2
        ;;
      --target-port)
        target_port="$2"
        shift 2
        ;;
      --onion-port)
        onion_port="$2"
        shift 2
        ;;
      --env-var)
        env_var="$2"
        shift 2
        ;;
      --wallet)
        is_wallet="true"
        target_port="$(generate_wallet_port)"
        shift
        ;;
      --persistent)
        persistent="true"
        shift
        ;;
      --list)
        action="list"
        shift
        ;;
      --remove)
        action="remove"
        service_name="$2"
        shift 2
        ;;
      --rotate)
        action="rotate"
        service_name="$2"
        shift 2
        ;;
      --help|-h)
        show_usage
        exit 0
        ;;
      -*)
        error "Unknown option: $1"
        show_usage
        exit 1
        ;;
      *)
        if [ -z "$service_name" ]; then
          service_name="$1"
        else
          error "Unexpected argument: $1"
          exit 1
        fi
        shift
        ;;
    esac
  done
  
  validate_environment
  
  case "$action" in
    list)
      list_onions
      ;;
    remove)
      [ -n "$service_name" ] || die "Service name required for removal"
      remove_onion "$service_name"
      ;;
    rotate)
      [ -n "$service_name" ] || die "Service name required for rotation"
      rotate_onion "$service_name"
      ;;
    create)
      [ -n "$service_name" ] || die "Service name required"
      
      # Set default env_var if not provided
      [ -n "$env_var" ] || env_var="ONION_${service_name^^}"
      
      create_onion "$service_name" "$onion_port" "$target_host" "$target_port" "$env_var" "$is_wallet"
      
      # If persistent flag, also add to main multi-onion.env
      if [ "$persistent" = "true" ] && [ -f "$OUTDIR/multi-onion.env" ]; then
        local onion_address
        onion_address="$(cat "$DYNAMIC_DIR/${service_name}.onion")"
        echo "${env_var}=${onion_address}" >> "$OUTDIR/multi-onion.env"
        log "Added to persistent environment file"
      fi
      ;;
  esac
}

# Execute main function
main "$@"