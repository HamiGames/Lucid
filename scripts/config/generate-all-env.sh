#!/bin/bash
# Generate all environment configuration files
# Implements Step 2 from docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIGS_DIR="$PROJECT_ROOT/configs"
ENV_DIR="$CONFIGS_DIR/environment"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate secure random values
generate_secure_value() {
    local length=$1
    openssl rand -base64 $length | tr -d '\n'
}

# Function to create directory structure
create_directory_structure() {
    log_info "Creating directory structure..."
    
    mkdir -p "$CONFIGS_DIR"
    mkdir -p "$ENV_DIR"
    mkdir -p "$CONFIGS_DIR/docker"
    
    log_success "Directory structure created"
}

# Function to generate secure values
generate_secure_values() {
    log_info "Generating secure configuration values..."
    
    # Generate secure values using openssl rand -base64
    MONGODB_PASSWORD=$(generate_secure_value 32)
    REDIS_PASSWORD=$(generate_secure_value 32)
    JWT_SECRET_KEY=$(generate_secure_value 64)
    ENCRYPTION_KEY=$(generate_secure_value 32)
    TOR_PASSWORD=$(generate_secure_value 32)
    SESSION_SECRET=$(generate_secure_value 32)
    API_SECRET=$(generate_secure_value 32)
    
    # Network configuration
    PI_HOST="192.168.0.75"
    PI_USER="pickme"
    PI_DEPLOY_DIR="/opt/lucid/production"
    
    # Build configuration
    BUILD_PLATFORM="linux/arm64"
    BUILD_REGISTRY="pickme/lucid"
    BUILD_TAG="latest"
    
    # Database configuration
    MONGODB_URI="mongodb://lucid:${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin"
    REDIS_URI="redis://redis:6379/0"
    ELASTICSEARCH_URI="http://elasticsearch:9200"
    
    log_success "Secure values generated"
}

# Function to generate .env.pi-build
generate_pi_build_env() {
    log_info "Generating .env.pi-build..."
    
    cat > "$ENV_DIR/.env.pi-build" << EOF
# Raspberry Pi Build Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Target: Raspberry Pi 5 (192.168.0.75)

# Build Configuration
BUILD_PLATFORM=$BUILD_PLATFORM
BUILD_REGISTRY=$BUILD_REGISTRY
BUILD_TAG=$BUILD_TAG
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Pi Deployment Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR
PI_SSH_PORT=22

# Network Configuration
LUCID_NETWORK=lucid-pi-network
LUCID_SUBNET=172.20.0.0/16
LUCID_GATEWAY=172.20.0.1

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_CLI_EXPERIMENTAL=enabled
COMPOSE_PROJECT_NAME=lucid-pi

# Build Arguments
BUILDKIT_INLINE_CACHE=1
BUILDKIT_PROGRESS=plain
EOF

    log_success ".env.pi-build generated"
}

# Function to generate .env.foundation
generate_foundation_env() {
    log_info "Generating .env.foundation..."
    
    cat > "$ENV_DIR/.env.foundation" << EOF
# Phase 1 Foundation Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: MongoDB, Redis, Elasticsearch, Auth Service

# Database Configuration
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
MONGODB_DATABASE=lucid_production
MONGODB_PORT=27017

REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI
REDIS_PORT=6379
REDIS_MAXMEMORY=1gb

ELASTICSEARCH_URI=$ELASTICSEARCH_URI
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_HEAP_SIZE=1g

# Authentication Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Security Configuration
TOR_PASSWORD=$TOR_PASSWORD
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Service Configuration
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_HOST=auth-service
AUTH_SERVICE_TIMEOUT=30

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/foundation.log
EOF

    log_success ".env.foundation generated"
}

# Function to generate .env.core
generate_core_env() {
    log_info "Generating .env.core..."
    
    cat > "$ENV_DIR/.env.core" << EOF
# Phase 2 Core Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: API Gateway, Service Mesh, Blockchain Core

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI
ELASTICSEARCH_URI=$ELASTICSEARCH_URI

# Authentication Configuration (inherited from foundation)
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# API Gateway Configuration
API_GATEWAY_PORT=8080
API_GATEWAY_HOST=api-gateway
API_GATEWAY_TIMEOUT=30
API_GATEWAY_RATE_LIMIT=1000
API_GATEWAY_CORS_ORIGINS=*

# Service Mesh Configuration
SERVICE_MESH_CONTROLLER_PORT=8086
SERVICE_MESH_CONSUL_PORT=8500
SERVICE_MESH_ENVOY_PORT=8088
SERVICE_MESH_MTLS_ENABLED=true

# Blockchain Core Configuration
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_SESSION_ANCHORING_PORT=8085
BLOCKCHAIN_BLOCK_MANAGER_PORT=8086
BLOCKCHAIN_DATA_CHAIN_PORT=8087

# Consensus Configuration
CONSENSUS_ALGORITHM=PoOT
BLOCK_INTERVAL=10
BLOCK_SIZE_LIMIT=1MB
TRANSACTION_LIMIT=1000

# Network Configuration
NETWORK_PROTOCOL_VERSION=1.0.0
NETWORK_PEER_DISCOVERY=true
NETWORK_PEER_LIMIT=100

# Performance Configuration
CACHE_SIZE=1GB
CACHE_TTL=3600
CONNECTION_POOL_SIZE=100
EOF

    log_success ".env.core generated"
}

