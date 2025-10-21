#!/bin/bash
# Path: infrastructure/docker/tools/build-env.sh
# Build Environment Script for Lucid Tools Services
# Generates .env files for core infrastructure tools containers

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

log_info "Building environment files for Lucid Tools Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# API Gateway Environment
log_info "Creating api-gateway.env..."
cat > "$ENV_DIR/api-gateway.env" << EOF
# Lucid API Gateway Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev
LUCID_PLANE=ops
LUCID_CLUSTER_ID=dev-core

# Service Configuration
SERVICE_NAME=api-gateway
SERVICE_PORT=8080
SERVICE_HOST=0.0.0.0

# NGINX Configuration
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024
NGINX_CLIENT_MAX_BODY_SIZE=100M

# Upstream Services
API_SERVER_UPSTREAM=http://lucid_api:8081
AUTH_SERVICE_UPSTREAM=http://authentication:8085
BLOCKCHAIN_API_UPSTREAM=http://blockchain-api:8084

# Load Balancing
LOAD_BALANCE_METHOD=round_robin
HEALTH_CHECK_INTERVAL=30
UPSTREAM_TIMEOUT=30

# Security Configuration
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/lucid.crt
SSL_KEY_PATH=/etc/ssl/private/lucid.key

# Rate Limiting
RATE_LIMIT_ZONE_SIZE=10m
RATE_LIMIT_RATE=10r/s
RATE_LIMIT_BURST=20

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8081
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_HEADERS=Content-Type,Authorization

# Logging Configuration
LOG_LEVEL=info
LOG_FORMAT=json
ACCESS_LOG=/var/log/nginx/access.log
ERROR_LOG=/var/log/nginx/error.log

# Health Check Configuration
HEALTH_CHECK_PATH=/health
HEALTH_CHECK_INTERVAL=30
EOF

# API Server Environment
log_info "Creating api-server.env..."
cat > "$ENV_DIR/api-server.env" << EOF
# Lucid API Server Environment
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
SERVICE_NAME=api-server
SERVICE_PORT=8081
SERVICE_HOST=0.0.0.0

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
REDIS_URL=redis://lucid_redis:6379/0

# Authentication Configuration
JWT_SECRET_KEY=""
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Security Configuration
ENCRYPTION_KEY=""
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Performance Configuration
UVICORN_WORKERS=4
UVICORN_MAX_REQUESTS=1000
UVICORN_TIMEOUT=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
DATA_DIR=/data/api
LOGS_DIR=/data/logs
TEMP_DIR=/tmp/api

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
EOF

# Tor Proxy Environment
log_info "Creating tor-proxy.env..."
cat > "$ENV_DIR/tor-proxy.env" << EOF
# Lucid Tor Proxy Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev
LUCID_PLANE=ops
LUCID_CLUSTER_ID=dev-core

# Service Configuration
SERVICE_NAME=tor-proxy
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Tor Configuration
TOR_DATA_DIRECTORY=/var/lib/tor
TOR_RUN_DIRECTORY=/run/tor
TOR_LOG_DIRECTORY=/var/log/tor

# SOCKS Proxy Configuration
SOCKS_PORT=9050
SOCKS_POLICY=accept 127.0.0.1/32
SOCKS_POLICY_REJECT=reject *

# Control Port Configuration
CONTROL_PORT=9051
CONTROL_SOCKET_ENABLED=true
COOKIE_AUTHENTICATION=true
TOR_CONTROL_PASSWORD=""

# Onion Service Configuration
HIDDEN_SERVICE_DIR=/var/lib/tor/hidden_service
HIDDEN_SERVICE_PORT=80
HIDDEN_SERVICE_VERSION=3
ONION_API_GATEWAY=""
ONION_API_SERVER=""
ONION_TUNNEL=""
ONION_MONGO=""

# Network Configuration
EXIT_POLICY=reject *:*
DISABLE_NETWORK=0
CLIENT_REJECT_INTERNAL_ADDRESSES=1

# Logging Configuration
LOG_LEVEL=notice
LOG_FILE=/var/log/tor/notices.log
LOG_INFO_FILE=/var/log/tor/info.log

# Security Configuration
STRICT_NODES=1
FASCIST_FIREWALL=1
EOF

# Tunnel Tools Environment
log_info "Creating tunnel-tools.env..."
cat > "$ENV_DIR/tunnel-tools.env" << EOF
# Lucid Tunnel Tools Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=tunnel-tools
SERVICE_PORT=7000

# Tunnel Configuration
TUNNEL_TYPE=wireguard
TUNNEL_INTERFACE=wg0
TUNNEL_PORT=51820

