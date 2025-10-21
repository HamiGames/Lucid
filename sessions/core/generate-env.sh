#!/bin/bash
# Path: sessions/core/generate-env.sh
# Generate .env files for Session Core services
# Implements configuration requirements from docker-build-process-plan.md

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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

log_info "Generating Session Core environment files in: $SCRIPT_DIR"

# =============================================================================
# GENERATE SECURE VALUES
# =============================================================================
log_info "Generating cryptographically secure values..."

# Function to generate secure random string
generate_secure_value() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d '\n'
}

# Function to generate hex key
generate_hex_key() {
    local length=${1:-32}
    openssl rand -hex $length | tr -d '\n'
}

# Generate all required secure values
MONGODB_PASSWORD=$(generate_secure_value 32)
REDIS_PASSWORD=$(generate_secure_value 32)
JWT_SECRET=$(generate_secure_value 64)
ENCRYPTION_KEY=$(generate_hex_key 32)
SESSION_SECRET=$(generate_secure_value 32)
HMAC_KEY=$(generate_secure_value 32)
SIGNING_KEY=$(generate_hex_key 32)

log_success "Generated MONGODB_PASSWORD (32 bytes)"
log_success "Generated REDIS_PASSWORD (32 bytes)"
log_success "Generated JWT_SECRET (64 bytes)"
log_success "Generated ENCRYPTION_KEY (256-bit hex)"
log_success "Generated SESSION_SECRET (32 bytes)"
log_success "Generated HMAC_KEY (32 bytes)"
log_success "Generated SIGNING_KEY (256-bit hex)"

# Load additional values from central config if available
SECURE_ENV_FILE="$PROJECT_ROOT/configs/environment/.env.secure"
if [ -f "$SECURE_ENV_FILE" ]; then
    log_info "Loading additional values from $SECURE_ENV_FILE"
    source "$SECURE_ENV_FILE"
    # Override with central values if they exist
    MONGODB_PASSWORD="${MONGODB_PASSWORD:-$(generate_secure_value 32)}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-$(generate_secure_value 32)}"
    JWT_SECRET="${JWT_SECRET_KEY:-${JWT_SECRET}}"
    ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(generate_hex_key 32)}"
fi

# Load application config if available
APPLICATION_ENV="$PROJECT_ROOT/configs/environment/.env.application"
if [ -f "$APPLICATION_ENV" ]; then
    log_info "Loading application config from $APPLICATION_ENV"
    source "$APPLICATION_ENV"
fi

# =============================================================================
# Generate .env.orchestrator
# =============================================================================
log_info "Creating .env.orchestrator..."
cat > "$SCRIPT_DIR/.env.orchestrator" << 'EOF'
# Lucid Session Orchestrator Environment Configuration
# Generated: BUILD_TIMESTAMP_PLACEHOLDER
# File: sessions/core/.env.orchestrator
# Target: Raspberry Pi 5 (192.168.0.75)

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
BUILD_TIMESTAMP=BUILD_TIMESTAMP_PLACEHOLDER
GIT_SHA=GIT_SHA_PLACEHOLDER
BUILD_PLATFORM=linux/arm64

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app:/app/sessions/core

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================
SERVICE_NAME=session-orchestrator
SERVICE_PORT=8090
SERVICE_HOST=0.0.0.0

# =============================================================================
# ENVIRONMENT
# =============================================================================
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# =============================================================================
# ORCHESTRATION CONFIGURATION
# =============================================================================
ORCHESTRATOR_MODE=pipeline
PIPELINE_STAGES=chunker,encryptor,merkle-builder
STAGE_TIMEOUT=300
MAX_PIPELINE_RETRIES=3

# =============================================================================
# SESSION CONFIGURATION
# =============================================================================
SESSION_TIMEOUT=3600
SESSION_CLEANUP_INTERVAL=300
MAX_CONCURRENT_SESSIONS=10
SESSION_EXPIRY_HOURS=8
SESSION_CLEANUP_HOURS=24

# Session ID Generation
LUCID_SESSION_ID_ENTROPY_BITS=256
LUCID_SESSION_EXPIRY_HOURS=8
LUCID_SESSION_CLEANUP_HOURS=24

# Session Output
LUCID_SESSION_OUTPUT_DIR=/data/sessions
SESSION_DATA_DIR=/data/sessions

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# MongoDB Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_sessions
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=MONGODB_PASSWORD_PLACEHOLDER
MONGODB_URI=mongodb://lucid:MONGODB_PASSWORD_PLACEHOLDER@lucid-mongodb:27017/lucid_sessions?authSource=admin
MONGODB_AUTH_SOURCE=admin
MONGODB_POOL_SIZE=50

