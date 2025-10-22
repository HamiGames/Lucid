#!/bin/bash
# Path: scripts/deployment/generate-env-fallback.sh
# Fallback Environment File Generator
# Creates basic .env files if generate-all-env-complete.sh is not available
# MUST RUN ON PI CONSOLE

set -euo pipefail

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

# Project root
PROJECT_ROOT="${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}"

echo ""
log_info "========================================"
log_info "Fallback Environment File Generator"
log_info "========================================"
echo ""

# Function to generate secure value
generate_secure_value() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d '\n'
}

# Function to generate hex value
generate_hex_value() {
    local length=${1:-32}
    openssl rand -hex $length | tr -d '\n'
}

# Function to create foundation .env file
create_foundation_env() {
    log_info "Creating foundation .env file..."
    
    # Generate secure values
    local mongodb_password=$(generate_secure_value 32)
    local redis_password=$(generate_secure_value 32)
    local jwt_secret=$(generate_secure_value 64)
    local encryption_key=$(generate_hex_value 32)
    local tor_password=$(generate_secure_value 32)
    local session_secret=$(generate_secure_value 32)
    local api_secret=$(generate_secure_value 32)
    
    # Create foundation .env file
    cat > configs/environment/.env.foundation << EOF
# Foundation Environment Configuration
# Generated: $(date)
# Phase 1: Foundation Setup

# ============================================================================
# PROJECT IDENTIFICATION
# ============================================================================
LUCID_PROJECT=lucid
LUCID_VERSION=1.0.0
LUCID_PHASE=foundation
LUCID_BUILD_PHASE=1
LUCID_ENVIRONMENT=production

# ============================================================================
# DOCKER CONFIGURATION
# ============================================================================
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# ============================================================================
# PYTHON ENVIRONMENT
# ============================================================================
PYTHON_VERSION=3.11
PYTHON_ENV=production
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=/app

# ============================================================================
# FOUNDATION SERVICES CONFIGURATION
# ============================================================================

# MongoDB Configuration
MONGODB_VERSION=7.0
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid
MONGODB_URI=mongodb://lucid:${mongodb_password}@mongodb:27017/lucid?authSource=admin
MONGODB_REPLICA_SET=rs0
MONGODB_REPLICA_SET_ENABLED=true
MONGODB_AUTH_ENABLED=true
MONGODB_USER=lucid
MONGODB_PASSWORD=${mongodb_password}
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=${mongodb_password}

# Redis Configuration
REDIS_VERSION=7.0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URI=redis://:${redis_password}@redis:6379/0
REDIS_PASSWORD=${redis_password}
REDIS_CLUSTER_ENABLED=false
REDIS_MAX_MEMORY=512mb
REDIS_MAX_MEMORY_POLICY=allkeys-lru

# Elasticsearch Configuration
ELASTICSEARCH_VERSION=8.11.0
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_URI=http://elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=lucid
ELASTICSEARCH_CLUSTER_NAME=lucid-cluster
ELASTICSEARCH_DISCOVERY_TYPE=single-node
ELASTICSEARCH_SECURITY_ENABLED=false

# ============================================================================
# AUTHENTICATION SERVICE CONFIGURATION
# ============================================================================
AUTH_SERVICE_NAME=auth-service
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_URL=http://auth-service:8089

# JWT Configuration
JWT_SECRET_KEY=${jwt_secret}
JWT_SECRET=${jwt_secret}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# TRON Signature Verification
TRON_SIGNATURE_VERIFICATION_ENABLED=true
TRON_NETWORK=mainnet

# Hardware Wallet Support
ENABLE_HARDWARE_WALLET=true
LEDGER_SUPPORTED=true
TREZOR_SUPPORTED=true
KEEPKEY_SUPPORTED=true

# RBAC Configuration
RBAC_ENABLED=true
DEFAULT_USER_ROLE=user

# Security
BCRYPT_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5
LOGIN_COOLDOWN_MINUTES=15

# ============================================================================
# ENCRYPTION AND SECURITY
# ============================================================================
ENCRYPTION_KEY=${encryption_key}
TOR_PASSWORD=${tor_password}
SESSION_SECRET=${session_secret}
API_SECRET=${api_secret}

# ============================================================================
# STORAGE PATHS
# ============================================================================
DATA_ROOT=/data
LOGS_ROOT=/var/log/lucid
BACKUPS_ROOT=/backups

# Database Storage
MONGODB_DATA_PATH=/data/mongodb
REDIS_DATA_PATH=/data/redis
ELASTICSEARCH_DATA_PATH=/data/elasticsearch

# Application Storage
CHUNK_STORAGE_PATH=/data/chunks
SESSION_STORAGE_PATH=/data/sessions
MERKLE_STORAGE_PATH=/data/merkle
BLOCK_STORAGE_PATH=/data/blocks

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/var/log/lucid/foundation.log
LOG_MAX_SIZE=10MB
LOG_MAX_FILES=5
LOG_ROTATION_ENABLED=true

# Structured Logging
ENABLE_STRUCTURED_LOGGING=true
LOG_INCLUDE_TIMESTAMP=true
LOG_INCLUDE_REQUEST_ID=true
LOG_INCLUDE_USER_ID=true

# ============================================================================
# HEALTH CHECK CONFIGURATION
# ============================================================================
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/backups
BACKUP_COMPRESSION_ENABLED=true

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=false

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
ENCRYPTION_KEY_ROTATION_DAYS=30
SESSION_ENCRYPTION_ENABLED=true
TLS_ENABLED=false
MTLS_ENABLED=false

# ============================================================================
# DEVELOPMENT CONFIGURATION
# ============================================================================
DEBUG_MODE=false
VERBOSE_LOGGING=false
PROFILE_PERFORMANCE=false
ENABLE_TRACING=false
ENABLE_HOT_RELOAD=false

# ============================================================================
# GIT HOOKS CONFIGURATION
# ============================================================================
GIT_HOOKS_ENABLED=true
PRE_COMMIT_LINTING=true
PRE_PUSH_TESTING=false

# ============================================================================
# LINTING CONFIGURATION
# ============================================================================
LINTING_ENABLED=true
LINTER_PYTHON=ruff
LINTER_MARKDOWN=markdownlint
LINTER_YAML=yamllint
LINTER_DOCKER=hadolint

# ============================================================================
# TESTING CONFIGURATION
# ============================================================================
TESTING_FRAMEWORK=pytest
TEST_COVERAGE_MIN=95
TEST_PARALLEL_ENABLED=true
TEST_VERBOSE=false

# ============================================================================
# CONTAINER CONFIGURATION
# ============================================================================
# Distroless Base Images
DISTROLESS_PYTHON_BASE=gcr.io/distroless/python3-debian12
DISTROLESS_JAVA_BASE=gcr.io/distroless/java17-debian12

# Container Resource Limits
CONTAINER_MEMORY_LIMIT=2G
CONTAINER_CPU_LIMIT=2
CONTAINER_RESTART_POLICY=unless-stopped

# ============================================================================
# NETWORK TIMEOUTS
# ============================================================================
NETWORK_TIMEOUT=30
NETWORK_RETRY_ATTEMPTS=3
NETWORK_RETRY_DELAY=5
NETWORK_KEEPALIVE=true

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================
UVICORN_WORKERS=1
UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
UVICORN_MAX_REQUESTS=1000
UVICORN_MAX_REQUESTS_JITTER=100

# ============================================================================
# VALIDATION FLAGS
# ============================================================================
FOUNDATION_INITIALIZED=false
DATABASE_INITIALIZED=false
AUTH_SERVICE_INITIALIZED=false
NETWORK_INITIALIZED=false
EOF

    log_success "Foundation .env file created"
}

