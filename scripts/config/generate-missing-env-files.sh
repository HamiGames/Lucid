#!/bin/bash
# Path: scripts/config/generate-missing-env-files.sh
# Generate ONLY Missing .env.* Files (27 total)
# Extracts ACTUAL values from source files (.env.secrets, .env.foundation, etc.)
# Queries tor-proxy container for real onion URLs
# MUST RUN ON PI CONSOLE

set -euo pipefail

PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# LOAD ACTUAL VALUES FROM SOURCE FILES
# =============================================================================

load_source_files() {
    log_info "Loading actual values from source files..."
    
    # Source files to load actual values
    [[ -f "$ENV_DIR/.env.foundation" ]] && source "$ENV_DIR/.env.foundation"
    [[ -f "$ENV_DIR/.env.core" ]] && source "$ENV_DIR/.env.core"
    [[ -f "$ENV_DIR/.env.application" ]] && source "$ENV_DIR/.env.application"
    [[ -f "$ENV_DIR/.env.support" ]] && source "$ENV_DIR/.env.support"
    [[ -f "$ENV_DIR/.env.gui" ]] && source "$ENV_DIR/.env.gui"
    [[ -f "$ENV_DIR/.env.secrets" ]] && source "$ENV_DIR/.env.secrets"
    
    # Verify critical values loaded
    if [[ -z "${MONGODB_PASSWORD:-}" ]]; then
        log_error "MONGODB_PASSWORD not found in .env.foundation"
        exit 1
    fi
    if [[ -z "${REDIS_PASSWORD:-}" ]]; then
        log_error "REDIS_PASSWORD not found in .env.foundation"
        exit 1
    fi
    
    log_success "Source files loaded - actual values ready"
}

# Query tor-proxy container for onion addresses
get_tor_onion_addresses() {
    local container_name="tor-proxy"
    local onion_file="/run/lucid/onion/multi-onion.env"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}\$"; then
        log_warning "tor-proxy container not running, skipping onion address query"
        return 1
    fi
    
    if docker exec "$container_name" test -f "$onion_file" 2>/dev/null; then
        docker exec "$container_name" cat "$onion_file" 2>/dev/null | while IFS='=' read -r key value; do
            [[ -n "$key" && -n "$value" ]] && export "$key=$value"
        done
        return 0
    fi
    
    return 1
}

# =============================================================================
# VALIDATION
# =============================================================================

check_phase_files() {
    local missing=()
    for file in ".env.foundation" ".env.core" ".env.application" ".env.support" ".env.secrets"; do
        [[ ! -f "$ENV_DIR/$file" ]] && missing+=("$file")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Required files missing: ${missing[*]}"
        exit 1
    fi
    log_success "All required source files found"
}

# =============================================================================
# FILE GENERATION - All 27 missing files with ACTUAL values
# =============================================================================

generate_tor_proxy_env() {
    local file="$ENV_DIR/.env.tor-proxy"
    [[ -f "$file" ]] && { log_info "Skipping .env.tor-proxy (exists)"; return 0; }
    
    log_info "Creating .env.tor-proxy..."
    cat > "$file" << EOF
# Tor Proxy Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tor-proxy
SERVICE_PORT=9050
SERVICE_HOST=0.0.0.0

# Tor Configuration
TOR_CONTROL_PORT=9051
TOR_SOCKS_PORT=9050
TOR_CONTROL_PASSWORD=$TOR_PASSWORD
TOR_HIDDEN_SERVICE_DIR=/var/lib/tor/hidden_service

# Network Configuration
NETWORK_NAME=lucid-pi-network
NETWORK_SUBNET=172.20.0.0/16

# Security Configuration
READ_ONLY_FILESYSTEM=true
NO_NEW_PRIVILEGES=true
USER=65532:65532

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tor-proxy"
}

