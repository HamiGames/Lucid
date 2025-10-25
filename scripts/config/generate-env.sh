#!/bin/bash
# =============================================================================
# Lucid Environment Configuration Generator - Pi Console Native
# =============================================================================
# This script generates environment configuration files for the Lucid project
# Optimized for Raspberry Pi console usage with comprehensive validation
# 
# Features:
# - Pi console native with package requirement checks
# - Mount point validation for Pi storage
# - Robust fallback mechanisms for minimal Pi installations
# - Consistent .env.* file naming
# - Global path management
# =============================================================================

set -euo pipefail

# =============================================================================
# GLOBAL PATH CONFIGURATION
# =============================================================================
# Set global path variables for consistent file management across all scripts
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_CONFIG_DIR="$PROJECT_ROOT/configs/environment"
SCRIPTS_CONFIG_DIR="$PROJECT_ROOT/scripts/config"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
TEMPLATES_DIR="$PROJECT_ROOT/configs/templates"
BACKUP_DIR="$PROJECT_ROOT/configs/backups"

# Current script directory (for relative operations)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build configuration
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_PLATFORM="linux/arm64"

# =============================================================================
# PI CONSOLE NATIVE CONFIGURATION
# =============================================================================
# Pi-specific mount points and storage validation
PI_MOUNT_POINTS=(
    "/mnt/myssd"
    "/mnt/usb"
    "/mnt/sdcard"
    "/opt"
    "/var"
    "/tmp"
)

# Required Pi packages for environment generation
PI_REQUIRED_PACKAGES=(
    "openssl"
    "coreutils"
    "util-linux"
    "procps"
    "grep"
    "sed"
    "awk"
    "bash"
)

# Pi-specific fallback mechanisms
PI_FALLBACK_DIRS=(
    "/tmp/lucid-env"
    "/var/tmp/lucid-env"
    "/home/pi/lucid-env"
)

# =============================================================================
# COLORED OUTPUT FUNCTIONS
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${CYAN}[DEBUG]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }

# =============================================================================
# PI CONSOLE NATIVE VALIDATION FUNCTIONS
# =============================================================================

# Check if running on Pi console
check_pi_console() {
    log_info "Validating Pi console environment..."
    
    # Check if we're on a Pi
    if [ -f "/proc/device-tree/model" ]; then
        local model=$(cat /proc/device-tree/model 2>/dev/null || echo "unknown")
        if [[ "$model" == *"Raspberry Pi"* ]]; then
            log_success "Running on Raspberry Pi: $model"
            return 0
        fi
    fi
    
    # Check for Pi-specific hardware
    if [ -d "/sys/class/gpio" ] && [ -f "/proc/cpuinfo" ]; then
        if grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
            log_success "Running on Pi-compatible hardware"
            return 0
        fi
    fi
    
    log_warning "Not running on Pi console - some features may be limited"
    return 1
}

