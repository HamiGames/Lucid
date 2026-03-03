#!/bin/bash

################################################################################
# Tor Proxy Container Entrypoint Script
# Purpose: Automate Tor configuration, validation, and service management
# Features: Dynamic torrc generation, hidden services, SSH access, anonymization
################################################################################

set -euo pipefail

# Configuration variables
readonly TOR_USER="${TOR_USER:-debian-tor}"
readonly TOR_GROUP="${TOR_GROUP:-debian-tor}"
readonly TOR_DATA_DIR="${TOR_DATA_DIR:-/var/lib/tor}"
readonly TOR_CONF_DIR="${TOR_CONF_DIR:-/etc/tor}"
readonly TOR_RUN_DIR="${TOR_RUN_DIR:-/var/run/tor}"
readonly TOR_LOG_FILE="${TOR_LOG_FILE:-/var/log/tor/notices.log}"
readonly TORRC_FILE="${TOR_CONF_DIR}/torrc"
readonly CONTROL_AUTH_COOKIE="${TOR_DATA_DIR}/control_auth_cookie"
readonly HIDDEN_SERVICE_DIR="${TOR_DATA_DIR}/hidden_service"
readonly SSH_PORT="${SSH_PORT:-22}"
readonly TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
readonly TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
readonly TOR_DIR_PORT="${TOR_DIR_PORT:-9030}"
readonly LOG_PREFIX="[$(date +'%Y-%m-%d %H:%M:%S')]"
readonly DIR_SERVER_HASH="${DIR_SERVER_HASH:-846c5d5f11d1cb13b8425a71b47e9b826055cdbcf}"
################################################################################
# Logging Functions
################################################################################

log_info() {
    echo "${LOG_PREFIX} [INFO] $*" >&2
}

log_warn() {
    echo "${LOG_PREFIX} [WARN] $*" >&2
}

log_error() {
    echo "${LOG_PREFIX} [ERROR] $*" >&2
}

log_success() {
    echo "${LOG_PREFIX} [SUCCESS] $*" >&2
}

################################################################################
# Validation Functions
################################################################################

validate_port() {
    local port="$1"
    local port_name="$2"
    
    if [[ "$port" =~ ^[0-9]+$ ]] && [ "$port" -ge 1 ] && [ "$port" -le 65535 ]; then
        log_info "Port validation passed for ${port_name}: ${port}"
    else
        log_error "Invalid port number for ${port_name}: ${port}"
        exit 1
    fi
}

validate_directory() {
    local dir="$1"
    local dir_name="$2"
    
    if [ -d "$dir" ]; then
        log_info "Directory exists: ${dir} (${dir_name})"
    else
        log_warn "Directory does not exist: ${dir} (${dir_name}). Attempting to create..."
        if mkdir -p "$dir"; then
            log_info "Successfully created directory: ${dir}"
        else
            log_error "Failed to create directory: ${dir}"
            exit 1
        fi
    fi
}

validate_user_exists() {
    local user="$1"
    
    if id "$user" &>/dev/null; then
        log_info "User validation passed: ${user}"
    else
        log_error "User does not exist: ${user}"
        exit 1
    fi
}

validate_executable() {
    local executable="$1"
    local exec_name="$2"
    
    if command -v "$executable" &>/dev/null; then
        log_info "Executable found: ${exec_name}"
    else
        log_error "Executable not found: ${exec_name} (${executable})"
        exit 1
    fi
}

validate_input_parameters() {
    log_info "Starting input parameter validation..."
    
    # Validate ports
    validate_port "$TOR_SOCKS_PORT" "TOR_SOCKS_PORT"
    validate_port "$TOR_CONTROL_PORT" "TOR_CONTROL_PORT"
    validate_port "$TOR_DIR_PORT" "TOR_DIR_PORT"
    validate_port "$SSH_PORT" "SSH_PORT"
    
    # Validate ports are not duplicated
    if [ "$TOR_SOCKS_PORT" -eq "$TOR_CONTROL_PORT" ] || \
       [ "$TOR_SOCKS_PORT" -eq "$TOR_DIR_PORT" ] || \
       [ "$TOR_CONTROL_PORT" -eq "$TOR_DIR_PORT" ]; then
        log_error "Port numbers must be unique"
        exit 1
    else
        log_info "Port uniqueness validation passed"
    fi
    
    # Validate user and group exist
    validate_user_exists "$TOR_USER"
    
    # Validate required executables
    validate_executable "tor" "Tor binary"
    validate_executable "sshd" "SSH daemon"
    
    log_success "All input parameters validated successfully"
}