generate_server_tools_env() {
    local file="$ENV_DIR/.env.server-tools"
    [[ -f "$file" ]] && { log_info "Skipping .env.server-tools (exists)"; return 0; }
    
    log_info "Creating .env.server-tools..."
    cat > "$file" << EOF
# Server Tools Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=server-tools
SERVICE_PORT=8086
SERVICE_HOST=0.0.0.0

# Network Configuration
NETWORK_NAME=lucid-pi-network

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.server-tools"
}

generate_api_gateway_env() {
    local file="$ENV_DIR/.env.api-gateway"
    [[ -f "$file" ]] && { log_info "Skipping .env.api-gateway (exists)"; return 0; }
    
    log_info "Creating .env.api-gateway..."
    
    # Get onion address from tor-proxy if available
    get_tor_onion_addresses
    local api_onion="${API_GATEWAY_ONION:-}"
    
    cat > "$file" << EOF
# API Gateway Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=api-gateway
SERVICE_PORT=8080
SERVICE_HOST=172.20.0.10
SERVICE_URL=http://172.20.0.10:8080
${api_onion:+API_GATEWAY_ONION=$api_onion}

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60

# CORS Configuration
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.api-gateway"
}

generate_api_server_env() {
    local file="$ENV_DIR/.env.api-server"
    [[ -f "$file" ]] && { log_info "Skipping .env.api-server (exists)"; return 0; }
    
    log_info "Creating .env.api-server..."
    cat > "$file" << EOF
# API Server Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=api-server
SERVICE_PORT=8081
SERVICE_HOST=172.20.0.11
SERVICE_URL=http://172.20.0.11:8081

# API Gateway Integration
API_GATEWAY_URL=http://172.20.0.10:8080

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.api-server"
}

generate_openapi_gateway_env() {
    local file="$ENV_DIR/.env.openapi-gateway"
    [[ -f "$file" ]] && { log_info "Skipping .env.openapi-gateway (exists)"; return 0; }
    
    log_info "Creating .env.openapi-gateway..."
    
    # Get OpenAPI values from open-api system if available
    local openapi_host="${OPENAPI_GATEWAY_HOST:-172.20.0.12}"
    local openapi_port="${OPENAPI_GATEWAY_PORT:-8082}"
    
    cat > "$file" << EOF
# OpenAPI Gateway Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=openapi-gateway
SERVICE_PORT=$openapi_port
SERVICE_HOST=$openapi_host
SERVICE_URL=http://$openapi_host:$openapi_port

# OpenAPI Configuration
OPENAPI_SPEC_PATH=/app/openapi.yaml
SWAGGER_UI_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.openapi-gateway"
}

generate_openapi_server_env() {
    local file="$ENV_DIR/.env.openapi-server"
    [[ -f "$file" ]] && { log_info "Skipping .env.openapi-server (exists)"; return 0; }
    
    log_info "Creating .env.openapi-server..."
    
    # Get OpenAPI values from open-api system
    local openapi_gateway_host="${OPENAPI_GATEWAY_HOST:-172.20.0.12}"
    local openapi_server_host="${OPENAPI_SERVER_HOST:-172.20.0.13}"
    local openapi_server_port="${OPENAPI_SERVER_PORT:-8083}"
    
    cat > "$file" << EOF
# OpenAPI Server Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=openapi-server
SERVICE_PORT=$openapi_server_port
SERVICE_HOST=$openapi_server_host
SERVICE_URL=http://$openapi_server_host:$openapi_server_port

# OpenAPI Gateway Integration
OPENAPI_GATEWAY_URL=http://$openapi_gateway_host:8082

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.openapi-server"
}

generate_api_env() {
    local file="$ENV_DIR/.env.api"
    [[ -f "$file" ]] && { log_info "Skipping .env.api (exists)"; return 0; }
    
    log_info "Creating .env.api..."
    cat > "$file" << EOF
# API Service Configuration (03-api-gateway/api/)
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=api
SERVICE_PORT=8084
SERVICE_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.api"
}