# Function to create other .env files
create_other_env_files() {
    log_info "Creating additional .env files..."
    
    # Create core .env file
    cat > configs/environment/.env.core << EOF
# Core Services Configuration
# Generated: $(date)
# Phase 2: Core Services

# Database Configuration (inherited from foundation)
MONGODB_URI=mongodb://lucid:\${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:\${REDIS_PASSWORD}@redis:6379/0
ELASTICSEARCH_URI=http://elasticsearch:9200

# Authentication Configuration (inherited from foundation)
JWT_SECRET=\${JWT_SECRET}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}

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

    # Create application .env file
    cat > configs/environment/.env.application << EOF
# Application Services Configuration
# Generated: $(date)
# Phase 3: Application Services

# Database Configuration (inherited from foundation)
MONGODB_URI=mongodb://lucid:\${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:\${REDIS_PASSWORD}@redis:6379/0

# Authentication Configuration (inherited from foundation)
JWT_SECRET=\${JWT_SECRET}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}

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

    # Create support .env file
    cat > configs/environment/.env.support << EOF
# Support Services Configuration
# Generated: $(date)
# Phase 4: Support Services

# Database Configuration (inherited from foundation)
MONGODB_URI=mongodb://lucid:\${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:\${REDIS_PASSWORD}@redis:6379/0