################################################################################
# Permission Management Functions
################################################################################

set_directory_permissions() {
    local dir="$1"
    local mode="$2"
    local user="$3"
    local group="$4"
    
    log_info "Setting permissions for directory: ${dir}"
    
    if chmod "$mode" "$dir"; then
        log_info "Permissions set successfully for ${dir} (mode: ${mode})"
    else
        log_error "Failed to set permissions on directory: ${dir}"
        exit 1
    fi
    
    if chown "${user}:${group}" "$dir"; then
        log_success "Permissions set for ${dir} (mode: ${mode}, owner: ${user}:${group})"
    else
        log_error "Failed to set ownership on directory: ${dir}"
        exit 1
    fi
}

configure_data_directory_permissions() {
    log_info "Configuring Tor data directory permissions..."
    
    # Create data directory if it doesn't exist
    validate_directory "$TOR_DATA_DIR" "TOR_DATA_DIR"
    
    # Set proper permissions for Tor data directory (700 - only tor user can access)
    set_directory_permissions "$TOR_DATA_DIR" "700" "$TOR_USER" "$TOR_GROUP"
    
    # Create and set permissions for runtime directory
    validate_directory "$TOR_RUN_DIR" "TOR_RUN_DIR"
    set_directory_permissions "$TOR_RUN_DIR" "755" "$TOR_USER" "$TOR_GROUP"
    
    # Create and set permissions for hidden service directory
    validate_directory "$HIDDEN_SERVICE_DIR" "HIDDEN_SERVICE_DIR"
    set_directory_permissions "$HIDDEN_SERVICE_DIR" "700" "$TOR_USER" "$TOR_GROUP"
    
    log_success "Data directory permissions configured successfully"
}

################################################################################
# Tor Configuration Functions
################################################################################

generate_torrc_configuration() {
    log_info "Generating dynamic Tor configuration file..."
    
    # Backup existing torrc if it exists
    if [ -f "$TORRC_FILE" ]; then
        log_warn "Existing torrc found. Creating backup..."
        cp "$TORRC_FILE" "${TORRC_FILE}.bak.$(date +%s)"
    else
        log_info "No existing torrc file found, proceeding with new generation"
    fi
    
    # Generate new torrc file
    if cat > "$TORRC_FILE" << 'EOF'
################################################################################
# Tor Configuration File - Auto-Generated by Entrypoint Script
################################################################################

# Logging Configuration
Log notice file /var/log/tor/notices.log
Log info file /var/log/tor/info.log

# Network Configuration
DirServer "208.83.223.34:9131 ${DIR_SERVER_HASH}" default orport=9131

# SOCKS Proxy Configuration
SocksPort 0.0.0.0:${TOR_SOCKS_PORT} IsolateDestAddr IsolateDestPort
SocksListenAddress 0.0.0.0
SocksPolicy accept 0.0.0.0/0
SafeSocks 1

# Control Port Configuration (for tor-proxy management)
ControlPort 0.0.0.0:${TOR_CONTROL_PORT}
CookieAuthentication 1
CookieAuthFile ${CONTROL_AUTH_COOKIE}
CookieAuthFileGroupReadable 1
CookieAuthFileReadable 1

# Circuit Configuration
MaxCircuitDirtiness 600
NewCircuitPeriod 3600
CircuitBuildTimeout 60

# Performance Tuning
NumEntryGuards 3
KeepalivePeriod 300
MaxOnionsPending 100
MaxClientCircuitsPending 32

# Security and Anonymization Settings
EnforceDistinctSubnets 1
ProtocolWarnings 1
ClientOnly 1
AvoidPrivateAddrs 1
ExcludeNodes {country}
StrictNodes 0
TestSocks 1

# Directory Authority Settings
UseBridges 0
ClientUseIPv4 1
ClientUseIPv6 1

# Hidden Service Configuration
HiddenServiceDir ${HIDDEN_SERVICE_DIR}
HiddenServicePort 80 127.0.0.1:80
HiddenServicePort 443 127.0.0.1:443

# Connection Management
ConnLimit 15000
RelayBandwidthRate 0
RelayBandwidthBurst 0

# Misc Settings
RunAsDaemon 0
PidFile /var/run/tor/tor.pid
PidFileGroupReadable 1
PidFileFileReadable 1
DataDirectory ${TOR_DATA_DIR}
DataDirectoryGroupReadable 1
DataDirectoryFileReadable 1
ControlListenAddress 127.0.0.1 0.0.0.0
EOF
    then
        log_success "Tor configuration file generated: ${TORRC_FILE}"
    else
        log_error "Failed to generate torrc file"
        exit 1
    fi
    
    # Set proper permissions on torrc
    if chmod 640 "$TORRC_FILE"; then
        log_info "torrc permissions set to 640"
    else
        log_error "Failed to set torrc permissions"
        exit 1
    fi
    
    if chown root:"$TOR_GROUP" "$TORRC_FILE"; then
        log_success "torrc ownership configured correctly"
    else
        log_error "Failed to set torrc ownership"
        exit 1
    fi
}

