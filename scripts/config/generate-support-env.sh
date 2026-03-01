#!/bin/bash
# Generate .env.support for Phase 4 Support Services
# Based on: distro-deployment-plan.md Phase 4.4
# Generated: 2025-01-14
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
SCRIPT_DIR="/mnt/myssd/Lucid/Lucid/scripts/config"

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
    
    if [[ ! -d "$ENV_DIR" ]]; then
        echo "ERROR: Environment directory not found: $ENV_DIR"
        exit 1
    fi
    
    if [[ ! -d "$SCRIPTS_DIR" ]]; then
        echo "ERROR: Scripts directory not found: $SCRIPTS_DIR"
        exit 1
    fi
}

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# =============================================================================
# VALIDATION AND INITIALIZATION
# =============================================================================

# Run all validations
validate_pi_mounts
check_pi_packages
validate_paths

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️  Generating Support Services Environment Configuration${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo "Environment Directory: $ENV_DIR"
echo ""

# Configuration - Use Pi console paths
ENV_FILE="$ENV_DIR/.env.support"

# Create directory if it doesn't exist
mkdir -p "$ENV_DIR"

# =============================================================================
# FALLBACK MECHANISMS FOR MINIMAL PI INSTALLATIONS
# =============================================================================

# Function to generate secure random string (aligned with generate-secure-keys.sh)
# With fallback mechanisms for minimal Pi installations
generate_secure_string() {
    local length=${1:-32}
    
    # Primary method: openssl
    if command -v openssl &> /dev/null; then
        openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
    # Fallback 1: /dev/urandom with base64
    elif [[ -r /dev/urandom ]]; then
        head -c $((length * 3 / 4)) /dev/urandom | base64 | tr -d "=+/" | cut -c1-$length
    # Fallback 2: /dev/random with base64
    elif [[ -r /dev/random ]]; then
        head -c $((length * 3 / 4)) /dev/random | base64 | tr -d "=+/" | cut -c1-$length
    # Fallback 3: date + process ID (less secure but functional)
    else
        echo "WARNING: Using less secure fallback for random string generation"
        date +%s%N | sha256sum | cut -c1-$length
    fi
}

# Function to generate JWT secret (64 characters) - aligned with generate-secure-keys.sh
# With fallback mechanisms for minimal Pi installations
generate_jwt_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -base64 48 | tr -d "=+/"
    elif [[ -r /dev/urandom ]]; then
        head -c 36 /dev/urandom | base64 | tr -d "=+/"
    else
        echo "WARNING: Using less secure fallback for JWT secret generation"
        date +%s%N | sha256sum | cut -c1-64
    fi
}

# Function to generate encryption key (32 bytes = 256 bits) - aligned with generate-secure-keys.sh
# With fallback mechanisms for minimal Pi installations
generate_encryption_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    elif [[ -r /dev/urandom ]]; then
        head -c 32 /dev/urandom | hexdump -v -e '/1 "%02x"'
    else
        echo "WARNING: Using less secure fallback for encryption key generation"
        date +%s%N | sha256sum | cut -c1-64
    fi
}

# Function to generate database passwords - aligned with generate-secure-keys.sh
# With fallback mechanisms for minimal Pi installations
generate_db_password() {
    if command -v openssl &> /dev/null; then
        openssl rand -base64 24 | tr -d "=+/"
    elif [[ -r /dev/urandom ]]; then
        head -c 18 /dev/urandom | base64 | tr -d "=+/"
    else
        echo "WARNING: Using less secure fallback for database password generation"
        date +%s%N | sha256sum | cut -c1-32
    fi
}

# Generate secure random values using the same functions as generate-secure-keys.sh
MONGODB_PASSWORD=$(generate_db_password)
JWT_SECRET_KEY=$(generate_jwt_secret)
REDIS_PASSWORD=$(generate_db_password)
ELASTICSEARCH_PASSWORD=$(generate_db_password)
ENCRYPTION_KEY=$(generate_encryption_key)
ADMIN_SECRET=$(generate_secure_string 32)
TRON_PAYMENT_SECRET=$(generate_secure_string 32)
TOR_CONTROL_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/")