# Validate Pi mount points
validate_pi_mounts() {
    log_info "Validating Pi mount points..."
    
    local valid_mounts=0
    local total_mounts=${#PI_MOUNT_POINTS[@]}
    
    for mount_point in "${PI_MOUNT_POINTS[@]}"; do
        if [ -d "$mount_point" ] && [ -w "$mount_point" ]; then
            log_success "Mount point accessible: $mount_point"
            ((valid_mounts++))
        else
            log_warning "Mount point not accessible: $mount_point"
        fi
    done
    
    if [ $valid_mounts -eq 0 ]; then
        log_error "No valid mount points found! Cannot proceed."
        return 1
    elif [ $valid_mounts -lt $((total_mounts / 2)) ]; then
        log_warning "Limited mount points available - using fallback mechanisms"
    fi
    
    return 0
}

# Check required packages
check_pi_packages() {
    log_info "Checking required packages for Pi console..."
    
    local missing_packages=()
    
    for package in "${PI_REQUIRED_PACKAGES[@]}"; do
        if command -v "$package" >/dev/null 2>&1; then
            log_success "Package available: $package"
        else
            log_warning "Package missing: $package"
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_warning "Missing packages: ${missing_packages[*]}"
        log_info "Attempting to install missing packages..."
        
        # Try to install missing packages
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update >/dev/null 2>&1 || true
            for package in "${missing_packages[@]}"; do
                if sudo apt-get install -y "$package" >/dev/null 2>&1; then
                    log_success "Installed: $package"
                else
                    log_warning "Failed to install: $package - using fallback"
                fi
            done
        else
            log_warning "Package manager not available - using fallback mechanisms"
        fi
    fi
    
    return 0
}

# Validate storage space
validate_storage() {
    log_info "Validating storage space..."
    
    local min_space_mb=1000  # 1GB minimum
    local available_space=0
    
    # Check main project directory
    if [ -d "$PROJECT_ROOT" ]; then
        available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1024)}' 2>/dev/null || echo "0")
    else
        # Check parent directory
        local parent_dir=$(dirname "$PROJECT_ROOT")
        if [ -d "$parent_dir" ]; then
            available_space=$(df "$parent_dir" | awk 'NR==2 {print int($4/1024)}' 2>/dev/null || echo "0")
        fi
    fi
    
    if [ $available_space -gt $min_space_mb ]; then
        log_success "Storage space available: ${available_space}MB"
        return 0
    else
        log_warning "Limited storage space: ${available_space}MB (minimum: ${min_space_mb}MB)"
        
        # Try fallback directories
        for fallback_dir in "${PI_FALLBACK_DIRS[@]}"; do
            if [ -d "$fallback_dir" ] || mkdir -p "$fallback_dir" 2>/dev/null; then
                local fallback_space=$(df "$fallback_dir" | awk 'NR==2 {print int($4/1024)}' 2>/dev/null || echo "0")
                if [ $fallback_space -gt $min_space_mb ]; then
                    log_success "Using fallback directory: $fallback_dir (${fallback_space}MB available)"
                    PROJECT_ROOT="$fallback_dir/Lucid"
                    ENV_CONFIG_DIR="$PROJECT_ROOT/configs/environment"
                    return 0
                fi
            fi
        done
        
        log_error "Insufficient storage space and no fallback available!"
        return 1
    fi
}

