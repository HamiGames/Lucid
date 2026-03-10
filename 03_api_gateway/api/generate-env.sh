#!/bin/bash
# =============================================================================
# Lucid API Gateway Environment Generator - Pi Console Native
# =============================================================================
# This script generates environment configuration files for API Gateway service
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
API_GATEWAY_DIR="$PROJECT_ROOT/03-api-gateway/api"

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

log_info "API Gateway Environment Generator - Pi Console Native"
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
    log_info "API GATEWAY ENVIRONMENT GENERATOR - PI CONSOLE NATIVE"
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
    
    # Generate API Gateway specific environment
    log_info "Step 3: Generate API Gateway Specific Environment"
    
    # Load master environment
    if [ -f "$ENV_CONFIG_DIR/.env.master" ]; then
        source "$ENV_CONFIG_DIR/.env.master"
    fi
    
    # Generate API Gateway environment
    cat > "$ENV_CONFIG_DIR/.env.api-gateway" << EOF
# =============================================================================
# LUCID API GATEWAY ENVIRONMENT CONFIGURATION
# =============================================================================
# Generated: $(date '+%Y%m%d-%H%M%S')
# Service: api-gateway
# Port: 8080
# =============================================================================

# Build Information
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_PLATFORM=linux/arm64
BUILD_REGISTRY=pickme/lucid
BUILD_TAG=latest

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Service Configuration
SERVICE_NAME=api-gateway
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8080
API_GATEWAY_WORKERS=4
API_GATEWAY_TIMEOUT=30
UVICORN_WORKERS=4

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

# API Configuration
API_SECRET=$API_SECRET
API_RATE_LIMIT=1000
API_TIMEOUT=30

# CORS Configuration
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
CORS_HEADERS=Content-Type,Authorization,X-Requested-With
CORS_CREDENTIALS=true

# Upstream Services
SERVICE_MESH_ENABLED=true
SERVICE_MESH_CONTROLLER_HOST=lucid-service-mesh-controller
SERVICE_MESH_CONTROLLER_PORT=8086

AUTH_SERVICE_HOST=lucid-auth-service
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_UPSTREAM=http://lucid-auth-service:8089
AUTH_SERVICE_TIMEOUT=30

BLOCKCHAIN_API_HOST=lucid-blockchain-engine
BLOCKCHAIN_API_PORT=8084
BLOCKCHAIN_API_UPSTREAM=http://lucid-blockchain-engine:8084
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_SESSION_ANCHORING_PORT=8085
BLOCKCHAIN_BLOCK_MANAGER_PORT=8086
BLOCKCHAIN_DATA_CHAIN_PORT=8087

SESSION_API_HOST=lucid-session-api
SESSION_API_PORT=8087
SESSION_PIPELINE_PORT=8081
SESSION_RECORDER_PORT=8082
SESSION_CHUNK_PROCESSOR_PORT=8083

RDP_SERVER_MANAGER_HOST=lucid-rdp-server-manager
RDP_SERVER_MANAGER_PORT=8081
RDP_SESSION_CONTROLLER_PORT=8082
RDP_RESOURCE_MONITOR_PORT=8090

NODE_MANAGEMENT_HOST=lucid-node-management
NODE_MANAGEMENT_PORT=8095

ADMIN_INTERFACE_HOST=lucid-admin-interface
ADMIN_INTERFACE_PORT=8083

# Load Balancing
LOAD_BALANCE_METHOD=round_robin
HEALTH_CHECK_INTERVAL=30
UPSTREAM_TIMEOUT=30
UPSTREAM_MAX_FAILS=3
UPSTREAM_FAIL_TIMEOUT=30

# SSL/TLS Configuration
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/lucid-api-gateway.crt
SSL_KEY_PATH=/etc/ssl/private/lucid-api-gateway.key
SSL_CA_PATH=/etc/ssl/certs/ca.crt

# Security Headers
SECURITY_HEADERS_ENABLED=true
SECURITY_HEADERS_HSTS=true
SECURITY_HEADERS_CSP=true
SECURITY_HEADERS_XFRAME=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/api-gateway.log
LOG_MAX_SIZE=100MB
LOG_MAX_FILES=10
LOG_COMPRESS=true

ACCESS_LOG=/var/log/nginx/access.log
ERROR_LOG=/var/log/nginx/error.log

# Health Check Configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PATH=/api/v1/meta/health
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40s

# Performance Configuration
CONNECTION_POOL_SIZE=100
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3

# Cache Configuration
CACHE_ENABLED=true
CACHE_SIZE=1GB
CACHE_TTL=3600
CACHE_BACKEND=redis

# Nginx Configuration
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024
NGINX_CLIENT_MAX_BODY_SIZE=100M
NGINX_PROXY_BUFFERING=on
NGINX_PROXY_BUFFER_SIZE=4k
NGINX_PROXY_BUFFERS=8 4k

# Monitoring Configuration
MONITORING_ENABLED=true
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics
PROMETHEUS_INTERVAL=15

METRICS_PORT=9216
METRICS_PATH=/metrics

# Network Configuration
NETWORK_INTERFACE=eth0
NETWORK_MTU=1500
NETWORK_BUFFER_SIZE=65536

LUCID_NETWORK=lucid-pi-network
LUCID_SUBNET=172.20.0.0/16
LUCID_GATEWAY=172.20.0.1

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

# Data Directories
DATA_DIR=/data/api-gateway
LOG_DIR=/var/log/lucid
TEMP_DIR=/tmp/api-gateway
CACHE_DIR=/var/cache/lucid

# Pi Deployment Configuration
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

# Container Configuration
CONTAINER_RUNTIME=docker
COMPOSE_PROJECT_NAME=lucid-pi

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

# Debug & Development
DEBUG=false
DEVELOPMENT_MODE=false
HOT_RELOAD=false

# API Version
API_VERSION=v1
API_PREFIX=/api/v1

EOF

    log_success "API Gateway environment generated: $ENV_CONFIG_DIR/.env.api-gateway"
    echo ""
    
    # Final summary
    log_info "==================================================================="
    log_info "API GATEWAY ENVIRONMENT GENERATION COMPLETE!"
    log_info "==================================================================="
    echo ""
    log_info "Generated files:"
    log_info "  • .env.api-gateway    : $ENV_CONFIG_DIR/.env.api-gateway"
    echo ""
    log_success "API Gateway environment generation completed successfully!"
}

# Run main function
main "$@"