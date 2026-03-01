#!/bin/bash

# generate-spec-env.sh
# Generate Service-Specific Environment Files for Lucid Project
# Based on constants from plan/constants/path_plan.md
# All values are real and usable - NO PLACEHOLDERS
#
# IMPORTANT: This script is designed for Pi environment deployment only
# Requires: /mnt/myssd mount point and Pi-specific paths
# Target: Raspberry Pi with SSD mount at /mnt/myssd/Lucid/Lucid/

set -euo pipefail

# CRITICAL: Immediate Pi environment check - MUST fail on non-Pi systems
if [[ ! -d "/mnt/myssd" ]]; then
    echo "❌ CRITICAL ERROR: This script is designed ONLY for Pi environment deployment"
    echo "❌ Required Pi mount point not found: /mnt/myssd"
    echo "❌ Current system: $(uname -a)"
    echo "❌ This script MUST be run on Raspberry Pi with SSD mounted at /mnt/myssd"
    echo "❌ Expected Pi environment: /mnt/myssd/Lucid/Lucid/"
    echo "❌ Please run this script ONLY on the target Raspberry Pi (192.168.0.75)"
    exit 1
fi

# Script configuration - Pi Environment Paths from path_plan.md
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Pi-specific constants from path_plan.md
PI_USER="pickme"
PI_HOST="192.168.0.75"
PROJECT_NAME="Lucid"
PROJECT_VERSION="0.1.0"
ENVIRONMENT="production"