# Redis Configuration
REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=REDIS_PASSWORD_PLACEHOLDER
REDIS_URI=redis://:REDIS_PASSWORD_PLACEHOLDER@lucid-redis:6379
REDIS_DATABASE=1
REDIS_POOL_SIZE=50

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# JWT Configuration
JWT_SECRET=JWT_SECRET_PLACEHOLDER
JWT_SECRET_KEY=JWT_SECRET_PLACEHOLDER
JWT_ALGORITHM=HS256

# Encryption Configuration
ENCRYPTION_KEY=ENCRYPTION_KEY_PLACEHOLDER
MASTER_ENCRYPTION_KEY=ENCRYPTION_KEY_PLACEHOLDER
SESSION_SECRET=SESSION_SECRET_PLACEHOLDER
HMAC_KEY=HMAC_KEY_PLACEHOLDER

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
# Chunk Configuration
CHUNK_SIZE=8388608
LUCID_CHUNK_SIZE_MIN=8388608
LUCID_CHUNK_SIZE_MAX=16777216
MAX_CHUNK_SIZE=16777216

# Compression Configuration
COMPRESSION_LEVEL=1
LUCID_COMPRESSION_LEVEL=3

# Batch Configuration
BATCH_SIZE=100
PROCESSING_WORKERS=4

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/session-orchestrator.log

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
SESSION_DATA_DIR=/data/sessions
TEMP_DIR=/tmp/orchestrator
LOGS_DIR=/data/logs
OUTPUT_DIR=/data/sessions

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================
MONITORING_ENABLED=true
METRICS_PORT=9216
METRICS_PATH=/metrics

EOF

# =============================================================================
# Generate .env.chunker
# =============================================================================
log_info "Creating .env.chunker..."
cat > "$SCRIPT_DIR/.env.chunker" << 'EOF'
# Lucid Session Chunker Environment Configuration
# Generated: BUILD_TIMESTAMP_PLACEHOLDER
# File: sessions/core/.env.chunker
# Target: Raspberry Pi 5 (192.168.0.75)

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
BUILD_TIMESTAMP=BUILD_TIMESTAMP_PLACEHOLDER
GIT_SHA=GIT_SHA_PLACEHOLDER
BUILD_PLATFORM=linux/arm64

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app:/app/sessions/core

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================
SERVICE_NAME=chunker
SERVICE_PORT=8092
SERVICE_HOST=0.0.0.0

# =============================================================================
# ENVIRONMENT
# =============================================================================
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# =============================================================================
# CHUNKING CONFIGURATION
# =============================================================================
# Chunk Size Configuration
CHUNK_SIZE=8388608
LUCID_CHUNK_SIZE_MIN=8388608
LUCID_CHUNK_SIZE_MAX=16777216
MAX_CHUNK_SIZE=16777216
MIN_CHUNK_SIZE=1048576

# Chunking Algorithm
CHUNK_OVERLAP=0
CHUNK_ALGORITHM=rolling_hash
HASH_ALGORITHM=sha256

# Chunk Processing
CHUNK_PROCESSING_TIMEOUT=60
CHUNK_PROCESSING_WORKERS=4

# Output Configuration
LUCID_CHUNKER_OUTPUT_DIR=/data/chunks
CHUNKS_DIR=/data/chunks

# =============================================================================
# COMPRESSION CONFIGURATION
# =============================================================================
COMPRESSION_ENABLED=true
COMPRESSION_LEVEL=3
LUCID_COMPRESSION_LEVEL=3
SESSION_COMPRESSION_LEVEL=1

# Compression Engine
LUCID_COMPRESSION_PATH=/data/compression
LUCID_DEFAULT_COMPRESSION_LEVEL=3
LUCID_COMPRESSION_THRESHOLD=1024

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# MongoDB Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_chunks
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=MONGODB_PASSWORD_PLACEHOLDER
MONGODB_URI=mongodb://lucid:MONGODB_PASSWORD_PLACEHOLDER@lucid-mongodb:27017/lucid_chunks?authSource=admin
MONGODB_AUTH_SOURCE=admin