echo -e "${YELLOW}📝 Generating secure values for Support Services...${NC}"
echo "MONGODB_PASSWORD generated: ${MONGODB_PASSWORD:0:8}..."
echo "JWT_SECRET_KEY generated: ${JWT_SECRET_KEY:0:8}..."
echo "REDIS_PASSWORD generated: ${REDIS_PASSWORD:0:8}..."
echo "ELASTICSEARCH_PASSWORD generated: ${ELASTICSEARCH_PASSWORD:0:8}..."
echo "ENCRYPTION_KEY generated: ${ENCRYPTION_KEY:0:8}..."
echo "ADMIN_SECRET generated: ${ADMIN_SECRET:0:8}..."
echo "TRON_PAYMENT_SECRET generated: ${TRON_PAYMENT_SECRET:0:8}..."
echo "TOR_CONTROL_PASSWORD generated: ${TOR_CONTROL_PASSWORD:0:8}..."

# Create .env.support file
cat > "$ENV_FILE" << 'EOF'
# Phase 4 Support Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
# Target: Raspberry Pi 5 (192.168.0.75)
# Services: Admin Interface, TRON Payment Services (6 services on isolated network)
# Architecture: ARM64

# =============================================================================
# SYSTEM CONFIGURATION (Required by validate-env.sh)
# =============================================================================

PROJECT_NAME=Lucid
PROJECT_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# =============================================================================
# API GATEWAY CONFIGURATION (Required by validate-env.sh)
# =============================================================================

API_GATEWAY_HOST=172.20.0.10
API_GATEWAY_PORT=8080
API_RATE_LIMIT=1000

# =============================================================================
# AUTHENTICATION CONFIGURATION (Required by validate-env.sh)
# =============================================================================

JWT_SECRET=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
SESSION_TIMEOUT=1800

# =============================================================================
# SECURITY CONFIGURATION (Required by validate-env.sh)
# =============================================================================

ENCRYPTION_KEY=${ENCRYPTION_KEY}
SSL_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# =============================================================================
# BLOCKCHAIN CONFIGURATION (Required by validate-env.sh)
# =============================================================================

BLOCKCHAIN_NETWORK=lucid-mainnet
BLOCKCHAIN_CONSENSUS=PoOT
ANCHORING_ENABLED=true

# =============================================================================
# OPTIONAL CONFIGURATION (Optional by validate-env.sh)
# =============================================================================

# Hardware Configuration
HARDWARE_ACCELERATION=true
V4L2_ENABLED=true
GPU_ENABLED=false

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
HEALTH_CHECK_ENABLED=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30

# Alerting Configuration
ALERTING_ENABLED=true
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=85

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

# TRON Isolated Network (Payment Services)
LUCID_TRON_NETWORK=lucid-tron-isolated
LUCID_TRON_SUBNET=172.21.0.0/16
LUCID_TRON_GATEWAY=172.21.0.1

# =============================================================================
# DATABASE CONFIGURATION (Inherited from Foundation)
# =============================================================================

# MongoDB Configuration
MONGODB_HOST=172.20.0.11
MONGODB_PORT=27017
MONGODB_DATABASE=lucid
MONGODB_USERNAME=lucid
MONGODB_PASSWORD=${MONGODB_PASSWORD}
MONGODB_AUTH_SOURCE=admin
MONGODB_RETRY_WRITES=false
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@172.20.0.11:27017/lucid?authSource=admin&retryWrites=false

# Redis Configuration
REDIS_HOST=172.20.0.12
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@172.20.0.12:6379

# Elasticsearch Configuration
ELASTICSEARCH_HOST=172.20.0.13
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
ELASTICSEARCH_URL=http://elastic:${ELASTICSEARCH_PASSWORD}@172.20.0.13:9200

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

