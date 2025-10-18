#!/bin/bash
# Path: infrastructure/docker/admin/build-env.sh
# Build Environment Script for Lucid Admin UI Services
# Generates .env files for admin interface containers

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

log_info "Building environment files for Lucid Admin UI Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Admin UI Environment
log_info "Creating admin-ui.env..."
cat > "$ENV_DIR/admin-ui.env" << EOF
# Lucid Admin UI Environment
# Generated: $(date)

# Node.js Configuration
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
PORT=3000
HOSTNAME=0.0.0.0

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev
LUCID_PLANE=ops
LUCID_CLUSTER_ID=dev-core

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8081
NEXT_PUBLIC_WS_URL=ws://localhost:8081/ws
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8080

# Authentication Configuration
NEXT_PUBLIC_AUTH_URL=http://localhost:8085
NEXT_PUBLIC_JWT_SECRET=""

# Database Configuration
NEXT_PUBLIC_MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Blockchain Configuration
NEXT_PUBLIC_TRON_NETWORK=shasta
NEXT_PUBLIC_TRON_RPC_URL=https://api.shasta.trongrid.io

# Security Configuration
NEXT_PUBLIC_ENCRYPTION_KEY=""
NEXT_PUBLIC_TOR_ENABLED=true

# UI Configuration
NEXT_PUBLIC_APP_NAME=Lucid Admin
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_DEBUG_MODE=false

# Performance Configuration
NEXT_PUBLIC_MAX_FILE_SIZE=104857600
NEXT_PUBLIC_CHUNK_SIZE=8388608

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - admin-ui.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/admin-ui.env -t pickme/lucid:admin-ui ."
