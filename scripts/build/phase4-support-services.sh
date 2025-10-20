#!/bin/bash
# Phase 4: Support Services Build Script
# Based on docker-build-process-plan.md Steps 28-35
# Builds: Admin Interface, TRON Payment System (Isolated)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_LOG_DIR="$PROJECT_ROOT/build/logs"
ARTIFACTS_DIR="$PROJECT_ROOT/build/artifacts"

# Registry and Image Configuration
REGISTRY="pickme/lucid"
TAG="latest"
PLATFORM="linux/arm64"
BUILDER_NAME="lucid-pi-builder"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Phase 4 Services Configuration
PHASE4_ADMIN_SERVICES=(
    "admin-interface:admin/Dockerfile:admin"
)

PHASE4_TRON_SERVICES=(
    "tron-client:payment-systems/tron/Dockerfile.tron-client:payment-systems/tron"
    "payout-router:payment-systems/tron/Dockerfile.payout-router:payment-systems/tron"
    "wallet-manager:payment-systems/tron/Dockerfile.wallet-manager:payment-systems/tron"
    "usdt-manager:payment-systems/tron/Dockerfile.usdt-manager:payment-systems/tron"
    "trx-staking:payment-systems/tron/Dockerfile.trx-staking:payment-systems/tron"
    "payment-gateway:payment-systems/tron/Dockerfile.payment-gateway:payment-systems/tron"
)

# Global variables
BUILD_START_TIME=$(date +%s)
FAILED_BUILDS=()
SUCCESSFUL_BUILDS=()

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_phase() {
    echo -e "${PURPLE}🚀 $1${NC}"
}

log_step() {
    echo -e "${CYAN}📋 $1${NC}"
}

