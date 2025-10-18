#!/bin/bash
# Path: infrastructure/docker/blockchain/build-env.sh
# Build Environment Script for Lucid Blockchain Services
# Generates .env files for all blockchain-related containers

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_DIR="${SCRIPT_DIR}/env"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors
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

# Create environment directory
mkdir -p "$ENV_DIR"

log_info "Building environment files for Lucid Blockchain Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Common environment variables for all blockchain services
COMMON_ENV_VARS=(
    "PYTHONDONTWRITEBYTECODE=1"
    "PYTHONUNBUFFERED=1"
    "PYTHONPATH=/app"
    "BUILD_TIMESTAMP=$BUILD_TIMESTAMP"
    "GIT_SHA=$GIT_SHA"
    "LUCID_ENV=dev"
    "LUCID_NETWORK=testnet"
    "LUCID_PLANE=ops"
    "LUCID_CLUSTER_ID=dev-core"
    "LOG_LEVEL=DEBUG"
)

# Blockchain API Environment
log_info "Creating blockchain-api.env..."
cat > "$ENV_DIR/blockchain-api.env" << EOF
# Lucid Blockchain API Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8084
UVICORN_WORKERS=1

# Database Configuration
MONGO_URI=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONGO_DATABASE=lucid
MONGO_COLLECTION_PREFIX=blockchain

# Blockchain Network Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_HTTP_ENDPOINT=https://api.shasta.trongrid.io
TRONGRID_API_KEY=""
BLOCK_ONION=""
BLOCK_RPC_URL=""
ETH_RPC_URL=http://localhost:8545
ETH_CHAIN_ID=1337

# Security Configuration
KEY_ENC_SECRET=""
JWT_SECRET_KEY=""
ENCRYPTION_KEY=""
AGE_PRIVATE_KEY=""

# Data Directories
BLOCKCHAIN_DATA_DIR=/data/blockchain
WALLET_DATA_DIR=/data/wallets
LOG_DIR=/data/logs

# Performance Settings
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
EOF

# Blockchain Governance Environment
log_info "Creating blockchain-governance.env..."
cat > "$ENV_DIR/blockchain-governance.env" << EOF
# Lucid Blockchain Governance Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Governance Configuration
GOVERNANCE_PATH=/opt/lucid/governance
VOTING_PATH=/opt/lucid/voting
PARAMETERS_PATH=/opt/lucid/parameters

# Voting Configuration
VOTING_PERIOD_SECONDS=172800
PROPOSAL_THRESHOLD=1000
QUORUM_THRESHOLD=4000
VOTING_DELAY_SECONDS=86400
EXECUTION_DELAY_SECONDS=172800

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
LUCID_NETWORK_ID=lucid-dev

# Blockchain Configuration
LUCID_BLOCK_TIME=5
LUCID_MAX_BLOCK_TXS=100

# Security Configuration
GOVERNANCE_KEY=""
ADMIN_KEY=""

# Data Directories
DATA_DIR=/data/governance
CONSENSUS_DIR=/data/consensus

# Performance Settings
MAX_PROPOSALS=1000
MAX_VOTES_PER_PROPOSAL=10000
EOF

# Blockchain Sessions Data Environment
log_info "Creating blockchain-sessions-data.env..."
cat > "$ENV_DIR/blockchain-sessions-data.env" << EOF
# Lucid Blockchain Sessions Data Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Blockchain Configuration
CHAIN_RPC_URL=http://localhost:8545
CHAIN_ID=1337
LUCID_ANCHORS_ADDRESS=""
LUCID_CHUNK_STORE_ADDRESS=""

# Security Configuration
PRIVATE_KEY=""
ENCRYPTION_KEY=""

# Data Directories
CHAIN_DATA_DIR=/data/chain
SESSIONS_DATA_DIR=/data/sessions
ANCHORS_DIR=/data/anchors

# Performance Settings
BATCH_SIZE=100
GAS_LIMIT=1000000
CONFIRMATION_BLOCKS=3
EOF

# Blockchain VM Environment
log_info "Creating blockchain-vm.env..."
cat > "$ENV_DIR/blockchain-vm.env" << EOF
# Lucid Blockchain VM Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# VM Configuration
VM_STORAGE_PATH=/data/vm
VM_MAX_INSTANCES=10
VM_MEMORY_LIMIT=1024
VM_CPU_LIMIT=1

# Blockchain Configuration
CHAIN_RPC_URL=http://localhost:8545
CHAIN_ID=1337

# Security Configuration
VM_ENCRYPTION_KEY=""
VM_ACCESS_KEY=""

# Data Directories
VM_INSTANCES_DIR=/data/vm-instances
VM_LOGS_DIR=/data/logs

# Performance Settings
VM_STARTUP_TIMEOUT=60
VM_SHUTDOWN_TIMEOUT=30
EOF