# Blockchain Services (10 files)
generate_blockchain_api_env() {
    local file="$ENV_DIR/.env.blockchain-api"
    [[ -f "$file" ]] && { log_info "Skipping .env.blockchain-api (exists)"; return 0; }
    
    log_info "Creating .env.blockchain-api..."
    cat > "$file" << EOF
# Blockchain API Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=blockchain-api
SERVICE_PORT=8085
SERVICE_HOST=172.20.0.15
SERVICE_URL=http://172.20.0.15:8085

# Blockchain Configuration
BLOCKCHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-lucid-mainnet}
BLOCKCHAIN_CONSENSUS=${BLOCKCHAIN_CONSENSUS:-PoOT}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.blockchain-api"
}

generate_blockchain_governance_env() {
    local file="$ENV_DIR/.env.blockchain-governance"
    [[ -f "$file" ]] && { log_info "Skipping .env.blockchain-governance (exists)"; return 0; }
    
    log_info "Creating .env.blockchain-governance..."
    cat > "$file" << EOF
# Blockchain Governance Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=blockchain-governance
SERVICE_PORT=8086
SERVICE_HOST=172.20.0.16
SERVICE_URL=http://172.20.0.16:8086

# Blockchain Configuration
BLOCKCHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-lucid-mainnet}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.blockchain-governance"
}

generate_blockchain_sessions_data_env() {
    local file="$ENV_DIR/.env.blockchain-sessions-data"
    [[ -f "$file" ]] && { log_info "Skipping .env.blockchain-sessions-data (exists)"; return 0; }
    
    log_info "Creating .env.blockchain-sessions-data..."
    cat > "$file" << EOF
# Blockchain Sessions Data Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=blockchain-sessions-data
SERVICE_PORT=8087
SERVICE_HOST=172.20.0.17
SERVICE_URL=http://172.20.0.17:8087

# Session Configuration
SESSION_TIMEOUT=${SESSION_TIMEOUT:-1800}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.blockchain-sessions-data"
}

generate_blockchain_vm_env() {
    local file="$ENV_DIR/.env.blockchain-vm"
    [[ -f "$file" ]] && { log_info "Skipping .env.blockchain-vm (exists)"; return 0; }
    
    log_info "Creating .env.blockchain-vm..."
    cat > "$file" << EOF
# Blockchain VM Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=blockchain-vm
SERVICE_PORT=8088
SERVICE_HOST=172.20.0.18
SERVICE_URL=http://172.20.0.18:8088

# VM Configuration
VM_MEMORY_LIMIT=512M
VM_CPU_LIMIT=0.5

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.blockchain-vm"
}

generate_blockchain_ledger_env() {
    local file="$ENV_DIR/.env.blockchain-ledger"
    [[ -f "$file" ]] && { log_info "Skipping .env.blockchain-ledger (exists)"; return 0; }
    
    log_info "Creating .env.blockchain-ledger..."
    cat > "$file" << EOF
# Blockchain Ledger Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=blockchain-ledger
SERVICE_PORT=8089
SERVICE_HOST=172.20.0.19
SERVICE_URL=http://172.20.0.19:8089

# Ledger Configuration
LEDGER_STORAGE_PATH=/data/ledger
LEDGER_BACKUP_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.blockchain-ledger"
}

generate_tron_node_client_env() {
    local file="$ENV_DIR/.env.tron-node-client"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-node-client (exists)"; return 0; }
    
    log_info "Creating .env.tron-node-client..."
    cat > "$file" << EOF
# TRON Node Client Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-node-client
SERVICE_PORT=8090
SERVICE_HOST=172.20.0.20
SERVICE_URL=http://172.20.0.20:8090

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-node-client"
}

generate_contract_deployment_env() {
    local file="$ENV_DIR/.env.contract-deployment"
    [[ -f "$file" ]] && { log_info "Skipping .env.contract-deployment (exists)"; return 0; }
    
    log_info "Creating .env.contract-deployment..."
    cat > "$file" << EOF
# Contract Deployment Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=contract-deployment
SERVICE_PORT=8091
SERVICE_HOST=172.20.0.21
SERVICE_URL=http://172.20.0.21:8091

# Contract Configuration
CONTRACT_STORAGE_PATH=/data/contracts
SOLIDITY_COMPILER_VERSION=0.8.19

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.contract-deployment"
}

