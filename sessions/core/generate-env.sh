#!/bin/bash
# =============================================================================
# Lucid Session Core Environment Generator - Pi Console Native
# =============================================================================
# This script generates environment configuration files for Session Core services
# Uses the master environment generator with Pi console native optimizations
# =============================================================================

set -euo pipefail

# =============================================================================
# GLOBAL PATH CONFIGURATION
# =============================================================================
# Set global path variables for consistent file management
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_CONFIG_DIR="$PROJECT_ROOT/configs/environment"
SCRIPTS_CONFIG_DIR="$PROJECT_ROOT/scripts/config"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
SESSION_CORE_DIR="$PROJECT_ROOT/sessions/core"

# Current script directory (for relative operations)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

log_info "Session Core Environment Generator - Pi Console Native"
log_info "Project Root: $PROJECT_ROOT"
log_info "Environment Config Dir: $ENV_CONFIG_DIR"
log_info "Scripts Config Dir: $SCRIPTS_CONFIG_DIR"

# =============================================================================
# PI CONSOLE NATIVE VALIDATION
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
    
    local pi_mount_points=(
        "/mnt/myssd"
        "/mnt/usb"
        "/mnt/sdcard"
        "/opt"
        "/var"
        "/tmp"
    )
    
    local valid_mounts=0
    local total_mounts=${#pi_mount_points[@]}
    
    for mount_point in "${pi_mount_points[@]}"; do
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
    
    local required_packages=(
        "openssl"
        "coreutils"
        "util-linux"
        "procps"
        "grep"
        "sed"
        "awk"
        "bash"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
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

# =============================================================================
# DIRECTORY VALIDATION AND CREATION
# =============================================================================
log_info "Validating and creating required directories..."

# Create environment config directory if it doesn't exist
if [ ! -d "$ENV_CONFIG_DIR" ]; then
    log_info "Creating environment config directory: $ENV_CONFIG_DIR"
    mkdir -p "$ENV_CONFIG_DIR"
fi

# Create scripts config directory if it doesn't exist
if [ ! -d "$SCRIPTS_CONFIG_DIR" ]; then
    log_info "Creating scripts config directory: $SCRIPTS_CONFIG_DIR"
    mkdir -p "$SCRIPTS_CONFIG_DIR"
fi

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    log_info "==================================================================="
    log_info "SESSION CORE ENVIRONMENT GENERATOR - PI CONSOLE NATIVE"
    log_info "==================================================================="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Environment Config: $ENV_CONFIG_DIR"
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
    
    log_success "Pi console native validation completed"
    echo ""
    
    # Use master environment generator
    log_info "Step 2: Using Master Environment Generator"
    if [ -f "$SCRIPTS_CONFIG_DIR/generate-env.sh" ]; then
        log_info "Running master environment generator..."
        bash "$SCRIPTS_CONFIG_DIR/generate-env.sh"
        log_success "Master environment generation completed"
    else
        log_error "Master environment generator not found: $SCRIPTS_CONFIG_DIR/generate-env.sh"
        exit 1
    fi
    
    echo ""
    
    # Generate session-specific environments
    log_info "Step 3: Generate Session-Specific Environments"
    
    # Define session services with their ports
    local session_services=(
        "orchestrator:8090"
        "chunker:8092"
        "merkle-builder:8094"
    )
    
    for service_config in "${session_services[@]}"; do
        local service_name=$(echo "$service_config" | cut -d: -f1)
        local service_port=$(echo "$service_config" | cut -d: -f2)
        
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
# Generated: $(date '+%Y%m%d-%H%M%S')
# Service: $service_name
# Port: $service_port
# =============================================================================

# Build Information
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_PLATFORM=linux/arm64

# Service Configuration
SERVICE_NAME=$service_name
SERVICE_PORT=$service_port
SERVICE_HOST=0.0.0.0

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
    done
    
    log_success "Session-specific environment generation completed"
    echo ""
    
    # Final summary
    log_info "==================================================================="
    log_info "SESSION CORE ENVIRONMENT GENERATION COMPLETE!"
    log_info "==================================================================="
    echo ""
    log_info "Generated files:"
    for service_config in "${session_services[@]}"; do
        local service_name=$(echo "$service_config" | cut -d: -f1)
        log_info "  • .env.$service_name    : $ENV_CONFIG_DIR/.env.$service_name"
    done
    echo ""
    log_success "Session Core environment generation completed successfully!"
}

# Run main function
main "$@"