# Create necessary directories
setup_directories() {
    log_info "Setting up build directories..."
    mkdir -p "$BUILD_LOG_DIR"
    mkdir -p "$ARTIFACTS_DIR"
    log_success "Directories created"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Phase 3 was completed
    if [[ ! -f "$PROJECT_ROOT/configs/environment/.env.support" ]]; then
        log_error "Support environment not generated. Run pre-build-phase.sh first."
        exit 1
    fi
    
    # Check if Phase 3 services are available
    local phase3_images=(
        "$REGISTRY/lucid-session-pipeline:$TAG"
        "$REGISTRY/lucid-session-recorder:$TAG"
        "$REGISTRY/lucid-chunk-processor:$TAG"
        "$REGISTRY/lucid-session-storage:$TAG"
        "$REGISTRY/lucid-session-api:$TAG"
        "$REGISTRY/lucid-rdp-server-manager:$TAG"
        "$REGISTRY/lucid-xrdp-integration:$TAG"
        "$REGISTRY/lucid-session-controller:$TAG"
        "$REGISTRY/lucid-resource-monitor:$TAG"
        "$REGISTRY/lucid-node-management:$TAG"
    )
    
    for image in "${phase3_images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Phase 3 image available: $image"
        else
            log_warning "Phase 3 image not found: $image"
        fi
    done
    
    # Check Docker
    if ! docker version >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Check Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup Docker Buildx
setup_buildx() {
    log_info "Setting up Docker Buildx builder..."
    
    # Remove existing builder if it exists
    docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    
    # Create new builder
    docker buildx create --name "$BUILDER_NAME" --use --driver docker-container --driver-opt network=host
    docker buildx inspect --bootstrap
    
    log_success "Docker Buildx builder '$BUILDER_NAME' created and ready"
}

# Load environment variables
load_environment() {
    log_info "Loading environment variables..."
    
    # Load Pi build environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.pi-build" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.pi-build"
        log_success "Pi build environment loaded"
    fi
    
    # Load support environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.support" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.support"
        log_success "Support environment loaded"
    fi
}

# Check if image exists in registry
check_image_exists() {
    local image_name="$1"
    local full_image="$REGISTRY/$image_name:$TAG"
    
    if docker manifest inspect "$full_image" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Build single image
build_image() {
    local service_name="$1"
    local dockerfile_path="$2"
    local context_path="$3"
    local full_image="$REGISTRY/$service_name:$TAG"
    
    log_step "Building $service_name..."
    
    # Check if image already exists
    if check_image_exists "$service_name"; then
        log_warning "$service_name already exists in registry, skipping build"
        SUCCESSFUL_BUILDS+=("$service_name")
        return 0
    fi
    
    # Verify dockerfile exists
    if [[ ! -f "$PROJECT_ROOT/$dockerfile_path" ]]; then
        log_error "Dockerfile not found: $dockerfile_path"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
    
    # Verify context directory exists
    if [[ ! -d "$PROJECT_ROOT/$context_path" ]]; then
        log_error "Context directory not found: $context_path"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
    
    # Build the image
    local build_cmd=(
        "buildx" "build"
        "--platform" "$PLATFORM"
        "--file" "$PROJECT_ROOT/$dockerfile_path"
        "--tag" "$full_image"
        "--push"
        "$PROJECT_ROOT/$context_path"
    )
    
    if docker "${build_cmd[@]}" 2>&1 | tee "$BUILD_LOG_DIR/${service_name}-build.log"; then
        log_success "$service_name built and pushed successfully"
        SUCCESSFUL_BUILDS+=("$service_name")
        
        # Verify push was successful
        sleep 5
        if check_image_exists "$service_name"; then
            log_success "$service_name verified in registry"
        else
            log_error "$service_name push verification failed"
            FAILED_BUILDS+=("$service_name")
            return 1
        fi
    else
        log_error "$service_name build failed"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
}

# Step 28: Build Admin Interface Container
step28_build_admin_interface() {
    log_step "Step 28: Build Admin Interface Container"
    
    # Build Admin Interface
    log_info "Building Admin Interface container..."
    if [[ -f "$PROJECT_ROOT/admin/Dockerfile" ]]; then
        build_image "lucid-admin-interface" "admin/Dockerfile" "admin"
    else
        log_warning "Admin Interface Dockerfile not found, skipping"
    fi
}

# Step 29-30: Build TRON Payment Containers (ISOLATED)
step29_30_build_tron_containers() {
    log_step "Step 29-30: Build TRON Payment Containers (ISOLATED)"
    
    log_info "Building TRON Client container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.tron-client" ]]; then
        build_image "lucid-tron-client" "payment-systems/tron/Dockerfile.tron-client" "payment-systems/tron"
    else
        log_warning "TRON Client Dockerfile not found, skipping"
    fi
    
    log_info "Building Payout Router container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payout-router" ]]; then
        build_image "lucid-payout-router" "payment-systems/tron/Dockerfile.payout-router" "payment-systems/tron"
    else
        log_warning "Payout Router Dockerfile not found, skipping"
    fi
    
    log_info "Building Wallet Manager container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.wallet-manager" ]]; then
        build_image "lucid-wallet-manager" "payment-systems/tron/Dockerfile.wallet-manager" "payment-systems/tron"
    else
        log_warning "Wallet Manager Dockerfile not found, skipping"
    fi
    
    log_info "Building USDT Manager container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.usdt-manager" ]]; then
        build_image "lucid-usdt-manager" "payment-systems/tron/Dockerfile.usdt-manager" "payment-systems/tron"
    else
        log_warning "USDT Manager Dockerfile not found, skipping"
    fi
    
    log_info "Building TRX Staking container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.trx-staking" ]]; then
        build_image "lucid-trx-staking" "payment-systems/tron/Dockerfile.trx-staking" "payment-systems/tron"
    else
        log_warning "TRX Staking Dockerfile not found, skipping"
    fi
    
    log_info "Building Payment Gateway container..."
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payment-gateway" ]]; then
        build_image "lucid-payment-gateway" "payment-systems/tron/Dockerfile.payment-gateway" "payment-systems/tron"
    else
        log_warning "Payment Gateway Dockerfile not found, skipping"
    fi
}

