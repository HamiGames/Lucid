#!/bin/bash
# Path: infrastructure/docker/payment-systems/build-env.sh
# Build Environment Script for Lucid Payment Systems
# Generates .env files for payment processing containers

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

log_info "Building environment files for Lucid Payment Systems"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# TRON Client Environment
log_info "Creating tron-client.env..."
cat > "$ENV_DIR/tron-client.env" << EOF
# Lucid TRON Client Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=tron-client
SERVICE_PORT=8099

# TRON Network Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_API_KEY=""
TRON_GRID_API_KEY=""

# Wallet Configuration
TRON_PRIVATE_KEY=""
TRON_WALLET_ADDRESS=""
TRON_KEYSTORE_PATH=/data/keystore

# Contract Addresses
USDT_TRC20_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
PAYOUT_ROUTER_V0_ADDRESS=""
PAYOUT_ROUTER_KYC_ADDRESS=""

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
PAYMENT_DATABASE=lucid_payments

# Security Configuration
ENCRYPTION_KEY=""
COMPLIANCE_SIGNER_KEY=""
KYC_VERIFICATION_KEY=""

# Transaction Configuration
GAS_PRICE=420
GAS_LIMIT=1000000
CONFIRMATION_BLOCKS=20
TRANSACTION_TIMEOUT=300

# Performance Configuration
MAX_CONCURRENT_TRANSACTIONS=10
TRANSACTION_RETRY_ATTEMPTS=3
TRANSACTION_POLLING_INTERVAL=5

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
TRON_DATA_DIR=/data/tron
TRANSACTIONS_DIR=/data/transactions
LOGS_DIR=/data/logs
EOF

# Payout Router V0 Environment
log_info "Creating payout-router-v0.env..."
cat > "$ENV_DIR/payout-router-v0.env" << EOF
# Lucid Payout Router V0 Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=payout-router-v0
SERVICE_PORT=8102

# Router Configuration
ROUTER_VERSION=v0
ROUTER_CONTRACT_ADDRESS=""
ROUTER_OWNER_ADDRESS=""

# TRON Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=""

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
ROUTER_DATABASE=lucid_router

# Security Configuration
ROUTER_ENCRYPTION_KEY=""
COMPLIANCE_KEY=""
KYC_VERIFICATION_KEY=""

# Payout Configuration
MIN_PAYOUT_AMOUNT=1000000
MAX_PAYOUT_AMOUNT=100000000
PAYOUT_FEE_PERCENTAGE=0.5
PAYOUT_TIMEOUT=3600

# Performance Configuration
MAX_CONCURRENT_PAYOUTS=5
PAYOUT_RETRY_ATTEMPTS=3
PAYOUT_PROCESSING_INTERVAL=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
PAYOUT_DATA_DIR=/data/payouts
ROUTER_DATA_DIR=/data/router
LOGS_DIR=/data/logs
EOF

# USDT TRC20 Environment
log_info "Creating usdt-trc20.env..."
cat > "$ENV_DIR/usdt-trc20.env" << EOF
# Lucid USDT TRC20 Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=usdt-trc20
SERVICE_PORT=8103

# USDT Configuration
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
USDT_DECIMALS=6
USDT_SYMBOL=USDT

# TRON Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=""

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
USDT_DATABASE=lucid_usdt

# Security Configuration
USDT_ENCRYPTION_KEY=""
TRANSACTION_SIGNING_KEY=""
BALANCE_VERIFICATION_KEY=""

# Transaction Configuration
TRANSACTION_GAS_LIMIT=100000
TRANSACTION_GAS_PRICE=420
CONFIRMATION_BLOCKS=20
TRANSACTION_TIMEOUT=300

# Balance Configuration
BALANCE_CHECK_INTERVAL=60
BALANCE_SYNC_TIMEOUT=30
MIN_BALANCE_THRESHOLD=1000000

# Performance Configuration
MAX_CONCURRENT_TRANSFERS=10
TRANSFER_RETRY_ATTEMPTS=3
BALANCE_CACHE_TTL=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
USDT_DATA_DIR=/data/usdt
TRANSACTIONS_DIR=/data/transactions
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - tron-client.env"
log_info "  - payout-router-v0.env"
log_info "  - usdt-trc20.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/tron-client.env -t pickme/lucid:tron-client ."
log_info "  docker build --env-file $ENV_DIR/payout-router-v0.env -t pickme/lucid:payout-router-v0 ."
log_info "  docker build --env-file $ENV_DIR/usdt-trc20.env -t pickme/lucid:usdt-trc20 ."