# Blockchain Ledger Environment
log_info "Creating blockchain-ledger.env..."
cat > "$ENV_DIR/blockchain-ledger.env" << EOF
# Lucid Blockchain Ledger Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Ledger Configuration
LEDGER_STORAGE_PATH=/data/ledger
LUCID_NETWORK_ID=lucid-dev

# Blockchain Configuration
CHAIN_RPC_URL=http://localhost:8545
CHAIN_ID=1337

# Security Configuration
LEDGER_ENCRYPTION_KEY=""
SIGNING_KEY=""

# Data Directories
BLOCKS_DIR=/data/blocks
TRANSACTIONS_DIR=/data/transactions

# Performance Settings
BLOCK_SIZE_LIMIT=8388608
MAX_TRANSACTIONS_PER_BLOCK=1000
EOF

# TRON Node Client Environment
log_info "Creating tron-node-client.env..."
cat > "$ENV_DIR/tron-node-client.env" << EOF
# Lucid TRON Node Client Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# TRON Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=""

# Contract Addresses
PAYOUT_ROUTER_V0_ADDRESS=""
PAYOUT_ROUTER_KYC_ADDRESS=""
USDT_TRC20_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Security Configuration
COMPLIANCE_SIGNER_KEY=""
ENCRYPTION_KEY=""

# Data Directories
TRON_DATA_DIR=/data/tron
PAYOUTS_DIR=/data/payouts

# Performance Settings
GAS_PRICE=420
GAS_LIMIT=1000000
CONFIRMATION_BLOCKS=20
EOF

# Contract Deployment Environment
log_info "Creating contract-deployment.env..."
cat > "$ENV_DIR/contract-deployment.env" << EOF
# Lucid Contract Deployment Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Deployment Configuration
CONTRACT_ARTIFACTS_PATH=/data/contracts
DEPLOYMENT_LOG_PATH=/data/logs
COMPILER_STORAGE_PATH=/data/compiler

# TRON Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io

# Security Configuration
DEPLOYMENT_KEY=""
CONTRACT_OWNER_KEY=""

# Data Directories
CONTRACTS_DIR=/data/contracts
COMPILER_DIR=/data/compiler

# Performance Settings
DEPLOYMENT_TIMEOUT=300
VERIFICATION_TIMEOUT=60
EOF

# Contract Compiler Environment
log_info "Creating contract-compiler.env..."
cat > "$ENV_DIR/contract-compiler.env" << EOF
# Lucid Contract Compiler Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Compiler Configuration
COMPILER_STORAGE_PATH=/data/compiler
SOLC_VERSION=0.8.19

# Security Configuration
COMPILER_KEY=""
VERIFICATION_KEY=""

# Data Directories
CONTRACTS_DIR=/data/contracts
COMPILER_DIR=/data/compiler

# Performance Settings
COMPILATION_TIMEOUT=120
OPTIMIZATION_LEVEL=200
EOF

# On-System Chain Client Environment
log_info "Creating on-system-chain-client.env..."
cat > "$ENV_DIR/on-system-chain-client.env" << EOF
# Lucid On-System Chain Client Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Blockchain Configuration
CHAIN_RPC_URL=http://localhost:8545
CHAIN_ID=1337
LUCID_ANCHORS_ADDRESS=""
LUCID_CHUNK_STORE_ADDRESS=""

# Security Configuration
PRIVATE_KEY=""
ENCRYPTION_KEY=""

# Data Directories
CHAIN_DATA_DIR=/data/chain
ANCHORS_DIR=/data/anchors

# Performance Settings
BATCH_SIZE=100
GAS_LIMIT=1000000
CONFIRMATION_BLOCKS=3
EOF

# Deployment Orchestrator Environment
log_info "Creating deployment-orchestrator.env..."
cat > "$ENV_DIR/deployment-orchestrator.env" << EOF
# Lucid Deployment Orchestrator Environment
# Generated: $(date)

# Common Python settings
${COMMON_ENV_VARS[*]}

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Orchestrator Configuration
ORCHESTRATOR_STORAGE_PATH=/data/orchestrator

# Security Configuration
ORCHESTRATOR_KEY=""
DEPLOYMENT_KEY=""

# Data Directories
DEPLOYMENTS_DIR=/data/deployments
ORCHESTRATOR_DIR=/data/orchestrator

# Performance Settings
MAX_CONCURRENT_DEPLOYMENTS=5
DEPLOYMENT_TIMEOUT=600
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - blockchain-api.env"
log_info "  - blockchain-governance.env"
log_info "  - blockchain-sessions-data.env"
log_info "  - blockchain-vm.env"
log_info "  - blockchain-ledger.env"
log_info "  - tron-node-client.env"
log_info "  - contract-deployment.env"
log_info "  - contract-compiler.env"
log_info "  - on-system-chain-client.env"
log_info "  - deployment-orchestrator.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/blockchain-api.env -t pickme/lucid:blockchain-api ."
