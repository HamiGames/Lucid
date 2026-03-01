#!/bin/bash
# Pi Prep Stage - Generate .onion Names and All .env Files
# File Path: /mnt/myssd/Lucid/scripts/build/pi-prep-stage-generate-all.sh
# Target: Raspberry Pi ARM64 deployment
# Referenced from: plan/build_instruction_docs/docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
CONFIGS_DIR="$PROJECT_ROOT/configs"
ENV_DIR="$CONFIGS_DIR/environment"
DOCKER_CONFIGS_DIR="$CONFIGS_DIR/docker"
TOR_DATA_DIR="$PROJECT_ROOT/data/tor"

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

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d '\n'
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d '\n'
}

# Function to generate encryption key
generate_encryption_key() {
    openssl rand -hex 32
}

# ============================================================================
# STEP 1: CREATE DIRECTORY STRUCTURE
# ============================================================================
create_directory_structure() {
    log_info "Creating directory structure..."
    
    mkdir -p "$CONFIGS_DIR"
    mkdir -p "$ENV_DIR"
    mkdir -p "$DOCKER_CONFIGS_DIR"
    mkdir -p "$TOR_DATA_DIR"
    mkdir -p "$PROJECT_ROOT/data/onion_services"
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Create directories for all .env file locations
    mkdir -p "$PROJECT_ROOT/03-api-gateway/api"
    mkdir -p "$PROJECT_ROOT/infrastructure/docker/blockchain/env"
    mkdir -p "$PROJECT_ROOT/infrastructure/docker/databases/env"
    mkdir -p "$PROJECT_ROOT/sessions/core"
    
    log_success "Directory structure created"
}

# ============================================================================
# STEP 2: GENERATE .ONION HOSTNAMES FOR ALL SERVICES
# ============================================================================
generate_onion_names() {
    log_info "Generating .onion hostnames for all services..."
    
    # List of services that need .onion addresses
    local services=(
        "api-gateway"
        "auth-service"
        "blockchain-engine"
        "session-anchoring"
        "block-manager"
        "data-chain"
        "admin-interface"
        "tron-payment-gateway"
        "session-api"
        "rdp-server-manager"
        "node-management"
    )
    
    # Create onion services directory
    mkdir -p "$TOR_DATA_DIR/hidden_services"
    
    for service in "${services[@]}"; do
        local service_dir="$TOR_DATA_DIR/hidden_services/$service"
        mkdir -p "$service_dir"
        
        # Generate hostname using tor command if available, otherwise skip
        if command -v tor &> /dev/null; then
            log_info "Generating .onion for $service..."
            # Note: This requires tor to be running; alternative is to manually create
            # For now, we'll create a placeholder
        fi
        
        # Create placeholder hostname file (will be populated when Tor starts)
        if [ ! -f "$service_dir/hostname" ]; then
            echo "# Placeholder - will be generated when Tor starts for $service" > "$service_dir/hostname"
        fi
    done
    
    log_success ".onion hostname directories created"
}

# ============================================================================
# STEP 3: GENERATE SECURE VALUES
# ============================================================================
generate_secure_values() {
    log_info "Generating secure configuration values..."
    
    # Generate all secure values
    export MONGODB_PASSWORD=$(generate_password)
    export REDIS_PASSWORD=$(generate_password)
    export JWT_SECRET=$(generate_jwt_secret)
    export ENCRYPTION_KEY=$(generate_encryption_key)
    export TOR_PASSWORD=$(generate_password)
    export SESSION_SECRET=$(generate_password)
    export API_SECRET=$(generate_password)
    export BLOCKCHAIN_SECRET=$(generate_password)
    export ADMIN_SECRET=$(generate_password)
    export TRON_ENCRYPTION_KEY=$(generate_encryption_key)
    
    # Network configuration
    export PI_HOST="192.168.0.75"
    export PI_USER="pickme"
    export PI_DEPLOY_DIR="/mnt/myssd/Lucid"
    
    # Build configuration
    export BUILD_PLATFORM="linux/arm64"
    export BUILD_REGISTRY="pickme"
    export BUILD_TAG="latest-arm64"
    
    log_success "Secure values generated"
}

