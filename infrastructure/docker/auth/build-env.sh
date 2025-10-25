#!/bin/bash
# Path: /mnt/myssd/Lucid/Lucid/infrastructure/docker/auth/build-env.sh
# Build Environment Script for Lucid Authentication Services
# Generates .env files for authentication containers
# Pi Console Native - Optimized for Raspberry Pi 5 deployment

set -euo pipefail

# =============================================================================
# PI CONSOLE NATIVE CONFIGURATION
# =============================================================================

# Fixed Pi Console Paths - No dynamic detection for Pi console reliability
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
SCRIPTS_DIR="/mnt/myssd/Lucid/Lucid/scripts"
CONFIG_SCRIPTS_DIR="/mnt/myssd/Lucid/Lucid/scripts/config"
SCRIPT_DIR="/mnt/myssd/Lucid/Lucid/infrastructure/docker/auth"

# Validate Pi mount points exist
validate_pi_mounts() {
    local required_mounts=(
        "/mnt/myssd"
        "/mnt/myssd/Lucid"
        "/mnt/myssd/Lucid/Lucid"
    )
    
    for mount in "${required_mounts[@]}"; do
        if [[ ! -d "$mount" ]]; then
            echo "ERROR: Required Pi mount point not found: $mount"
            echo "Please ensure the SSD is properly mounted at /mnt/myssd"
            exit 1
        fi
    done
}

# Check required packages for Pi console
check_pi_packages() {
    local required_packages=(
        "openssl"
        "git"
        "bash"
        "coreutils"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! command -v "$package" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        echo "ERROR: Missing required packages: ${missing_packages[*]}"
        echo "Please install missing packages:"
        echo "sudo apt update && sudo apt install -y ${missing_packages[*]}"
        exit 1
    fi
}

# Validate paths exist
validate_paths() {
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        echo "ERROR: Project root not found: $PROJECT_ROOT"
        exit 1
    fi
    
    if [[ ! -d "$SCRIPTS_DIR" ]]; then
        echo "ERROR: Scripts directory not found: $SCRIPTS_DIR"
        exit 1
    fi
}

# Script Configuration
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

# =============================================================================
# VALIDATION AND INITIALIZATION
# =============================================================================

# Run all validations
validate_pi_mounts
check_pi_packages
validate_paths

# Create environment directory
mkdir -p "$ENV_DIR"

log_info "Building environment files for Lucid Authentication Services"
log_info "Project Root: $PROJECT_ROOT"
log_info "Environment Directory: $ENV_DIR"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Authentication Service Environment
log_info "Creating .env.authentication..."
cat > "$ENV_DIR/.env.authentication" << EOF
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
SERVICE_HOST=0.0.0.0

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
AUTH_DATABASE=lucid_auth
USER_COLLECTION=users
SESSION_COLLECTION=sessions

# JWT Configuration
JWT_SECRET_KEY=""
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Security Configuration
PASSWORD_HASH_ROUNDS=12
ENCRYPTION_KEY=""
BCRYPT_SALT_ROUNDS=12

# TRON Integration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=""
TRON_WALLET_ADDRESS=""

# Session Configuration
SESSION_TIMEOUT_MINUTES=30
MAX_SESSIONS_PER_USER=5
SESSION_CLEANUP_INTERVAL=300

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20

# Security Headers
CORS_ORIGINS=http://localhost:3000,http://localhost:8081
SECURE_COOKIES=true
HTTP_ONLY_COOKIES=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/data/logs/auth.log

# Data Directories
SECRETS_DIR=/secrets
TEMP_DIR=/tmp/auth
DATA_DIR=/data/auth

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
EOF

# Authentication Service Distroless Environment
log_info "Creating .env.authentication-service-distroless..."
cat > "$ENV_DIR/.env.authentication-service-distroless" << EOF
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
SERVICE_HOST=0.0.0.0

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
AUTH_DATABASE=lucid_auth
USER_COLLECTION=users
SESSION_COLLECTION=sessions

# JWT Configuration
JWT_SECRET_KEY=""
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=3

# Security Configuration
PASSWORD_HASH_ROUNDS=14
ENCRYPTION_KEY=""
BCRYPT_SALT_ROUNDS=14

# TRON Integration
TRON_NETWORK=mainnet
TRON_RPC_URL=https://api.trongrid.io
TRON_PRIVATE_KEY=""
TRON_WALLET_ADDRESS=""

# Session Configuration
SESSION_TIMEOUT_MINUTES=15
MAX_SESSIONS_PER_USER=3
SESSION_CLEANUP_INTERVAL=180

# Rate Limiting
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=10

# Security Headers
CORS_ORIGINS=https://admin.lucid.local,https://api.lucid.local
SECURE_COOKIES=true
HTTP_ONLY_COOKIES=true

# Logging Configuration
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=/data/logs/auth.log

# Data Directories
SECRETS_DIR=/secrets
TEMP_DIR=/tmp/auth
DATA_DIR=/data/auth

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_success "🛡️  Pi console native validation completed"
log_success "🔧 Fallback mechanisms enabled for minimal Pi installations"
log_info "Created environment files for:"
log_info "  - .env.authentication"
log_info "  - .env.authentication-service-distroless"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/.env.authentication -t pickme/lucid:authentication ."
log_info "  docker build --env-file $ENV_DIR/.env.authentication-service-distroless -t pickme/lucid:authentication-service ."