generate_contract_compiler_env() {
    local file="$ENV_DIR/.env.contract-compiler"
    [[ -f "$file" ]] && { log_info "Skipping .env.contract-compiler (exists)"; return 0; }
    
    log_info "Creating .env.contract-compiler..."
    cat > "$file" << EOF
# Contract Compiler Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=contract-compiler
SERVICE_PORT=8092
SERVICE_HOST=172.20.0.22
SERVICE_URL=http://172.20.0.22:8092

# Compiler Configuration
SOLIDITY_VERSION=0.8.19
OPTIMIZATION_ENABLED=true
OPTIMIZATION_RUNS=200

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.contract-compiler"
}

generate_on_system_chain_client_env() {
    local file="$ENV_DIR/.env.on-system-chain-client"
    [[ -f "$file" ]] && { log_info "Skipping .env.on-system-chain-client (exists)"; return 0; }
    
    log_info "Creating .env.on-system-chain-client..."
    cat > "$file" << EOF
# On-System Chain Client Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=on-system-chain-client
SERVICE_PORT=8093
SERVICE_HOST=172.20.0.23
SERVICE_URL=http://172.20.0.23:8093

# Chain Configuration
CHAIN_NETWORK=${BLOCKCHAIN_NETWORK:-lucid-mainnet}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.on-system-chain-client"
}

generate_deployment_orchestrator_env() {
    local file="$ENV_DIR/.env.deployment-orchestrator"
    [[ -f "$file" ]] && { log_info "Skipping .env.deployment-orchestrator (exists)"; return 0; }
    
    log_info "Creating .env.deployment-orchestrator..."
    cat > "$file" << EOF
# Deployment Orchestrator Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=deployment-orchestrator
SERVICE_PORT=8094
SERVICE_HOST=172.20.0.24
SERVICE_URL=http://172.20.0.24:8094

# Orchestration Configuration
ORCHESTRATION_MODE=production
DEPLOYMENT_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.deployment-orchestrator"
}

# Session Services (4 files)
generate_chunker_env() {
    local file="sessions/core/.env.chunker"
    [[ -f "$file" ]] && { log_info "Skipping sessions/core/.env.chunker (exists)"; return 0; }
    
    log_info "Creating sessions/core/.env.chunker..."
    mkdir -p "sessions/core"
    cat > "$file" << EOF
# Session Chunker Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=chunker
SERVICE_PORT=8095
SERVICE_HOST=172.20.0.25
SERVICE_URL=http://172.20.0.25:8095

# Chunking Configuration
CHUNK_SIZE=${SESSION_CHUNK_SIZE:-10485760}
MAX_CHUNKS_PER_SESSION=1000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created sessions/core/.env.chunker"
}

generate_merkle_builder_env() {
    local file="sessions/core/.env.merkle_builder"
    [[ -f "$file" ]] && { log_info "Skipping sessions/core/.env.merkle_builder (exists)"; return 0; }
    
    log_info "Creating sessions/core/.env.merkle_builder..."
    mkdir -p "sessions/core"
    cat > "$file" << EOF
# Merkle Builder Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=merkle_builder
SERVICE_PORT=8096
SERVICE_HOST=172.20.0.26
SERVICE_URL=http://172.20.0.26:8096

# Merkle Configuration
MERKLE_ALGORITHM=sha256
MERKLE_TREE_DEPTH=20

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created sessions/core/.env.merkle_builder"
}

generate_orchestrator_env() {
    local file="sessions/core/.env.orchestrator"
    [[ -f "$file" ]] && { log_info "Skipping sessions/core/.env.orchestrator (exists)"; return 0; }
    
    log_info "Creating sessions/core/.env.orchestrator..."
    mkdir -p "sessions/core"
    cat > "$file" << EOF
# Session Orchestrator Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=orchestrator
SERVICE_PORT=8097
SERVICE_HOST=172.20.0.27
SERVICE_URL=http://172.20.0.27:8097

# Orchestration Configuration
SESSION_TIMEOUT=${SESSION_TIMEOUT:-1800}
MAX_SESSIONS=10000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created sessions/core/.env.orchestrator"
}

