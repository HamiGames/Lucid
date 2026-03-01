#!/bin/bash
################################################################################
# Pi ENV Real Value Generator - NO PLACEHOLDERS
# File: scripts/build/pi-generate-real-env-values.sh
# Target: /mnt/myssd/Lucid/Lucid on Raspberry Pi
# Purpose: Generate REAL values for ALL .env files - ZERO placeholders
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Project root
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# GENERATE ALL REAL VALUES UPFRONT
# ============================================================================
log_info "Generating ALL real cryptographic values..."

# Generate passwords (32 bytes base64)
MONGODB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
TOR_PASSWORD=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
SESSION_SECRET=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
API_SECRET=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
BLOCKCHAIN_SECRET=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')
ADMIN_SECRET=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/')

# Generate JWT secrets (64 bytes base64)
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n' | tr -d '/')
JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n' | tr -d '/')

# Generate encryption keys (32 bytes hex)
ENCRYPTION_KEY=$(openssl rand -hex 32)
TRON_ENCRYPTION_KEY=$(openssl rand -hex 32)

# Generate TRON private keys (32 bytes hex)
TRON_PRIVATE_KEY=$(openssl rand -hex 32)
TRON_MASTER_PRIVATE_KEY=$(openssl rand -hex 32)

# Build info
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "$(openssl rand -hex 4)")

log_success "All cryptographic values generated"

# ============================================================================
# CREATE DIRECTORY STRUCTURE
# ============================================================================
log_info "Creating directory structure..."

mkdir -p "$PROJECT_ROOT/configs/environment"
mkdir -p "$PROJECT_ROOT/03-api-gateway/api"
mkdir -p "$PROJECT_ROOT/infrastructure/docker/blockchain/env"
mkdir -p "$PROJECT_ROOT/infrastructure/docker/databases/env"
mkdir -p "$PROJECT_ROOT/sessions/core"

log_success "Directory structure created"

# ============================================================================
# GENERATE env.pi-build (REPLACE EXISTING)
# ============================================================================
log_info "Generating configs/environment/env.pi-build with REAL values..."

cat > "$PROJECT_ROOT/configs/environment/env.pi-build" << EOF
# Lucid Pi Build Environment Configuration
# Target: Raspberry Pi (192.168.0.75)
# Generated: $BUILD_DATE
# ALL REAL VALUES - ZERO PLACEHOLDERS

# ============================================================================
# PI TARGET CONFIGURATION
# ============================================================================
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/mnt/myssd/Lucid/Lucid
PI_ARCHITECTURE=linux/arm64
PI_PLATFORM=linux/arm64

# ============================================================================
# BUILD HOST CONFIGURATION (Windows 11)
# ============================================================================
BUILD_HOST=windows11
BUILD_ARCHITECTURE=linux/arm64
DOCKER_BUILDX_ENABLED=true
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# ============================================================================
# DOCKER REGISTRY CONFIGURATION
# ============================================================================
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=pickme
DOCKER_IMAGE_PREFIX=lucid
DOCKER_TAG_SUFFIX=arm64

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================
LUCID_NETWORK=lucid-pi-network
LUCID_NETWORK_SUBNET=172.20.0.0/16
LUCID_NETWORK_GATEWAY=172.20.0.1
LUCID_TRON_ISOLATED_NETWORK=lucid-tron-isolated
LUCID_TRON_ISOLATED_SUBNET=172.21.0.0/16

# ============================================================================
# SERVICE PORTS (Fixed Assignments)
# ============================================================================
API_GATEWAY_PORT=8080
BLOCKCHAIN_CORE_PORT=8084
AUTH_SERVICE_PORT=8089
SESSION_API_PORT=8087
NODE_MANAGEMENT_PORT=8095
ADMIN_INTERFACE_PORT=8083
TRON_PAYMENT_PORT=8091

# ============================================================================
# DATABASE CONFIGURATION - REAL VALUES
# ============================================================================
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@192.168.0.75:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://:$REDIS_PASSWORD@192.168.0.75:6379/0
ELASTICSEARCH_URL=http://192.168.0.75:9200

# ============================================================================
# SECURITY - REAL GENERATED VALUES
# ============================================================================
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
TOR_CONTROL_PASSWORD=$TOR_PASSWORD
TOR_PASSWORD=$TOR_PASSWORD

