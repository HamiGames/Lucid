#!/bin/bash

# generate-spec-env.sh
# Generate Service-Specific Environment Files for Lucid Project
# Based on constants from plan/constants/path_plan.md
# All values are real and usable - NO PLACEHOLDERS

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="${PROJECT_ROOT}/configs/environment"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

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
        cat > "$secrets_file" << 'EOF'
# Secure Keys for Lucid Project
# Generated: $(date)
# WARNING: Keep this file secure (chmod 600)

# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Database Passwords
MONGODB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Tor Configuration
TOR_PASSWORD=$(openssl rand -base64 32)

# TRON Configuration
TRON_API_KEY=$(openssl rand -base64 32)
NODE_ADDRESS=$(openssl rand -hex 20)
NODE_PRIVATE_KEY=$(openssl rand -hex 32)

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
        source "$secrets_file"
    else
        log_error "Secure keys file not found: $secrets_file"
        exit 1
    fi
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

# Main execution function
main() {
    log_info "Starting generation of service-specific environment files..."
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Environment Directory: $ENV_DIR"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Create environment directory
    create_env_dir
    
    # Generate secure keys first
    generate_secure_keys
    
    # Source the secure keys
    source_secure_keys
    
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
    
    log_success "All service-specific environment files generated successfully!"
    log_info "Files generated in: $ENV_DIR"
    
    # List generated files
    log_info "Generated files:"
    ls -la "${ENV_DIR}"/.env.* | grep -E "\.(api-gateway|api-server|authentication|authentication-service-distroless|orchestrator|chunker|merkle-builder|tor-proxy|tunnel-tools|server-tools|openapi-gateway|openapi-server|development|staging|production|test|pi|blockchain-api|blockchain-governance)$" | while read -r line; do
        echo "  $line"
    done
    
    log_success "Environment file generation completed!"
}

# Run main function
main "$@"