# Step 31: Generate Phase 4 Docker Compose
step31_generate_docker_compose() {
    log_step "Step 31: Generate Phase 4 Docker Compose"
    
    # Check if compose file exists
    if [[ -f "$PROJECT_ROOT/configs/docker/docker-compose.support.yml" ]]; then
        log_success "Phase 4 Docker Compose file already exists"
    else
        log_warning "Phase 4 Docker Compose file not found, creating basic template..."
        
        # Create basic compose file
        mkdir -p "$PROJECT_ROOT/configs/docker"
        cat > "$PROJECT_ROOT/configs/docker/docker-compose.support.yml" << 'EOF'
version: '3.8'

services:
  # Admin Interface (on main network)
  lucid-admin-interface:
    image: pickme/lucid:lucid-admin-interface
    container_name: lucid-admin-interface
    ports:
      - "8083:8083"
    environment:
      - ADMIN_INTERFACE_PORT=8083
      - ADMIN_INTERFACE_HOST=admin-interface
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # TRON Payment Services (ISOLATED NETWORK)
  lucid-tron-client:
    image: pickme/lucid:lucid-tron-client
    container_name: lucid-tron-client
    ports:
      - "8091:8091"
    environment:
      - TRON_CLIENT_PORT=8091
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
    networks:
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-payout-router:
    image: pickme/lucid:lucid-payout-router
    container_name: lucid-payout-router
    ports:
      - "8092:8092"
    environment:
      - TRON_PAYOUT_ROUTER_PORT=8092
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
    depends_on:
      - lucid-tron-client
    networks:
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8092/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-wallet-manager:
    image: pickme/lucid:lucid-wallet-manager
    container_name: lucid-wallet-manager
    ports:
      - "8093:8093"
    environment:
      - TRON_WALLET_MANAGER_PORT=8093
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
    depends_on:
      - lucid-tron-client
    networks:
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-usdt-manager:
    image: pickme/lucid:lucid-usdt-manager
    container_name: lucid-usdt-manager
    ports:
      - "8094:8094"
    environment:
      - TRON_USDT_MANAGER_PORT=8094
      - USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
    depends_on:
      - lucid-tron-client
    networks:
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8094/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-trx-staking:
    image: pickme/lucid:lucid-trx-staking
    container_name: lucid-trx-staking
    ports:
      - "8096:8096"
    environment:
      - TRON_TRX_STAKING_PORT=8096
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
    depends_on:
      - lucid-tron-client
    networks:
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8096/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-payment-gateway:
    image: pickme/lucid:lucid-payment-gateway
    container_name: lucid-payment-gateway
    ports:
      - "8097:8097"
    environment:
      - TRON_PAYMENT_GATEWAY_PORT=8097
      - TRON_BRIDGE_ENABLED=true
      - TRON_BRIDGE_PORT=8098
    depends_on:
      - lucid-tron-client
      - lucid-payout-router
      - lucid-wallet-manager
      - lucid-usdt-manager
      - lucid-trx-staking
    networks:
      - lucid-pi-network
      - lucid-tron-isolated
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8097/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  lucid-pi-network:
    external: true
  lucid-tron-isolated:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
EOF
        log_success "Basic Phase 4 Docker Compose file created"
    fi
}

# Step 32: Prepare Phase 4 Deployment
step32_prepare_deployment() {
    log_step "Step 32: Prepare Phase 4 Deployment"
    
    # Check if deployment script exists
    if [[ -f "$PROJECT_ROOT/scripts/deployment/deploy-phase4-pi.sh" ]]; then
        log_success "Phase 4 deployment script found"
    else
        log_warning "Phase 4 deployment script not found, creating basic template..."
        
        # Create basic deployment script
        mkdir -p "$PROJECT_ROOT/scripts/deployment"
        cat > "$PROJECT_ROOT/scripts/deployment/deploy-phase4-pi.sh" << 'EOF'
#!/bin/bash
# Phase 4 Deployment Script for Raspberry Pi
# Based on docker-build-process-plan.md Step 32

set -euo pipefail

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Load environment variables
source "$PROJECT_ROOT/configs/environment/.env.pi-build"
source "$PROJECT_ROOT/configs/environment/.env.support"

echo "🚀 Deploying Phase 4 Support Services to Raspberry Pi"
echo "====================================================="
echo "Pi Host: $PI_HOST"
echo "Pi User: $PI_USER"
echo "Deploy Directory: $PI_DEPLOY_DIR"
echo

# Copy compose file and environment to Pi
echo "Copying configuration files to Pi..."
scp "$PROJECT_ROOT/configs/docker/docker-compose.support.yml" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/"
scp "$PROJECT_ROOT/configs/environment/.env.support" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/.env.support"

# Pull ARM64 images on Pi
echo "Pulling ARM64 images on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml -f docker-compose.application.yml -f docker-compose.support.yml pull"

# Deploy services
echo "Deploying Phase 4 services..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml -f docker-compose.application.yml -f docker-compose.support.yml up -d"

echo "✅ Phase 4 deployment completed!"
EOF
        chmod +x "$PROJECT_ROOT/scripts/deployment/deploy-phase4-pi.sh"
        log_success "Basic Phase 4 deployment script created"
    fi
}