# =============================================================================
# DIRECTORY VALIDATION AND CREATION
# =============================================================================
validate_and_create_directories() {
    log_info "Validating and creating required directories..."
    
    local directories=(
        "$PROJECT_ROOT"
        "$ENV_CONFIG_DIR"
        "$SCRIPTS_CONFIG_DIR"
        "$TEMPLATES_DIR"
        "$BACKUP_DIR"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            log_info "Creating directory: $dir"
            if mkdir -p "$dir" 2>/dev/null; then
                log_success "Created directory: $dir"
            else
                log_error "Failed to create directory: $dir"
                return 1
            fi
        else
            log_success "Directory exists: $dir"
        fi
        
        # Check write permissions
        if [ -w "$dir" ]; then
            log_success "Directory writable: $dir"
        else
            log_warning "Directory not writable: $dir - attempting to fix permissions"
            if chmod 755 "$dir" 2>/dev/null; then
                log_success "Fixed permissions for: $dir"
            else
                log_error "Cannot fix permissions for: $dir"
                return 1
            fi
        fi
    done
    
    return 0
}

# =============================================================================
# SECURE VALUE GENERATION WITH FALLBACKS
# =============================================================================
generate_secure_value() {
    local length=${1:-32}
    local value=""
    
    # Try multiple methods for generating secure values
    if command -v openssl >/dev/null 2>&1; then
        value=$(openssl rand -base64 $length 2>/dev/null | tr -d '\n' || echo "")
    fi
    
    if [ -z "$value" ] && command -v python3 >/dev/null 2>&1; then
        value=$(python3 -c "import secrets; print(secrets.token_urlsafe($length))" 2>/dev/null || echo "")
    fi
    
    if [ -z "$value" ] && [ -r "/dev/urandom" ]; then
        value=$(head -c $length /dev/urandom 2>/dev/null | base64 | tr -d '\n' | cut -c1-$length || echo "")
    fi
    
    if [ -z "$value" ]; then
        # Ultimate fallback - use date and process ID
        value=$(date +%s%N | sha256sum | cut -c1-$length || echo "fallback$(date +%s)")
        log_warning "Using fallback value generation method"
    fi
    
    echo "$value"
}

generate_hex_key() {
    local length=${1:-32}
    local value=""
    
    if command -v openssl >/dev/null 2>&1; then
        value=$(openssl rand -hex $length 2>/dev/null | tr -d '\n' || echo "")
    fi
    
    if [ -z "$value" ] && [ -r "/dev/urandom" ]; then
        value=$(head -c $length /dev/urandom 2>/dev/null | hexdump -v -e '/1 "%02x"' | cut -c1-$((length*2)) || echo "")
    fi
    
    if [ -z "$value" ]; then
        value=$(generate_secure_value $length | hexdump -v -e '/1 "%02x"' | cut -c1-$((length*2)) || echo "fallback$(date +%s)")
        log_warning "Using fallback hex key generation"
    fi
    
    echo "$value"
}

# =============================================================================
# ENVIRONMENT FILE GENERATION
# =============================================================================
generate_master_env() {
    log_info "Generating master environment configuration..."
    
    # Generate secure values
    local mongodb_password=$(generate_secure_value 32)
    local redis_password=$(generate_secure_value 32)
    local jwt_secret=$(generate_secure_value 64)
    local encryption_key=$(generate_hex_key 32)
    local session_secret=$(generate_secure_value 32)
    local hmac_key=$(generate_secure_value 32)
    local signing_key=$(generate_hex_key 32)
    local tor_password=$(generate_secure_value 32)
    local api_secret=$(generate_secure_value 32)
    
    # Generate .onion addresses for Tor
    local api_gateway_onion=""
    local auth_service_onion=""
    local blockchain_onion=""
    
    if command -v openssl >/dev/null 2>&1; then
        # Generate v3 .onion addresses
        for i in {1..3}; do
            local temp_dir=$(mktemp -d 2>/dev/null || echo "/tmp")
            if openssl genpkey -algorithm ed25519 -out "$temp_dir/key.pem" 2>/dev/null; then
                local pubkey=$(openssl pkey -in "$temp_dir/key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base32 | tr -d '=' | tr '[:upper:]' '[:lower:]' || echo "")
                if [ -n "$pubkey" ]; then
                    case $i in
                        1) api_gateway_onion="${pubkey:0:56}.onion" ;;
                        2) auth_service_onion="${pubkey:0:56}.onion" ;;
                        3) blockchain_onion="${pubkey:0:56}.onion" ;;
                    esac
                fi
            fi
            rm -rf "$temp_dir" 2>/dev/null || true
        done
    fi
    
    # Fallback .onion addresses
    if [ -z "$api_gateway_onion" ]; then
        api_gateway_onion="lucid-api-$(generate_secure_value 16 | cut -c1-16).onion"
    fi
    if [ -z "$auth_service_onion" ]; then
        auth_service_onion="lucid-auth-$(generate_secure_value 16 | cut -c1-16).onion"
    fi
    if [ -z "$blockchain_onion" ]; then
        blockchain_onion="lucid-blockchain-$(generate_secure_value 16 | cut -c1-16).onion"
    fi
    
    # Create master environment file
    cat > "$ENV_CONFIG_DIR/.env.master" << EOF
# =============================================================================
# LUCID MASTER ENVIRONMENT CONFIGURATION
# =============================================================================
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA
# Platform: $BUILD_PLATFORM
# Target: Raspberry Pi Console
# =============================================================================

# Build Information
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
BUILD_PLATFORM=$BUILD_PLATFORM
BUILD_REGISTRY=pickme/lucid