generate_encryptor_env() {
    local file="sessions/encryption/.env.encryptor"
    [[ -f "$file" ]] && { log_info "Skipping sessions/encryption/.env.encryptor (exists)"; return 0; }
    
    log_info "Creating sessions/encryption/.env.encryptor..."
    mkdir -p "sessions/encryption"
    cat > "$file" << EOF
# Session Encryptor Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=encryptor
SERVICE_PORT=8098
SERVICE_HOST=172.20.0.28
SERVICE_URL=http://172.20.0.28:8098

# Encryption Configuration
ENCRYPTION_ALGORITHM=AES-256-GCM

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created sessions/encryption/.env.encryptor"
}

# TRON Payment Services (7 files)
generate_tron_client_env() {
    local file="$ENV_DIR/.env.tron-client"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-client (exists)"; return 0; }
    
    log_info "Creating .env.tron-client..."
    cat > "$file" << EOF
# TRON Client Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-client
SERVICE_PORT=8091
SERVICE_HOST=172.21.0.10
SERVICE_URL=http://172.21.0.10:8091

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-client"
}

generate_tron_payout_router_env() {
    local file="$ENV_DIR/.env.tron-payout-router"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-payout-router (exists)"; return 0; }
    
    log_info "Creating .env.tron-payout-router..."
    cat > "$file" << EOF
# TRON Payout Router Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-payout-router
SERVICE_PORT=8092
SERVICE_HOST=172.21.0.11
SERVICE_URL=http://172.21.0.11:8092

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-payout-router"
}

generate_tron_wallet_manager_env() {
    local file="$ENV_DIR/.env.tron-wallet-manager"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-wallet-manager (exists)"; return 0; }
    
    log_info "Creating .env.tron-wallet-manager..."
    cat > "$file" << EOF
# TRON Wallet Manager Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-wallet-manager
SERVICE_PORT=8093
SERVICE_HOST=172.21.0.12
SERVICE_URL=http://172.21.0.12:8093

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}

# Wallet Configuration
WALLET_STORAGE_PATH=/data/wallets
WALLET_ENCRYPTION_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-wallet-manager"
}

generate_tron_usdt_manager_env() {
    local file="$ENV_DIR/.env.tron-usdt-manager"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-usdt-manager (exists)"; return 0; }
    
    log_info "Creating .env.tron-usdt-manager..."
    cat > "$file" << EOF
# TRON USDT Manager Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-usdt-manager
SERVICE_PORT=8094
SERVICE_HOST=172.21.0.13
SERVICE_URL=http://172.21.0.13:8094

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}
USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS:-TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-usdt-manager"
}

generate_tron_staking_env() {
    local file="$ENV_DIR/.env.tron-staking"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-staking (exists)"; return 0; }
    
    log_info "Creating .env.tron-staking..."
    cat > "$file" << EOF
# TRON Staking Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-staking
SERVICE_PORT=8096
SERVICE_HOST=172.21.0.14
SERVICE_URL=http://172.21.0.14:8096

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}

# Staking Configuration
STAKING_MIN_AMOUNT=1000000
STAKING_REWARD_RATE=0.05

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-staking"
}

generate_tron_payment_gateway_env() {
    local file="$ENV_DIR/.env.tron-payment-gateway"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-payment-gateway (exists)"; return 0; }
    
    log_info "Creating .env.tron-payment-gateway..."
    cat > "$file" << EOF
# TRON Payment Gateway Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=tron-payment-gateway
SERVICE_PORT=8097
SERVICE_HOST=172.21.0.15
SERVICE_URL=http://172.21.0.15:8097

# TRON Network Configuration
TRON_NETWORK=${TRON_NETWORK:-mainnet}
TRON_RPC_URL=${TRON_RPC_URL:-https://api.trongrid.io}
USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS:-TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t}

# Payment Configuration
PAYMENT_TIMEOUT=300
PAYMENT_CONFIRMATION_BLOCKS=20

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.tron-payment-gateway"
}