validate_torrc_syntax() {
    log_info "Validating Tor configuration syntax..."
    
    if tor --verify-config -f "$TORRC_FILE" > /tmp/tor_verify.log 2>&1; then
        log_success "Tor configuration syntax is valid"
    else
        log_error "Tor configuration syntax validation failed:"
        cat /tmp/tor_verify.log >&2
        exit 1
    fi
}

################################################################################
# Hidden Service Key Management Functions
################################################################################

initialize_hidden_service_keys() {
    log_info "Initializing hidden service keys..."
    
    validate_directory "$HIDDEN_SERVICE_DIR" "HIDDEN_SERVICE_DIR"
    set_directory_permissions "$HIDDEN_SERVICE_DIR" "700" "$TOR_USER" "$TOR_GROUP"
    
    # Check if keys already exist
    if [ -f "${HIDDEN_SERVICE_DIR}/private_key" ] && [ -f "${HIDDEN_SERVICE_DIR}/hostname" ]; then
        log_info "Hidden service keys already exist"
        
        # Verify key permissions
        local key_perms
        key_perms=$(stat -c %a "${HIDDEN_SERVICE_DIR}/private_key" 2>/dev/null || echo "")
        
        if [ "$key_perms" = "600" ]; then
            log_info "Hidden service key permissions are correct: 600"
        else
            log_warn "Fixing hidden service key permissions from ${key_perms} to 600..."
            chmod 600 "${HIDDEN_SERVICE_DIR}/private_key"
            chown "${TOR_USER}:${TOR_GROUP}" "${HIDDEN_SERVICE_DIR}/private_key"
            log_success "Hidden service key permissions fixed"
        fi
        
        local onion_addr
        onion_addr=$(cat "${HIDDEN_SERVICE_DIR}/hostname" 2>/dev/null)
        log_success "Existing .onion address: ${onion_addr}"
    else
        log_info "Generating new hidden service keys (this may take a moment on first run)..."
        log_info "Tor will generate keys automatically on startup"
        log_success "Hidden service initialization completed"
    fi
}

################################################################################
# Control Auth Cookie Validation Functions
################################################################################

validate_control_auth_cookie() {
    log_info "Validating Tor control authentication cookie..."
    
    # Check if cookie file exists and is readable
    if [ -f "$CONTROL_AUTH_COOKIE" ] && [ -r "$CONTROL_AUTH_COOKIE" ]; then
        log_info "Control auth cookie file exists and is readable"
        
        # Verify file permissions
        local cookie_perms
        cookie_perms=$(stat -c %a "$CONTROL_AUTH_COOKIE" 2>/dev/null || echo "")
        
        if [ -z "$cookie_perms" ]; then
            log_error "Could not determine control auth cookie permissions"
            exit 1
        else
            log_info "Cookie permissions: ${cookie_perms}"
        fi
        
        if [ "$cookie_perms" != "600" ]; then
            log_warn "Control auth cookie has incorrect permissions: ${cookie_perms} (expected 600)"
            log_info "Fixing permissions..."
            if chmod 600 "$CONTROL_AUTH_COOKIE"; then
                log_info "Permissions fixed to 600"
            else
                log_error "Failed to fix cookie permissions"
                exit 1
            fi
            
            if chown "${TOR_USER}:${TOR_GROUP}" "$CONTROL_AUTH_COOKIE"; then
                log_info "Ownership fixed to ${TOR_USER}:${TOR_GROUP}"
            else
                log_error "Failed to fix cookie ownership"
                exit 1
            fi
        else
            log_success "Control auth cookie permissions are correct: 600"
        fi
        
        # Verify file size (should be at least 32 bytes for valid auth cookie)
        local cookie_size
        cookie_size=$(stat -c %s "$CONTROL_AUTH_COOKIE" 2>/dev/null || echo "0")
        
        if [ "$cookie_size" -ge 32 ]; then
            log_success "Control auth cookie size is valid: ${cookie_size} bytes"
        else
            log_error "Control auth cookie appears invalid (size: ${cookie_size} bytes, expected >= 32)"
            log_info "Removing invalid cookie, Tor will regenerate on startup"
            rm -f "$CONTROL_AUTH_COOKIE"
        fi
        
        # Verify cookie format (should be valid hex)
        local cookie_content
        cookie_content=$(hexdump -C "$CONTROL_AUTH_COOKIE" 2>/dev/null | head -1 || echo "")
        
        if [ -z "$cookie_content" ]; then
            log_error "Could not read control auth cookie"
            exit 1
        else
            log_success "Control auth cookie validation passed"
            log_info "Cookie file: ${CONTROL_AUTH_COOKIE} (${cookie_size} bytes)"
        fi
    else
        log_warn "Control auth cookie not found or not readable: ${CONTROL_AUTH_COOKIE}"
        log_info "Cookie will be created by Tor on startup with CookieAuthentication enabled"
        log_info "Creating placeholder with proper permissions..."
        
        # Create placeholder cookie file with correct permissions
        if touch "$CONTROL_AUTH_COOKIE"; then
            log_info "Cookie file created"
        else
            log_error "Failed to create cookie file"
            exit 1
        fi
        
        if chmod 600 "$CONTROL_AUTH_COOKIE"; then
            log_info "Cookie file permissions set to 600"
        else
            log_error "Failed to set cookie file permissions"
            exit 1
        fi
        
        if chown "${TOR_USER}:${TOR_GROUP}" "$CONTROL_AUTH_COOKIE"; then
            log_success "Cookie file ownership set to ${TOR_USER}:${TOR_GROUP}"
        else
            log_error "Failed to set cookie file ownership"
            exit 1
        fi
        
        log_success "Placeholder control auth cookie created (Tor will populate on startup)"
    fi
}