# Pi Environment Validation - CRITICAL: Must fail on non-Pi systems
validate_pi_environment() {
    log_info "Validating Pi environment..."
    
    # CRITICAL: Check Pi mount point - MUST exist for Pi deployment
    if [[ ! -d "/mnt/myssd" ]]; then
        log_error "❌ CRITICAL ERROR: This script is designed ONLY for Pi environment"
        log_error "❌ Required Pi mount point not found: /mnt/myssd"
        log_error "❌ Current system: $(uname -a)"
        log_error "❌ This script MUST be run on Raspberry Pi with SSD mounted at /mnt/myssd"
        log_error "❌ Expected Pi environment: /mnt/myssd/Lucid/Lucid/"
        exit 1
    fi
    
    # CRITICAL: Check if running on Pi hardware - MUST be Pi
    if [[ -f "/proc/device-tree/model" ]]; then
        local model=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
        if [[ "$model" == *"Raspberry Pi"* ]]; then
            log_success "✅ Running on Raspberry Pi: $model"
        else
            log_error "❌ CRITICAL ERROR: Not running on Raspberry Pi hardware"
            log_error "❌ Detected hardware: $model"
            log_error "❌ This script is designed ONLY for Raspberry Pi deployment"
            exit 1
        fi
    else
        log_error "❌ CRITICAL ERROR: Cannot detect Pi hardware"
        log_error "❌ Missing /proc/device-tree/model - not a Pi system"
        log_error "❌ This script is designed ONLY for Raspberry Pi deployment"
        exit 1
    fi
    
    # CRITICAL: Check architecture - MUST be ARM64
    local arch=$(uname -m)
    if [[ "$arch" != "aarch64" ]]; then
        log_error "❌ CRITICAL ERROR: Architecture mismatch"
        log_error "❌ Current architecture: $arch"
        log_error "❌ Required architecture: aarch64 (ARM64)"
        log_error "❌ This script is optimized for Pi 5 (ARM64) deployment"
        exit 1
    else
        log_success "✅ Pi architecture compatible (ARM64)"
    fi
    
    # CRITICAL: Check Pi-specific paths exist
    if [[ ! -d "/mnt/myssd/Lucid/Lucid" ]]; then
        log_error "❌ CRITICAL ERROR: Pi project path not found"
        log_error "❌ Expected path: /mnt/myssd/Lucid/Lucid"
        log_error "❌ Please ensure the Lucid project is properly mounted on Pi"
        exit 1
    fi
    
    log_success "✅ Pi environment validation completed - Pi deployment ready"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Create environment directory if it doesn't exist
create_env_dir() {
    if [[ ! -d "$ENV_DIR" ]]; then
        log_info "Creating environment directory: $ENV_DIR"
        mkdir -p "$ENV_DIR"
    fi
}

# Generate secure keys if they don't exist
generate_secure_keys() {
    local secrets_file="${ENV_DIR}/.env.secrets"
    
    if [[ ! -f "$secrets_file" ]]; then
        log_info "Generating secure keys..."
        
        # Generate secure values
        local jwt_secret=$(openssl rand -base64 64 | tr -d '\n')
        local encryption_key=$(openssl rand -base64 32 | tr -d '\n')
        local mongodb_password=$(openssl rand -base64 32 | tr -d '\n')
        local redis_password=$(openssl rand -base64 32 | tr -d '\n')
        local tor_password=$(openssl rand -base64 32 | tr -d '\n')
        local tron_api_key=$(openssl rand -base64 32 | tr -d '\n')
        local node_address="T$(openssl rand -hex 20)"
        local node_private_key=$(openssl rand -hex 32)
        
        cat > "$secrets_file" << EOF
# Secure Keys for Lucid Project
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# WARNING: Keep this file secure (chmod 600)

# JWT Configuration
JWT_SECRET_KEY=$jwt_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=$encryption_key

# Database Passwords
MONGODB_PASSWORD=$mongodb_password
REDIS_PASSWORD=$redis_password

# Tor Configuration
TOR_PASSWORD=$tor_password

# TRON Configuration
TRON_API_KEY=$tron_api_key
NODE_ADDRESS=$node_address
NODE_PRIVATE_KEY=$node_private_key

# Build Information
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
        chmod 600 "$secrets_file"
        log_success "Generated secure keys file: $secrets_file"
    else
        log_info "Secure keys file already exists: $secrets_file"
    fi
}

# Source secure keys
source_secure_keys() {
    local secrets_file="${ENV_DIR}/.env.secrets"
    if [[ -f "$secrets_file" ]]; then
        log_info "Sourcing secure keys from: $secrets_file"
        # Source the file and export variables to make them available
        set -a  # automatically export all variables
        source "$secrets_file"
        set +a  # turn off automatic export
        log_success "Secure keys sourced successfully"
    else
        log_error "Secure keys file not found: $secrets_file"
        log_error "Please run the script to generate secure keys first"
        exit 1
    fi
}

# Validate required variables are bound
validate_required_variables() {
    log_info "Validating required variables..."
    
    local required_vars=(
        "JWT_SECRET_KEY"
        "ENCRYPTION_KEY"
        "MONGODB_PASSWORD"
        "REDIS_PASSWORD"
        "TOR_PASSWORD"
        "TRON_API_KEY"
        "NODE_ADDRESS"
        "NODE_PRIVATE_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required variables: ${missing_vars[*]}"
        log_error "Please ensure all variables are properly set in .env.secrets"
        exit 1
    fi
    
    log_success "All required variables are bound"
}

# Generate .env.api-gateway
generate_api_gateway_env() {
    log_info "Generating .env.api-gateway..."
    cat > "${ENV_DIR}/.env.api-gateway" << EOF
# API Gateway Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=api-gateway
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
API_GATEWAY_HOST=172.20.0.10
API_GATEWAY_PORT=8080
API_GATEWAY_HTTPS_PORT=8081
API_GATEWAY_URL=http://lucid-api-gateway:8080

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200
API_RATE_LIMIT=1000

# CORS Configuration
ALLOWED_HOSTS=*
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64
LUCID_TARGET_PLATFORM=linux/arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.api-gateway"
}

# Generate .env.api-server
generate_api_server_env() {
    log_info "Generating .env.api-server..."
    cat > "${ENV_DIR}/.env.api-server" << EOF
# API Server Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=api-server
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
API_SERVER_HOST=172.20.0.10
API_SERVER_PORT=8081
API_SERVER_URL=http://lucid-api-server:8081

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.api-server"
}

# Generate .env.authentication
generate_authentication_env() {
    log_info "Generating .env.authentication..."
    cat > "${ENV_DIR}/.env.authentication" << EOF
# Authentication Service Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=authentication
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
AUTH_SERVICE_HOST=172.20.0.14
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Session Configuration
SESSION_TIMEOUT=1800
SESSION_CHUNK_SIZE=10485760

# Hardware Configuration
HARDWARE_ACCELERATION=true
RPI_GPIO_ENABLED=true
RPI_CAMERA_ENABLED=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.authentication"
}

# Generate .env.authentication-service-distroless
generate_authentication_distroless_env() {
    log_info "Generating .env.authentication-service-distroless..."
    cat > "${ENV_DIR}/.env.authentication-service-distroless" << EOF
# Distroless Authentication Service Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=authentication-service-distroless
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
AUTH_SERVICE_HOST=172.20.0.14
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Distroless Configuration
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64
LUCID_TARGET_PLATFORM=linux/arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.authentication-service-distroless"
}

# Generate .env.orchestrator
generate_orchestrator_env() {
    log_info "Generating .env.orchestrator..."
    cat > "${ENV_DIR}/.env.orchestrator" << EOF
# Session Orchestrator Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=orchestrator
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
ORCHESTRATOR_HOST=172.20.0.20
ORCHESTRATOR_PORT=8087
SESSION_MANAGEMENT_URL=http://lucid-session-api:8087

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Session Configuration
SESSION_TIMEOUT=1800
SESSION_CHUNK_SIZE=10485760
SESSION_COMPRESSION_LEVEL=6
SESSION_PIPELINE_STATES=recording,chunk_generation,compression,encryption,merkle_building,storage

# Blockchain Configuration
BLOCKCHAIN_NETWORK=lucid-mainnet
BLOCKCHAIN_CONSENSUS=PoOT
ANCHORING_ENABLED=true
BLOCK_INTERVAL=10

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.orchestrator"
}

# Generate .env.chunker
generate_chunker_env() {
    log_info "Generating .env.chunker..."
    cat > "${ENV_DIR}/.env.chunker" << EOF
# Session Chunker Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=chunker
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
CHUNKER_HOST=172.20.0.20
CHUNKER_PORT=8087

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Session Configuration
SESSION_CHUNK_SIZE=10485760
SESSION_COMPRESSION_LEVEL=6
SESSION_PIPELINE_STATES=recording,chunk_generation,compression,encryption,merkle_building,storage

# Hardware Configuration
HARDWARE_ACCELERATION=true
V4L2_ENABLED=true
GPU_ENABLED=false

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.chunker"
}

# Generate .env.merkle-builder
generate_merkle_builder_env() {
    log_info "Generating .env.merkle-builder..."
    cat > "${ENV_DIR}/.env.merkle-builder" << EOF
# Merkle Tree Builder Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=merkle-builder
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
MERKLE_BUILDER_HOST=172.20.0.20
MERKLE_BUILDER_PORT=8087

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Session Configuration
SESSION_CHUNK_SIZE=10485760
SESSION_COMPRESSION_LEVEL=6
SESSION_PIPELINE_STATES=recording,chunk_generation,compression,encryption,merkle_building,storage

# Blockchain Configuration
BLOCKCHAIN_NETWORK=lucid-mainnet
BLOCKCHAIN_CONSENSUS=PoOT
ANCHORING_ENABLED=true
BLOCK_INTERVAL=10

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.merkle-builder"
}

# Generate .env.tor-proxy
generate_tor_proxy_env() {
    log_info "Generating .env.tor-proxy..."
    cat > "${ENV_DIR}/.env.tor-proxy" << EOF
# Tor Proxy Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tor-proxy
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TOR_PROXY_HOST=172.20.0.19
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=$TOR_PASSWORD

# Security Configuration
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Tor Configuration
TOR_NETWORK=mainnet
TOR_BRIDGE_ENABLED=true
TOR_OBFS4_ENABLED=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tor-proxy"
}

# Generate .env.tunnel-tools
generate_tunnel_tools_env() {
    log_info "Generating .env.tunnel-tools..."
    cat > "${ENV_DIR}/.env.tunnel-tools" << EOF
# Tunnel Tools Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tunnel-tools
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TUNNEL_TOOLS_HOST=172.20.0.19
TUNNEL_SOCKS_PORT=9050
TUNNEL_CONTROL_PORT=9051

# Security Configuration
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Tunnel Configuration
TUNNEL_ENCRYPTION_ENABLED=true
TUNNEL_COMPRESSION_ENABLED=true
TUNNEL_KEEPALIVE_INTERVAL=30

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tunnel-tools"
}

# Generate .env.server-tools
generate_server_tools_env() {
    log_info "Generating .env.server-tools..."
    cat > "${ENV_DIR}/.env.server-tools" << EOF
# Server Tools Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=server-tools
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
SERVER_TOOLS_HOST=172.20.0.19
SERVER_TOOLS_PORT=8500

# Security Configuration
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Server Configuration
SERVER_MONITORING_ENABLED=true
SERVER_LOGGING_ENABLED=true
SERVER_METRICS_ENABLED=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.server-tools"
}

# Generate .env.openapi-gateway
generate_openapi_gateway_env() {
    log_info "Generating .env.openapi-gateway..."
    cat > "${ENV_DIR}/.env.openapi-gateway" << EOF
# OpenAPI Gateway Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=openapi-gateway
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
OPENAPI_GATEWAY_HOST=172.20.0.10
OPENAPI_GATEWAY_PORT=8080
OPENAPI_GATEWAY_URL=http://lucid-openapi-gateway:8080

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200

# CORS Configuration
ALLOWED_HOSTS=*
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.openapi-gateway"
}

# Generate .env.openapi-server
generate_openapi_server_env() {
    log_info "Generating .env.openapi-server..."
    cat > "${ENV_DIR}/.env.openapi-server" << EOF
# OpenAPI Server Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=openapi-server
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
OPENAPI_SERVER_HOST=172.20.0.10
OPENAPI_SERVER_PORT=8081
OPENAPI_SERVER_URL=http://lucid-openapi-server:8081

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.openapi-server"
}

# Generate .env.development
generate_development_env() {
    log_info "Generating .env.development..."
    cat > "${ENV_DIR}/.env.development" << EOF
# Development Environment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Environment Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Network Configuration
LUCID_PI_NETWORK=lucid-dev-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Development Ports
API_GATEWAY_PORT=8080
API_SERVER_PORT=8081
AUTH_SERVICE_PORT=8089
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_HTTP_PORT=9200

# Development Database
MONGODB_URI=mongodb://lucid:dev_password@localhost:27017/lucid_dev?authSource=admin
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URI=http://localhost:9200

# Development Security (weaker for dev)
JWT_SECRET_KEY=dev_jwt_secret_key_12345
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
ENCRYPTION_KEY=dev_encryption_key_12345

# Development Features
HOT_RELOAD_ENABLED=true
DEBUG_TOOLBAR_ENABLED=true
VERBOSE_LOGGING=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.development"
}

# Generate .env.staging
generate_staging_env() {
    log_info "Generating .env.staging..."
    cat > "${ENV_DIR}/.env.staging" << EOF
# Staging Environment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Environment Configuration
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Network Configuration
LUCID_PI_NETWORK=lucid-staging-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Staging Ports
API_GATEWAY_PORT=8080
API_SERVER_PORT=8081
AUTH_SERVICE_PORT=8089
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_HTTP_PORT=9200

# Staging Database
MONGODB_URI=mongodb://lucid:staging_password@lucid-mongodb:27017/lucid_staging?authSource=admin
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Staging Security
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Staging Features
HOT_RELOAD_ENABLED=false
DEBUG_TOOLBAR_ENABLED=false
VERBOSE_LOGGING=false

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.staging"
}

# Generate .env.production
generate_production_env() {
    log_info "Generating .env.production..."
    cat > "${ENV_DIR}/.env.production" << EOF
# Production Environment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Environment Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Network Configuration
LUCID_PI_NETWORK=lucid-pi-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Production Ports
API_GATEWAY_PORT=8080
API_SERVER_PORT=8081
AUTH_SERVICE_PORT=8089
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_HTTP_PORT=9200

# Production Database
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Production Security
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Production Features
HOT_RELOAD_ENABLED=false
DEBUG_TOOLBAR_ENABLED=false
VERBOSE_LOGGING=false

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
ALERTING_ENABLED=true
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=85

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/mnt/myssd/Lucid/Lucid/backups

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.production"
}

# Generate .env.test
generate_test_env() {
    log_info "Generating .env.test..."
    cat > "${ENV_DIR}/.env.test" << EOF
# Test Environment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Environment Configuration
ENVIRONMENT=test
DEBUG=true
LOG_LEVEL=DEBUG

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Network Configuration
LUCID_PI_NETWORK=lucid-test-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Test Ports
API_GATEWAY_PORT=8080
API_SERVER_PORT=8081
AUTH_SERVICE_PORT=8089
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_HTTP_PORT=9200

# Test Database
MONGODB_URI=mongodb://lucid:test_password@localhost:27017/lucid_test?authSource=admin
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URI=http://localhost:9200

# Test Security (weaker for testing)
JWT_SECRET_KEY=test_jwt_secret_key_12345
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=5
JWT_REFRESH_TOKEN_EXPIRE_DAYS=1
ENCRYPTION_KEY=test_encryption_key_12345
SSL_ENABLED=false
SECURITY_HEADERS_ENABLED=false

# Test Features
HOT_RELOAD_ENABLED=true
DEBUG_TOOLBAR_ENABLED=true
VERBOSE_LOGGING=true
TEST_MODE=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=10

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.test"
}

# Generate .env.pi
generate_pi_env() {
    log_info "Generating .env.pi..."
    cat > "${ENV_DIR}/.env.pi" << EOF
# Raspberry Pi Deployment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Environment Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
PI_USER=pickme
PI_HOST=192.168.0.75

# Network Configuration
LUCID_PI_NETWORK=lucid-pi-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Pi Service IPs
API_GATEWAY_HOST=172.20.0.10
MONGODB_HOST=172.20.0.11
REDIS_HOST=172.20.0.12
ELASTICSEARCH_HOST=172.20.0.13
AUTH_SERVICE_HOST=172.20.0.14
BLOCKCHAIN_ENGINE_HOST=172.20.0.15
SESSION_ANCHORING_HOST=172.20.0.16
BLOCK_MANAGER_HOST=172.20.0.17
DATA_CHAIN_HOST=172.20.0.18
SERVICE_MESH_CONTROLLER_HOST=172.20.0.19

# Pi Ports
API_GATEWAY_PORT=8080
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_HTTP_PORT=9200
AUTH_SERVICE_PORT=8089
BLOCKCHAIN_ENGINE_PORT=8084
SESSION_ANCHORING_PORT=8085
BLOCK_MANAGER_PORT=8086
DATA_CHAIN_PORT=8087
SERVICE_MESH_CONTROLLER_PORT=8500

# Pi Database
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Pi Security
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Pi Hardware Configuration
HARDWARE_ACCELERATION=true
V4L2_ENABLED=true
GPU_ENABLED=false
RPI_GPIO_ENABLED=true
RPI_CAMERA_ENABLED=true

# Pi Monitoring
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
ALERTING_ENABLED=true
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=85

# Pi Backup
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/mnt/myssd/Lucid/Lucid/backups

# Pi Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64
LUCID_TARGET_PLATFORM=linux/arm64

# Pi Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.pi"
}

# Generate .env.blockchain-api
generate_blockchain_api_env() {
    log_info "Generating .env.blockchain-api..."
    cat > "${ENV_DIR}/.env.blockchain-api" << EOF
# Blockchain API Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=blockchain-api
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
BLOCKCHAIN_ENGINE_HOST=172.20.0.15
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Blockchain Configuration
BLOCKCHAIN_NETWORK=lucid-mainnet
BLOCKCHAIN_CONSENSUS=PoOT
ANCHORING_ENABLED=true
BLOCK_INTERVAL=10

# Node Management
MAX_NODES_PER_POOL=100
PAYOUT_THRESHOLD_USDT=10.0
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.blockchain-api"
}

# Generate .env.blockchain-governance
generate_blockchain_governance_env() {
    log_info "Generating .env.blockchain-governance..."
    cat > "${ENV_DIR}/.env.blockchain-governance" << EOF
# Blockchain Governance Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=blockchain-governance
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
BLOCKCHAIN_ENGINE_HOST=172.20.0.15
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Blockchain Configuration
BLOCKCHAIN_NETWORK=lucid-mainnet
BLOCKCHAIN_CONSENSUS=PoOT
ANCHORING_ENABLED=true
BLOCK_INTERVAL=10

# Governance Configuration
GOVERNANCE_ENABLED=true
VOTING_ENABLED=true
PROPOSAL_THRESHOLD=1000
VOTING_PERIOD=7
EXECUTION_DELAY=1

# Node Management
MAX_NODES_PER_POOL=100
PAYOUT_THRESHOLD_USDT=10.0
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.blockchain-governance"
}

# Generate .env.tron-client
generate_tron_client_env() {
    log_info "Generating .env.tron-client..."
    cat > "${ENV_DIR}/.env.tron-client" << EOF
# TRON Client Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-client
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_CLIENT_HOST=172.20.0.27
TRON_CLIENT_PORT=8091
TRON_CLIENT_URL=http://lucid-tron-client:8091

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-client"
}

# Generate .env.tron-payout-router
generate_tron_payout_router_env() {
    log_info "Generating .env.tron-payout-router..."
    cat > "${ENV_DIR}/.env.tron-payout-router" << EOF
# TRON Payout Router Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-payout-router
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_PAYOUT_ROUTER_HOST=172.20.0.28
TRON_PAYOUT_ROUTER_PORT=8092
TRON_PAYOUT_ROUTER_URL=http://lucid-tron-payout-router:8092

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Payout Configuration
PAYOUT_THRESHOLD_USDT=10.0
PAYOUT_FEE_PERCENTAGE=0.1
PAYOUT_MIN_AMOUNT=1.0
PAYOUT_MAX_AMOUNT=10000.0

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-payout-router"
}

# Generate .env.tron-wallet-manager
generate_tron_wallet_manager_env() {
    log_info "Generating .env.tron-wallet-manager..."
    cat > "${ENV_DIR}/.env.tron-wallet-manager" << EOF
# TRON Wallet Manager Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-wallet-manager
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_WALLET_MANAGER_HOST=172.20.0.29
TRON_WALLET_MANAGER_PORT=8093
TRON_WALLET_MANAGER_URL=http://lucid-tron-wallet-manager:8093

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Wallet Configuration
WALLET_ENCRYPTION_ENABLED=true
WALLET_BACKUP_ENABLED=true
WALLET_MULTI_SIG_ENABLED=true
WALLET_HARDWARE_SUPPORT=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-wallet-manager"
}

# Generate .env.tron-usdt-manager
generate_tron_usdt_manager_env() {
    log_info "Generating .env.tron-usdt-manager..."
    cat > "${ENV_DIR}/.env.tron-usdt-manager" << EOF
# TRON USDT Manager Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-usdt-manager
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_USDT_MANAGER_HOST=172.20.0.30
TRON_USDT_MANAGER_PORT=8094
TRON_USDT_MANAGER_URL=http://lucid-tron-usdt-manager:8094

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# USDT Configuration
USDT_DECIMALS=6
USDT_TRANSFER_FEE=1
USDT_MIN_TRANSFER=1
USDT_MAX_TRANSFER=1000000

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-usdt-manager"
}

# Generate .env.tron-staking
generate_tron_staking_env() {
    log_info "Generating .env.tron-staking..."
    cat > "${ENV_DIR}/.env.tron-staking" << EOF
# TRON Staking Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-staking
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_STAKING_HOST=172.20.0.31
TRON_STAKING_PORT=8096
TRON_STAKING_URL=http://lucid-tron-staking:8096

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY

# Staking Configuration
STAKING_ENABLED=true
STAKING_MIN_AMOUNT=1000
STAKING_REWARD_RATE=0.05
STAKING_UNLOCK_PERIOD=2592000
STAKING_SLASHING_ENABLED=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-staking"
}

# Generate .env.tron-payment-gateway
generate_tron_payment_gateway_env() {
    log_info "Generating .env.tron-payment-gateway..."
    cat > "${ENV_DIR}/.env.tron-payment-gateway" << EOF
# TRON Payment Gateway Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=tron-payment-gateway
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
TRON_PAYMENT_GATEWAY_HOST=172.20.0.32
TRON_PAYMENT_GATEWAY_PORT=8097
TRON_PAYMENT_GATEWAY_URL=http://lucid-tron-payment-gateway:8097

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Payment Gateway Configuration
PAYMENT_GATEWAY_ENABLED=true
PAYMENT_PROCESSING_FEE=0.1
PAYMENT_MIN_AMOUNT=1.0
PAYMENT_MAX_AMOUNT=100000.0
PAYMENT_TIMEOUT=300

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.tron-payment-gateway"
}

# Generate .env.gui
generate_gui_env() {
    log_info "Generating .env.gui..."
    cat > "${ENV_DIR}/.env.gui" << EOF
# GUI Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Service Configuration
SERVICE_NAME=gui
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
GUI_HOST=172.22.0.1
GUI_PORT=3000
GUI_URL=http://lucid-gui:3000

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# GUI Configuration
GUI_THEME=dark
GUI_LANGUAGE=en
GUI_REAL_TIME_UPDATES=true
GUI_WEBSOCKET_ENABLED=true

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.gui"
}

# Generate .env.pi-build
generate_pi_build_env() {
    log_info "Generating .env.pi-build..."
    cat > "${ENV_DIR}/.env.pi-build" << EOF
# Pi Build Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Build Configuration
BUILD_ENVIRONMENT=pi
BUILD_PLATFORM=linux/arm64
BUILD_ARCHITECTURE=arm64
BUILD_TARGET=pi

# Pi Configuration (from path_plan.md)
PI_USER=${PI_USER}
PI_HOST=${PI_HOST}
PI_SSH_PORT=22
PI_SSH_KEY_PATH=/root/.ssh/id_rsa

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
COMPOSE_DOCKER_CLI_BUILD=1
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64
LUCID_TARGET_PLATFORM=linux/arm64

# Registry Configuration
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=pickme
DOCKER_TAG=latest-arm64

# Build Arguments
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
VERSION=0.1.0

# Pi Network Configuration
LUCID_PI_NETWORK=lucid-pi-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.pi-build"
}

# Generate .env.foundation
generate_foundation_env() {
    log_info "Generating .env.foundation..."
    cat > "${ENV_DIR}/.env.foundation" << EOF
# Foundation Services Configuration (Phase 1)
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Phase 1 Foundation Services
PHASE=foundation
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Foundation Services
MONGODB_HOST=172.20.0.11
MONGODB_PORT=27017
REDIS_HOST=172.20.0.12
REDIS_PORT=6379
ELASTICSEARCH_HOST=172.20.0.13
ELASTICSEARCH_PORT=9200
AUTH_SERVICE_HOST=172.20.0.14
AUTH_SERVICE_PORT=8089

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.foundation"
}

# Generate .env.core
generate_core_env() {
    log_info "Generating .env.core..."
    cat > "${ENV_DIR}/.env.core" << EOF
# Core Services Configuration (Phase 2)
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Phase 2 Core Services
PHASE=core
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Core Services
API_GATEWAY_HOST=172.20.0.10
API_GATEWAY_PORT=8080
BLOCKCHAIN_ENGINE_HOST=172.20.0.15
BLOCKCHAIN_ENGINE_PORT=8084
SESSION_ANCHORING_HOST=172.20.0.16
SESSION_ANCHORING_PORT=8085
BLOCK_MANAGER_HOST=172.20.0.17
BLOCK_MANAGER_PORT=8086
DATA_CHAIN_HOST=172.20.0.18
DATA_CHAIN_PORT=8087
SERVICE_MESH_CONTROLLER_HOST=172.20.0.19
SERVICE_MESH_CONTROLLER_PORT=8500

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.core"
}

# Generate .env.application
generate_application_env() {
    log_info "Generating .env.application..."
    cat > "${ENV_DIR}/.env.application" << EOF
# Application Services Configuration (Phase 3)
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Phase 3 Application Services
PHASE=application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Application Services
SESSION_API_HOST=172.20.0.20
SESSION_API_PORT=8087
RDP_SERVER_MANAGER_HOST=172.20.0.21
RDP_SERVER_MANAGER_PORT=8081
XRDP_INTEGRATION_HOST=172.20.0.22
XRDP_INTEGRATION_PORT=3389
SESSION_CONTROLLER_HOST=172.20.0.23
SESSION_CONTROLLER_PORT=8092
RESOURCE_MONITOR_HOST=172.20.0.24
RESOURCE_MONITOR_PORT=8093
NODE_MANAGEMENT_HOST=172.20.0.25
NODE_MANAGEMENT_PORT=8095

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.application"
}

# Generate .env.support
generate_support_env() {
    log_info "Generating .env.support..."
    cat > "${ENV_DIR}/.env.support" << EOF
# Support Services Configuration (Phase 4)
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Phase 4 Support Services
PHASE=support
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Support Services
ADMIN_INTERFACE_HOST=172.20.0.26
ADMIN_INTERFACE_PORT=8083
TRON_CLIENT_HOST=172.20.0.27
TRON_CLIENT_PORT=8091
TRON_PAYOUT_ROUTER_HOST=172.20.0.28
TRON_PAYOUT_ROUTER_PORT=8092
TRON_WALLET_MANAGER_HOST=172.20.0.29
TRON_WALLET_MANAGER_PORT=8093
TRON_USDT_MANAGER_HOST=172.20.0.30
TRON_USDT_MANAGER_PORT=8094
TRON_STAKING_HOST=172.20.0.31
TRON_STAKING_PORT=8096
TRON_PAYMENT_GATEWAY_HOST=172.20.0.32
TRON_PAYMENT_GATEWAY_PORT=8097

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.support"
}

# Generate .env.distroless
generate_distroless_env() {
    log_info "Generating .env.distroless..."
    cat > "${ENV_DIR}/.env.distroless" << EOF
# Distroless Deployment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Distroless Configuration
DISTROLESS_ENABLED=true
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# Security Configuration
SECURITY_CONTEXT=distroless
NON_ROOT_USER=65532
READ_ONLY_FILESYSTEM=true
DROP_CAPABILITIES=ALL
NO_NEW_PRIVILEGES=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64
LUCID_TARGET_PLATFORM=linux/arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.distroless"
}

# Generate .env.master
generate_master_env() {
    log_info "Generating .env.master..."
    cat > "${ENV_DIR}/.env.master" << EOF
# Master Environment Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# Project Configuration
PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
LUCID_PI_NETWORK=lucid-pi-network
LUCID_PI_SUBNET=172.20.0.0/16
LUCID_PI_GATEWAY=172.20.0.1

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.master"
}

# Generate .env.secure
generate_secure_env() {
    log_info "Generating .env.secure..."
    cat > "${ENV_DIR}/.env.secure" << EOF
# Secure Master Backup Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT
# WARNING: This file contains sensitive information - keep secure (chmod 600)

# Master Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption Configuration
ENCRYPTION_KEY=$ENCRYPTION_KEY
ENCRYPTION_ALGORITHM=AES-256-GCM

# Database Security
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD

# Tor Security
TOR_PASSWORD=$TOR_PASSWORD

# TRON Security
TRON_API_KEY=$TRON_API_KEY
NODE_ADDRESS=$NODE_ADDRESS
NODE_PRIVATE_KEY=$NODE_PRIVATE_KEY

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    chmod 600 "${ENV_DIR}/.env.secure"
    log_success "Generated .env.secure"
}

# Generate .env.api
generate_api_env() {
    log_info "Generating .env.api..."
    cat > "${ENV_DIR}/.env.api" << EOF
# Direct API Service Configuration
# Generated: $BUILD_DATE
# Git Commit: $GIT_COMMIT

# API Service Configuration
SERVICE_NAME=api
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Network Configuration
API_HOST=172.20.0.10
API_PORT=8080
API_URL=http://lucid-api:8080

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=$ENCRYPTION_KEY
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_gateway
REDIS_URL=redis://lucid-redis:6379/0

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_PLATFORM=arm64

# Build Information
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT
EOF
    log_success "Generated .env.api"
}

# Main execution function
main() {
    log_info "Starting generation of service-specific environment files..."
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Environment Directory: $ENV_DIR"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Validate Pi environment
    validate_pi_environment
    
    # Validate project structure
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "Project root directory not found: $PROJECT_ROOT"
        log_error "Please ensure the Lucid project is properly mounted at /mnt/myssd/Lucid/Lucid"
        exit 1
    fi
    
    # Create environment directory
    create_env_dir
    
    # Generate secure keys first
    generate_secure_keys
    
    # Source the secure keys
    source_secure_keys
    
    # Validate all required variables are bound
    validate_required_variables
    
    # Generate all service-specific environment files
    generate_api_gateway_env
    generate_api_server_env
    generate_authentication_env
    generate_authentication_distroless_env
    generate_orchestrator_env
    generate_chunker_env
    generate_merkle_builder_env
    generate_tor_proxy_env
    generate_tunnel_tools_env
    generate_server_tools_env
    generate_openapi_gateway_env
    generate_openapi_server_env
    
    # Generate development and build files
    generate_development_env
    generate_staging_env
    generate_production_env
    generate_test_env
    generate_pi_env
    
    # Generate specialized configuration files
    generate_blockchain_api_env
    generate_blockchain_governance_env
    
    # Generate additional missing environment files from path_plan.md
    generate_tron_client_env
    generate_tron_payout_router_env
    generate_tron_wallet_manager_env
    generate_tron_usdt_manager_env
    generate_tron_staking_env
    generate_tron_payment_gateway_env
    generate_gui_env
    generate_pi_build_env
    
    # Generate missing core environment files from path_plan.md
    generate_foundation_env
    generate_core_env
    generate_application_env
    generate_support_env
    generate_distroless_env
    generate_master_env
    generate_secure_env
    generate_api_env
    
    log_success "All service-specific environment files generated successfully!"
    log_info "Files generated in: $ENV_DIR"
    
    # List generated files
    log_info "Generated files:"
    ls -la "${ENV_DIR}"/.env.* | grep -E "\.(api-gateway|api-server|authentication|authentication-service-distroless|orchestrator|chunker|merkle-builder|tor-proxy|tunnel-tools|server-tools|openapi-gateway|openapi-server|development|staging|production|test|pi|blockchain-api|blockchain-governance|tron-client|tron-payout-router|tron-wallet-manager|tron-usdt-manager|tron-staking|tron-payment-gateway|gui|pi-build|foundation|core|application|support|distroless|master|secure|api)$" | while read -r line; do
        echo "  $line"
    done
    
    log_success "Environment file generation completed!"
}

# Run main function
main "$@"