# ============================================================================
# TRON CONFIGURATION - REAL VALUES
# ============================================================================
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRON_PRIVATE_KEY=$TRON_PRIVATE_KEY
TRON_ENCRYPTION_KEY=$TRON_ENCRYPTION_KEY

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================
BUILD_PHASE=all
BUILD_PARALLEL=true
BUILD_DISTROLESS=true
BUILD_MULTI_STAGE=true
BUILD_DATE=$BUILD_DATE
GIT_COMMIT=$GIT_COMMIT

# ============================================================================
# DEPLOYMENT CONFIGURATION
# ============================================================================
DEPLOY_METHOD=ssh
DEPLOY_SSH_KEY_PATH=~/.ssh/id_rsa
DEPLOY_TIMEOUT=300
DEPLOY_RETRIES=3

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================
VALIDATE_HEALTH_CHECKS=true
VALIDATE_SERVICE_DEPENDENCIES=true
VALIDATE_NETWORK_ISOLATION=true
VALIDATE_TRON_ISOLATION=true
EOF

log_success "env.pi-build created with REAL values"

# ============================================================================
# GENERATE env.foundation
# ============================================================================
log_info "Generating configs/environment/env.foundation..."

cat > "$PROJECT_ROOT/configs/environment/env.foundation" << EOF
# Phase 1 Foundation Services Configuration
# Generated: $BUILD_DATE
# ALL REAL VALUES - NO PLACEHOLDERS

# Database Configuration - REAL PASSWORDS
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

# Authentication - REAL SECRETS
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ENCRYPTION_KEY=$ENCRYPTION_KEY

# Security - REAL PASSWORDS
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

# Health Checks
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/foundation.log
EOF

log_success "env.foundation created"

# ============================================================================
# GENERATE env.core
# ============================================================================
log_info "Generating configs/environment/env.core..."

cat > "$PROJECT_ROOT/configs/environment/env.core" << EOF
# Phase 2 Core Services Configuration
# Generated: $BUILD_DATE
# ALL REAL VALUES

# Database Configuration
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200

# Authentication
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# API Gateway
API_GATEWAY_PORT=8080
API_GATEWAY_HOST=lucid-api-gateway
API_GATEWAY_TIMEOUT=30
API_GATEWAY_RATE_LIMIT=1000
API_GATEWAY_CORS_ORIGINS=*
API_SECRET=$API_SECRET

# Service Mesh
SERVICE_MESH_CONTROLLER_PORT=8500
SERVICE_MESH_CONSUL_PORT=8500
SERVICE_MESH_ENVOY_PORT=8088
SERVICE_MESH_MTLS_ENABLED=true

# Blockchain Core
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_SESSION_ANCHORING_PORT=8085
BLOCKCHAIN_BLOCK_MANAGER_PORT=8086
BLOCKCHAIN_DATA_CHAIN_PORT=8087
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET

# Consensus
CONSENSUS_ALGORITHM=PoOT
BLOCK_INTERVAL=10
BLOCK_TIME_SECONDS=10
BLOCK_SIZE_LIMIT=1048576
TRANSACTION_LIMIT=1000
MAX_TRANSACTIONS_PER_BLOCK=1000

# Network
NETWORK_PROTOCOL_VERSION=1.0.0
NETWORK_PEER_DISCOVERY=true
NETWORK_PEER_LIMIT=100

# Performance
CACHE_SIZE=1073741824
CACHE_TTL=3600
CONNECTION_POOL_SIZE=100
EOF

log_success "env.core created"

# ============================================================================
# GENERATE env.application
# ============================================================================
log_info "Generating configs/environment/env.application..."

cat > "$PROJECT_ROOT/configs/environment/env.application" << EOF
# Phase 3 Application Services Configuration
# Generated: $BUILD_DATE

# Database
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Session Management
SESSION_PIPELINE_PORT=8083
SESSION_RECORDER_PORT=8084
SESSION_CHUNK_PROCESSOR_PORT=8085
SESSION_STORAGE_PORT=8086
SESSION_API_PORT=8087
SESSION_SECRET=$SESSION_SECRET
SESSION_CHUNK_SIZE=10485760
SESSION_COMPRESSION_LEVEL=6
SESSION_ENCRYPTION_ENABLED=true
SESSION_MERKLE_TREE_ENABLED=true

