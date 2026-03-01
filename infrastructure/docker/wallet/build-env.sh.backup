#!/bin/bash
# Path: infrastructure/docker/wallet/build-env.sh
# Build Environment Script for Lucid Wallet Services
# Generates .env files for wallet management containers

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

log_info "Building environment files for Lucid Wallet Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Software Vault Environment
log_info "Creating software-vault.env..."
cat > "$ENV_DIR/software-vault.env" << EOF
# Lucid Software Vault Environment
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
SERVICE_NAME=software-vault
SERVICE_PORT=8110

# Vault Configuration
VAULT_TYPE=software
VAULT_ENCRYPTION=AES-256-GCM
VAULT_KEY_DERIVATION=PBKDF2
VAULT_KEY_ITERATIONS=100000

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
VAULT_DATABASE=lucid_vault

# Security Configuration
MASTER_VAULT_KEY=""
VAULT_ENCRYPTION_KEY=""
VAULT_SIGNING_KEY=""
VAULT_ACCESS_CONTROL=true

# Key Management Configuration
KEY_ROTATION_INTERVAL=86400
KEY_BACKUP_ENABLED=true
KEY_EXPORT_ENABLED=false
KEY_SHARING_ENABLED=false

# Performance Configuration
VAULT_CACHE_SIZE=1000
VAULT_CACHE_TTL=3600
MAX_CONCURRENT_OPERATIONS=50

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
VAULT_DATA_DIR=/data/vault
VAULT_KEYS_DIR=/data/keys
VAULT_BACKUP_DIR=/data/backup
LOGS_DIR=/data/logs
EOF

# Role Manager Environment
log_info "Creating role-manager.env..."
cat > "$ENV_DIR/role-manager.env" << EOF
# Lucid Role Manager Environment
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
SERVICE_NAME=role-manager
SERVICE_PORT=8111

# Role Configuration
ROLE_HIERARCHY_ENABLED=true
ROLE_INHERITANCE=true
ROLE_PERMISSIONS_GRANULAR=true
ROLE_AUDIT_ENABLED=true

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
ROLE_DATABASE=lucid_roles
ROLE_COLLECTION=roles
PERMISSION_COLLECTION=permissions

# Security Configuration
ROLE_ENCRYPTION_KEY=""
PERMISSION_SIGNING_KEY=""
ROLE_ACCESS_CONTROL=true
PERMISSION_VALIDATION=true

# Permission Configuration
PERMISSION_CACHE_ENABLED=true
PERMISSION_CACHE_TTL=1800
PERMISSION_VALIDATION_TIMEOUT=5
MAX_PERMISSIONS_PER_ROLE=100

# Performance Configuration
ROLE_CACHE_SIZE=500
ROLE_SYNC_INTERVAL=300
MAX_CONCURRENT_ROLE_CHECKS=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
ROLE_DATA_DIR=/data/roles
PERMISSION_DATA_DIR=/data/permissions
AUDIT_DATA_DIR=/data/audit
LOGS_DIR=/data/logs
EOF

# Key Rotation Environment
log_info "Creating key-rotation.env..."
cat > "$ENV_DIR/key-rotation.env" << EOF
# Lucid Key Rotation Environment
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
SERVICE_NAME=key-rotation
SERVICE_PORT=8112

# Key Rotation Configuration
ROTATION_ALGORITHM=automatic
ROTATION_INTERVAL=86400
ROTATION_THRESHOLD=0.8
ROTATION_BACKUP_ENABLED=true

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
KEY_DATABASE=lucid_keys
ROTATION_DATABASE=lucid_rotation

# Security Configuration
ROTATION_MASTER_KEY=""
ROTATION_ENCRYPTION_KEY=""
ROTATION_SIGNING_KEY=""
ROTATION_AUDIT_ENABLED=true

# Key Management Configuration
KEY_GENERATION_ALGORITHM=RSA-4096
KEY_EXPORT_FORMAT=PEM
KEY_IMPORT_VALIDATION=true
KEY_ARCHIVE_ENABLED=true

# Performance Configuration
ROTATION_BATCH_SIZE=10
ROTATION_TIMEOUT=300
MAX_CONCURRENT_ROTATIONS=5
ROTATION_RETRY_ATTEMPTS=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
KEY_DATA_DIR=/data/keys
ROTATION_DATA_DIR=/data/rotation
ARCHIVE_DATA_DIR=/data/archive
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - software-vault.env"
log_info "  - role-manager.env"
log_info "  - key-rotation.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/software-vault.env -t pickme/lucid:software-vault ."
log_info "  docker build --env-file $ENV_DIR/role-manager.env -t pickme/lucid:role-manager ."
log_info "  docker build --env-file $ENV_DIR/key-rotation.env -t pickme/lucid:key-rotation ."