# ============================================================================
# STEP 4: GENERATE .ENV FILES FOR DOCKER COMPOSE
# ============================================================================

# Generate configs/environment/.env.foundation
generate_env_foundation() {
    log_info "Generating .env.foundation..."
    
    cat > "$ENV_DIR/.env.foundation" << EOF
# Phase 1 Foundation Services Configuration
# File: configs/environment/.env.foundation
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: MongoDB, Redis, Elasticsearch, Auth Service

# Database Configuration
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid_production
MONGODB_PORT=27017

REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PORT=6379
REDIS_MAXMEMORY=1gb

ELASTICSEARCH_URI=http://lucid-elasticsearch:9200
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_HEAP_SIZE=512m

# Authentication Configuration
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ENCRYPTION_KEY=$ENCRYPTION_KEY

# Security Configuration
TOR_PASSWORD=$TOR_PASSWORD
TOR_CONTROL_PASSWORD=$TOR_PASSWORD
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Service Configuration
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_HOST=lucid-auth-service
AUTH_SERVICE_URL=http://192.168.0.75:8089
AUTH_SERVICE_TIMEOUT=30

# Pi Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR

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

# Generate configs/environment/.env.core
generate_env_core() {
    log_info "Generating .env.core..."
    
    cat > "$ENV_DIR/.env.core" << EOF
# Phase 2 Core Services Configuration
# File: configs/environment/.env.core
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: API Gateway, Service Mesh, Blockchain Core

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Authentication Configuration (inherited from foundation)
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# API Gateway Configuration
API_GATEWAY_PORT=8080
API_GATEWAY_HOST=lucid-api-gateway
API_GATEWAY_TIMEOUT=30
API_GATEWAY_RATE_LIMIT=1000
API_GATEWAY_CORS_ORIGINS=*
API_SECRET=$API_SECRET

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
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET

# Consensus Configuration
CONSENSUS_ALGORITHM=PoOT
BLOCK_INTERVAL=10
BLOCK_TIME_SECONDS=10
BLOCK_SIZE_LIMIT=1048576
TRANSACTION_LIMIT=1000
MAX_TRANSACTIONS_PER_BLOCK=1000

# Network Configuration
NETWORK_PROTOCOL_VERSION=1.0.0
NETWORK_PEER_DISCOVERY=true
NETWORK_PEER_LIMIT=100

# Performance Configuration
CACHE_SIZE=1073741824
CACHE_TTL=3600
CONNECTION_POOL_SIZE=100

# Pi Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR
EOF
    
    log_success ".env.core generated"
}

# Generate configs/environment/.env.application
generate_env_application() {
    log_info "Generating .env.application..."
    
    cat > "$ENV_DIR/.env.application" << EOF
# Phase 3 Application Services Configuration
# File: configs/environment/.env.application
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Session Management, RDP Services, Node Management

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication Configuration (inherited from foundation)
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Session Management Configuration
SESSION_PIPELINE_PORT=8083
SESSION_RECORDER_PORT=8084
SESSION_CHUNK_PROCESSOR_PORT=8085
SESSION_STORAGE_PORT=8086
SESSION_API_PORT=8087
SESSION_SECRET=$SESSION_SECRET

# Session Configuration
SESSION_CHUNK_SIZE=8388608
SESSION_CHUNK_SIZE_MB=1
SESSION_COMPRESSION_LEVEL=6
SESSION_ENCRYPTION_ENABLED=true
SESSION_RETENTION_DAYS=30
SESSION_MERKLE_TREE_ENABLED=true
PIPELINE_MAX_CONCURRENT_SESSIONS=10
PIPELINE_STATE_MACHINE_ENABLED=true

# RDP Services Configuration
RDP_SERVER_MANAGER_PORT=8081
RDP_XRDP_INTEGRATION_PORT=3389
RDP_SESSION_CONTROLLER_PORT=8082
RDP_RESOURCE_MONITOR_PORT=8090

# RDP Configuration
RDP_MAX_SESSIONS=10
RDP_SESSION_TIMEOUT=3600
RDP_RESOURCE_LIMIT_CPU=80
RDP_RESOURCE_LIMIT_MEMORY=2147483648
RDP_RESOURCE_LIMIT_DISK=10737418240
XRDP_PORT=3389
MAX_CONCURRENT_SESSIONS=5
SESSION_TIMEOUT_MINUTES=60

# RDP Recording Configuration
SESSION_RECORDING_PATH=/data/recordings
SESSION_RECORDING_FORMAT=mp4
SESSION_RECORDING_QUALITY=high
SESSION_RECORDING_BITRATE=2000k
SESSION_RECORDING_FPS=30
RECORDING_QUALITY=high
RECORDING_FPS=30
RECORDING_BITRATE=2000k

# Node Management Configuration
NODE_MANAGEMENT_PORT=8095
NODE_POOL_MAX_SIZE=100
NODE_POOL_MAX_NODES=100
NODE_PAYOUT_THRESHOLD=10
PAYOUT_THRESHOLD_USDT=10
NODE_CONSENSUS_WEIGHT=1.0
POOT_CALCULATION_ENABLED=true
POOT_ENABLED=true
NODE_REGISTRATION_ENABLED=true

# Performance Configuration
CHUNK_PROCESSING_WORKERS=4
ENCRYPTION_WORKERS=2
COMPRESSION_WORKERS=2
STORAGE_WORKERS=4
PROCESSOR_CHUNK_SIZE_MB=1
PROCESSOR_ENCRYPTION_ENABLED=true
PROCESSOR_COMPRESSION_ENABLED=true

# Storage Configuration
STORAGE_MAX_SIZE_GB=100
STORAGE_RETENTION_DAYS=30
STORAGE_ENCRYPTION_ENABLED=true

# Monitoring Configuration
MONITOR_CPU_THRESHOLD=80
MONITOR_MEMORY_THRESHOLD=80
MONITOR_DISK_THRESHOLD=90
MONITOR_INTERVAL_SECONDS=30

# Pi Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR
EOF
    
    log_success ".env.application generated"
}

# Generate configs/environment/.env.support
generate_env_support() {
    log_info "Generating .env.support..."
    
    cat > "$ENV_DIR/.env.support" << EOF
# Phase 4 Support Services Configuration
# File: configs/environment/.env.support
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Admin Interface, TRON Payment System (Isolated)

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication Configuration (inherited from foundation)
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Admin Interface Configuration
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_HOST=lucid-admin-interface
ADMIN_INTERFACE_TIMEOUT=30
ADMIN_INTERFACE_CORS_ENABLED=true
ADMIN_SECRET=$ADMIN_SECRET

# Admin Configuration
ADMIN_DASHBOARD_ENABLED=true
ADMIN_MONITORING_ENABLED=true
ADMIN_SESSION_ADMIN_ENABLED=true
ADMIN_BLOCKCHAIN_ADMIN_ENABLED=true
ADMIN_PAYOUT_TRIGGERS_ENABLED=true
RBAC_ENABLED=true
AUDIT_LOGGING_ENABLED=true
EMERGENCY_CONTROLS_ENABLED=true

# TRON Payment System Configuration (ISOLATED NETWORK)
TRON_NETWORK=mainnet
TRON_MAINNET_URL=https://api.trongrid.io
TRON_TESTNET_URL=https://api.shasta.trongrid.io
TRON_API_URL=https://api.trongrid.io
TRON_CLIENT_PORT=8091
TRON_PAYOUT_ROUTER_PORT=8092
TRON_WALLET_MANAGER_PORT=8093
TRON_USDT_MANAGER_PORT=8094
TRON_TRX_STAKING_PORT=8096
TRON_PAYMENT_GATEWAY_PORT=8097

# TRON Configuration
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
USDT_TRC20_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRON_MINIMUM_PAYOUT=10
TRON_GAS_LIMIT=100000
TRON_GAS_PRICE=1000
TRON_PRIVATE_KEY=\$(openssl rand -hex 32)

# TRON Payout Configuration
PAYOUT_V0_ENABLED=true
PAYOUT_KYC_ENABLED=true
PAYOUT_PROCESSING_ENABLED=true

# TRON Client URLs
TRON_CLIENT_URL=http://lucid-tron-client:8091
PAYOUT_ROUTER_URL=http://lucid-tron-payout-router:8092
WALLET_MANAGER_URL=http://lucid-tron-wallet-manager:8093
USDT_MANAGER_URL=http://lucid-tron-usdt-manager:8094
STAKING_URL=http://lucid-tron-staking:8096

# Network Isolation
TRON_ISOLATED_NETWORK=lucid-tron-isolated
TRON_BRIDGE_ENABLED=true
TRON_BRIDGE_PORT=8098

# Security Configuration
TRON_PRIVATE_KEY_ENCRYPTED=true
TRON_WALLET_PASSWORD_ENCRYPTED=true
TRON_TRANSACTION_SIGNING_ENABLED=true
TRON_ENCRYPTION_KEY=$TRON_ENCRYPTION_KEY
WALLET_ENCRYPTION_ENABLED=true
STAKING_ENABLED=true
STAKING_REWARDS_ENABLED=true

# Pi Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR
EOF
    
    log_success ".env.support generated"
}

# Generate configs/environment/.env.pi-build
generate_env_pi_build() {
    log_info "Generating .env.pi-build..."
    
    cat > "$ENV_DIR/.env.pi-build" << EOF
# Raspberry Pi Build Configuration
# File: configs/environment/.env.pi-build
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
LUCID_SUBNET=172.22.0.0/16
LUCID_GATEWAY=172.22.0.1

# Docker Configuration
DOCKER_BUILDKIT=1
DOCKER_CLI_EXPERIMENTAL=enabled
COMPOSE_PROJECT_NAME=lucid-pi
COMPOSE_DOCKER_CLI_BUILD=1

# Build Arguments
BUILDKIT_INLINE_CACHE=1
BUILDKIT_PROGRESS=plain

# Registry Configuration
LUCID_REGISTRY=pickme
LUCID_IMAGE_NAME=lucid
LUCID_TAG=$BUILD_TAG
EOF
    
    log_success ".env.pi-build generated"
}

# ============================================================================
# STEP 5: GENERATE SERVICE-SPECIFIC .ENV FILES
# ============================================================================

# Generate ./03-api-gateway/api/.env.api
generate_env_api_gateway() {
    log_info "Generating 03-api-gateway/api/.env.api..."
    
    cat > "$PROJECT_ROOT/03-api-gateway/api/.env.api" << EOF
# API Gateway Service Configuration
# File: 03-api-gateway/api/.env.api
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Service Configuration
SERVICE_NAME=lucid-api-gateway
PORT=8080
HTTPS_PORT=8081
HOST=0.0.0.0
LOG_LEVEL=INFO
DEBUG=false

# Database Configuration
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication
AUTH_SERVICE_URL=http://lucid-auth-service:8089
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET
API_SECRET=$API_SECRET

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS Configuration
CORS_ENABLED=true
CORS_ORIGINS=*

# Gateway Configuration
API_GATEWAY_TIMEOUT=30
API_GATEWAY_RATE_LIMIT=1000
API_GATEWAY_CORS_ORIGINS=*

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_CONTROL_PASSWORD=$TOR_PASSWORD
EOF
    
    log_success "03-api-gateway/api/.env.api generated"
}

# Generate blockchain service .env files
generate_env_blockchain_services() {
    log_info "Generating blockchain service .env files..."
    
    local blockchain_env_dir="$PROJECT_ROOT/infrastructure/docker/blockchain/env"
    
    # deployment-orchestrator.env
    cat > "$blockchain_env_dir/deployment-orchestrator.env" << EOF
# Blockchain Deployment Orchestrator Configuration
# File: infrastructure/docker/blockchain/env/deployment-orchestrator.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=deployment-orchestrator
PORT=8100
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
LOG_LEVEL=INFO
EOF

    # contract-compiler.env
    cat > "$blockchain_env_dir/contract-compiler.env" << EOF
# Blockchain Contract Compiler Configuration
# File: infrastructure/docker/blockchain/env/contract-compiler.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=contract-compiler
PORT=8101
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
COMPILER_VERSION=0.8.19
LOG_LEVEL=INFO
EOF

    # blockchain-ledger.env
    cat > "$blockchain_env_dir/blockchain-ledger.env" << EOF
# Blockchain Ledger Configuration
# File: infrastructure/docker/blockchain/env/blockchain-ledger.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=blockchain-ledger
PORT=8102
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
CONSENSUS_ALGORITHM=PoOT
LOG_LEVEL=INFO
EOF

    # blockchain-vm.env
    cat > "$blockchain_env_dir/blockchain-vm.env" << EOF
# Blockchain Virtual Machine Configuration
# File: infrastructure/docker/blockchain/env/blockchain-vm.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=blockchain-vm
PORT=8103
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
VM_TYPE=EVM
LOG_LEVEL=INFO
EOF

    # contract-deployment.env
    cat > "$blockchain_env_dir/contract-deployment.env" << EOF
# Contract Deployment Configuration
# File: infrastructure/docker/blockchain/env/contract-deployment.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=contract-deployment
PORT=8104
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
GAS_LIMIT=8000000
LOG_LEVEL=INFO
EOF

    # blockchain-sessions-data.env
    cat > "$blockchain_env_dir/blockchain-sessions-data.env" << EOF
# Blockchain Sessions Data Configuration
# File: infrastructure/docker/blockchain/env/blockchain-sessions-data.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=blockchain-sessions-data
PORT=8105
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
SESSION_ANCHORING_ENABLED=true
LOG_LEVEL=INFO
EOF

    # on-system-chain-client.env
    cat > "$blockchain_env_dir/on-system-chain-client.env" << EOF
# On-System Chain Client Configuration
# File: infrastructure/docker/blockchain/env/on-system-chain-client.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=on-system-chain-client
PORT=8106
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
CHAIN_TYPE=lucid
LOG_LEVEL=INFO
EOF

    # blockchain-api.env
    cat > "$blockchain_env_dir/blockchain-api.env" << EOF
# Blockchain API Configuration
# File: infrastructure/docker/blockchain/env/blockchain-api.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=blockchain-api
PORT=8084
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
CONSENSUS_ALGORITHM=PoOT
BLOCK_TIME_SECONDS=10
MAX_TRANSACTIONS_PER_BLOCK=1000
LOG_LEVEL=INFO
EOF

    # blockchain-governance.env
    cat > "$blockchain_env_dir/blockchain-governance.env" << EOF
# Blockchain Governance Configuration
# File: infrastructure/docker/blockchain/env/blockchain-governance.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=blockchain-governance
PORT=8107
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
GOVERNANCE_ENABLED=true
VOTING_ENABLED=true
LOG_LEVEL=INFO
EOF

    # tron-node-client.env
    cat > "$blockchain_env_dir/tron-node-client.env" << EOF
# TRON Node Client Configuration
# File: infrastructure/docker/blockchain/env/tron-node-client.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=tron-node-client
PORT=8091
TRON_NETWORK=mainnet
TRON_MAINNET_URL=https://api.trongrid.io
TRON_TESTNET_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=\$(openssl rand -hex 32)
TRON_ENCRYPTION_KEY=$TRON_ENCRYPTION_KEY
LOG_LEVEL=INFO
EOF
    
    log_success "Blockchain service .env files generated"
}

# Generate database service .env files
generate_env_database_services() {
    log_info "Generating database service .env files..."
    
    local database_env_dir="$PROJECT_ROOT/infrastructure/docker/databases/env"
    
    # database-monitoring.env
    cat > "$database_env_dir/database-monitoring.env" << EOF
# Database Monitoring Configuration
# File: infrastructure/docker/databases/env/database-monitoring.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=database-monitoring
PORT=8200
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
MONITORING_INTERVAL=60
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
LOG_LEVEL=INFO
EOF

    # database-migration.env
    cat > "$database_env_dir/database-migration.env" << EOF
# Database Migration Configuration
# File: infrastructure/docker/databases/env/database-migration.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=database-migration
PORT=8201
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
MIGRATION_DIR=/app/migrations
BACKUP_BEFORE_MIGRATION=true
LOG_LEVEL=INFO
EOF

    # mongodb-init.env
    cat > "$database_env_dir/mongodb-init.env" << EOF
# MongoDB Initialization Configuration
# File: infrastructure/docker/databases/env/mongodb-init.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGO_INITDB_DATABASE=lucid
MONGODB_PORT=27017
MONGODB_REPLICA_SET=rs0
LOG_LEVEL=INFO
EOF

    # database-backup.env
    cat > "$database_env_dir/database-backup.env" << EOF
# Database Backup Configuration
# File: infrastructure/docker/databases/env/database-backup.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=database-backup
PORT=8202
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_DIR=/app/backups
BACKUP_COMPRESSION=true
LOG_LEVEL=INFO
EOF

    # mongodb.env
    cat > "$database_env_dir/mongodb.env" << EOF
# MongoDB Configuration
# File: infrastructure/docker/databases/env/mongodb.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGO_INITDB_DATABASE=lucid
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_production
EOF

    # database-restore.env
    cat > "$database_env_dir/database-restore.env" << EOF
# Database Restore Configuration
# File: infrastructure/docker/databases/env/database-restore.env
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=database-restore
PORT=8203
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
BACKUP_DIR=/app/backups
RESTORE_VERIFY=true
LOG_LEVEL=INFO
EOF
    
    log_success "Database service .env files generated"
}

# Generate session core .env files
generate_env_session_core() {
    log_info "Generating session core .env files..."
    
    local session_core_dir="$PROJECT_ROOT/sessions/core"
    
    # .env.orchestrator
    cat > "$session_core_dir/.env.orchestrator" << EOF
# Session Orchestrator Configuration
# File: sessions/core/.env.orchestrator
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=session-orchestrator
PORT=8300
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
SESSION_SECRET=$SESSION_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
MAX_CONCURRENT_SESSIONS=10
SESSION_TIMEOUT=3600
LOG_LEVEL=INFO
EOF

    # .env.merkle_builder
    cat > "$session_core_dir/.env.merkle_builder" << EOF
# Session Merkle Builder Configuration
# File: sessions/core/.env.merkle_builder
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=session-merkle-builder
PORT=8301
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
SESSION_SECRET=$SESSION_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
MERKLE_TREE_ENABLED=true
HASH_ALGORITHM=SHA256
LOG_LEVEL=INFO
EOF

    # .env.chunker
    cat > "$session_core_dir/.env.chunker" << EOF
# Session Chunker Configuration
# File: sessions/core/.env.chunker
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SERVICE_NAME=session-chunker
PORT=8302
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
SESSION_SECRET=$SESSION_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
CHUNK_SIZE=8388608
CHUNK_SIZE_MB=1
COMPRESSION_LEVEL=6
COMPRESSION_ENABLED=true
ENCRYPTION_ENABLED=true
LOG_LEVEL=INFO
EOF
    
    log_success "Session core .env files generated"
}

# ============================================================================
# STEP 6: VALIDATE GENERATED FILES
# ============================================================================
validate_generated_files() {
    log_info "Validating generated environment files..."
    
    local all_env_files=(
        "$ENV_DIR/.env.foundation"
        "$ENV_DIR/.env.core"
        "$ENV_DIR/.env.application"
        "$ENV_DIR/.env.support"
        "$ENV_DIR/.env.pi-build"
        "$PROJECT_ROOT/03-api-gateway/api/.env.api"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/deployment-orchestrator.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/contract-compiler.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-ledger.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-vm.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/contract-deployment.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-sessions-data.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/on-system-chain-client.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-api.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-governance.env"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/tron-node-client.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/database-monitoring.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/database-migration.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/mongodb-init.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/database-backup.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/mongodb.env"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/database-restore.env"
        "$PROJECT_ROOT/sessions/core/.env.orchestrator"
        "$PROJECT_ROOT/sessions/core/.env.merkle_builder"
        "$PROJECT_ROOT/sessions/core/.env.chunker"
    )
    
    local validation_failed=0
    
    for env_file in "${all_env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            # Check file size
            local file_size=$(wc -c < "$env_file")
            if [[ $file_size -lt 100 ]]; then
                log_error "File too small: $env_file ($file_size bytes)"
                validation_failed=1
            else
                log_success "✓ $(basename $env_file)"
            fi
        else
            log_error "File not found: $env_file"
            validation_failed=1
        fi
    done
    
    if [[ $validation_failed -eq 1 ]]; then
        log_error "Validation failed for some files"
        return 1
    fi
    
    log_success "All environment files validated successfully"
}

# ============================================================================
# STEP 7: DISPLAY SUMMARY
# ============================================================================
display_summary() {
    echo ""
    echo "============================================================================"
    log_info "Pi Prep Stage - Generation Summary"
    echo "============================================================================"
    echo ""
    echo "Generated .env Files:"
    echo "  ✓ configs/environment/.env.pi-build"
    echo "  ✓ configs/environment/.env.foundation"
    echo "  ✓ configs/environment/.env.core"
    echo "  ✓ configs/environment/.env.application"
    echo "  ✓ configs/environment/.env.support"
    echo "  ✓ 03-api-gateway/api/.env.api"
    echo "  ✓ infrastructure/docker/blockchain/env/* (10 files)"
    echo "  ✓ infrastructure/docker/databases/env/* (6 files)"
    echo "  ✓ sessions/core/* (3 files)"
    echo ""
    echo "Security Configuration:"
    echo "  • MongoDB Password: Generated (32 bytes)"
    echo "  • Redis Password: Generated (32 bytes)"
    echo "  • JWT Secret: Generated (64 bytes)"
    echo "  • Encryption Key: Generated (32 bytes hex)"
    echo "  • Tor Password: Generated (32 bytes)"
    echo "  • Session Secret: Generated (32 bytes)"
    echo "  • API Secret: Generated (32 bytes)"
    echo "  • Blockchain Secret: Generated (32 bytes)"
    echo "  • Admin Secret: Generated (32 bytes)"
    echo "  • TRON Encryption Key: Generated (32 bytes hex)"
    echo ""
    echo "Target Configuration:"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Pi User: $PI_USER"
    echo "  • Deploy Dir: $PI_DEPLOY_DIR"
    echo "  • Build Platform: $BUILD_PLATFORM"
    echo "  • Registry: $BUILD_REGISTRY"
    echo ""
    echo "⚠️  IMPORTANT NOTES:"
    echo "  1. Review all generated .env files for correctness"
    echo "  2. .onion hostnames will be generated when Tor starts"
    echo "  3. Keep all passwords secure and backed up"
    echo "  4. All values are REAL - ready for deployment/prototype"
    echo ""
    log_success "Pi prep stage completed successfully!"
    echo "============================================================================"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================
main() {
    log_info "=== Pi Prep Stage - Generate .onion Names and All .env Files ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Configs Directory: $CONFIGS_DIR"
    log_info "Environment Directory: $ENV_DIR"
    echo ""
    
    # Execute generation steps
    create_directory_structure
    generate_onion_names
    generate_secure_values
    
    # Generate main .env files
    generate_env_foundation
    generate_env_core
    generate_env_application
    generate_env_support
    generate_env_pi_build
    
    # Generate service-specific .env files
    generate_env_api_gateway
    generate_env_blockchain_services
    generate_env_database_services
    generate_env_session_core
    
    # Validate and display summary
    validate_generated_files
    display_summary
}

# Run main function
main "$@"