# RDP Services
RDP_SERVER_MANAGER_PORT=8081
RDP_XRDP_INTEGRATION_PORT=3389
RDP_SESSION_CONTROLLER_PORT=8082
RDP_RESOURCE_MONITOR_PORT=8090
RDP_MAX_SESSIONS=10
RDP_SESSION_TIMEOUT=3600

# Node Management
NODE_MANAGEMENT_PORT=8095
NODE_POOL_MAX_SIZE=100
PAYOUT_THRESHOLD_USDT=10
POOT_ENABLED=true
EOF

log_success "env.application created"

# ============================================================================
# GENERATE env.support
# ============================================================================
log_info "Generating configs/environment/env.support..."

cat > "$PROJECT_ROOT/configs/environment/env.support" << EOF
# Phase 4 Support Services Configuration
# Generated: $BUILD_DATE

# Database
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Admin Interface
ADMIN_INTERFACE_PORT=8083
ADMIN_SECRET=$ADMIN_SECRET
RBAC_ENABLED=true
AUDIT_LOGGING_ENABLED=true

# TRON Payment System (ISOLATED)
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
TRON_CLIENT_PORT=8091
TRON_PAYOUT_ROUTER_PORT=8092
TRON_WALLET_MANAGER_PORT=8093
TRON_USDT_MANAGER_PORT=8094
TRON_TRX_STAKING_PORT=8096
TRON_PAYMENT_GATEWAY_PORT=8097
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRON_MINIMUM_PAYOUT=10
TRON_PRIVATE_KEY=$TRON_PRIVATE_KEY
TRON_ENCRYPTION_KEY=$TRON_ENCRYPTION_KEY
EOF

log_success "env.support created"

# ============================================================================
# GENERATE 03-api-gateway/api/.env.api
# ============================================================================
log_info "Generating 03-api-gateway/api/.env.api..."

cat > "$PROJECT_ROOT/03-api-gateway/api/.env.api" << EOF
# API Gateway Configuration
# Generated: $BUILD_DATE

SERVICE_NAME=lucid-api-gateway
PORT=8080
HTTPS_PORT=8081
HOST=0.0.0.0
LOG_LEVEL=INFO
DEBUG=false

# Database
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@lucid-redis:6379/0

# Authentication
AUTH_SERVICE_URL=http://lucid-auth-service:8089
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
API_SECRET=$API_SECRET

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS
CORS_ENABLED=true
CORS_ORIGINS=*

# Tor
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_CONTROL_PASSWORD=$TOR_PASSWORD
EOF

log_success "03-api-gateway/api/.env.api created"

# ============================================================================
# GENERATE BLOCKCHAIN ENV FILES
# ============================================================================
log_info "Generating blockchain env files..."

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/deployment-orchestrator.env" << EOF
SERVICE_NAME=deployment-orchestrator
PORT=8100
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/contract-compiler.env" << EOF
SERVICE_NAME=contract-compiler
PORT=8101
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
COMPILER_VERSION=0.8.19
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-ledger.env" << EOF
SERVICE_NAME=blockchain-ledger
PORT=8102
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
CONSENSUS_ALGORITHM=PoOT
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-vm.env" << EOF
SERVICE_NAME=blockchain-vm
PORT=8103
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
VM_TYPE=EVM
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/contract-deployment.env" << EOF
SERVICE_NAME=contract-deployment
PORT=8104
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
GAS_LIMIT=8000000
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-sessions-data.env" << EOF
SERVICE_NAME=blockchain-sessions-data
PORT=8105
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
SESSION_ANCHORING_ENABLED=true
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/on-system-chain-client.env" << EOF
SERVICE_NAME=on-system-chain-client
PORT=8106
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
CHAIN_TYPE=lucid
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-api.env" << EOF
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

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/blockchain-governance.env" << EOF
SERVICE_NAME=blockchain-governance
PORT=8107
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
GOVERNANCE_ENABLED=true
VOTING_ENABLED=true
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/blockchain/env/tron-node-client.env" << EOF
SERVICE_NAME=tron-node-client
PORT=8091
TRON_NETWORK=mainnet
TRON_MAINNET_URL=https://api.trongrid.io
TRON_TESTNET_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=$TRON_PRIVATE_KEY
TRON_ENCRYPTION_KEY=$TRON_ENCRYPTION_KEY
LOG_LEVEL=INFO
EOF