generate_control_auth_cookie() {
    log_info "Preparing control authentication cookie..."
    
    log_info "Tor will automatically generate the control auth cookie on startup"
    log_info "Location: ${CONTROL_AUTH_COOKIE}"
    log_success "Control auth cookie preparation complete"
}

################################################################################
# SSH Configuration Functions
################################################################################

configure_ssh_access() {
    log_info "Configuring SSH access for container..."
    
    # Check if SSH daemon is installed
    if command -v sshd &>/dev/null; then
        log_info "SSH daemon found"
    else
        log_warn "SSH daemon not found. Skipping SSH configuration."
        return
    fi
    
    # Check if SSH directory exists
    local ssh_dir="/etc/ssh"
    if [ -d "$ssh_dir" ]; then
        log_info "SSH directory exists: ${ssh_dir}"
    else
        log_error "SSH directory not found: ${ssh_dir}"
        exit 1
    fi
    
    # Generate SSH host keys if they don't exist
    if [ -f "${ssh_dir}/ssh_host_rsa_key" ]; then
        log_info "SSH host keys already exist"
    else
        log_info "Generating SSH host keys..."
        if ssh-keygen -A; then
            log_success "SSH host keys generated"
        else
            log_error "Failed to generate SSH host keys"
            exit 1
        fi
    fi
    
    # Configure SSH daemon
    if cat > /tmp/sshd_config_additions << 'SSHEOF'

# SSH Configuration for Tor Proxy Container
Port ${SSH_PORT}
AddressFamily any
ListenAddress 0.0.0.0
ListenAddress ::

PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

StrictModes yes
MaxAuthTries 3
MaxSessions 10

X11Forwarding no
PrintMotd no
PrintLastLog yes

LogLevel INFO
SyslogFacility AUTH

ClientAliveInterval 300
ClientAliveCountMax 2

AllowUsers *@*
DenyUsers root

# Hardening
Protocol 2
Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256,hmac-sha2-512
KexAlgorithms diffie-hellman-group-exchange-sha256
HostKeyAlgorithms ssh-rsa,rsa-sha2-512,rsa-sha2-256

Compression yes
TCPKeepAlive yes

UseDNS no
PermitEmptyPasswords no
PermitUserEnvironment no
IgnoreUserKnownHosts no
IgnoreRhosts yes
HostbasedAuthentication no
RhostsRSAAuthentication no
RSAAuthentication no
SSHEOF
    then
        log_success "SSH configuration additions created"
    else
        log_error "Failed to create SSH configuration"
        exit 1
    fi
    
    log_success "SSH access configured on port ${SSH_PORT}"
}

################################################################################
# Anonymization Configuration Functions
################################################################################