# Authentication Configuration (inherited from foundation)
JWT_SECRET=\${JWT_SECRET}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}

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

    # Create GUI .env file
    cat > configs/environment/.env.gui << EOF
# GUI Integration Configuration
# Generated: $(date)
# GUI Services

# Database Configuration (inherited from foundation)
MONGODB_URI=mongodb://lucid:\${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:\${REDIS_PASSWORD}@redis:6379/0

# Authentication Configuration (inherited from foundation)
JWT_SECRET=\${JWT_SECRET}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}

# GUI Configuration
GUI_NETWORK=lucid-gui-network
GUI_API_BRIDGE_PORT=8099
GUI_DOCKER_MANAGER_PORT=8100
GUI_TOR_MANAGER_PORT=8101
GUI_HARDWARE_WALLET_PORT=8102

# Electron GUI Configuration
ELECTRON_ENABLED=true
ELECTRON_DEBUG=false
ELECTRON_DEV_TOOLS=false

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
LEDGER_ENABLED=true
TREZOR_ENABLED=true
KEEPKEY_ENABLED=true
EOF

    # Create secure backup file
    cat > configs/environment/.env.secure << EOF
# Secure Environment Backup
# Generated: $(date)
# DO NOT COMMIT TO VERSION CONTROL

# This file contains all secure values for backup purposes
# Keep this file secure and do not share

MONGODB_PASSWORD=\${MONGODB_PASSWORD}
REDIS_PASSWORD=\${REDIS_PASSWORD}
JWT_SECRET=\${JWT_SECRET}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}
TOR_PASSWORD=\${TOR_PASSWORD}
SESSION_SECRET=\${SESSION_SECRET}
API_SECRET=\${API_SECRET}
EOF

    log_success "Additional .env files created"
}

# Main execution
main() {
    # Check if we're in the right directory
    if [ ! -f "configs/docker/distroless/distroless-runtime-config.yml" ]; then
        log_error "Not in project root directory!"
        log_error "Please run from: $PROJECT_ROOT"
        exit 1
    fi

    # Create environment directory if it doesn't exist
    mkdir -p configs/environment

    # Create foundation .env file
    create_foundation_env

    # Create other .env files
    create_other_env_files

    # Set secure permissions
    chmod 600 configs/environment/.env.secure
    chmod 644 configs/environment/.env.*

    log_success "========================================"
    log_success "Environment files created successfully!"
    log_success "========================================"
    echo ""
    log_info "Created files:"
    log_info "  • configs/environment/.env.foundation"
    log_info "  • configs/environment/.env.core"
    log_info "  • configs/environment/.env.application"
    log_info "  • configs/environment/.env.support"
    log_info "  • configs/environment/.env.gui"
    log_info "  • configs/environment/.env.secure (backup)"
    echo ""
    log_info "Next steps:"
    log_info "  1. Create networks: bash scripts/deployment/create-distroless-networks.sh"
    log_info "  2. Create distroless .env: bash scripts/deployment/create-distroless-env.sh"
    log_info "  3. Deploy services: bash scripts/deployment/deploy-distroless-complete.sh full"
    echo ""
}

# Run main function
main "$@"