log_success "Blockchain env files created (10 files)"

# ============================================================================
# GENERATE DATABASE ENV FILES
# ============================================================================
log_info "Generating database env files..."

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/database-monitoring.env" << EOF
SERVICE_NAME=database-monitoring
PORT=8200
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
MONITORING_INTERVAL=60
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/database-migration.env" << EOF
SERVICE_NAME=database-migration
PORT=8201
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
MIGRATION_DIR=/app/migrations
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/mongodb-init.env" << EOF
MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGO_INITDB_DATABASE=lucid
MONGODB_PORT=27017
MONGODB_REPLICA_SET=rs0
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/database-backup.env" << EOF
SERVICE_NAME=database-backup
PORT=8202
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
LOG_LEVEL=INFO
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/mongodb.env" << EOF
MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=$MONGODB_PASSWORD
MONGO_INITDB_DATABASE=lucid
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_production
EOF

cat > "$PROJECT_ROOT/infrastructure/docker/databases/env/database-restore.env" << EOF
SERVICE_NAME=database-restore
PORT=8203
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
BACKUP_DIR=/app/backups
LOG_LEVEL=INFO
EOF

log_success "Database env files created (6 files)"

# ============================================================================
# GENERATE SESSION CORE ENV FILES
# ============================================================================
log_info "Generating session core env files..."

cat > "$PROJECT_ROOT/sessions/core/.env.orchestrator" << EOF
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

cat > "$PROJECT_ROOT/sessions/core/.env.merkle_builder" << EOF
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

cat > "$PROJECT_ROOT/sessions/core/.env.chunker" << EOF
SERVICE_NAME=session-chunker
PORT=8302
MONGODB_URI=mongodb://lucid:$MONGODB_PASSWORD@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_URI=redis://:$REDIS_PASSWORD@lucid-redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD
SESSION_SECRET=$SESSION_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
CHUNK_SIZE=10485760
COMPRESSION_LEVEL=6
COMPRESSION_ENABLED=true
ENCRYPTION_ENABLED=true
LOG_LEVEL=INFO
EOF

log_success "Session core env files created (3 files)"

# ============================================================================
# VALIDATION
# ============================================================================
log_info "Validating generated files..."

total_files=0
valid_files=0

env_files=(
    "$PROJECT_ROOT/configs/environment/env.pi-build"
    "$PROJECT_ROOT/configs/environment/env.foundation"
    "$PROJECT_ROOT/configs/environment/env.core"
    "$PROJECT_ROOT/configs/environment/env.application"
    "$PROJECT_ROOT/configs/environment/env.support"
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

for env_file in "${env_files[@]}"; do
    total_files=$((total_files + 1))
    if [[ -f "$env_file" ]]; then
        # Check for placeholders
        if grep -q 'PLACEHOLDER\|${' "$env_file"; then
            log_error "PLACEHOLDERS FOUND in $(basename $env_file)"
        else
            log_success "✓ $(basename $env_file) - NO PLACEHOLDERS"
            valid_files=$((valid_files + 1))
        fi
    else
        log_error "Missing: $env_file"
    fi
done

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "============================================================================"
log_info "ENV Generation Complete - ALL REAL VALUES"
echo "============================================================================"
echo ""
echo "Files Generated: $valid_files / $total_files"
echo ""
echo "Generated Secrets:"
echo "  • MongoDB Password: $(echo $MONGODB_PASSWORD | cut -c1-8)... (32 bytes)"
echo "  • Redis Password: $(echo $REDIS_PASSWORD | cut -c1-8)... (32 bytes)"
echo "  • JWT Secret: $(echo $JWT_SECRET | cut -c1-8)... (64 bytes)"
echo "  • Encryption Key: $(echo $ENCRYPTION_KEY | cut -c1-16)... (32 bytes hex)"
echo "  • TOR Password: $(echo $TOR_PASSWORD | cut -c1-8)... (32 bytes)"
echo "  • TRON Private Key: $(echo $TRON_PRIVATE_KEY | cut -c1-16)... (32 bytes hex)"
echo ""
echo "Target: Raspberry Pi 5 (192.168.0.75)"
echo "Project: /mnt/myssd/Lucid/Lucid"
echo ""
log_success "ALL ENV FILES READY FOR DEPLOYMENT - ZERO PLACEHOLDERS!"
echo "============================================================================"