# Redis Configuration
REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=REDIS_PASSWORD_PLACEHOLDER
REDIS_URI=redis://:REDIS_PASSWORD_PLACEHOLDER@lucid-redis:6379

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
CHUNK_ENCRYPTION=false
ENCRYPTION_KEY=ENCRYPTION_KEY_PLACEHOLDER
JWT_SECRET=JWT_SECRET_PLACEHOLDER

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
MAX_CONCURRENT_CHUNKS=10
CHUNK_BUFFER_SIZE=1048576
CHUNK_PROCESSING_THREADS=4

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/chunker.log

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
CHUNKS_DIR=/data/chunks
TEMP_DIR=/tmp/chunker
LOGS_DIR=/data/logs
LUCID_CHUNK_MANAGER_DIR=/data/chunks

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================
MONITORING_ENABLED=true
METRICS_PORT=9217
METRICS_PATH=/metrics

EOF

# =============================================================================
# Generate .env.merkle_builder
# =============================================================================
log_info "Creating .env.merkle_builder..."
cat > "$SCRIPT_DIR/.env.merkle_builder" << 'EOF'
# Lucid Merkle Builder Environment Configuration
# Generated: BUILD_TIMESTAMP_PLACEHOLDER
# File: sessions/core/.env.merkle_builder
# Target: Raspberry Pi 5 (192.168.0.75)

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
BUILD_TIMESTAMP=BUILD_TIMESTAMP_PLACEHOLDER
GIT_SHA=GIT_SHA_PLACEHOLDER
BUILD_PLATFORM=linux/arm64

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app:/app/sessions/core

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================
SERVICE_NAME=merkle-builder
SERVICE_PORT=8094
SERVICE_HOST=0.0.0.0

# =============================================================================
# ENVIRONMENT
# =============================================================================
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# =============================================================================
# MERKLE TREE CONFIGURATION
# =============================================================================
# Merkle Algorithm Configuration
MERKLE_ALGORITHM=sha256
MERKLE_HASH_ALGORITHM=sha256
MERKLE_LEAF_SIZE=32
MERKLE_TREE_HEIGHT=20

# Merkle Tree Processing
MERKLE_BATCH_SIZE=1000
MERKLE_BUILD_TIMEOUT=300
MAX_CONCURRENT_TREES=5

# Merkle Output
LUCID_MERKLE_OUTPUT_DIR=/data/merkle_roots
MERKLE_DIR=/data/merkle

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# MongoDB Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_merkle
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=MONGODB_PASSWORD_PLACEHOLDER
MONGODB_URI=mongodb://lucid:MONGODB_PASSWORD_PLACEHOLDER@lucid-mongodb:27017/lucid_merkle?authSource=admin
MONGODB_AUTH_SOURCE=admin

# Redis Configuration
REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=REDIS_PASSWORD_PLACEHOLDER
REDIS_URI=redis://:REDIS_PASSWORD_PLACEHOLDER@lucid-redis:6379

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# Merkle Root Signing
MERKLE_ROOT_SIGNATURE=true
SIGNING_KEY=SIGNING_KEY_PLACEHOLDER

# Encryption Configuration
ENCRYPTION_KEY=ENCRYPTION_KEY_PLACEHOLDER
JWT_SECRET=JWT_SECRET_PLACEHOLDER

# =============================================================================
# BLOCKCHAIN ANCHORING
# =============================================================================
# Session Anchoring Configuration
ANCHORING_ENABLED=true
ANCHORING_BATCH_SIZE=10
ANCHORING_INTERVAL=60
ANCHORING_TIMEOUT=30
SESSION_MERKLE_TREE_ENABLED=true

# Blockchain Connection
BLOCKCHAIN_ENGINE_HOST=lucid-blockchain-engine
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_SESSION_ANCHORING_PORT=8085

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
MAX_TREE_DEPTH=20
MAX_LEAVES_PER_TREE=1048576
TREE_BUILD_THREADS=2
PARALLEL_TREE_BUILDS=3

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/merkle-builder.log

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
MERKLE_DIR=/data/merkle
MERKLE_ROOTS_DIR=/data/merkle_roots
TEMP_DIR=/tmp/merkle-builder
LOGS_DIR=/data/logs

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================
MONITORING_ENABLED=true
METRICS_PORT=9218
METRICS_PATH=/metrics

# =============================================================================
# STORAGE RETENTION
# =============================================================================
SESSION_RETENTION_DAYS=30
MERKLE_ROOT_RETENTION_DAYS=90
ARCHIVE_ENABLED=true
ARCHIVE_PATH=/data/archive

EOF

# Replace placeholders with actual GENERATED values in all three files
log_info "Injecting generated secure values into .env files..."