generate_tron_secrets_env() {
    local file="$ENV_DIR/.env.tron-secrets"
    [[ -f "$file" ]] && { log_info "Skipping .env.tron-secrets (exists)"; return 0; }
    
    log_info "Creating .env.tron-secrets..."
    cat > "$file" << EOF
# TRON Secrets Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA
# WARNING: This file contains sensitive TRON keys - chmod 600

# TRON Private Keys (from .env.support)
TRON_PRIVATE_KEY=$TRON_PRIVATE_KEY
TRON_MASTER_PRIVATE_KEY=${TRON_MASTER_PRIVATE_KEY:-$TRON_PRIVATE_KEY}

# TRON Wallet Addresses (from .env.support)
TRON_WALLET_ADDRESS=$TRON_WALLET_ADDRESS
TRON_MASTER_WALLET_ADDRESS=${TRON_MASTER_WALLET_ADDRESS:-$TRON_WALLET_ADDRESS}

# TRON API Keys (from .env.support)
TRON_API_KEY=$TRON_API_KEY
EOF
    chmod 600 "$file"
    log_success "Created .env.tron-secrets (permissions: 600)"
}

# Node Services (1 file)
generate_node_env() {
    local file="$ENV_DIR/.env.node"
    [[ -f "$file" ]] && { log_info "Skipping .env.node (exists)"; return 0; }
    
    log_info "Creating .env.node..."
    cat > "$file" << EOF
# Node Management Service Configuration
# Generated: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA

# Service Configuration
SERVICE_NAME=node
SERVICE_PORT=8099
SERVICE_HOST=172.20.0.29
SERVICE_URL=http://172.20.0.29:8099

# Node Configuration
NODE_ID=$(hostname)
NODE_REGION=us-east

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    chmod 664 "$file"
    log_success "Created .env.node"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log_info "========================================"
    log_info "Generate Missing .env.* Files (27 total)"
    log_info "========================================"
    echo ""
    
    cd "$PROJECT_ROOT" || { log_error "Cannot access project root"; exit 1; }
    
    check_phase_files
    load_source_files
    
    echo ""
    log_info "Generating 27 missing .env.* files with actual values..."
    echo ""
    
    # Foundation Services (2 files)
    generate_tor_proxy_env
    generate_server_tools_env
    
    # API & Gateway Services (5 files)
    generate_api_gateway_env
    generate_api_server_env
    generate_openapi_gateway_env
    generate_openapi_server_env
    generate_api_env
    
    # Blockchain Services (10 files)
    generate_blockchain_api_env
    generate_blockchain_governance_env
    generate_blockchain_sessions_data_env
    generate_blockchain_vm_env
    generate_blockchain_ledger_env
    generate_tron_node_client_env
    generate_contract_deployment_env
    generate_contract_compiler_env
    generate_on_system_chain_client_env
    generate_deployment_orchestrator_env
    
    # Session Services (4 files)
    generate_chunker_env
    generate_merkle_builder_env
    generate_orchestrator_env
    generate_encryptor_env
    
    # TRON Payment Services (7 files)
    generate_tron_client_env
    generate_tron_payout_router_env
    generate_tron_wallet_manager_env
    generate_tron_usdt_manager_env
    generate_tron_staking_env
    generate_tron_payment_gateway_env
    generate_tron_secrets_env
    
    # Node Services (1 file)
    generate_node_env
    
    echo ""
    log_success "========================================"
    log_success "All 27 missing .env.* files generated!"
    log_success "========================================"
    echo ""
    log_info "Files contain service-specific configuration only"
    log_info "Passwords/secrets loaded from .env.foundation/.env.secrets via docker-compose"
}

main "$@"