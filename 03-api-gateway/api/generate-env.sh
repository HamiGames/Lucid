#!/bin/bash
# Path: 03-api-gateway/api/generate-env.sh
# Generate .env.api file for API Gateway service
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
ENV_FILE="$SCRIPT_DIR/.env.api"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

log_info "Generating API Gateway environment file: $ENV_FILE"

# =============================================================================
# LOAD SECURE VALUES FROM MASTER FILE
# =============================================================================
log_info "Loading secure values from master secure file..."

# Load from master secure file if available
SECURE_ENV_FILE="$PROJECT_ROOT/configs/environment/.env.secure"
if [ -f "$SECURE_ENV_FILE" ]; then
    log_info "Loading values from $SECURE_ENV_FILE"
    source "$SECURE_ENV_FILE"
    log_success "Loaded secure values from master file"
else
    log_warning "Master secure file not found, generating new values..."

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

    # Function to generate .onion address (v3)
    generate_onion_address() {
        # Generate ed25519 private key
        local temp_dir=$(mktemp -d)
        openssl genpkey -algorithm ed25519 -out "$temp_dir/private_key.pem" 2>/dev/null
        
        # Extract public key and create .onion address
        # For v3 onion addresses: first 32 bytes of public key -> base32 -> add .onion
        local pubkey=$(openssl pkey -in "$temp_dir/private_key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base32 | tr -d '=' | tr '[:upper:]' '[:lower:]')
        
        # Clean up
        rm -rf "$temp_dir"
        
        # Return .onion address (truncate to 56 chars + .onion)
        echo "${pubkey:0:56}.onion"
    }

    # Generate all required secure values
    MONGODB_PASSWORD=$(generate_secure_value 32)
    REDIS_PASSWORD=$(generate_secure_value 32)
    JWT_SECRET=$(generate_secure_value 64)
    ENCRYPTION_KEY=$(generate_hex_key 32)
    SESSION_SECRET=$(generate_secure_value 32)
    TOR_PASSWORD=$(generate_secure_value 32)
    API_SECRET=$(generate_secure_value 32)
    HMAC_KEY=$(generate_secure_value 32)

    log_success "Generated MONGODB_PASSWORD (32 bytes)"
    log_success "Generated REDIS_PASSWORD (32 bytes)"
    log_success "Generated JWT_SECRET (64 bytes)"
    log_success "Generated ENCRYPTION_KEY (256-bit hex)"
    log_success "Generated SESSION_SECRET (32 bytes)"
    log_success "Generated TOR_PASSWORD (32 bytes)"
    log_success "Generated API_SECRET (32 bytes)"
    log_success "Generated HMAC_KEY (32 bytes)"

    # Generate .onion addresses for Tor hidden services
    log_info "Generating Tor .onion addresses..."
    API_GATEWAY_ONION=$(generate_onion_address)
    AUTH_SERVICE_ONION=$(generate_onion_address)
    BLOCKCHAIN_API_ONION=$(generate_onion_address)

    log_success "Generated API_GATEWAY_ONION: $API_GATEWAY_ONION"
    log_success "Generated AUTH_SERVICE_ONION: $AUTH_SERVICE_ONION"
    log_success "Generated BLOCKCHAIN_API_ONION: $BLOCKCHAIN_API_ONION"
fi

# Load foundation config if available
FOUNDATION_ENV="$PROJECT_ROOT/configs/environment/.env.foundation"
if [ -f "$FOUNDATION_ENV" ]; then
    log_info "Loading foundation config from $FOUNDATION_ENV"
    source "$FOUNDATION_ENV"
fi

# Generate .env.api file
cat > "$ENV_FILE" << 'EOF'
# Lucid API Gateway Environment Configuration
# Generated: BUILD_TIMESTAMP_PLACEHOLDER
# File: 03-api-gateway/api/.env.api
# Target: Raspberry Pi 5 (192.168.0.75)

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
BUILD_TIMESTAMP=BUILD_TIMESTAMP_PLACEHOLDER
GIT_SHA=GIT_SHA_PLACEHOLDER
BUILD_PLATFORM=linux/arm64
BUILD_REGISTRY=pickme/lucid
BUILD_TAG=latest

# =============================================================================
# PYTHON CONFIGURATION
# =============================================================================
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================
SERVICE_NAME=api-gateway
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8080
API_GATEWAY_WORKERS=4
API_GATEWAY_TIMEOUT=30
UVICORN_WORKERS=4

# =============================================================================
# ENVIRONMENT
# =============================================================================
LUCID_ENV=production
LUCID_NETWORK=mainnet
LUCID_PLANE=ops
LUCID_CLUSTER_ID=pi-production

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# MongoDB Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid_production
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=MONGODB_PASSWORD_PLACEHOLDER
MONGODB_URI=mongodb://lucid:MONGODB_PASSWORD_PLACEHOLDER@lucid-mongodb:27017/lucid_production?authSource=admin
MONGODB_AUTH_SOURCE=admin
MONGODB_POOL_SIZE=50
MONGODB_MAX_IDLE_TIME=30000
MONGODB_SERVER_SELECTION_TIMEOUT=5000

# Redis Configuration
REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=REDIS_PASSWORD_PLACEHOLDER
REDIS_URI=redis://:REDIS_PASSWORD_PLACEHOLDER@lucid-redis:6379
REDIS_DATABASE=0
REDIS_POOL_SIZE=100
REDIS_MAX_CONNECTIONS=1000
REDIS_TIMEOUT=5

# Elasticsearch Configuration
ELASTICSEARCH_HOST=lucid-elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_URI=http://lucid-elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=lucid

# =============================================================================
# AUTHENTICATION & SECURITY
# =============================================================================
# JWT Configuration
JWT_SECRET=JWT_SECRET_PLACEHOLDER
JWT_SECRET_KEY=JWT_SECRET_PLACEHOLDER
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_EXPIRATION=3600

# Encryption Configuration
ENCRYPTION_KEY=ENCRYPTION_KEY_PLACEHOLDER
ENCRYPTION_ALGORITHM=AES-256-GCM
ENCRYPTION_IV_LENGTH=12

# Session Configuration
SESSION_TIMEOUT=3600
SESSION_SECRET=SESSION_SECRET_PLACEHOLDER
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
HARDWARE_WALLET_TIMEOUT=30
HARDWARE_WALLET_RETRY_ATTEMPTS=3

# =============================================================================
# ROUTING & LOAD BALANCING
# =============================================================================
# API Rate Limiting
API_RATE_LIMIT=1000
RATE_LIMIT_ZONE_SIZE=10m
RATE_LIMIT_RATE=100r/s
RATE_LIMIT_BURST=200

# CORS Configuration
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
CORS_HEADERS=Content-Type,Authorization,X-Requested-With
CORS_CREDENTIALS=true

# =============================================================================
# UPSTREAM SERVICES
# =============================================================================
# Service Mesh Integration
SERVICE_MESH_ENABLED=true
SERVICE_MESH_CONTROLLER_HOST=lucid-service-mesh-controller
SERVICE_MESH_CONTROLLER_PORT=8086

# Authentication Service
AUTH_SERVICE_HOST=lucid-auth-service
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_UPSTREAM=http://lucid-auth-service:8089
AUTH_SERVICE_TIMEOUT=30

# Blockchain Services
BLOCKCHAIN_API_HOST=lucid-blockchain-engine
BLOCKCHAIN_API_PORT=8084
BLOCKCHAIN_API_UPSTREAM=http://lucid-blockchain-engine:8084
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_SESSION_ANCHORING_PORT=8085
BLOCKCHAIN_BLOCK_MANAGER_PORT=8086
BLOCKCHAIN_DATA_CHAIN_PORT=8087

# Session Services
SESSION_API_HOST=lucid-session-api
SESSION_API_PORT=8087
SESSION_PIPELINE_PORT=8081
SESSION_RECORDER_PORT=8082
SESSION_CHUNK_PROCESSOR_PORT=8083

# RDP Services
RDP_SERVER_MANAGER_HOST=lucid-rdp-server-manager
RDP_SERVER_MANAGER_PORT=8081
RDP_SESSION_CONTROLLER_PORT=8082
RDP_RESOURCE_MONITOR_PORT=8090

# Node Management
NODE_MANAGEMENT_HOST=lucid-node-management
NODE_MANAGEMENT_PORT=8095

# Admin Interface
ADMIN_INTERFACE_HOST=lucid-admin-interface
ADMIN_INTERFACE_PORT=8083

# =============================================================================
# LOAD BALANCING
# =============================================================================
LOAD_BALANCE_METHOD=round_robin
HEALTH_CHECK_INTERVAL=30
UPSTREAM_TIMEOUT=30
UPSTREAM_MAX_FAILS=3
UPSTREAM_FAIL_TIMEOUT=30

# =============================================================================
# SSL/TLS CONFIGURATION
# =============================================================================
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/lucid-api-gateway.crt
SSL_KEY_PATH=/etc/ssl/private/lucid-api-gateway.key
SSL_CA_PATH=/etc/ssl/certs/ca.crt

# Security Headers
SECURITY_HEADERS_ENABLED=true
SECURITY_HEADERS_HSTS=true
SECURITY_HEADERS_CSP=true
SECURITY_HEADERS_XFRAME=true

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/lucid/api-gateway.log
LOG_MAX_SIZE=100MB
LOG_MAX_FILES=10
LOG_COMPRESS=true

ACCESS_LOG=/var/log/nginx/access.log
ERROR_LOG=/var/log/nginx/error.log

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PATH=/api/v1/meta/health
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40s

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
# Connection Pooling
CONNECTION_POOL_SIZE=100
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3

# Cache Configuration
CACHE_ENABLED=true
CACHE_SIZE=1GB
CACHE_TTL=3600
CACHE_BACKEND=redis

# =============================================================================
# NGINX CONFIGURATION
# =============================================================================
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024
NGINX_CLIENT_MAX_BODY_SIZE=100M
NGINX_PROXY_BUFFERING=on
NGINX_PROXY_BUFFER_SIZE=4k
NGINX_PROXY_BUFFERS=8 4k

# =============================================================================
# MONITORING & METRICS
# =============================================================================
# Prometheus Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics
PROMETHEUS_INTERVAL=15

# Health Monitoring
MONITORING_ENABLED=true
METRICS_PORT=9216
METRICS_PATH=/metrics

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================
NETWORK_INTERFACE=eth0
NETWORK_MTU=1500
NETWORK_BUFFER_SIZE=65536

# Docker Network
LUCID_NETWORK=lucid-pi-network
LUCID_SUBNET=172.20.0.0/16
LUCID_GATEWAY=172.20.0.1

# =============================================================================
# TOR CONFIGURATION
# =============================================================================
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=TOR_PASSWORD_PLACEHOLDER
TOR_DATA_DIR=/var/lib/tor

# Tor Hidden Service Addresses (.onion)
API_GATEWAY_ONION=API_GATEWAY_ONION_PLACEHOLDER
AUTH_SERVICE_ONION=AUTH_SERVICE_ONION_PLACEHOLDER
BLOCKCHAIN_API_ONION=BLOCKCHAIN_API_ONION_PLACEHOLDER

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
DATA_DIR=/data/api-gateway
LOG_DIR=/var/log/lucid
TEMP_DIR=/tmp/api-gateway
CACHE_DIR=/var/cache/lucid

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================
# Pi Deployment Configuration
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production
PI_SSH_PORT=22

# Container Configuration
CONTAINER_RUNTIME=docker
COMPOSE_PROJECT_NAME=lucid-pi

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true
BACKUP_STORAGE_PATH=/var/backups/lucid

# =============================================================================
# ALERTING CONFIGURATION
# =============================================================================
ALERTING_ENABLED=true
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=80
ALERT_DISK_THRESHOLD=90
ALERT_NETWORK_THRESHOLD=1000
ALERT_ERROR_RATE_THRESHOLD=5

# =============================================================================
# DEBUG & DEVELOPMENT
# =============================================================================
DEBUG=false
DEVELOPMENT_MODE=false
HOT_RELOAD=false

# =============================================================================
# BLOCKCHAIN NETWORK (NO TRON - ISOLATED)
# =============================================================================
# Blockchain Core Settings (TRON-FREE ZONE)
BLOCKCHAIN_NETWORK=lucid
BLOCKCHAIN_CONSENSUS=PoOT
BLOCKCHAIN_BLOCK_TIME=10
BLOCKCHAIN_DIFFICULTY=1

# Session Anchoring
ANCHORING_ENABLED=true
ANCHORING_BATCH_SIZE=10
ANCHORING_INTERVAL=60
ANCHORING_TIMEOUT=30

# =============================================================================
# API VERSION
# =============================================================================
API_VERSION=v1
API_PREFIX=/api/v1

EOF

# Replace placeholders with actual GENERATED values
log_info "Injecting generated secure values into .env.api file..."

sed -i "s/BUILD_TIMESTAMP_PLACEHOLDER/$BUILD_TIMESTAMP/g" "$ENV_FILE"
sed -i "s/GIT_SHA_PLACEHOLDER/$GIT_SHA/g" "$ENV_FILE"

# Replace with GENERATED secure values
sed -i "s|MONGODB_PASSWORD_PLACEHOLDER|$MONGODB_PASSWORD|g" "$ENV_FILE"
sed -i "s|REDIS_PASSWORD_PLACEHOLDER|$REDIS_PASSWORD|g" "$ENV_FILE"
sed -i "s|JWT_SECRET_PLACEHOLDER|$JWT_SECRET|g" "$ENV_FILE"
sed -i "s|ENCRYPTION_KEY_PLACEHOLDER|$ENCRYPTION_KEY|g" "$ENV_FILE"
sed -i "s|SESSION_SECRET_PLACEHOLDER|$SESSION_SECRET|g" "$ENV_FILE"
sed -i "s|TOR_PASSWORD_PLACEHOLDER|$TOR_PASSWORD|g" "$ENV_FILE"

# Replace with GENERATED .onion addresses
sed -i "s|API_GATEWAY_ONION_PLACEHOLDER|$API_GATEWAY_ONION|g" "$ENV_FILE"
sed -i "s|AUTH_SERVICE_ONION_PLACEHOLDER|$AUTH_SERVICE_ONION|g" "$ENV_FILE"
sed -i "s|BLOCKCHAIN_API_ONION_PLACEHOLDER|$BLOCKCHAIN_API_ONION|g" "$ENV_FILE"

log_success "API Gateway environment file generated: $ENV_FILE"

# Validate no placeholders remain
if grep -q "_PLACEHOLDER" "$ENV_FILE"; then
    log_error "Some placeholders were not replaced! This should not happen."
    grep "_PLACEHOLDER" "$ENV_FILE" || true
    exit 1
else
    log_success "All placeholders replaced with generated values"
fi

# Save generated secrets to a secure reference file
SECRETS_FILE="$SCRIPT_DIR/.env.api.secrets"
log_info "Saving generated secrets to: $SECRETS_FILE"

cat > "$SECRETS_FILE" << EOF
# API Gateway Generated Secrets Reference
# Generated: $(date)
# WARNING: Keep this file secure! Never commit to version control!

MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
SESSION_SECRET=$SESSION_SECRET
TOR_PASSWORD=$TOR_PASSWORD
API_SECRET=$API_SECRET
HMAC_KEY=$HMAC_KEY

# Tor Hidden Service Addresses
API_GATEWAY_ONION=$API_GATEWAY_ONION
AUTH_SERVICE_ONION=$AUTH_SERVICE_ONION
BLOCKCHAIN_API_ONION=$BLOCKCHAIN_API_ONION
EOF

chmod 600 "$SECRETS_FILE"
log_success "Secrets saved to $SECRETS_FILE (permissions: 600)"

echo ""
log_info "==================================================================="
log_info "API Gateway Environment Generation Complete!"
log_info "==================================================================="
echo ""
log_info "Generated files:"
log_info "  • .env.api          : $ENV_FILE"
log_info "  • .env.api.secrets  : $SECRETS_FILE"
echo ""
log_info "Build details:"
log_info "  • Build timestamp   : $BUILD_TIMESTAMP"
log_info "  • Git SHA           : $GIT_SHA"
echo ""
log_info "Generated secure values:"
log_info "  • MongoDB Password  : ${MONGODB_PASSWORD:0:8}... (32 bytes)"
log_info "  • Redis Password    : ${REDIS_PASSWORD:0:8}... (32 bytes)"
log_info "  • JWT Secret        : ${JWT_SECRET:0:12}... (64 bytes)"
log_info "  • Encryption Key    : ${ENCRYPTION_KEY:0:16}... (256-bit hex)"
log_info "  • Session Secret    : ${SESSION_SECRET:0:8}... (32 bytes)"
log_info "  • TOR Password      : ${TOR_PASSWORD:0:8}... (32 bytes)"
echo ""
log_info "Generated .onion addresses:"
log_info "  • API Gateway       : $API_GATEWAY_ONION"
log_info "  • Auth Service      : $AUTH_SERVICE_ONION"
log_info "  • Blockchain API    : $BLOCKCHAIN_API_ONION"
echo ""
log_warning "SECURITY NOTICE:"
log_warning "  • Keep .env.api.secrets file secure (chmod 600)"
log_warning "  • Never commit .env.api.secrets to version control"
log_warning "  • Backup secrets file to secure location"
log_warning "  • Rotate keys regularly in production"
echo ""
log_success "API Gateway .env.api generation complete!"

