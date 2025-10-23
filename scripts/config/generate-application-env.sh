#!/bin/bash
# Generate .env.application for Phase 3 Application Services
# Based on: distro-deployment-plan.md Phase 4.3
# Generated: 2025-01-14

set -euo pipefail

# Project root configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Generating Application Services Environment Configuration${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Configuration
ENV_FILE="configs/environment/.env.application"

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
ENCRYPTION_KEY=$(generate_encryption_key)
SESSION_SECRET=$(generate_secure_string 32)
NODE_MANAGEMENT_SECRET=$(generate_secure_string 32)

echo -e "${YELLOW}📝 Generating secure values for Application Services...${NC}"
echo "MONGODB_PASSWORD generated: ${MONGODB_PASSWORD:0:8}..."
echo "JWT_SECRET_KEY generated: ${JWT_SECRET_KEY:0:8}..."
echo "REDIS_PASSWORD generated: ${REDIS_PASSWORD:0:8}..."
echo "ELASTICSEARCH_PASSWORD generated: ${ELASTICSEARCH_PASSWORD:0:8}..."
echo "ENCRYPTION_KEY generated: ${ENCRYPTION_KEY:0:8}..."
echo "SESSION_SECRET generated: ${SESSION_SECRET:0:8}..."
echo "NODE_MANAGEMENT_SECRET generated: ${NODE_MANAGEMENT_SECRET:0:8}..."

# Create .env.application file
cat > "$ENV_FILE" << 'EOF'
# Phase 3 Application Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Target: Raspberry Pi 5 (192.168.0.75)
# Services: Session Pipeline, Session Recorder, Chunk Processor, Session Storage, Session API, RDP Services, Node Management
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

# Main Network (Foundation + Core + Application + Blockchain)
LUCID_MAIN_NETWORK=lucid-pi-network
LUCID_MAIN_SUBNET=172.20.0.0/16
LUCID_MAIN_GATEWAY=172.20.0.1

# =============================================================================
# DATABASE CONFIGURATION (Inherited from Foundation)
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
# SECURITY CONFIGURATION (Inherited from Foundation)
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Encryption Configuration
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENCRYPTION_ALGORITHM=AES-256-GCM

# Session Configuration
SESSION_SECRET=${SESSION_SECRET}
SESSION_TIMEOUT=1800

# =============================================================================
# APPLICATION SERVICES CONFIGURATION
# =============================================================================

# Session Pipeline
SESSION_PIPELINE_HOST=session-pipeline
SESSION_PIPELINE_PORT=8083
SESSION_PIPELINE_URL=http://session-pipeline:8083

# Session Recorder
SESSION_RECORDER_HOST=session-recorder
SESSION_RECORDER_PORT=8084
SESSION_RECORDER_URL=http://session-recorder:8084

# Session Processor (Chunk Processor)
SESSION_PROCESSOR_HOST=session-processor
SESSION_PROCESSOR_PORT=8085
SESSION_PROCESSOR_URL=http://session-processor:8085

# Session Storage
SESSION_STORAGE_HOST=session-storage
SESSION_STORAGE_PORT=8086
SESSION_STORAGE_URL=http://session-storage:8086

# Session API
SESSION_API_HOST=session-api
SESSION_API_PORT=8087
SESSION_API_URL=http://session-api:8087

# RDP Server Manager
RDP_SERVER_MANAGER_HOST=rdp-server-manager
RDP_SERVER_MANAGER_PORT=8090
RDP_SERVER_MANAGER_URL=http://rdp-server-manager:8090

# RDP XRDP Integration
RDP_XRDP_HOST=rdp-xrdp
RDP_XRDP_PORT=8091
RDP_XRDP_URL=http://rdp-xrdp:8091

# RDP Controller
RDP_CONTROLLER_HOST=rdp-controller
RDP_CONTROLLER_PORT=8092
RDP_CONTROLLER_URL=http://rdp-controller:8092

# RDP Monitor
RDP_MONITOR_HOST=rdp-monitor
RDP_MONITOR_PORT=8093
RDP_MONITOR_URL=http://rdp-monitor:8093

# Node Management
NODE_MANAGEMENT_HOST=node-management
NODE_MANAGEMENT_PORT=8095
NODE_MANAGEMENT_URL=http://node-management:8095

# =============================================================================
# SESSION MANAGEMENT CONFIGURATION
# =============================================================================