# Function to generate .env.application
generate_application_env() {
    log_info "Generating .env.application..."
    
    cat > "$ENV_DIR/.env.application" << EOF
# Phase 3 Application Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Session Management, RDP Services, Node Management

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI

# Authentication Configuration (inherited from foundation)
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Session Management Configuration
SESSION_PIPELINE_PORT=8081
SESSION_RECORDER_PORT=8082
SESSION_CHUNK_PROCESSOR_PORT=8083
SESSION_STORAGE_PORT=8084
SESSION_API_PORT=8087

# Session Configuration
SESSION_CHUNK_SIZE=8388608
SESSION_COMPRESSION_LEVEL=1
SESSION_ENCRYPTION_ENABLED=true
SESSION_RETENTION_DAYS=30
SESSION_MERKLE_TREE_ENABLED=true

# RDP Services Configuration
RDP_SERVER_MANAGER_PORT=8081
RDP_XRDP_INTEGRATION_PORT=3389
RDP_SESSION_CONTROLLER_PORT=8082
RDP_RESOURCE_MONITOR_PORT=8090

# RDP Configuration
RDP_MAX_SESSIONS=10
RDP_SESSION_TIMEOUT=3600
RDP_RESOURCE_LIMIT_CPU=80
RDP_RESOURCE_LIMIT_MEMORY=2GB
RDP_RESOURCE_LIMIT_DISK=10GB

# Node Management Configuration
NODE_MANAGEMENT_PORT=8095
NODE_POOL_MAX_SIZE=100
NODE_PAYOUT_THRESHOLD=10
NODE_CONSENSUS_WEIGHT=1.0

# Performance Configuration
CHUNK_PROCESSING_WORKERS=4
ENCRYPTION_WORKERS=2
COMPRESSION_WORKERS=2
STORAGE_WORKERS=4
EOF

    log_success ".env.application generated"
}

# Function to generate .env.support
generate_support_env() {
    log_info "Generating .env.support..."
    
    cat > "$ENV_DIR/.env.support" << EOF
# Phase 4 Support Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Admin Interface, TRON Payment System (Isolated)

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI

# Authentication Configuration (inherited from foundation)
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Admin Interface Configuration
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_HOST=admin-interface
ADMIN_INTERFACE_TIMEOUT=30
ADMIN_INTERFACE_CORS_ENABLED=true

# Admin Configuration
ADMIN_DASHBOARD_ENABLED=true
ADMIN_MONITORING_ENABLED=true
ADMIN_SESSION_ADMIN_ENABLED=true
ADMIN_BLOCKCHAIN_ADMIN_ENABLED=true
ADMIN_PAYOUT_TRIGGERS_ENABLED=true

# TRON Payment System Configuration (ISOLATED NETWORK)
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
TRON_CLIENT_PORT=8091
TRON_PAYOUT_ROUTER_PORT=8092
TRON_WALLET_MANAGER_PORT=8093
TRON_USDT_MANAGER_PORT=8094
TRON_TRX_STAKING_PORT=8096
TRON_PAYMENT_GATEWAY_PORT=8097

# TRON Configuration
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRON_MINIMUM_PAYOUT=10
TRON_GAS_LIMIT=100000
TRON_GAS_PRICE=1000

# Network Isolation
TRON_ISOLATED_NETWORK=lucid-tron-isolated
TRON_BRIDGE_ENABLED=true
TRON_BRIDGE_PORT=8098

# Security Configuration
TRON_PRIVATE_KEY_ENCRYPTED=true
TRON_WALLET_PASSWORD_ENCRYPTED=true
TRON_TRANSACTION_SIGNING_ENABLED=true
EOF

    log_success ".env.support generated"
}