# Tor Configuration
TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# =============================================================================
# SUPPORT SERVICES CONFIGURATION
# =============================================================================

# Admin Interface
ADMIN_INTERFACE_HOST=172.20.0.30
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_URL=http://172.20.0.30:8083

# TRON Payment Services (ISOLATED NETWORK)
TRON_CLIENT_HOST=172.21.0.10
TRON_CLIENT_PORT=8091
TRON_CLIENT_URL=http://172.21.0.10:8091

TRON_PAYOUT_ROUTER_HOST=172.21.0.11
TRON_PAYOUT_ROUTER_PORT=8092
TRON_PAYOUT_ROUTER_URL=http://172.21.0.11:8092

TRON_WALLET_MANAGER_HOST=172.21.0.12
TRON_WALLET_MANAGER_PORT=8093
TRON_WALLET_MANAGER_URL=http://172.21.0.12:8093

TRON_USDT_MANAGER_HOST=172.21.0.13
TRON_USDT_MANAGER_PORT=8094
TRON_USDT_MANAGER_URL=http://172.21.0.13:8094

TRON_STAKING_HOST=172.21.0.14
TRON_STAKING_PORT=8096
TRON_STAKING_URL=http://172.21.0.14:8096

TRON_PAYMENT_GATEWAY_HOST=172.21.0.15
TRON_PAYMENT_GATEWAY_PORT=8097
TRON_PAYMENT_GATEWAY_URL=http://172.21.0.15:8097

# =============================================================================
# ADMIN INTERFACE CONFIGURATION
# =============================================================================

# Admin Interface Configuration
ADMIN_SECRET=${ADMIN_SECRET}
ADMIN_INTERFACE_TIMEOUT=30
ADMIN_INTERFACE_CORS_ENABLED=true

# Admin Dashboard Configuration
ADMIN_DASHBOARD_ENABLED=true
ADMIN_DASHBOARD_PORT=8083
ADMIN_DASHBOARD_URL=http://admin-interface:8083

# Admin Monitoring Configuration
ADMIN_MONITORING_ENABLED=true
ADMIN_MONITORING_METRICS_ENABLED=true
ADMIN_MONITORING_ALERT_ENABLED=true

# Admin Session Management
ADMIN_SESSION_ADMIN_ENABLED=true
ADMIN_SESSION_TIMEOUT=3600
ADMIN_SESSION_MAX_SESSIONS=10

# Admin Blockchain Management
ADMIN_BLOCKCHAIN_ADMIN_ENABLED=true
ADMIN_BLOCKCHAIN_MONITORING_ENABLED=true
ADMIN_BLOCKCHAIN_ALERT_ENABLED=true

# Admin Payout Management
ADMIN_PAYOUT_TRIGGERS_ENABLED=true
ADMIN_PAYOUT_MONITORING_ENABLED=true
ADMIN_PAYOUT_ALERT_ENABLED=true

# =============================================================================
# TRON BLOCKCHAIN CONFIGURATION
# =============================================================================

# TRON Network Configuration
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
TRON_PRIVATE_KEY=your_private_key_here
TRON_ADDRESS=your_address_here

# TRON Payment Configuration
TRON_PAYMENT_SECRET=${TRON_PAYMENT_SECRET}
TRON_PAYMENT_TIMEOUT=30
TRON_PAYMENT_RETRY_ATTEMPTS=3

# USDT Configuration
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
USDT_DECIMALS=6
USDT_MINIMUM_PAYOUT=10

# TRON Gas Configuration
TRON_GAS_LIMIT=100000
TRON_GAS_PRICE=1000
TRON_GAS_FEE_LIMIT=1000000

# TRON Staking Configuration
TRON_STAKING_ENABLED=true
TRON_STAKING_MINIMUM_AMOUNT=1000
TRON_STAKING_REWARD_RATE=0.05

# =============================================================================
# TRON PAYMENT SERVICES CONFIGURATION
# =============================================================================