# Project Paths
PROJECT_ROOT=$PROJECT_ROOT
ENV_CONFIG_DIR=$ENV_CONFIG_DIR
SCRIPTS_CONFIG_DIR=$SCRIPTS_CONFIG_DIR
SCRIPTS_DIR=$SCRIPTS_DIR
TEMPLATES_DIR=$TEMPLATES_DIR
BACKUP_DIR=$BACKUP_DIR

# Environment
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# Database Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_production
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=$mongodb_password
MONGODB_URI=mongodb://lucid:$mongodb_password@lucid-mongodb:27017/lucid_production?authSource=admin
MONGODB_AUTH_SOURCE=admin
MONGODB_POOL_SIZE=50

REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=$redis_password
REDIS_URI=redis://:$redis_password@lucid-redis:6379
REDIS_DATABASE=0
REDIS_POOL_SIZE=100

# Security Configuration
JWT_SECRET=$jwt_secret
JWT_SECRET_KEY=$jwt_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ENCRYPTION_KEY=$encryption_key
ENCRYPTION_ALGORITHM=AES-256-GCM
ENCRYPTION_IV_LENGTH=12

SESSION_SECRET=$session_secret
SESSION_TIMEOUT=3600
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

HMAC_KEY=$hmac_key
SIGNING_KEY=$signing_key

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=$tor_password
TOR_DATA_DIR=/var/lib/tor

# Tor Hidden Services
API_GATEWAY_ONION=$api_gateway_onion
AUTH_SERVICE_ONION=$auth_service_onion
BLOCKCHAIN_ONION=$blockchain_onion

# API Configuration
API_SECRET=$api_secret
API_RATE_LIMIT=1000
API_TIMEOUT=30

# Network Configuration
LUCID_NETWORK=lucid-pi-network
LUCID_SUBNET=172.20.0.0/16
LUCID_GATEWAY=172.20.0.1

# Pi-specific Configuration
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production
PI_SSH_PORT=22
PI_ARCHITECTURE=aarch64
PI_OPTIMIZATION=true

# Hardware Configuration
HARDWARE_ACCELERATION=true
V4L2_ENABLED=true
GPU_MEMORY=128
CPU_CORES=4
MEMORY_LIMIT=2G

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/lucid.log
LOG_MAX_SIZE=100MB
LOG_MAX_FILES=10
LOG_COMPRESS=true

# Monitoring Configuration
MONITORING_ENABLED=true
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics
GRAFANA_ENABLED=true
GRAFANA_PORT=3000

# Health Check Configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true
BACKUP_STORAGE_PATH=/var/backups/lucid

# Alerting Configuration
ALERTING_ENABLED=true
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=80
ALERT_DISK_THRESHOLD=90
ALERT_NETWORK_THRESHOLD=1000
ALERT_ERROR_RATE_THRESHOLD=5

EOF

    log_success "Master environment file generated: $ENV_CONFIG_DIR/.env.master"
    
    # Save secrets to secure file
    cat > "$ENV_CONFIG_DIR/.env.secrets" << EOF
# =============================================================================
# LUCID GENERATED SECRETS REFERENCE
# =============================================================================
# Generated: $(date)
# WARNING: Keep this file secure! Never commit to version control!
# =============================================================================

MONGODB_PASSWORD=$mongodb_password
REDIS_PASSWORD=$redis_password
JWT_SECRET=$jwt_secret
ENCRYPTION_KEY=$encryption_key
SESSION_SECRET=$session_secret
HMAC_KEY=$hmac_key
SIGNING_KEY=$signing_key
TOR_PASSWORD=$tor_password
API_SECRET=$api_secret

# Tor Hidden Service Addresses
API_GATEWAY_ONION=$api_gateway_onion
AUTH_SERVICE_ONION=$auth_service_onion
BLOCKCHAIN_ONION=$blockchain_onion

EOF

    chmod 600 "$ENV_CONFIG_DIR/.env.secrets"
    log_success "Secrets saved to: $ENV_CONFIG_DIR/.env.secrets (permissions: 600)"
}

