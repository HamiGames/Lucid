#!/bin/bash

# Generate .env.distroless file for Raspberry Pi deployment
# This script creates environment variables for distroless deployment

set -e

# Project root configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# Configuration
ENV_FILE="configs/environment/.env.distroless"

echo "Generating .env.distroless for Lucid project..."
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Create directory if it doesn't exist
mkdir -p "$(dirname "$ENV_FILE")"

# Function to generate secure random string (aligned with generate-secure-keys.sh)
generate_secure_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret (64 characters) - aligned with generate-secure-keys.sh
generate_jwt_secret() {
    openssl rand -base64 48 | tr -d "=+/"
}

# Function to generate encryption key (32 bytes = 256 bits) - aligned with generate-secure-keys.sh
generate_encryption_key() {
    openssl rand -hex 32
}

# Function to generate database passwords - aligned with generate-secure-keys.sh
generate_db_password() {
    openssl rand -base64 24 | tr -d "=+/"
}

# Generate secure random values using the same functions as generate-secure-keys.sh
MONGODB_PASSWORD=$(generate_db_password)
JWT_SECRET_KEY=$(generate_jwt_secret)
REDIS_PASSWORD=$(generate_db_password)
ELASTICSEARCH_PASSWORD=$(generate_db_password)
USER_ID=$(openssl rand -hex 16)
SESSION_SECRET=$(generate_secure_string 32)
ENCRYPTION_KEY=$(generate_encryption_key)
TOR_CONTROL_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/")

# Create .env.distroless file
cat > "$ENV_FILE" << 'EOF'
# Lucid Distroless Environment Configuration
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Target: Raspberry Pi 5 (192.168.0.75)
# Architecture: ARM64

# =============================================================================
# DISTROLESS BASE CONFIGURATION
# =============================================================================

# Distroless Base Image
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# Build Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
COMPOSE_DOCKER_CLI_BUILD=1

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Main Network
LUCID_MAIN_NETWORK=lucid-pi-network
LUCID_MAIN_SUBNET=172.20.0.0/16
LUCID_MAIN_GATEWAY=172.20.0.1

# TRON Isolated Network
LUCID_TRON_NETWORK=lucid-tron-isolated
LUCID_TRON_SUBNET=172.21.0.0/16
LUCID_TRON_GATEWAY=172.21.0.1

# GUI Network
LUCID_GUI_NETWORK=lucid-gui-network
LUCID_GUI_SUBNET=172.22.0.0/16
LUCID_GUI_GATEWAY=172.22.0.1

# Distroless Production Network
LUCID_DISTROLESS_PROD_NETWORK=lucid-distroless-production
LUCID_DISTROLESS_PROD_SUBNET=172.23.0.0/16
LUCID_DISTROLESS_PROD_GATEWAY=172.23.0.1

# Distroless Development Network
LUCID_DISTROLESS_DEV_NETWORK=lucid-distroless-dev
LUCID_DISTROLESS_DEV_SUBNET=172.24.0.0/16
LUCID_DISTROLESS_DEV_GATEWAY=172.24.0.1

# Multi-Stage Build Network
LUCID_MULTI_STAGE_NETWORK=lucid-multi-stage-network
LUCID_MULTI_STAGE_SUBNET=172.25.0.0/16
LUCID_MULTI_STAGE_GATEWAY=172.25.0.1

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# MongoDB Configuration
MONGODB_HOST=lucid-mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=lucid
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=${MONGODB_PASSWORD}
MONGODB_AUTH_SOURCE=admin
MONGODB_RETRY_WRITES=false
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin&retryWrites=false

# Redis Configuration
REDIS_HOST=lucid-redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379

# Elasticsearch Configuration
ELASTICSEARCH_HOST=lucid-elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
ELASTICSEARCH_URL=http://elastic:${ELASTICSEARCH_PASSWORD}@lucid-elasticsearch:9200

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Session Configuration
SESSION_SECRET=${SESSION_SECRET}
SESSION_TIMEOUT=1800