# Network Configuration
TUNNEL_NETWORK=10.0.0.0/24
TUNNEL_DNS=1.1.1.1,1.0.0.1
TUNNEL_MTU=1420

# Security Configuration
TUNNEL_PRIVATE_KEY=""
TUNNEL_PUBLIC_KEY=""
TUNNEL_PRESHARED_KEY=""

# Performance Configuration
TUNNEL_PERSISTENT_KEEPALIVE=25
TUNNEL_ALLOWED_IPS=0.0.0.0/0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
EOF

# Server Tools Environment
log_info "Creating server-tools.env..."
cat > "$ENV_DIR/server-tools.env" << EOF
# Lucid Server Tools Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=server-tools
TOOLS_DIR=/opt/lucid/tools
SCRIPTS_DIR=/opt/lucid/scripts
LOG_DIR=/var/log/lucid

# Database Configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Network Configuration
TOR_PROXY_HOST=tor-proxy
TOR_PROXY_PORT=9050
API_GATEWAY_HOST=lucid_api_gateway
API_GATEWAY_PORT=8080
API_SERVER_HOST=lucid_api
API_SERVER_PORT=8081

# Health Check Configuration
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=3

# Backup Configuration
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ROTATION_SIZE=100MB
LOG_ROTATION_COUNT=10

# Security Configuration
SECURE_MODE=true
ENCRYPTION_KEY=""
EOF

# OpenAPI Gateway Environment
log_info "Creating openapi-gateway.env..."
cat > "$ENV_DIR/openapi-gateway.env" << EOF
# Lucid OpenAPI Gateway Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=openapi-gateway
SERVICE_PORT=8082
SERVICE_HOST=0.0.0.0

# NGINX Configuration
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024

# Upstream Services
OPENAPI_SERVER_UPSTREAM=http://openapi-server:8083

# Security Configuration
SSL_ENABLED=false
SSL_CERT_PATH=/etc/ssl/certs/lucid.crt
SSL_KEY_PATH=/etc/ssl/private/lucid.key

# Rate Limiting
RATE_LIMIT_ZONE_SIZE=10m
RATE_LIMIT_RATE=5r/s
RATE_LIMIT_BURST=10

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8082
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS

# Logging Configuration
LOG_LEVEL=info
LOG_FORMAT=json
ACCESS_LOG=/var/log/nginx/access.log
ERROR_LOG=/var/log/nginx/error.log
EOF

# OpenAPI Server Environment
log_info "Creating openapi-server.env..."
cat > "$ENV_DIR/openapi-server.env" << EOF
# Lucid OpenAPI Server Environment
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
SERVICE_NAME=openapi-server
SERVICE_PORT=8083
SERVICE_HOST=0.0.0.0

# OpenAPI Configuration
OPENAPI_TITLE=Lucid API
OPENAPI_VERSION=1.0.0
OPENAPI_DESCRIPTION=Lucid Remote Desktop Protocol API

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Performance Configuration
UVICORN_WORKERS=2
UVICORN_MAX_REQUESTS=500

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Documentation Configuration
DOCS_URL=/docs
REDOC_URL=/redoc
OPENAPI_URL=/openapi.json
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - api-gateway.env"
log_info "  - api-server.env"
log_info "  - tor-proxy.env"
log_info "  - tunnel-tools.env"
log_info "  - server-tools.env"
log_info "  - openapi-gateway.env"
log_info "  - openapi-server.env"

# Also create .env.api in 03-api-gateway/api/ directory for direct service use
log_info "Creating .env.api in 03-api-gateway/api/ directory..."
API_GATEWAY_DIR="$PROJECT_ROOT/03-api-gateway/api"
mkdir -p "$API_GATEWAY_DIR"

# Create .env.api from api-gateway.env
cp "$ENV_DIR/api-gateway.env" "$API_GATEWAY_DIR/.env.api"
log_info "  - Created $API_GATEWAY_DIR/.env.api"

log_success "API Gateway environment file also created in 03-api-gateway/api/ directory"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/api-gateway.env -t pickme/lucid:api-gateway ."
log_info "  docker build --env-file $ENV_DIR/api-server.env -t pickme/lucid:api-server ."
log_info "  docker build --env-file $ENV_DIR/tor-proxy.env -t pickme/lucid:tor-proxy ."
log_info "  docker build --env-file $ENV_DIR/tunnel-tools.env -t pickme/lucid:tunnel-tools ."
log_info "  docker build --env-file $ENV_DIR/server-tools.env -t pickme/lucid:server-tools ."
log_info "  docker build --env-file $ENV_DIR/openapi-gateway.env -t pickme/lucid:openapi-gateway ."
log_info "  docker build --env-file $ENV_DIR/openapi-server.env -t pickme/lucid:openapi-server ."
