#!/bin/bash
# Path: infrastructure/docker/users/build-env.sh
# Build Environment Script for Lucid User Services
# Generates .env files for user management containers

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

log_info "Building environment files for Lucid User Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# User Manager Environment
log_info "Creating user-manager.env..."
cat > "$ENV_DIR/user-manager.env" << EOF
# Lucid User Manager Environment
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
SERVICE_NAME=user-manager
SERVICE_PORT=8104

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
USER_DATABASE=lucid_users
USER_COLLECTION=users
PROFILE_COLLECTION=profiles

# Authentication Configuration
JWT_SECRET_KEY=""
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Security Configuration
PASSWORD_HASH_ROUNDS=12
ENCRYPTION_KEY=""
BCRYPT_SALT_ROUNDS=12
SESSION_SECRET=""

# User Configuration
MAX_USERS=10000
USER_SESSION_TIMEOUT=3600
USER_PROFILE_LIMIT=5
USER_DATA_RETENTION_DAYS=365

# TRON Integration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_WALLET_CREATION=true
TRON_WALLET_BACKUP=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
USER_DATA_DIR=/data/users
USER_PROFILES_DIR=/data/profiles
LOGS_DIR=/data/logs
EOF

# Authentication Service Environment
log_info "Creating authentication.env..."
cat > "$ENV_DIR/authentication.env" << EOF
# Lucid Authentication Service Environment
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
SERVICE_NAME=authentication
SERVICE_PORT=8085

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
AUTH_DATABASE=lucid_auth
USER_COLLECTION=users
SESSION_COLLECTION=sessions

# Authentication Configuration
AUTH_METHOD=jwt
SESSION_MANAGEMENT=true
MULTI_FACTOR_AUTH=false

# Security Configuration
PASSWORD_HASH_ROUNDS=12
ENCRYPTION_KEY=""
BCRYPT_SALT_ROUNDS=12
SESSION_SECRET=""

# Session Configuration
SESSION_TIMEOUT=3600
SESSION_CLEANUP_INTERVAL=300
MAX_SESSIONS_PER_USER=5
SESSION_ENCRYPTION=true

# TRON Integration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_WALLET_AUTH=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8081
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
AUTH_DATA_DIR=/data/auth
SESSIONS_DIR=/data/sessions
LOGS_DIR=/data/logs
EOF

# Authentication Service Distroless Environment
log_info "Creating authentication-service.distroless.env..."
cat > "$ENV_DIR/authentication-service.distroless.env" << EOF
# Lucid Authentication Service Distroless Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=production

# Service Configuration
SERVICE_NAME=authentication-service
SERVICE_PORT=8085

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
AUTH_DATABASE=lucid_auth
USER_COLLECTION=users
SESSION_COLLECTION=sessions

# Authentication Configuration
AUTH_METHOD=jwt
SESSION_MANAGEMENT=true
MULTI_FACTOR_AUTH=true

# Security Configuration
PASSWORD_HASH_ROUNDS=14
ENCRYPTION_KEY=""
BCRYPT_SALT_ROUNDS=14
SESSION_SECRET=""

# Session Configuration
SESSION_TIMEOUT=1800
SESSION_CLEANUP_INTERVAL=180
MAX_SESSIONS_PER_USER=3
SESSION_ENCRYPTION=true

# TRON Integration
TRON_NETWORK=mainnet
TRON_RPC_URL=https://api.trongrid.io
TRON_WALLET_AUTH=true

# Rate Limiting
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=10

# CORS Configuration
CORS_ORIGINS=https://admin.lucid.local,https://api.lucid.local
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS

# Logging Configuration
LOG_LEVEL=WARNING
LOG_FORMAT=json

# Data Directories
AUTH_DATA_DIR=/data/auth
SESSIONS_DIR=/data/sessions
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - user-manager.env"
log_info "  - authentication.env"
log_info "  - authentication-service.distroless.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/user-manager.env -t pickme/lucid:user-manager ."
log_info "  docker build --env-file $ENV_DIR/authentication.env -t pickme/lucid:authentication ."
log_info "  docker build --env-file $ENV_DIR/authentication-service.distroless.env -t pickme/lucid:authentication-service ."
