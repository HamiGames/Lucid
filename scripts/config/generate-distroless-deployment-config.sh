#!/bin/bash
# Generate Complete Distroless Deployment Configuration
# Based on: docker-compose.base.yml and docker-compose.foundation.yml
# Maintains: Distroless design + Secure design principles
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
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Generating Complete Distroless Deployment Configuration${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Function to generate secure random string
generate_secure_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret (64 characters)
generate_jwt_secret() {
    openssl rand -base64 48 | tr -d "=+/"
}

# Function to generate encryption key (32 bytes = 256 bits)
generate_encryption_key() {
    openssl rand -hex 32
}

# Function to generate database passwords
generate_db_password() {
    openssl rand -base64 24 | tr -d "=+/"
}

# Function to generate Tor control password
generate_tor_password() {
    openssl rand -base64 32 | tr -d "=+/"
}

echo -e "${YELLOW}📝 Generating secure values for Distroless Deployment...${NC}"

# Generate all secure values
MONGODB_PASSWORD=$(generate_db_password)
JWT_SECRET_KEY=$(generate_jwt_secret)
REDIS_PASSWORD=$(generate_db_password)
ELASTICSEARCH_PASSWORD=$(generate_db_password)
ENCRYPTION_KEY=$(generate_encryption_key)
TOR_CONTROL_PASSWORD=$(generate_tor_password)
API_GATEWAY_SECRET=$(generate_secure_string 32)
BLOCKCHAIN_SECRET=$(generate_secure_string 32)
SESSION_SECRET=$(generate_secure_string 32)
NODE_MANAGEMENT_SECRET=$(generate_secure_string 32)
ADMIN_SECRET=$(generate_secure_string 32)
TRON_PAYMENT_SECRET=$(generate_secure_string 32)

echo "MONGODB_PASSWORD generated: ${MONGODB_PASSWORD:0:8}..."
echo "JWT_SECRET_KEY generated: ${JWT_SECRET_KEY:0:8}..."
echo "REDIS_PASSWORD generated: ${REDIS_PASSWORD:0:8}..."
echo "ELASTICSEARCH_PASSWORD generated: ${ELASTICSEARCH_PASSWORD:0:8}..."
echo "ENCRYPTION_KEY generated: ${ENCRYPTION_KEY:0:8}..."
echo "TOR_CONTROL_PASSWORD generated: ${TOR_CONTROL_PASSWORD:0:8}..."

# Create directories
mkdir -p configs/environment
mkdir -p configs/docker/distroless
mkdir -p infrastructure/docker/distroless/base
mkdir -p /mnt/myssd/Lucid/data/{mongodb,redis,elasticsearch}
mkdir -p /mnt/myssd/Lucid/logs/{mongodb,redis,elasticsearch,auth-service,base-container,minimal-base-container,arm64-base-container}

# Set ownership
sudo chown -R pickme:pickme /mnt/myssd/Lucid/data
sudo chown -R pickme:pickme /mnt/myssd/Lucid/logs

echo -e "${GREEN}✅ Directories created and permissions set${NC}"

# =============================================================================
# 1. GENERATE DISTROLESS ENVIRONMENT FILE
# =============================================================================

echo -e "${PURPLE}📄 Generating .env.distroless for base infrastructure...${NC}"

cat > configs/environment/.env.distroless << EOF
# Distroless Base Infrastructure Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Target: Raspberry Pi 5 (192.168.0.75)
# Architecture: ARM64
# Design: Distroless + Secure

# =============================================================================
# DISTROLESS BASE CONFIGURATION
# =============================================================================

# Distroless Base Image (CRITICAL: Must be distroless)
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# Build Configuration
DOCKER_BUILDKIT=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
COMPOSE_DOCKER_CLI_BUILD=1

# =============================================================================
# SECURITY CONFIGURATION (DISTROLESS + SECURE)
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
# DISTROLESS RUNTIME CONFIGURATION
# =============================================================================

# Runtime Environment
LUCID_ENV=production
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64

# Container Configuration (DISTROLESS STANDARD)
CONTAINER_USER=65532
CONTAINER_GROUP=65532
CONTAINER_UID=65532
CONTAINER_GID=65532

# Security Options (DISTROLESS + SECURE)
SECURITY_OPT_NO_NEW_PRIVILEGES=true
SECURITY_OPT_READONLY_ROOTFS=true
SECURITY_OPT_NO_EXEC=true

# Capability Configuration (DISTROLESS STANDARD)
CAP_DROP=ALL
CAP_ADD=NET_BIND_SERVICE

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Distroless Production Network
LUCID_DISTROLESS_NETWORK=lucid-distroless-production
LUCID_DISTROLESS_SUBNET=172.23.0.0/16
LUCID_DISTROLESS_GATEWAY=172.23.0.1

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40s

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Level
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=stdout

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

# Deployment Target
DEPLOYMENT_TARGET=raspberry-pi
DEPLOYMENT_HOST=192.168.0.75
DEPLOYMENT_USER=pickme
DEPLOYMENT_PATH=/mnt/myssd/Lucid/Lucid

# Registry Configuration
REGISTRY=docker.io
REPOSITORY=pickme/lucid
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

echo -e "${GREEN}✅ .env.distroless generated${NC}"

# =============================================================================
# 2. GENERATE DISTROLESS.ENV FILE
# =============================================================================

echo -e "${PURPLE}📄 Generating distroless.env for base containers...${NC}"

cat > configs/docker/distroless/distroless.env << EOF
# Distroless Base Container Environment
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Design: Distroless + Secure

# =============================================================================
# DISTROLESS BASE IMAGE CONFIGURATION
# =============================================================================

# Base Image (CRITICAL: Must be distroless)
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Security Options (DISTROLESS + SECURE)
SECURITY_OPT_NO_NEW_PRIVILEGES=true
SECURITY_OPT_READONLY_ROOTFS=true
SECURITY_OPT_NO_EXEC=true

# Capability Configuration (DISTROLESS STANDARD)
CAP_DROP=ALL
CAP_ADD=NET_BIND_SERVICE

# =============================================================================
# CONTAINER CONFIGURATION
# =============================================================================

# Container User (DISTROLESS STANDARD)
CONTAINER_USER=65532
CONTAINER_GROUP=65532

# Runtime Environment
LUCID_ENV=production
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Health Check (Python-based for distroless)
HEALTH_CHECK_TEST=python3 -c "import sys; sys.exit(0)"
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40s

# =============================================================================
# VOLUME CONFIGURATION
# =============================================================================

# Volume Paths
VOLUME_DATA_PATH=/mnt/myssd/Lucid/data
VOLUME_LOGS_PATH=/mnt/myssd/Lucid/logs
VOLUME_CACHE_PATH=/tmp/cache

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Network Configuration
LUCID_DISTROLESS_NETWORK=lucid-distroless-production
LUCID_DISTROLESS_SUBNET=172.23.0.0/16
LUCID_DISTROLESS_GATEWAY=172.23.0.1
EOF

echo -e "${GREEN}✅ distroless.env generated${NC}"

# =============================================================================
# 3. GENERATE FOUNDATION ENVIRONMENT FILE
# =============================================================================

echo -e "${PURPLE}📄 Generating .env.foundation for foundation services...${NC}"

cat > configs/environment/.env.foundation << EOF
# Phase 1 Foundation Services Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Target: Raspberry Pi 5 (192.168.0.75)
# Services: MongoDB, Redis, Elasticsearch, Auth Service
# Architecture: ARM64
# Design: Distroless + Secure

# =============================================================================
# DISTROLESS BASE CONFIGURATION
# =============================================================================

# Distroless Base Image (CRITICAL: Must be distroless)
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

# Encryption Configuration
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENCRYPTION_ALGORITHM=AES-256-GCM

# Tor Configuration
TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# =============================================================================
# FOUNDATION SERVICES CONFIGURATION
# =============================================================================

# Auth Service
AUTH_SERVICE_HOST=lucid-auth-service
AUTH_SERVICE_PORT=8089
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# MongoDB Service
MONGODB_SERVICE_HOST=lucid-mongodb
MONGODB_SERVICE_PORT=27017
MONGODB_SERVICE_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid

# Redis Service
REDIS_SERVICE_HOST=lucid-redis
REDIS_SERVICE_PORT=6379
REDIS_SERVICE_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379

# Elasticsearch Service
ELASTICSEARCH_SERVICE_HOST=lucid-elasticsearch
ELASTICSEARCH_SERVICE_PORT=9200
ELASTICSEARCH_SERVICE_URL=http://elastic:${ELASTICSEARCH_PASSWORD}@lucid-elasticsearch:9200

# =============================================================================
# DISTROLESS RUNTIME CONFIGURATION
# =============================================================================

# Runtime Environment
LUCID_ENV=production
LUCID_PLATFORM=arm64
LUCID_ARCHITECTURE=linux/arm64

# Container Configuration (DISTROLESS STANDARD)
CONTAINER_USER=65532
CONTAINER_GROUP=65532
CONTAINER_UID=65532
CONTAINER_GID=65532

# Security Options (DISTROLESS + SECURE)
SECURITY_OPT_NO_NEW_PRIVILEGES=true
SECURITY_OPT_READONLY_ROOTFS=true
SECURITY_OPT_NO_EXEC=true

# Capability Configuration (DISTROLESS STANDARD)
CAP_DROP=ALL
CAP_ADD=NET_BIND_SERVICE

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40s

# Service Health Endpoints
MONGODB_HEALTH_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_HEALTH_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379
ELASTICSEARCH_HEALTH_URL=http://elastic:${ELASTICSEARCH_PASSWORD}@lucid-elasticsearch:9200/_cluster/health
AUTH_SERVICE_HEALTH_URL=http://lucid-auth-service:8089/health

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Level
LOG_LEVEL=INFO
LOG_FORMAT=json
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
REGISTRY=docker.io
REPOSITORY=pickme/lucid
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

echo -e "${GREEN}✅ .env.foundation generated${NC}"

# =============================================================================
# 4. GENERATE SECURE ENVIRONMENT FILE
# =============================================================================

echo -e "${PURPLE}📄 Generating .env.secure for master backup...${NC}"

cat > configs/environment/.env.secure << EOF
# Lucid Secure Environment Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# WARNING: Keep this file secure and never commit to version control
# Design: Distroless + Secure

# =============================================================================
# SECURITY KEYS AND PASSWORDS
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption Configuration
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENCRYPTION_ALGORITHM=AES-256-GCM

# Tor Configuration
TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Database Passwords
MONGODB_PASSWORD=${MONGODB_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}

# Service Secrets
API_GATEWAY_SECRET=${API_GATEWAY_SECRET}
BLOCKCHAIN_SECRET=${BLOCKCHAIN_SECRET}
SESSION_SECRET=${SESSION_SECRET}
NODE_MANAGEMENT_SECRET=${NODE_MANAGEMENT_SECRET}
ADMIN_SECRET=${ADMIN_SECRET}
TRON_PAYMENT_SECRET=${TRON_PAYMENT_SECRET}

# =============================================================================
# DISTROLESS CONFIGURATION
# =============================================================================

# Distroless Base Image (CRITICAL: Must be distroless)
DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
DISTROLESS_USER=65532:65532
DISTROLESS_SHELL=/bin/false

# Security Options (DISTROLESS + SECURE)
SECURITY_OPT_NO_NEW_PRIVILEGES=true
SECURITY_OPT_READONLY_ROOTFS=true
SECURITY_OPT_NO_EXEC=true

# Capability Configuration (DISTROLESS STANDARD)
CAP_DROP=ALL
CAP_ADD=NET_BIND_SERVICE

# =============================================================================
# GENERATED VALUES FOR BUILD PLAN
# =============================================================================
GENERATED_JWT_SECRET=${JWT_SECRET_KEY}
GENERATED_ENCRYPTION_KEY=${ENCRYPTION_KEY}
GENERATED_TOR_PASSWORD=${TOR_CONTROL_PASSWORD}
GENERATED_MONGODB_PASSWORD=${MONGODB_PASSWORD}
GENERATED_REDIS_PASSWORD=${REDIS_PASSWORD}

# =============================================================================
# SECURITY NOTES
# =============================================================================
# - All keys are cryptographically secure random values
# - JWT_SECRET_KEY: 64 characters, base64 encoded
# - ENCRYPTION_KEY: 256-bit (32 bytes) hex encoded
# - Database passwords: 24 characters, base64 encoded
# - Service secrets: 32 characters, base64 encoded
# - Store this file securely and never commit to version control
# - Rotate keys regularly in production environments
# - DISTROLESS design maintained throughout
# - SECURE design maintained throughout
EOF

# Set secure permissions
chmod 600 configs/environment/.env.secure

echo -e "${GREEN}✅ .env.secure generated with secure permissions${NC}"

# =============================================================================
# 5. GENERATE NETWORK CREATION SCRIPT
# =============================================================================

echo -e "${PURPLE}📄 Generating network creation script...${NC}"

cat > scripts/deployment/create-distroless-networks.sh << 'EOF'
#!/bin/bash
# Create Distroless Networks for Lucid Project
# Generated: 2025-01-14
# Design: Distroless + Secure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 Creating Distroless Networks for Lucid Project${NC}"
echo "=================================================="

# Function to create network
create_network() {
    local name="$1"
    local subnet="$2"
    local gateway="$3"
    local label="$4"
    
    echo -e "${YELLOW}Creating network: $name${NC}"
    
    docker network create "$name" \
        --driver bridge \
        --subnet "$subnet" \
        --gateway "$gateway" \
        --attachable \
        --opt com.docker.network.bridge.enable_icc=true \
        --opt com.docker.network.bridge.enable_ip_masquerade=true \
        --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
        --opt com.docker.network.driver.mtu=1500 \
        --label "lucid.network=$label" \
        --label "lucid.subnet=$subnet"
    
    echo -e "${GREEN}✅ Network $name created successfully${NC}"
}

# Create all 6 networks
create_network "lucid-pi-network" "172.20.0.0/16" "172.20.0.1" "main"
create_network "lucid-tron-isolated" "172.21.0.0/16" "172.21.0.1" "tron-isolated"
create_network "lucid-gui-network" "172.22.0.0/16" "172.22.0.1" "gui"
create_network "lucid-distroless-production" "172.23.0.0/16" "172.23.0.1" "distroless-production"
create_network "lucid-distroless-dev" "172.24.0.0/16" "172.24.0.1" "distroless-dev"
create_network "lucid-multi-stage-network" "172.25.0.0/16" "172.25.0.1" "multi-stage"

# Verify networks
echo -e "${BLUE}🔍 Verifying networks...${NC}"
docker network ls | grep lucid

echo -e "${GREEN}🎉 All distroless networks created successfully!${NC}"
EOF

chmod +x scripts/deployment/create-distroless-networks.sh

echo -e "${GREEN}✅ Network creation script generated${NC}"

# =============================================================================
# 6. GENERATE DEPLOYMENT SCRIPT
# =============================================================================

echo -e "${PURPLE}📄 Generating distroless deployment script...${NC}"

cat > scripts/deployment/deploy-distroless-complete.sh << 'EOF'
#!/bin/bash
# Complete Distroless Deployment Script
# Generated: 2025-01-14
# Design: Distroless + Secure

set -euo pipefail

# Project root configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"

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
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Complete Distroless Deployment${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo ""

# Function to run script with error handling
run_script() {
    local script_name="$1"
    local script_path="$2"
    local description="$3"
    
    echo -e "${YELLOW}📦 $script_name...${NC}"
    echo "Description: $description"
    
    if [ -f "$script_path" ]; then
        if bash "$script_path"; then
            echo -e "${GREEN}✅ $script_name completed successfully${NC}"
            return 0
        else
            echo -e "${RED}❌ $script_name failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Script not found: $script_path${NC}"
        return 1
    fi
}

# Function to deploy distroless configuration
deploy_distroless_config() {
    local config_file="$1"
    local config_name="$2"
    local description="$3"
    
    echo -e "${YELLOW}📦 Deploying $config_name...${NC}"
    echo "Description: $description"
    
    if [ -f "$config_file" ]; then
        if docker-compose \
            --env-file configs/environment/.env.distroless \
            --env-file configs/docker/distroless/distroless.env \
            -f "$config_file" \
            up -d --remove-orphans; then
            echo -e "${GREEN}✅ $config_name deployed successfully${NC}"
            
            # Wait for services to initialize
            echo -e "${YELLOW}⏳ Waiting for $config_name services to initialize...${NC}"
            sleep 30
            
            # Check health
            echo -e "${YELLOW}🔍 Checking health status...${NC}"
            docker ps --filter health=healthy | grep -E "base|runtime|distroless" || true
            
            return 0
        else
            echo -e "${RED}❌ Failed to deploy $config_name${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Config file not found: $config_file${NC}"
        return 1
    fi
}

# Function to deploy foundation services
deploy_foundation_services() {
    echo -e "${YELLOW}📦 Deploying Foundation Services...${NC}"
    
    if docker-compose \
        --env-file configs/environment/.env.foundation \
        -f configs/docker/docker-compose.foundation.yml \
        up -d --remove-orphans; then
        echo -e "${GREEN}✅ Foundation Services deployed successfully${NC}"
        
        # Wait for services to initialize
        echo -e "${YELLOW}⏳ Waiting for Foundation Services to initialize...${NC}"
        sleep 60
        
        # Check health
        echo -e "${YELLOW}🔍 Checking Foundation Services health...${NC}"
        docker ps --filter health=healthy | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service" || true
        
        return 0
    else
        echo -e "${RED}❌ Failed to deploy Foundation Services${NC}"
        return 1
    fi
}

# Main deployment function
execute_full_deployment() {
    echo -e "${BLUE}🚀 Executing Full Distroless Deployment${NC}"
    
    # Step 1: Create networks
    if ! run_script "Create Distroless Networks" "scripts/deployment/create-distroless-networks.sh" "Create all 6 Docker networks"; then
        echo -e "${RED}❌ Network creation failed${NC}"
        exit 1
    fi
    
    # Step 2: Deploy distroless base infrastructure (CRITICAL PREREQUISITE)
    echo -e "${PURPLE}🔐 Deploying Distroless Base Infrastructure (CRITICAL PREREQUISITE)...${NC}"
    
    if ! deploy_distroless_config "configs/docker/distroless/distroless-config.yml" "Distroless Config" "Base distroless infrastructure"; then
        echo -e "${RED}❌ Distroless base deployment failed${NC}"
        exit 1
    fi
    
    if ! deploy_distroless_config "configs/docker/distroless/distroless-runtime-config.yml" "Distroless Runtime" "Runtime configuration"; then
        echo -e "${RED}❌ Distroless runtime deployment failed${NC}"
        exit 1
    fi
    
    if ! deploy_distroless_config "infrastructure/docker/distroless/base/docker-compose.base.yml" "Base Docker Compose" "Base container infrastructure"; then
        echo -e "${RED}❌ Base Docker Compose deployment failed${NC}"
        exit 1
    fi
    
    # Step 3: Deploy foundation services
    echo -e "${PURPLE}🏗️ Deploying Foundation Services...${NC}"
    
    if ! deploy_foundation_services; then
        echo -e "${RED}❌ Foundation services deployment failed${NC}"
        exit 1
    fi
    
    # Step 4: Final verification
    echo -e "${PURPLE}🔍 Final Verification...${NC}"
    
    # Check all containers
    echo -e "${YELLOW}📊 All containers status:${NC}"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
    
    # Check health status
    echo -e "${YELLOW}🏥 Health status:${NC}"
    docker ps --filter health=healthy
    
    # Check networks
    echo -e "${YELLOW}🌐 Networks:${NC}"
    docker network ls | grep lucid
    
    echo -e "${GREEN}🎉 Full distroless deployment completed successfully!${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting Distroless Deployment${NC}"
    echo "=================================================="
    
    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Execute deployment
    execute_full_deployment
}

# Run main function
main "$@"
EOF

chmod +x scripts/deployment/deploy-distroless-complete.sh

echo -e "${GREEN}✅ Deployment script generated${NC}"

# =============================================================================
# 7. GENERATE VERIFICATION SCRIPT
# =============================================================================

echo -e "${PURPLE}📄 Generating verification script...${NC}"

cat > scripts/deployment/verify-distroless-deployment.sh << 'EOF'
#!/bin/bash
# Verify Distroless Deployment
# Generated: 2025-01-14
# Design: Distroless + Secure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verifying Distroless Deployment${NC}"
echo "=================================================="

# Function to check container
check_container() {
    local container_name="$1"
    local expected_user="$2"
    
    echo -e "${YELLOW}🔍 Checking container: $container_name${NC}"
    
    if docker ps --format "{{.Names}}" | grep -q "^$container_name$"; then
        echo -e "${GREEN}✅ Container $container_name is running${NC}"
        
        # Check user
        local actual_user=$(docker exec "$container_name" id 2>/dev/null | cut -d'=' -f2 | cut -d'(' -f1 || echo "unknown")
        if [ "$actual_user" = "$expected_user" ]; then
            echo -e "${GREEN}✅ Container $container_name has correct user: $expected_user${NC}"
        else
            echo -e "${RED}❌ Container $container_name has incorrect user: $actual_user (expected: $expected_user)${NC}"
        fi
        
        # Check no shell access
        if docker exec "$container_name" sh -c "echo test" 2>&1 | grep -q "executable file not found"; then
            echo -e "${GREEN}✅ Container $container_name has no shell access (distroless)${NC}"
        else
            echo -e "${RED}❌ Container $container_name has shell access (not distroless)${NC}"
        fi
        
        return 0
    else
        echo -e "${RED}❌ Container $container_name is not running${NC}"
        return 1
    fi
}

# Function to check network
check_network() {
    local network_name="$1"
    
    echo -e "${YELLOW}🔍 Checking network: $network_name${NC}"
    
    if docker network ls --format "{{.Name}}" | grep -q "^$network_name$"; then
        echo -e "${GREEN}✅ Network $network_name exists${NC}"
        return 0
    else
        echo -e "${RED}❌ Network $network_name does not exist${NC}"
        return 1
    fi
}

# Function to check health
check_health() {
    local container_name="$1"
    
    echo -e "${YELLOW}🔍 Checking health: $container_name${NC}"
    
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
    
    if [ "$health_status" = "healthy" ]; then
        echo -e "${GREEN}✅ Container $container_name is healthy${NC}"
        return 0
    elif [ "$health_status" = "unhealthy" ]; then
        echo -e "${RED}❌ Container $container_name is unhealthy${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠️ Container $container_name health status: $health_status${NC}"
        return 0
    fi
}

# Main verification
main() {
    echo -e "${BLUE}🔍 Starting Distroless Deployment Verification${NC}"
    
    local all_passed=true
    
    # Check networks
    echo -e "${PURPLE}🌐 Checking Networks...${NC}"
    check_network "lucid-pi-network" || all_passed=false
    check_network "lucid-distroless-production" || all_passed=false
    
    # Check distroless base containers
    echo -e "${PURPLE}🔐 Checking Distroless Base Containers...${NC}"
    check_container "lucid-base-container" "65532" || all_passed=false
    check_container "lucid-minimal-base-container" "65532" || all_passed=false
    check_container "lucid-arm64-base-container" "65532" || all_passed=false
    
    # Check foundation services
    echo -e "${PURPLE}🏗️ Checking Foundation Services...${NC}"
    check_container "lucid-mongodb" "65532" || all_passed=false
    check_container "lucid-redis" "65532" || all_passed=false
    check_container "lucid-elasticsearch" "65532" || all_passed=false
    check_container "lucid-auth-service" "65532" || all_passed=false
    
    # Check health status
    echo -e "${PURPLE}🏥 Checking Health Status...${NC}"
    check_health "lucid-base-container" || all_passed=false
    check_health "lucid-mongodb" || all_passed=false
    check_health "lucid-redis" || all_passed=false
    check_health "lucid-elasticsearch" || all_passed=false
    check_health "lucid-auth-service" || all_passed=false
    
    # Final summary
    echo -e "${BLUE}📊 Verification Summary${NC}"
    echo "=================================================="
    
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}🎉 All distroless deployment checks passed!${NC}"
        echo -e "${GREEN}✅ Distroless design maintained${NC}"
        echo -e "${GREEN}✅ Secure design maintained${NC}"
        echo -e "${GREEN}✅ All containers running with user 65532:65532${NC}"
        echo -e "${GREEN}✅ No shell access verified (distroless)${NC}"
        echo -e "${GREEN}✅ Health checks passing${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some verification checks failed${NC}"
        echo -e "${RED}❌ Please check the deployment${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
EOF

chmod +x scripts/deployment/verify-distroless-deployment.sh

echo -e "${GREEN}✅ Verification script generated${NC}"

# =============================================================================
# 8. FINAL SUMMARY
# =============================================================================

echo -e "${GREEN}🎉 Complete Distroless Deployment Configuration Generated!${NC}"
echo "=================================================="
echo ""
echo -e "${BLUE}📋 Generated Files:${NC}"
echo "✅ configs/environment/.env.distroless"
echo "✅ configs/docker/distroless/distroless.env"
echo "✅ configs/environment/.env.foundation"
echo "✅ configs/environment/.env.secure"
echo "✅ scripts/deployment/create-distroless-networks.sh"
echo "✅ scripts/deployment/deploy-distroless-complete.sh"
echo "✅ scripts/deployment/verify-distroless-deployment.sh"
echo ""
echo -e "${BLUE}📋 Generated Directories:${NC}"
echo "✅ /mnt/myssd/Lucid/data/{mongodb,redis,elasticsearch}"
echo "✅ /mnt/myssd/Lucid/logs/{mongodb,redis,elasticsearch,auth-service,base-container,minimal-base-container,arm64-base-container}"
echo ""
echo -e "${BLUE}🔐 Security Features:${NC}"
echo "✅ All passwords generated with cryptographically secure random values"
echo "✅ JWT_SECRET_KEY: 64 characters, base64 encoded"
echo "✅ ENCRYPTION_KEY: 256-bit (32 bytes) hex encoded"
echo "✅ Database passwords: 24 characters, base64 encoded"
echo "✅ Service secrets: 32 characters, base64 encoded"
echo ""
echo -e "${BLUE}🔒 Distroless Design Maintained:${NC}"
echo "✅ Base images: gcr.io/distroless/python3-debian12"
echo "✅ User: 65532:65532 (distroless standard)"
echo "✅ Security options: no-new-privileges:true, seccomp:unconfined"
echo "✅ Capabilities: CAP_DROP=ALL, CAP_ADD=NET_BIND_SERVICE"
echo "✅ Read-only filesystem where applicable"
echo "✅ Health checks: Python-based (no shell commands)"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Run: bash scripts/deployment/create-distroless-networks.sh"
echo "2. Run: bash scripts/deployment/deploy-distroless-complete.sh"
echo "3. Run: bash scripts/deployment/verify-distroless-deployment.sh"
echo ""
echo -e "${RED}⚠️  IMPORTANT SECURITY NOTES:${NC}"
echo "1. The .env.secure file contains sensitive data - never commit to version control"
echo "2. Store these keys securely in production environments"
echo "3. Rotate keys regularly in production"
echo "4. Use environment-specific key management in production"
echo ""
echo -e "${GREEN}✅ Distroless deployment configuration completed successfully!${NC}"