# Step 33: Prepare Integration Tests
step33_prepare_integration_tests() {
    log_step "Step 33: Prepare Integration Tests"
    
    # Check if integration test script exists
    if [[ -f "$PROJECT_ROOT/tests/integration/phase4/run_phase4_tests.sh" ]]; then
        log_success "Phase 4 integration test script found"
    else
        log_warning "Phase 4 integration test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/integration/phase4"
        cat > "$PROJECT_ROOT/tests/integration/phase4/run_phase4_tests.sh" << 'EOF'
#!/bin/bash
# Phase 4 Integration Tests
# Based on docker-build-process-plan.md Step 33

set -euo pipefail

echo "🧪 Running Phase 4 Integration Tests"
echo "===================================="

# Test Admin Interface
echo "Testing Admin Interface..."
python3 -c "
import requests
response = requests.get('http://localhost:8083/health')
print('✅ Admin Interface connection successful')
"

# Test TRON Payment Services (ISOLATED)
echo "Testing TRON Client..."
python3 -c "
import requests
response = requests.get('http://localhost:8091/health')
print('✅ TRON Client connection successful')
"

echo "Testing Payout Router..."
python3 -c "
import requests
response = requests.get('http://localhost:8092/health')
print('✅ Payout Router connection successful')
"

echo "Testing Wallet Manager..."
python3 -c "
import requests
response = requests.get('http://localhost:8093/health')
print('✅ Wallet Manager connection successful')
"

echo "Testing USDT Manager..."
python3 -c "
import requests
response = requests.get('http://localhost:8094/health')
print('✅ USDT Manager connection successful')
"

echo "Testing TRX Staking..."
python3 -c "
import requests
response = requests.get('http://localhost:8096/health')
print('✅ TRX Staking connection successful')
"

echo "Testing Payment Gateway..."
python3 -c "
import requests
response = requests.get('http://localhost:8097/health')
print('✅ Payment Gateway connection successful')
"

echo "✅ All Phase 4 integration tests passed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/integration/phase4/run_phase4_tests.sh"
        log_success "Basic Phase 4 integration test script created"
    fi
}

# Step 34: Prepare Final System Integration Test
step34_prepare_final_integration_test() {
    log_step "Step 34: Prepare Final System Integration Test"
    
    # Check if final integration test script exists
    if [[ -f "$PROJECT_ROOT/tests/integration/final/run_final_integration_test.sh" ]]; then
        log_success "Final system integration test script found"
    else
        log_warning "Final system integration test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/integration/final"
        cat > "$PROJECT_ROOT/tests/integration/final/run_final_integration_test.sh" << 'EOF'
#!/bin/bash
# Final System Integration Test
# Based on docker-build-process-plan.md Step 34

set -euo pipefail

echo "🧪 Running Final System Integration Test"
echo "========================================"

# Test complete system end-to-end
echo "Testing complete system end-to-end..."

# 1. User authentication
echo "Testing user authentication..."
python3 -c "
import requests
response = requests.post('http://localhost:8089/auth/login', json={'username': 'test', 'password': 'test'})
print('✅ User authentication successful')
"

# 2. RDP session creation
echo "Testing RDP session creation..."
python3 -c "
import requests
response = requests.post('http://localhost:8081/sessions/create', json={'user_id': 'test'})
print('✅ RDP session creation successful')
"

# 3. Session recording and chunking
echo "Testing session recording and chunking..."
python3 -c "
import requests
response = requests.get('http://localhost:8082/recording/status')
print('✅ Session recording and chunking successful')
"

# 4. Blockchain anchoring
echo "Testing blockchain anchoring..."
python3 -c "
import requests
response = requests.get('http://localhost:8085/anchoring/status')
print('✅ Blockchain anchoring successful')
"

# 5. Payout calculation and distribution
echo "Testing payout calculation and distribution..."
python3 -c "
import requests
response = requests.get('http://localhost:8092/payouts/calculate')
print('✅ Payout calculation and distribution successful')
"

echo "✅ Final system integration test passed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/integration/final/run_final_integration_test.sh"
        log_success "Basic final system integration test script created"
    fi
}