# Function to generate .env.gui
generate_gui_env() {
    log_info "Generating .env.gui..."
    
    cat > "$ENV_DIR/.env.gui" << EOF
# GUI Integration Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Electron GUI, API Bridge, Docker Manager, Tor Manager, Hardware Wallet

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI

# Authentication Configuration (inherited from foundation)
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# GUI API Bridge Configuration
GUI_API_BRIDGE_PORT=8099
GUI_API_BRIDGE_HOST=gui-api-bridge
GUI_API_BRIDGE_TIMEOUT=30

# GUI Docker Manager Configuration
GUI_DOCKER_MANAGER_PORT=8100
GUI_DOCKER_MANAGER_HOST=gui-docker-manager
GUI_DOCKER_MANAGER_TIMEOUT=30

# GUI Tor Manager Configuration
GUI_TOR_MANAGER_PORT=8101
GUI_TOR_MANAGER_HOST=gui-tor-manager
GUI_TOR_MANAGER_TIMEOUT=30

# GUI Hardware Wallet Configuration
GUI_HARDWARE_WALLET_PORT=8102
GUI_HARDWARE_WALLET_HOST=gui-hardware-wallet
GUI_HARDWARE_WALLET_TIMEOUT=30

# Electron GUI Configuration
ELECTRON_GUI_PORT=3000
ELECTRON_GUI_HOST=localhost
ELECTRON_GUI_DEVELOPMENT=false
ELECTRON_GUI_PRODUCTION=true

# GUI Variants
GUI_VARIANTS=user,developer,node,admin
GUI_DEFAULT_VARIANT=user

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
HARDWARE_WALLET_SUPPORTED=ledger,trezor,keepkey
HARDWARE_WALLET_TIMEOUT=30

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_DATA_DIR=/var/lib/tor
TOR_LOG_DIR=/var/log/tor

# GUI Security Configuration
GUI_HTTPS_ENABLED=true
GUI_CERT_PATH=/etc/ssl/certs/lucid-gui.crt
GUI_KEY_PATH=/etc/ssl/private/lucid-gui.key
GUI_CORS_ENABLED=true
GUI_CORS_ORIGINS=*
EOF

    log_success ".env.gui generated"
}

# Function to validate generated files
validate_generated_files() {
    log_info "Validating generated environment files..."
    
    local env_files=(
        ".env.pi-build"
        ".env.foundation"
        ".env.core"
        ".env.application"
        ".env.support"
        ".env.gui"
    )
    
    for env_file in "${env_files[@]}"; do
        local file_path="$ENV_DIR/$env_file"
        
        if [[ -f "$file_path" ]]; then
            # Check for placeholder values
            if grep -q '\${' "$file_path"; then
                log_error "Placeholder values found in $env_file"
                exit 1
            fi
            
            # Check file size
            local file_size=$(wc -c < "$file_path")
            if [[ $file_size -lt 100 ]]; then
                log_error "File $env_file is too small ($file_size bytes)"
                exit 1
            fi
            
            log_success "$env_file validated"
        else
            log_error "File not found: $env_file"
            exit 1
        fi
    done
    
    log_success "All environment files validated"
}

# Function to display summary
display_summary() {
    log_info "Environment Configuration Generation Summary:"
    echo ""
    echo "Generated Files:"
    echo "  • $ENV_DIR/.env.pi-build"
    echo "  • $ENV_DIR/.env.foundation"
    echo "  • $ENV_DIR/.env.core"
    echo "  • $ENV_DIR/.env.application"
    echo "  • $ENV_DIR/.env.support"
    echo "  • $ENV_DIR/.env.gui"
    echo ""
    echo "Configuration Details:"
    echo "  • MongoDB Password: Generated (32 bytes)"
    echo "  • Redis Password: Generated (32 bytes)"
    echo "  • JWT Secret Key: Generated (64 bytes)"
    echo "  • Encryption Key: Generated (32 bytes)"
    echo "  • Tor Password: Generated (32 bytes)"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Pi User: $PI_USER"
    echo "  • Build Platform: $BUILD_PLATFORM"
    echo "  • Build Registry: $BUILD_REGISTRY"
    echo ""
    log_success "Environment configuration generation completed successfully!"
}

# Main execution
main() {
    log_info "=== Environment Configuration Generation ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Configs Directory: $CONFIGS_DIR"
    log_info "Environment Directory: $ENV_DIR"
    echo ""
    
    # Execute generation steps
    create_directory_structure
    generate_secure_values
    generate_pi_build_env
    generate_foundation_env
    generate_core_env
    generate_application_env
    generate_support_env
    generate_gui_env
    validate_generated_files
    
    # Display summary
    echo ""
    display_summary
}

# Run main function
main "$@"