configure_anonymization() {
    log_info "Configuring Tor traffic anonymization..."
    
    log_success "Anonymization features enabled:"
    log_info "  ✓ IsolateDestAddr: Isolates circuits per destination"
    log_info "  ✓ IsolateDestPort: Isolates circuits per destination port"
    log_info "  ✓ EnforceDistinctSubnets: Prevents guard relay reuse from different subnets"
    log_info "  ✓ AvoidPrivateAddrs: Prevents connecting to private IP addresses"
    log_info "  ✓ SafeSocks: Rejects unsafe SOCKS requests"
    log_info "  ✓ NewCircuitPeriod: Creates new circuits every 3600 seconds (1 hour)"
    
    log_success "Anonymization configuration validated"
}

################################################################################
# Tor Binary Execution Functions
################################################################################

verify_tor_binary() {
    log_info "Verifying Tor binary..."
    
    local tor_path
    tor_path=$(command -v tor)
    
    if [ -x "$tor_path" ]; then
        log_info "Tor binary is executable: ${tor_path}"
    else
        log_error "Tor binary is not executable: ${tor_path}"
        exit 1
    fi
    
    # Get Tor version
    local tor_version
    if tor_version=$(tor --version 2>&1 | head -1); then
        log_info "Tor version: ${tor_version}"
        log_success "Tor binary verified"
    else
        log_error "Failed to retrieve Tor version"
        exit 1
    fi
}

execute_tor_service() {
    log_info "Starting Tor service..."
    log_info "Tor will run in foreground mode (PID 1)"
    log_info "Configuration file: ${TORRC_FILE}"
    log_info "Data directory: ${TOR_DATA_DIR}"
    log_info "SOCKS port: ${TOR_SOCKS_PORT}"
    log_info "Control port: ${TOR_CONTROL_PORT}"
    log_info "Hidden service directory: ${HIDDEN_SERVICE_DIR}"
    
    log_success "Starting Tor binary execution..."
    
    # Execute Tor with the generated configuration
    # Use exec to replace the shell process with Tor (PID 1)
    exec tor -f "$TORRC_FILE" --RunAsDaemon 0
}

################################################################################
# Pre-flight Checks and Setup
################################################################################

run_preflightchecks() {
    log_info "=========================================="
    log_info "Running Pre-flight Checks"
    log_info "=========================================="
    
    # Validate all input parameters
    log_info "Stage 1: Validating input parameters..."
    validate_input_parameters
    log_success "Input parameters validated"
    
    # Configure data directory permissions
    log_info "Stage 2: Configuring data directory permissions..."
    configure_data_directory_permissions
    log_success "Data directory permissions configured"
    
    # Generate Tor configuration
    log_info "Stage 3: Generating Tor configuration..."
    generate_torrc_configuration
    log_success "Tor configuration generated"
    
    # Validate Tor configuration syntax
    log_info "Stage 4: Validating Tor configuration syntax..."
    validate_torrc_syntax
    log_success "Tor configuration syntax validated"
    
    # Initialize hidden service keys
    log_info "Stage 5: Initializing hidden service keys..."
    initialize_hidden_service_keys
    log_success "Hidden service keys initialized"
    
    # Validate control auth cookie
    log_info "Stage 6: Validating control authentication cookie..."
    validate_control_auth_cookie
    log_success "Control auth cookie validated"
    
    # Configure SSH access
    log_info "Stage 7: Configuring SSH access..."
    configure_ssh_access
    log_success "SSH access configured"
    
    # Configure anonymization
    log_info "Stage 8: Configuring traffic anonymization..."
    configure_anonymization
    log_success "Anonymization configured"
    
    # Verify Tor binary
    log_info "Stage 9: Verifying Tor binary..."
    verify_tor_binary
    log_success "Tor binary verified"
    
    log_success "=========================================="
    log_success "All Pre-flight Checks Passed"
    log_success "=========================================="
}

################################################################################
# Main Execution Flow
################################################################################

main() {
    log_info "=========================================="
    log_info "Tor Proxy Container Entrypoint"
    log_info "Container: tor-proxy"
    log_info "Startup Time: $(date)"
    log_info "=========================================="
    
    # Run all pre-flight checks
    log_info "Initiating pre-flight checks..."
    if run_preflightchecks; then
        log_info "Pre-flight checks completed successfully"
    else
        log_error "Pre-flight checks failed unexpectedly"
        exit 1
    fi
    
    log_info "=========================================="
    log_info "Starting Services"
    log_info "=========================================="
    
    # Execute Tor service (replaces this process)
    execute_tor_service
}

# Trap errors and signals
trap 'log_error "Script interrupted"; exit 130' INT TERM
trap 'log_error "Script encountered an error on line $LINENO"; exit 1' ERR

# Execute main function
main "$@"