# User Configuration
USER_ID=${USER_ID}
USER_ROLE=admin

# Encryption Configuration
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENCRYPTION_ALGORITHM=AES-256-GCM

# Tor Configuration
TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

# API Gateway
API_GATEWAY_HOST=api-gateway
API_GATEWAY_PORT=8080
API_GATEWAY_URL=http://api-gateway:8080

# Auth Service
AUTH_SERVICE_HOST=lucid-auth-service
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Blockchain Engine
BLOCKCHAIN_ENGINE_HOST=blockchain-engine
BLOCKCHAIN_ENGINE_PORT=8084
BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084

# Service Mesh
SERVICE_MESH_HOST=service-mesh
SERVICE_MESH_PORT=8500
SERVICE_MESH_URL=http://service-mesh:8500

# Session API
SESSION_API_HOST=session-api
SESSION_API_PORT=8087
SESSION_API_URL=http://session-api:8087

# RDP Services
RDP_SERVER_MANAGER_HOST=rdp-server-manager
RDP_SERVER_MANAGER_PORT=8095
RDP_SERVER_MANAGER_URL=http://rdp-server-manager:8095

# Admin Interface
ADMIN_INTERFACE_HOST=admin-interface
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_URL=http://admin-interface:8083

# TRON Payment Services
TRON_CLIENT_HOST=tron-client
TRON_CLIENT_PORT=8091
TRON_CLIENT_URL=http://tron-client:8091

# =============================================================================
# DISTROLESS RUNTIME CONFIGURATION
# =============================================================================

# Runtime Environment
LUCID_ENV=production
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64

# Container Configuration
CONTAINER_USER=65532
CONTAINER_GROUP=65532
CONTAINER_UID=65532
CONTAINER_GID=65532

# Security Options
SECURITY_OPT_NO_NEW_PRIVILEGES=true
SECURITY_OPT_READONLY_ROOTFS=true
SECURITY_OPT_NO_EXEC=true

# Capability Configuration
CAP_DROP=ALL
CAP_ADD=NET_BIND_SERVICE

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Level
LOG_LEVEL=INFO
LOG_FORMAT=json

# Log Output
LOG_OUTPUT=stdout
LOG_FILE=/dev/stdout

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Metrics Configuration
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics

# =============================================================================
# TRON BLOCKCHAIN CONFIGURATION
# =============================================================================

# TRON Network Configuration
TRON_NETWORK=shasta
TRON_NODE_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=your_private_key_here
TRON_ADDRESS=your_address_here

# USDT Configuration
USDT_CONTRACT_ADDRESS=TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
USDT_DECIMALS=6

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

# Deployment Target
DEPLOYMENT_TARGET=raspberry-pi
DEPLOYMENT_HOST=192.168.0.75
DEPLOYMENT_USER=pickme
DEPLOYMENT_PATH=/mnt/myssd/Lucid/Lucid

# Registry Configuration
REGISTRY=ghcr.io
REPOSITORY=hamigames/lucid
IMAGE_TAG=latest-arm64

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================

# Build Platform
BUILD_PLATFORM=linux/arm64
BUILD_ARCH=arm64
BUILD_OS=linux

# Build Arguments
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_VERSION=0.1.0
BUILD_REVISION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
EOF

# Validate required environment variables
validate_env() {
    local required_vars=(
        "MONGODB_PASSWORD"
        "JWT_SECRET_KEY"
        "REDIS_PASSWORD"
        "ELASTICSEARCH_PASSWORD"
        "USER_ID"
        "SESSION_SECRET"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: Required environment variable $var is not set"
            exit 1
        fi
    done
}

# Validate environment
validate_env

echo "✅ .env.distroless generated successfully at $ENV_FILE"
echo "📋 Environment variables configured for distroless deployment"
echo "🔒 Security keys generated with secure random values"
echo "🌐 Network configuration set for Raspberry Pi deployment"
echo "📦 Container configuration optimized for distroless runtime"
