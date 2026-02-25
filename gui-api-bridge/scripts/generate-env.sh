#!/bin/bash
# GUI API Bridge Environment Generator
# File: gui-api-bridge/scripts/generate-env.sh
# Purpose: Generate environment configuration for GUI API Bridge
# Aligned with 03-api-gateway patterns
# No hardcoded values - all generated from environment or defaults

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

log_info "GUI API Bridge Environment Generator"
log_info "Script Dir: $SCRIPT_DIR"
log_info "Project Dir: $PROJECT_DIR"
log_info "Workspace Dir: $WORKSPACE_DIR"
echo ""

# Configuration directories
CONFIG_DIR="$PROJECT_DIR/config"
TEMPLATE_FILE="$CONFIG_DIR/env.gui-api-bridge.template"

# Create config directory if needed
if [ ! -d "$CONFIG_DIR" ]; then
    log_info "Creating config directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

# Helper function to get or generate a secret
get_or_generate_secret() {
    local secret_name="$1"
    local secret_length="${2:-32}"
    
    # Try to get from environment
    local env_var_name="${secret_name}_SECRET"
    if [ -n "${!env_var_name:-}" ]; then
        echo "${!env_var_name}"
        return
    fi
    
    # Generate new secret
    if command -v openssl &> /dev/null; then
        openssl rand -base64 "$secret_length" | tr -d '\n'
    elif command -v python3 &> /dev/null; then
        python3 -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes($secret_length)).decode())" | tr -d '\n'
    else
        # Fallback: use /dev/urandom if available
        head -c "$secret_length" /dev/urandom | base64 | tr -d '\n'
    fi
}

log_info "Generating environment configuration..."
echo ""

# Generate environment file
OUTPUT_FILE="$PROJECT_DIR/.env"

log_info "Creating environment file: $OUTPUT_FILE"
cat > "$OUTPUT_FILE" << EOF
# ========================================================================
# Lucid GUI API Bridge Environment Configuration
# ========================================================================
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# Service: gui-api-bridge
# Port: 8102
# ========================================================================

# Service Configuration
SERVICE_NAME=gui-api-bridge
SERVICE_VERSION=1.0.0
HOST=0.0.0.0
PORT=8102
SERVICE_URL=http://lucid-gui-api-bridge:8102

# Environment
ENVIRONMENT=${ENVIRONMENT:-production}
DEBUG=${DEBUG:-false}
LUCID_ENV=${LUCID_ENV:-production}
LUCID_PLATFORM=${LUCID_PLATFORM:-arm64}
PROJECT_ROOT=${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}

# Database Configuration
MONGODB_URL=${MONGODB_URL:-mongodb://lucid:\${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin}
MONGODB_URI=
REDIS_URL=${REDIS_URL:-redis://:\${REDIS_PASSWORD}@lucid-redis:6379/0}

# Backend Service URLs (Required in production)
API_GATEWAY_URL=http://lucid-api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089
SESSION_API_URL=http://lucid-session-api:8087
NODE_MANAGEMENT_URL=http://lucid-node-management:8095
ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
TRON_PAYMENT_URL=http://lucid-tron-client:8091

# Security Configuration
JWT_SECRET_KEY=$(get_or_generate_secret "JWT" 32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS Configuration
ALLOWED_HOSTS=*
CORS_ORIGINS=*

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST_SIZE=200

# SSL Configuration
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/gui-api-bridge.crt
SSL_KEY_PATH=/etc/ssl/private/gui-api-bridge.key

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30s

# ========================================================================
# Note: For production deployment, ensure the following are set:
# ========================================================================
# - MONGODB_PASSWORD: MongoDB password
# - REDIS_PASSWORD: Redis password
# - JWT_SECRET_KEY: Strong JWT secret (auto-generated if not provided)
# - All backend service URLs should point to valid service instances
#
# Load sensitive values from a separate .env.secrets file:
#   docker-compose --env-file .env --env-file .env.secrets up
# ========================================================================
EOF

log_success "Environment file created: $OUTPUT_FILE"
echo ""

# Create template file if it doesn't exist
if [ ! -f "$TEMPLATE_FILE" ]; then
    log_info "Creating environment template: $TEMPLATE_FILE"
    cat > "$TEMPLATE_FILE" << 'EOF'
# ========================================================================
# Lucid GUI API Bridge Environment Template
# ========================================================================
# Copy this file to .env and configure the values
# For production: Use strong secrets and correct service URLs
# ========================================================================

# Service Configuration
SERVICE_NAME=gui-api-bridge
SERVICE_VERSION=1.0.0
HOST=0.0.0.0
PORT=8102
SERVICE_URL=http://lucid-gui-api-bridge:8102

# Environment (development, staging, production)
ENVIRONMENT=production
DEBUG=false
LUCID_ENV=production
LUCID_PLATFORM=arm64
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Database Configuration
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
MONGODB_URI=
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0

# Backend Service URLs (must be configured for production)
API_GATEWAY_URL=http://lucid-api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089
SESSION_API_URL=http://lucid-session-api:8087
NODE_MANAGEMENT_URL=http://lucid-node-management:8095
ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
TRON_PAYMENT_URL=http://lucid-tron-client:8091

# Security Configuration
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS Configuration
ALLOWED_HOSTS=*
CORS_ORIGINS=*

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST_SIZE=200

# SSL Configuration
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/gui-api-bridge.crt
SSL_KEY_PATH=/etc/ssl/private/gui-api-bridge.key

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30s

# ========================================================================
# Sensitive values to be provided via .env.secrets:
# ========================================================================
# MONGODB_PASSWORD=your-mongodb-password
# REDIS_PASSWORD=your-redis-password
# ========================================================================
EOF
    log_success "Template file created: $TEMPLATE_FILE"
else
    log_info "Template file already exists: $TEMPLATE_FILE"
fi

echo ""
echo "=========================================="
echo "Environment generation completed!"
echo "=========================================="
echo ""
log_success "Environment file: $OUTPUT_FILE"
log_success "Template file: $TEMPLATE_FILE"
echo ""
log_info "Next steps:"
echo "  1. Review the generated .env file"
echo "  2. Set MONGODB_PASSWORD and REDIS_PASSWORD in .env"
echo "  3. Verify all service URLs are correct"
echo "  4. Run: docker-compose up -d lucid-gui-api-bridge"
echo ""