# Session Configuration
SESSION_CHUNK_SIZE=8388608
SESSION_COMPRESSION_LEVEL=1
SESSION_ENCRYPTION_ENABLED=true
SESSION_RETENTION_DAYS=30
SESSION_MERKLE_TREE_ENABLED=true

# Session Processing
SESSION_PROCESSING_WORKERS=4
SESSION_ENCRYPTION_WORKERS=2
SESSION_COMPRESSION_WORKERS=2
SESSION_STORAGE_WORKERS=4

# Session Pipeline Configuration
SESSION_PIPELINE_BATCH_SIZE=100
SESSION_PIPELINE_TIMEOUT=30
SESSION_PIPELINE_RETRY_ATTEMPTS=3

# Session Recorder Configuration
SESSION_RECORDER_BUFFER_SIZE=64MB
SESSION_RECORDER_FLUSH_INTERVAL=5s
SESSION_RECORDER_COMPRESSION_ENABLED=true

# Session Storage Configuration
SESSION_STORAGE_BACKEND=mongodb
SESSION_STORAGE_INDEXING_ENABLED=true
SESSION_STORAGE_CACHING_ENABLED=true

# =============================================================================
# RDP SERVICES CONFIGURATION
# =============================================================================

# RDP Configuration
RDP_MAX_SESSIONS=10
RDP_SESSION_TIMEOUT=3600
RDP_RESOURCE_LIMIT_CPU=80
RDP_RESOURCE_LIMIT_MEMORY=2GB
RDP_RESOURCE_LIMIT_DISK=10GB

# RDP Server Manager Configuration
RDP_SERVER_MANAGER_POOL_SIZE=5
RDP_SERVER_MANAGER_TIMEOUT=30
RDP_SERVER_MANAGER_HEALTH_CHECK_INTERVAL=60s

# RDP XRDP Configuration
RDP_XRDP_DISPLAY_RESOLUTION=1920x1080
RDP_XRDP_COLOR_DEPTH=24
RDP_XRDP_COMPRESSION_ENABLED=true

# RDP Controller Configuration
RDP_CONTROLLER_SESSION_TIMEOUT=3600
RDP_CONTROLLER_IDLE_TIMEOUT=1800
RDP_CONTROLLER_MAX_IDLE_SESSIONS=5

# RDP Monitor Configuration
RDP_MONITOR_METRICS_ENABLED=true
RDP_MONITOR_ALERT_THRESHOLD_CPU=80
RDP_MONITOR_ALERT_THRESHOLD_MEMORY=80
RDP_MONITOR_ALERT_THRESHOLD_DISK=90

# =============================================================================
# NODE MANAGEMENT CONFIGURATION
# =============================================================================

# Node Management Configuration
NODE_MANAGEMENT_SECRET=${NODE_MANAGEMENT_SECRET}
NODE_POOL_MAX_SIZE=100
NODE_PAYOUT_THRESHOLD=10
NODE_CONSENSUS_WEIGHT=1.0

# Node Pool Configuration
NODE_POOL_MIN_SIZE=5
NODE_POOL_SCALE_UP_THRESHOLD=80
NODE_POOL_SCALE_DOWN_THRESHOLD=20
NODE_POOL_HEALTH_CHECK_INTERVAL=30s

# Node Performance Configuration
NODE_PERFORMANCE_MONITORING=true
NODE_PERFORMANCE_METRICS_ENABLED=true
NODE_PERFORMANCE_ALERT_THRESHOLD=90

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
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3

# Service Health Endpoints
SESSION_PIPELINE_HEALTH_URL=http://session-pipeline:8083/health
SESSION_RECORDER_HEALTH_URL=http://session-recorder:8084/health
SESSION_PROCESSOR_HEALTH_URL=http://session-processor:8085/health
SESSION_STORAGE_HEALTH_URL=http://session-storage:8086/health
SESSION_API_HEALTH_URL=http://session-api:8087/health
RDP_SERVER_MANAGER_HEALTH_URL=http://rdp-server-manager:8090/health
NODE_MANAGEMENT_HEALTH_URL=http://node-management:8095/health

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

# Metrics Configuration
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics

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
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
        "NODE_MANAGEMENT_SECRET"
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

echo -e "${GREEN}✅ .env.application generated successfully at $ENV_FILE${NC}"
echo -e "${GREEN}📋 Application services environment configured for distroless deployment${NC}"
echo -e "${GREEN}🔒 Security keys generated with secure random values${NC}"
echo -e "${GREEN}🌐 Network configuration set for Raspberry Pi deployment${NC}"
echo -e "${GREEN}📦 Container configuration optimized for distroless runtime${NC}"