for env_file in "$SCRIPT_DIR/.env.orchestrator" "$SCRIPT_DIR/.env.chunker" "$SCRIPT_DIR/.env.merkle_builder"; do
    sed -i "s/BUILD_TIMESTAMP_PLACEHOLDER/$BUILD_TIMESTAMP/g" "$env_file"
    sed -i "s/GIT_SHA_PLACEHOLDER/$GIT_SHA/g" "$env_file"
    
    # Replace with GENERATED secure values
    sed -i "s|MONGODB_PASSWORD_PLACEHOLDER|$MONGODB_PASSWORD|g" "$env_file"
    sed -i "s|REDIS_PASSWORD_PLACEHOLDER|$REDIS_PASSWORD|g" "$env_file"
    sed -i "s|JWT_SECRET_PLACEHOLDER|$JWT_SECRET|g" "$env_file"
    sed -i "s|ENCRYPTION_KEY_PLACEHOLDER|$ENCRYPTION_KEY|g" "$env_file"
    sed -i "s|SESSION_SECRET_PLACEHOLDER|$SESSION_SECRET|g" "$env_file"
    sed -i "s|HMAC_KEY_PLACEHOLDER|$HMAC_KEY|g" "$env_file"
    sed -i "s|SIGNING_KEY_PLACEHOLDER|$SIGNING_KEY|g" "$env_file"
done

log_success "Session Core environment files generated successfully!"

# Validate no placeholders remain
has_placeholders=false
for env_file in "$SCRIPT_DIR/.env.orchestrator" "$SCRIPT_DIR/.env.chunker" "$SCRIPT_DIR/.env.merkle_builder"; do
    if grep -q "_PLACEHOLDER" "$env_file"; then
        has_placeholders=true
        log_error "Placeholders found in $env_file"
        grep "_PLACEHOLDER" "$env_file" || true
    fi
done

if [ "$has_placeholders" = true ]; then
    log_error "Some placeholders were not replaced! This should not happen."
    exit 1
else
    log_success "All placeholders replaced with generated values"
fi

# Save generated secrets to a secure reference file
SECRETS_FILE="$SCRIPT_DIR/.env.sessions.secrets"
log_info "Saving generated secrets to: $SECRETS_FILE"

cat > "$SECRETS_FILE" << EOF
# Session Core Generated Secrets Reference
# Generated: $(date)
# WARNING: Keep this file secure! Never commit to version control!

MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
SESSION_SECRET=$SESSION_SECRET
HMAC_KEY=$HMAC_KEY
SIGNING_KEY=$SIGNING_KEY
EOF

chmod 600 "$SECRETS_FILE"
log_success "Secrets saved to $SECRETS_FILE (permissions: 600)"

echo ""
log_info "==================================================================="
log_info "Session Core Environment Generation Complete!"
log_info "==================================================================="
echo ""
log_info "Generated files:"
log_info "  • .env.orchestrator     : $SCRIPT_DIR/.env.orchestrator"
log_info "  • .env.chunker          : $SCRIPT_DIR/.env.chunker"
log_info "  • .env.merkle_builder   : $SCRIPT_DIR/.env.merkle_builder"
log_info "  • .env.sessions.secrets : $SECRETS_FILE"
echo ""
log_info "Build details:"
log_info "  • Build timestamp       : $BUILD_TIMESTAMP"
log_info "  • Git SHA               : $GIT_SHA"
echo ""
log_info "Generated secure values:"
log_info "  • MongoDB Password      : ${MONGODB_PASSWORD:0:8}... (32 bytes)"
log_info "  • Redis Password        : ${REDIS_PASSWORD:0:8}... (32 bytes)"
log_info "  • JWT Secret            : ${JWT_SECRET:0:12}... (64 bytes)"
log_info "  • Encryption Key        : ${ENCRYPTION_KEY:0:16}... (256-bit hex)"
log_info "  • Session Secret        : ${SESSION_SECRET:0:8}... (32 bytes)"
log_info "  • HMAC Key              : ${HMAC_KEY:0:8}... (32 bytes)"
log_info "  • Signing Key           : ${SIGNING_KEY:0:16}... (256-bit hex)"
echo ""
log_warning "SECURITY NOTICE:"
log_warning "  • Keep .env.sessions.secrets file secure (chmod 600)"
log_warning "  • Never commit .env.sessions.secrets to version control"
log_warning "  • Backup secrets file to secure location"
log_warning "  • Rotate keys regularly in production"
echo ""
log_success "Session Core environment generation complete!"