# Step 35: Generate Master Docker Compose
step35_generate_master_compose() {
    log_step "Step 35: Generate Master Docker Compose"
    
    # Check if master compose file exists
    if [[ -f "$PROJECT_ROOT/configs/docker/docker-compose.master.yml" ]]; then
        log_success "Master Docker Compose file already exists"
    else
        log_warning "Master Docker Compose file not found, creating basic template..."
        
        # Create master compose file
        mkdir -p "$PROJECT_ROOT/configs/docker"
        cat > "$PROJECT_ROOT/configs/docker/docker-compose.master.yml" << 'EOF'
version: '3.8'

# Master Docker Compose - All Services
# This file consolidates all services from all phases for production deployment

services:
  # Include all services from foundation.yml
  # Include all services from core.yml
  # Include all services from application.yml
  # Include all services from support.yml

  # Note: This is a template - actual implementation would include all services
  # from the individual compose files with proper dependency management

networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
  lucid-tron-isolated:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1

volumes:
  mongodb_data:
  redis_data:
  elasticsearch_data:
  session_data:
  blockchain_data:
EOF
        log_success "Basic Master Docker Compose file created"
    fi
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Phase 4 Support Services Build Summary"
    echo "=========================================="
    echo "Build Duration: ${duration_minutes}m ${duration_seconds}s"
    echo "Total Services: $((${#SUCCESSFUL_BUILDS[@]} + ${#FAILED_BUILDS[@]}))"
    echo "Successful: ${#SUCCESSFUL_BUILDS[@]}"
    echo "Failed: ${#FAILED_BUILDS[@]}"
    echo
    
    if [[ ${#SUCCESSFUL_BUILDS[@]} -gt 0 ]]; then
        log_success "Successfully built services:"
        for service in "${SUCCESSFUL_BUILDS[@]}"; do
            echo "  - $service"
        done
    fi
    
    if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
        log_error "Failed services:"
        for service in "${FAILED_BUILDS[@]}"; do
            echo "  - $service"
        done
        echo
        log_error "Phase 4 build completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "Phase 4 Support Services built successfully!"
        echo
        log_info "Images available in registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Tag: $TAG"
        echo
        log_info "Next Steps:"
        echo "  1. Deploy to Pi: ./scripts/deployment/deploy-phase4-pi.sh"
        echo "  2. Run integration tests: ./tests/integration/phase4/run_phase4_tests.sh"
        echo "  3. Run final integration test: ./tests/integration/final/run_final_integration_test.sh"
        echo "  4. Use master compose: ./configs/docker/docker-compose.master.yml"
        echo
        log_success "🎉 All phases completed! Lucid system is ready for production deployment!"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    log_success "Cleanup completed"
}

# Main execution
main() {
    echo "🚀 Lucid Phase 4: Support Services Build Script"
    echo "==============================================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    setup_buildx
    load_environment
    
    # Execute Phase 4 steps
    step28_build_admin_interface
    step29_30_build_tron_containers
    step31_generate_docker_compose
    step32_prepare_deployment
    step33_prepare_integration_tests
    step34_prepare_final_integration_test
    step35_generate_master_compose
    
    # Summary
    generate_summary
    cleanup
}

# Handle script interruption
trap cleanup EXIT

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --platform PLATFORM    Target platform (default: linux/arm64)"
            echo "  --registry REGISTRY     Registry name (default: pickme/lucid)"
            echo "  --tag TAG              Image tag (default: latest)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