# TRON Client Configuration
TRON_CLIENT_TIMEOUT=30
TRON_CLIENT_RETRY_ATTEMPTS=3
TRON_CLIENT_HEALTH_CHECK_INTERVAL=60s

# TRON Payout Router Configuration
TRON_PAYOUT_ROUTER_BATCH_SIZE=100
TRON_PAYOUT_ROUTER_TIMEOUT=30
TRON_PAYOUT_ROUTER_RETRY_ATTEMPTS=3

# TRON Wallet Manager Configuration
TRON_WALLET_MANAGER_ENCRYPTION_ENABLED=true
TRON_WALLET_MANAGER_BACKUP_ENABLED=true
TRON_WALLET_MANAGER_MULTI_SIG_ENABLED=true

# TRON USDT Manager Configuration
TRON_USDT_MANAGER_BALANCE_MONITORING=true
TRON_USDT_MANAGER_AUTO_REPLENISHMENT=true
TRON_USDT_MANAGER_LOW_BALANCE_THRESHOLD=1000

# TRON Staking Configuration
TRON_STAKING_AUTO_STAKING=true
TRON_STAKING_REWARD_DISTRIBUTION=true
TRON_STAKING_COMPOUNDING_ENABLED=true

# TRON Payment Gateway Configuration
TRON_PAYMENT_GATEWAY_WEBHOOK_ENABLED=true
TRON_PAYMENT_GATEWAY_RATE_LIMITING=true
TRON_PAYMENT_GATEWAY_FRAUD_DETECTION=true

# =============================================================================
# NETWORK ISOLATION CONFIGURATION
# =============================================================================

# TRON Isolated Network Configuration
TRON_ISOLATED_NETWORK=lucid-tron-isolated
TRON_ISOLATED_SUBNET=172.21.0.0/16
TRON_ISOLATED_GATEWAY=172.21.0.1

# TRON Bridge Configuration
TRON_BRIDGE_ENABLED=true
TRON_BRIDGE_PORT=8098
TRON_BRIDGE_TIMEOUT=30
TRON_BRIDGE_ENCRYPTION_ENABLED=true

# Network Security Configuration
TRON_NETWORK_SECURITY_ENABLED=true
TRON_NETWORK_FIREWALL_ENABLED=true
TRON_NETWORK_ACCESS_CONTROL_ENABLED=true

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
ADMIN_INTERFACE_HEALTH_URL=http://172.20.0.30:8083/health
TRON_CLIENT_HEALTH_URL=http://172.21.0.10:8091/health
TRON_PAYOUT_ROUTER_HEALTH_URL=http://172.21.0.11:8092/health
TRON_WALLET_MANAGER_HEALTH_URL=http://172.21.0.12:8093/health
TRON_USDT_MANAGER_HEALTH_URL=http://172.21.0.13:8094/health
TRON_STAKING_HEALTH_URL=http://172.21.0.14:8096/health
TRON_PAYMENT_GATEWAY_HEALTH_URL=http://172.21.0.15:8097/health

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
DEPLOYMENT_PATH=$PROJECT_ROOT

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
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
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
        "ADMIN_SECRET"
        "TRON_PAYMENT_SECRET"
        "TOR_CONTROL_PASSWORD"
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

echo -e "${GREEN}✅ .env.support generated successfully at $ENV_FILE${NC}"
echo -e "${GREEN}📋 Support services environment configured for distroless deployment${NC}"
echo -e "${GREEN}🔒 Security keys generated with secure random values${NC}"
echo -e "${GREEN}🌐 Network configuration set for Raspberry Pi deployment${NC}"
echo -e "${GREEN}📦 Container configuration optimized for distroless runtime${NC}"
echo -e "${GREEN}🛡️  Pi console native validation completed${NC}"
echo -e "${GREEN}🔧 Fallback mechanisms enabled for minimal Pi installations${NC}"
echo -e "${GREEN}📁 Environment file saved to: $ENV_FILE${NC}"
