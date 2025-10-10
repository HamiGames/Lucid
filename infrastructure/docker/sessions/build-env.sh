#!/bin/bash
# Path: infrastructure/docker/sessions/build-env.sh
# Build Environment Script for Lucid Session Services
# Generates .env files for session processing containers

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

log_info "Building environment files for Lucid Session Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Session Orchestrator Environment
log_info "Creating session-orchestrator.env..."
cat > "$ENV_DIR/session-orchestrator.env" << EOF
# Lucid Session Orchestrator Environment
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
SERVICE_NAME=session-orchestrator
SERVICE_PORT=8090

# Orchestration Configuration
ORCHESTRATOR_MODE=pipeline
PIPELINE_STAGES=chunker,encryptor,merkle-builder
STAGE_TIMEOUT=300

# Session Configuration
SESSION_TIMEOUT=3600
SESSION_CLEANUP_INTERVAL=300
MAX_CONCURRENT_SESSIONS=10

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
SESSION_DATABASE=lucid_sessions

# Security Configuration
ENCRYPTION_KEY=""
SESSION_SECRET=""
HMAC_KEY=""

# Performance Configuration
CHUNK_SIZE=8388608
COMPRESSION_LEVEL=1
BATCH_SIZE=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
SESSION_DATA_DIR=/data/sessions
TEMP_DIR=/tmp/orchestrator
LOGS_DIR=/data/logs
EOF

# Session Recorder Environment
log_info "Creating session-recorder.env..."
cat > "$ENV_DIR/session-recorder.env" << EOF
# Lucid Session Recorder Environment
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
SERVICE_NAME=session-recorder
SERVICE_PORT=8091

# Recording Configuration
RECORDING_FORMAT=mp4
RECORDING_QUALITY=high
RECORDING_FPS=30
RECORDING_RESOLUTION=1920x1080

# FFmpeg Configuration
FFMPEG_PATH=/usr/bin/ffmpeg
FFMPEG_PRESET=ultrafast
FFMPEG_CRF=23
FFMPEG_THREADS=4

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
RECORDING_DATABASE=lucid_recordings

# Storage Configuration
RECORDING_STORAGE_PATH=/data/recordings
RECORDING_MAX_SIZE=1073741824
RECORDING_RETENTION_DAYS=30

# Security Configuration
RECORDING_ENCRYPTION=true
ENCRYPTION_KEY=""

# Performance Configuration
RECORDING_BUFFER_SIZE=1048576
RECORDING_CHUNK_SIZE=8388608
MAX_CONCURRENT_RECORDINGS=5

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
RECORDINGS_DIR=/data/recordings
TEMP_DIR=/tmp/recorder
LOGS_DIR=/data/logs
EOF

# Session Chunker Environment
log_info "Creating chunker.env..."
cat > "$ENV_DIR/chunker.env" << EOF
# Lucid Session Chunker Environment
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
SERVICE_NAME=chunker
SERVICE_PORT=8092

# Chunking Configuration
CHUNK_SIZE=8388608
CHUNK_OVERLAP=0
CHUNK_ALGORITHM=rolling_hash
HASH_ALGORITHM=sha256

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
CHUNK_DATABASE=lucid_chunks

# Performance Configuration
MAX_CHUNK_SIZE=16777216
MIN_CHUNK_SIZE=1048576
CHUNK_PROCESSING_TIMEOUT=60

# Security Configuration
CHUNK_ENCRYPTION=false
ENCRYPTION_KEY=""

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
CHUNKS_DIR=/data/chunks
TEMP_DIR=/tmp/chunker
LOGS_DIR=/data/logs
EOF

# Session Encryptor Environment
log_info "Creating encryptor.env..."
cat > "$ENV_DIR/encryptor.env" << EOF
# Lucid Session Encryptor Environment
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
SERVICE_NAME=encryptor
SERVICE_PORT=8093

# Encryption Configuration
ENCRYPTION_ALGORITHM=AES-256-GCM
KEY_DERIVATION_FUNCTION=PBKDF2
KEY_DERIVATION_ITERATIONS=100000

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
ENCRYPTION_DATABASE=lucid_encrypted

# Security Configuration
MASTER_ENCRYPTION_KEY=""
KEY_ROTATION_INTERVAL=86400
ENCRYPTION_SALT_SIZE=32

# Performance Configuration
ENCRYPTION_CHUNK_SIZE=1048576
MAX_CONCURRENT_ENCRYPTIONS=10
ENCRYPTION_TIMEOUT=120

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
ENCRYPTED_DIR=/data/encrypted
TEMP_DIR=/tmp/encryptor
LOGS_DIR=/data/logs
EOF

# Merkle Builder Environment
log_info "Creating merkle-builder.env..."
cat > "$ENV_DIR/merkle-builder.env" << EOF
# Lucid Merkle Builder Environment
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
SERVICE_NAME=merkle-builder
SERVICE_PORT=8094

# Merkle Tree Configuration
MERKLE_ALGORITHM=sha256
MERKLE_LEAF_SIZE=32
MERKLE_TREE_HEIGHT=20

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MERKLE_DATABASE=lucid_merkle

# Performance Configuration
MERKLE_BATCH_SIZE=1000
MERKLE_BUILD_TIMEOUT=300
MAX_CONCURRENT_TREES=5

# Security Configuration
MERKLE_ROOT_SIGNATURE=true
SIGNING_KEY=""

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
MERKLE_DIR=/data/merkle
TEMP_DIR=/tmp/merkle-builder
LOGS_DIR=/data/logs
EOF

# Clipboard Handler Environment
log_info "Creating clipboard-handler.env..."
cat > "$ENV_DIR/clipboard-handler.env" << EOF
# Lucid Clipboard Handler Environment
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
SERVICE_NAME=clipboard-handler
SERVICE_PORT=8095

# Clipboard Configuration
CLIPBOARD_MAX_SIZE=1048576
CLIPBOARD_FORMATS=text,html,image
CLIPBOARD_COMPRESSION=true

# Security Configuration
CLIPBOARD_ENCRYPTION=true
ENCRYPTION_KEY=""
CLIPBOARD_VALIDATION=true

# Performance Configuration
CLIPBOARD_BUFFER_SIZE=65536
CLIPBOARD_SYNC_INTERVAL=100
MAX_CLIPBOARD_HISTORY=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
CLIPBOARD_DIR=/data/clipboard
TEMP_DIR=/tmp/clipboard
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - session-orchestrator.env"
log_info "  - session-recorder.env"
log_info "  - chunker.env"
log_info "  - encryptor.env"
log_info "  - merkle-builder.env"
log_info "  - clipboard-handler.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/session-orchestrator.env -t pickme/lucid:session-orchestrator ."
log_info "  docker build --env-file $ENV_DIR/session-recorder.env -t pickme/lucid:session-recorder ."
log_info "  docker build --env-file $ENV_DIR/chunker.env -t pickme/lucid:chunker ."
log_info "  docker build --env-file $ENV_DIR/encryptor.env -t pickme/lucid:encryptor ."
log_info "  docker build --env-file $ENV_DIR/merkle-builder.env -t pickme/lucid:merkle-builder ."
log_info "  docker build --env-file $ENV_DIR/clipboard-handler.env -t pickme/lucid:clipboard-handler ."