# =============================================================================
# SERVICE-SPECIFIC ENVIRONMENT GENERATION
# =============================================================================
generate_service_env() {
    local service_name="$1"
    local service_port="$2"
    local service_host="${3:-0.0.0.0}"
    
    log_info "Generating environment for service: $service_name"
    
    # Load master environment
    if [ -f "$ENV_CONFIG_DIR/.env.master" ]; then
        source "$ENV_CONFIG_DIR/.env.master"
    fi
    
    # Generate service-specific environment
    cat > "$ENV_CONFIG_DIR/.env.$service_name" << EOF
# =============================================================================
# LUCID $service_name ENVIRONMENT CONFIGURATION
# =============================================================================
# Generated: $BUILD_TIMESTAMP
# Service: $service_name
# Port: $service_port
# Host: $service_host
# =============================================================================

# Build Information
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
BUILD_PLATFORM=$BUILD_PLATFORM

# Service Configuration
SERVICE_NAME=$service_name
SERVICE_PORT=$service_port
SERVICE_HOST=$service_host

# Environment
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# Database Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_production
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid_production?authSource=admin
MONGODB_AUTH_SOURCE=admin
MONGODB_POOL_SIZE=50

REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379
REDIS_DATABASE=0
REDIS_POOL_SIZE=100

# Security Configuration
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ENCRYPTION_KEY=$ENCRYPTION_KEY
ENCRYPTION_ALGORITHM=AES-256-GCM
ENCRYPTION_IV_LENGTH=12

SESSION_SECRET=$SESSION_SECRET
SESSION_TIMEOUT=3600
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

HMAC_KEY=$HMAC_KEY
SIGNING_KEY=$SIGNING_KEY

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=$TOR_PASSWORD
TOR_DATA_DIR=/var/lib/tor

# Tor Hidden Services
API_GATEWAY_ONION=$API_GATEWAY_ONION
AUTH_SERVICE_ONION=$AUTH_SERVICE_ONION
BLOCKCHAIN_ONION=$BLOCKCHAIN_ONION

# Network Configuration
LUCID_NETWORK=lucid-pi-network
LUCID_SUBNET=172.20.0.0/16
LUCID_GATEWAY=172.20.0.1

# Pi-specific Configuration
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production
PI_SSH_PORT=22
PI_ARCHITECTURE=aarch64
PI_OPTIMIZATION=true

# Hardware Configuration
HARDWARE_ACCELERATION=true
V4L2_ENABLED=true
GPU_MEMORY=128
CPU_CORES=4
MEMORY_LIMIT=2G

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/$service_name.log
LOG_MAX_SIZE=100MB
LOG_MAX_FILES=10
LOG_COMPRESS=true

# Health Check Configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Monitoring Configuration
MONITORING_ENABLED=true
METRICS_PORT=$((9090 + service_port % 100))
METRICS_PATH=/metrics

EOF

    log_success "Service environment generated: $ENV_CONFIG_DIR/.env.$service_name"
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================
validate_environment_files() {
    log_info "Validating generated environment files..."
    
    local env_files=(
        "$ENV_CONFIG_DIR/.env.master"
        "$ENV_CONFIG_DIR/.env.secrets"
    )
    
    for env_file in "${env_files[@]}"; do
        if [ -f "$env_file" ]; then
            log_success "Environment file exists: $env_file"
            
            # Check for required variables
            local required_vars=(
                "MONGODB_PASSWORD"
                "REDIS_PASSWORD"
                "JWT_SECRET"
                "ENCRYPTION_KEY"
                "SESSION_SECRET"
            )
            
            for var in "${required_vars[@]}"; do
                if grep -q "^${var}=" "$env_file"; then
                    log_success "Required variable found: $var"
                else
                    log_error "Required variable missing: $var"
                    return 1
                fi
            done
        else
            log_error "Environment file missing: $env_file"
            return 1
        fi
    done
    
    log_success "Environment file validation completed"
    return 0
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================
backup_existing_configs() {
    log_info "Backing up existing configurations..."
    
    if [ -d "$ENV_CONFIG_DIR" ]; then
        local backup_file="$BACKUP_DIR/env-backup-$BUILD_TIMESTAMP.tar.gz"
        
        if tar -czf "$backup_file" -C "$ENV_CONFIG_DIR" . 2>/dev/null; then
            log_success "Configuration backup created: $backup_file"
        else
            log_warning "Failed to create configuration backup"
        fi
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    log_info "==================================================================="
    log_info "LUCID ENVIRONMENT CONFIGURATION GENERATOR - PI CONSOLE NATIVE"
    log_info "==================================================================="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Environment Config: $ENV_CONFIG_DIR"
    log_info "Build Timestamp: $BUILD_TIMESTAMP"
    log_info "Git SHA: $GIT_SHA"
    log_info "Platform: $BUILD_PLATFORM"
    echo ""
    
    # Pi console native validation
    log_info "Step 1: Pi Console Native Validation"
    if ! check_pi_console; then
        log_warning "Not running on Pi console - some features may be limited"
    fi
    
    if ! validate_pi_mounts; then
        log_error "Pi mount validation failed!"
        exit 1
    fi
    
    if ! check_pi_packages; then
        log_warning "Package validation completed with warnings"
    fi
    
    if ! validate_storage; then
        log_error "Storage validation failed!"
        exit 1
    fi
    
    log_success "Pi console native validation completed"
    echo ""
    
    # Directory validation and creation
    log_info "Step 2: Directory Validation and Creation"
    if ! validate_and_create_directories; then
        log_error "Directory validation failed!"
        exit 1
    fi
    
    log_success "Directory validation completed"
    echo ""
    
    # Backup existing configurations
    log_info "Step 3: Backup Existing Configurations"
    backup_existing_configs
    
    log_success "Backup completed"
    echo ""
    
    # Generate master environment
    log_info "Step 4: Generate Master Environment"
    generate_master_env
    
    log_success "Master environment generation completed"
    echo ""
    
    # Generate service-specific environments
    log_info "Step 5: Generate Service-Specific Environments"
    
    # Define services with their ports
    local services=(
        "api-gateway:8080"
        "auth-service:8089"
        "blockchain-core:8084"
        "session-management:8085"
        "rdp-services:8086"
        "node-management:8087"
        "admin-interface:8083"
        "orchestrator:8090"
        "chunker:8092"
        "merkle-builder:8094"
    )
    
    for service_config in "${services[@]}"; do
        local service_name=$(echo "$service_config" | cut -d: -f1)
        local service_port=$(echo "$service_config" | cut -d: -f2)
        
        generate_service_env "$service_name" "$service_port"
    done
    
    log_success "Service environment generation completed"
    echo ""
    
    # Validate generated files
    log_info "Step 6: Validate Generated Files"
    if ! validate_environment_files; then
        log_error "Environment file validation failed!"
        exit 1
    fi
    
    log_success "Environment file validation completed"
    echo ""
    
    # Final summary
    log_info "==================================================================="
    log_info "ENVIRONMENT GENERATION COMPLETE!"
    log_info "==================================================================="
    echo ""
    log_info "Generated files:"
    log_info "  • .env.master        : $ENV_CONFIG_DIR/.env.master"
    log_info "  • .env.secrets       : $ENV_CONFIG_DIR/.env.secrets"
    for service_config in "${services[@]}"; do
        local service_name=$(echo "$service_config" | cut -d: -f1)
        log_info "  • .env.$service_name    : $ENV_CONFIG_DIR/.env.$service_name"
    done
    echo ""
    log_info "Build details:"
    log_info "  • Build timestamp   : $BUILD_TIMESTAMP"
    log_info "  • Git SHA           : $GIT_SHA"
    log_info "  • Platform          : $BUILD_PLATFORM"
    echo ""
    log_warning "SECURITY NOTICE:"
    log_warning "  • Keep .env.secrets file secure (chmod 600)"
    log_warning "  • Never commit .env.secrets to version control"
    log_warning "  • Backup secrets file to secure location"
    log_warning "  • Rotate keys regularly in production"
    echo ""
    log_success "Environment generation completed successfully!"
}

# Run main function
main "$@"