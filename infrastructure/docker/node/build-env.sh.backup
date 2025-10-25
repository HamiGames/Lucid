#!/bin/bash
# Path: infrastructure/docker/node/build-env.sh
# Build Environment Script for Lucid Node Services
# Generates .env files for distributed node containers

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

log_info "Building environment files for Lucid Node Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# DHT Node Environment
log_info "Creating dht-node.env..."
cat > "$ENV_DIR/dht-node.env" << EOF
# Lucid DHT Node Environment
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
SERVICE_NAME=dht-node
SERVICE_PORT=8116

# DHT Configuration
DHT_NETWORK_ID=lucid-dht
DHT_BOOTSTRAP_NODES=""
DHT_NODE_ID=""
DHT_PORT=8116
DHT_PROTOCOL_VERSION=1

# Network Configuration
DHT_MAX_CONNECTIONS=100
DHT_CONNECTION_TIMEOUT=30
DHT_PING_INTERVAL=60
DHT_PING_TIMEOUT=10

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
DHT_DATABASE=lucid_dht

# Security Configuration
DHT_ENCRYPTION_KEY=""
DHT_SIGNING_KEY=""
DHT_ACCESS_CONTROL=true
DHT_AUTHENTICATION=true

# Performance Configuration
DHT_CACHE_SIZE=1000
DHT_CACHE_TTL=3600
DHT_REPLICATION_FACTOR=3
DHT_CONSISTENCY_LEVEL=eventual

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
DHT_DATA_DIR=/data/dht
DHT_CACHE_DIR=/data/cache
DHT_LOGS_DIR=/data/logs
EOF

# Leader Selection Environment
log_info "Creating leader-selection.env..."
cat > "$ENV_DIR/leader-selection.env" << EOF
# Lucid Leader Selection Environment
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
SERVICE_NAME=leader-selection
SERVICE_PORT=8117

# Leader Selection Configuration
LEADER_SELECTION_ALGORITHM=raft
LEADER_ELECTION_TIMEOUT=5000
LEADER_HEARTBEAT_INTERVAL=1000
LEADER_TERM_TIMEOUT=10000

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
LEADER_DATABASE=lucid_leader

# Security Configuration
LEADER_ENCRYPTION_KEY=""
LEADER_SIGNING_KEY=""
LEADER_ACCESS_CONTROL=true
LEADER_AUTHENTICATION=true

# Performance Configuration
LEADER_CACHE_SIZE=500
LEADER_CACHE_TTL=1800
LEADER_SYNC_INTERVAL=300
MAX_CONCURRENT_ELECTIONS=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
LEADER_DATA_DIR=/data/leader
ELECTION_DATA_DIR=/data/elections
LEADER_LOGS_DIR=/data/logs
EOF

# Task Proofs Environment
log_info "Creating task-proofs.env..."
cat > "$ENV_DIR/task-proofs.env" << EOF
# Lucid Task Proofs Environment
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
SERVICE_NAME=task-proofs
SERVICE_PORT=8118

# Task Proofs Configuration
PROOF_ALGORITHM=zk-SNARK
PROOF_GENERATION_TIMEOUT=300
PROOF_VERIFICATION_TIMEOUT=60
PROOF_CACHE_ENABLED=true

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
PROOF_DATABASE=lucid_proofs

# Security Configuration
PROOF_ENCRYPTION_KEY=""
PROOF_SIGNING_KEY=""
PROOF_ACCESS_CONTROL=true
PROOF_AUDIT_ENABLED=true

# Performance Configuration
PROOF_CACHE_SIZE=1000
PROOF_CACHE_TTL=3600
MAX_CONCURRENT_PROOFS=20
PROOF_BATCH_SIZE=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
PROOF_DATA_DIR=/data/proofs
PROOF_CACHE_DIR=/data/cache
PROOF_LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - dht-node.env"
log_info "  - leader-selection.env"
log_info "  - task-proofs.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/dht-node.env -t pickme/lucid:dht-node ."
log_info "  docker build --env-file $ENV_DIR/leader-selection.env -t pickme/lucid:leader-selection ."
log_info "  docker build --env-file $ENV_DIR/task-proofs.env -t pickme/lucid:task-proofs ."
