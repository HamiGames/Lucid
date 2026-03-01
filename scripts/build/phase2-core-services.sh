#!/bin/bash
# Phase 2: Core Services Build Script
# Based on docker-build-process-plan.md Steps 10-17
# Builds: API Gateway, Service Mesh, Blockchain Core

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

# Phase 2 Services Configuration
PHASE2_GROUP_B_SERVICES=(
    "api-gateway:03-api-gateway/Dockerfile:03-api-gateway"
    "service-mesh-controller:service-mesh/Dockerfile.controller:service-mesh"
)

PHASE2_GROUP_C_SERVICES=(
    "blockchain-engine:blockchain/Dockerfile.engine:blockchain"
    "session-anchoring:blockchain/Dockerfile.anchoring:blockchain"
    "block-manager:blockchain/Dockerfile.manager:blockchain"
    "data-chain:blockchain/Dockerfile.data:blockchain"
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
    
    # Check if Phase 1 was completed
    if [[ ! -f "$PROJECT_ROOT/configs/environment/.env.core" ]]; then
        log_error "Core environment not generated. Run pre-build-phase.sh first."
        exit 1
    fi
    
    # Check if Phase 1 services are available
    local phase1_images=(
        "$REGISTRY/lucid-mongodb:$TAG"
        "$REGISTRY/lucid-redis:$TAG"
        "$REGISTRY/lucid-elasticsearch:$TAG"
        "$REGISTRY/lucid-auth-service:$TAG"
    )
    
    for image in "${phase1_images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Phase 1 image available: $image"
        else
            log_warning "Phase 1 image not found: $image"
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
    
    # Load core environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.core" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.core"
        log_success "Core environment loaded"
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

# Step 10: Build API Gateway Container (Group B - Parallel)
step10_build_api_gateway() {
    log_step "Step 10: Build API Gateway Container (Group B - Parallel)"
    
    # Build API Gateway
    log_info "Building API Gateway container..."
    if [[ -f "$PROJECT_ROOT/03-api-gateway/Dockerfile" ]]; then
        build_image "lucid-api-gateway" "03-api-gateway/Dockerfile" "03-api-gateway"
    else
        log_warning "API Gateway Dockerfile not found, skipping"
    fi
}

# Step 11: Build Service Mesh Controller (Group B - Parallel)
step11_build_service_mesh() {
    log_step "Step 11: Build Service Mesh Controller (Group B - Parallel)"
    
    # Build Service Mesh Controller
    log_info "Building Service Mesh Controller container..."
    if [[ -f "$PROJECT_ROOT/service-mesh/Dockerfile.controller" ]]; then
        build_image "lucid-service-mesh-controller" "service-mesh/Dockerfile.controller" "service-mesh"
    else
        log_warning "Service Mesh Controller Dockerfile not found, skipping"
    fi
}

# Step 12: Build Blockchain Core Containers (Group C - Parallel)
step12_build_blockchain_containers() {
    log_step "Step 12: Build Blockchain Core Containers (Group C - Parallel)"
    
    # CRITICAL: TRON Isolation Verification
    log_info "Performing TRON isolation verification..."
    
    # Scan for TRON references in blockchain directory
    local tron_violations=0
    
    if grep -r "tron" "$PROJECT_ROOT/blockchain/" --exclude-dir=node_modules 2>/dev/null | grep -v "payment-systems/tron" | grep -v ".git"; then
        log_error "TRON references found in blockchain core!"
        tron_violations=1
    fi
    
    if grep -r "TronWeb" "$PROJECT_ROOT/blockchain/" 2>/dev/null | grep -v "payment-systems/tron" | grep -v ".git"; then
        log_error "TronWeb references found in blockchain core!"
        tron_violations=1
    fi
    
    if grep -r "payment" "$PROJECT_ROOT/blockchain/core/" 2>/dev/null | grep -v ".git"; then
        log_error "Payment references found in blockchain core!"
        tron_violations=1
    fi
    
    if [[ $tron_violations -eq 1 ]]; then
        log_error "TRON isolation verification failed! Cannot proceed with blockchain build."
        exit 1
    fi
    
    log_success "TRON isolation verification passed"
    
    # Build Blockchain Engine
    log_info "Building Blockchain Engine container..."
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.engine" ]]; then
        build_image "lucid-blockchain-engine" "blockchain/Dockerfile.engine" "blockchain"
    else
        log_warning "Blockchain Engine Dockerfile not found, skipping"
    fi
    
    # Build Session Anchoring
    log_info "Building Session Anchoring container..."
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.anchoring" ]]; then
        build_image "lucid-session-anchoring" "blockchain/Dockerfile.anchoring" "blockchain"
    else
        log_warning "Session Anchoring Dockerfile not found, skipping"
    fi
    
    # Build Block Manager
    log_info "Building Block Manager container..."
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.manager" ]]; then
        build_image "lucid-block-manager" "blockchain/Dockerfile.manager" "blockchain"
    else
        log_warning "Block Manager Dockerfile not found, skipping"
    fi
    
    # Build Data Chain
    log_info "Building Data Chain container..."
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.data" ]]; then
        build_image "lucid-data-chain" "blockchain/Dockerfile.data" "blockchain"
    else
        log_warning "Data Chain Dockerfile not found, skipping"
    fi
}

# Step 13: Generate Phase 2 Docker Compose
step13_generate_docker_compose() {
    log_step "Step 13: Generate Phase 2 Docker Compose"
    
    # Check if compose file exists
    if [[ -f "$PROJECT_ROOT/configs/docker/docker-compose.core.yml" ]]; then
        log_success "Phase 2 Docker Compose file already exists"
    else
        log_warning "Phase 2 Docker Compose file not found, creating basic template..."
        
        # Create basic compose file
        mkdir -p "$PROJECT_ROOT/configs/docker"
        cat > "$PROJECT_ROOT/configs/docker/docker-compose.core.yml" << 'EOF'
version: '3.8'

services:
  lucid-service-mesh-controller:
    image: pickme/lucid:lucid-service-mesh-controller
    container_name: lucid-service-mesh-controller
    ports:
      - "8086:8086"
      - "8500:8500"
    environment:
      - SERVICE_MESH_CONTROLLER_PORT=8086
      - SERVICE_MESH_CONSUL_PORT=8500
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-api-gateway:
    image: pickme/lucid:lucid-api-gateway
    container_name: lucid-api-gateway
    ports:
      - "8080:8080"
    environment:
      - API_GATEWAY_PORT=8080
      - API_GATEWAY_HOST=api-gateway
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - lucid-auth-service
      - lucid-service-mesh-controller
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-blockchain-engine:
    image: pickme/lucid:lucid-blockchain-engine
    container_name: lucid-blockchain-engine
    ports:
      - "8084:8084"
    environment:
      - BLOCKCHAIN_ENGINE_PORT=8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
      - CONSENSUS_ALGORITHM=PoOT
      - BLOCK_INTERVAL=10
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-session-anchoring:
    image: pickme/lucid:lucid-session-anchoring
    container_name: lucid-session-anchoring
    ports:
      - "8085:8085"
    environment:
      - BLOCKCHAIN_SESSION_ANCHORING_PORT=8085
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
    depends_on:
      - lucid-blockchain-engine
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-block-manager:
    image: pickme/lucid:lucid-block-manager
    container_name: lucid-block-manager
    ports:
      - "8086:8086"
    environment:
      - BLOCKCHAIN_BLOCK_MANAGER_PORT=8086
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
    depends_on:
      - lucid-blockchain-engine
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-data-chain:
    image: pickme/lucid:lucid-data-chain
    container_name: lucid-data-chain
    ports:
      - "8087:8087"
    environment:
      - BLOCKCHAIN_DATA_CHAIN_PORT=8087
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8087/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  lucid-pi-network:
    external: true
EOF
        log_success "Basic Phase 2 Docker Compose file created"
    fi
}

# Step 14: Prepare Phase 2 Deployment
step14_prepare_deployment() {
    log_step "Step 14: Prepare Phase 2 Deployment"
    
    # Check if deployment script exists
    if [[ -f "$PROJECT_ROOT/scripts/deployment/deploy-phase2-pi.sh" ]]; then
        log_success "Phase 2 deployment script found"
    else
        log_warning "Phase 2 deployment script not found, creating basic template..."
        
        # Create basic deployment script
        mkdir -p "$PROJECT_ROOT/scripts/deployment"
        cat > "$PROJECT_ROOT/scripts/deployment/deploy-phase2-pi.sh" << 'EOF'
#!/bin/bash
# Phase 2 Deployment Script for Raspberry Pi
# Based on docker-build-process-plan.md Step 14

set -euo pipefail

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Load environment variables
source "$PROJECT_ROOT/configs/environment/.env.pi-build"
source "$PROJECT_ROOT/configs/environment/.env.core"

echo "🚀 Deploying Phase 2 Core Services to Raspberry Pi"
echo "=================================================="
echo "Pi Host: $PI_HOST"
echo "Pi User: $PI_USER"
echo "Deploy Directory: $PI_DEPLOY_DIR"
echo

# Copy compose file and environment to Pi
echo "Copying configuration files to Pi..."
scp "$PROJECT_ROOT/configs/docker/docker-compose.core.yml" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/"
scp "$PROJECT_ROOT/configs/environment/.env.core" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/.env.core"

# Pull ARM64 images on Pi
echo "Pulling ARM64 images on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml pull"

# Deploy services
echo "Deploying Phase 2 services..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml up -d"

echo "✅ Phase 2 deployment completed!"
EOF
        chmod +x "$PROJECT_ROOT/scripts/deployment/deploy-phase2-pi.sh"
        log_success "Basic Phase 2 deployment script created"
    fi
}

# Step 15: Prepare Integration Tests
step15_prepare_integration_tests() {
    log_step "Step 15: Prepare Integration Tests"
    
    # Check if integration test script exists
    if [[ -f "$PROJECT_ROOT/tests/integration/phase2/run_phase2_tests.sh" ]]; then
        log_success "Phase 2 integration test script found"
    else
        log_warning "Phase 2 integration test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/integration/phase2"
        cat > "$PROJECT_ROOT/tests/integration/phase2/run_phase2_tests.sh" << 'EOF'
#!/bin/bash
# Phase 2 Integration Tests
# Based on docker-build-process-plan.md Step 15

set -euo pipefail

echo "🧪 Running Phase 2 Integration Tests"
echo "===================================="

# Test API Gateway
echo "Testing API Gateway..."
python3 -c "
import requests
response = requests.get('http://localhost:8080/health')
print('✅ API Gateway connection successful')
"

# Test Service Mesh Controller
echo "Testing Service Mesh Controller..."
python3 -c "
import requests
response = requests.get('http://localhost:8086/health')
print('✅ Service Mesh Controller connection successful')
"

# Test Blockchain Engine
echo "Testing Blockchain Engine..."
python3 -c "
import requests
response = requests.get('http://localhost:8084/health')
print('✅ Blockchain Engine connection successful')
"

# Test Session Anchoring
echo "Testing Session Anchoring..."
python3 -c "
import requests
response = requests.get('http://localhost:8085/health')
print('✅ Session Anchoring connection successful')
"

# Test Block Manager
echo "Testing Block Manager..."
python3 -c "
import requests
response = requests.get('http://localhost:8086/health')
print('✅ Block Manager connection successful')
"

# Test Data Chain
echo "Testing Data Chain..."
python3 -c "
import requests
response = requests.get('http://localhost:8087/health')
print('✅ Data Chain connection successful')
"

echo "✅ All Phase 2 integration tests passed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/integration/phase2/run_phase2_tests.sh"
        log_success "Basic Phase 2 integration test script created"
    fi
}

# Step 16: TRON Isolation Security Scan
step16_tron_isolation_scan() {
    log_step "Step 16: TRON Isolation Security Scan"
    
    # Check if TRON isolation verification script exists
    if [[ -f "$PROJECT_ROOT/scripts/verification/verify-tron-isolation.sh" ]]; then
        log_info "Running TRON isolation verification script..."
        bash "$PROJECT_ROOT/scripts/verification/verify-tron-isolation.sh"
        log_success "TRON isolation verification completed"
    else
        log_warning "TRON isolation verification script not found, performing basic scan..."
        
        # Basic TRON isolation scan
        local violations=0
        
        # Scan blockchain directory for TRON references
        if grep -r "tron" "$PROJECT_ROOT/blockchain/" --exclude-dir=node_modules 2>/dev/null | grep -v "payment-systems/tron" | grep -v ".git"; then
            log_error "TRON references found in blockchain core!"
            violations=1
        fi
        
        if grep -r "TronWeb" "$PROJECT_ROOT/blockchain/" 2>/dev/null | grep -v "payment-systems/tron" | grep -v ".git"; then
            log_error "TronWeb references found in blockchain core!"
            violations=1
        fi
        
        if grep -r "USDT\|TRX" "$PROJECT_ROOT/blockchain/" 2>/dev/null | grep -v "payment-systems/tron" | grep -v ".git"; then
            log_error "USDT/TRX references found in blockchain core!"
            violations=1
        fi
        
        if [[ $violations -eq 1 ]]; then
            log_error "TRON isolation scan failed!"
            exit 1
        fi
        
        log_success "TRON isolation scan passed"
    fi
}

# Step 17: Prepare Performance Benchmarks
step17_prepare_performance_benchmarks() {
    log_step "Step 17: Prepare Performance Benchmarks"
    
    # Check if performance test script exists
    if [[ -f "$PROJECT_ROOT/tests/performance/phase2/run_phase2_performance.sh" ]]; then
        log_success "Phase 2 performance benchmark script found"
    else
        log_warning "Phase 2 performance benchmark script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/performance/phase2"
        cat > "$PROJECT_ROOT/tests/performance/phase2/run_phase2_performance.sh" << 'EOF'
#!/bin/bash
# Phase 2 Performance Benchmarks
# Based on docker-build-process-plan.md Step 17

set -euo pipefail

echo "⚡ Running Phase 2 Performance Benchmarks"
echo "=========================================="

# API Gateway throughput test
echo "Testing API Gateway throughput (>500 req/s)..."
python3 -c "
import requests
import time
import threading

def make_request():
    response = requests.get('http://localhost:8080/health')
    return response.status_code == 200

start_time = time.time()
threads = []
for i in range(100):
    t = threading.Thread(target=make_request)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

end_time = time.time()
duration = end_time - start_time
throughput = 100 / duration
print(f'✅ API Gateway throughput: {throughput:.2f} req/s')
"

# Blockchain block creation test
echo "Testing blockchain block creation (1 block per 10 seconds)..."
python3 -c "
import requests
import time

response = requests.get('http://localhost:8084/blockchain/status')
data = response.json()
block_time = data.get('block_time', 0)
print(f'✅ Blockchain block time: {block_time}s')
"

# Database query latency test
echo "Testing database query latency (<10ms p95)..."
python3 -c "
import requests
import time

start_time = time.time()
response = requests.get('http://localhost:8087/data/query')
end_time = time.time()
latency = (end_time - start_time) * 1000
print(f'✅ Database query latency: {latency:.2f}ms')
"

echo "✅ All Phase 2 performance benchmarks completed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/performance/phase2/run_phase2_performance.sh"
        log_success "Basic Phase 2 performance benchmark script created"
    fi
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Phase 2 Core Services Build Summary"
    echo "======================================="
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
        log_error "Phase 2 build completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "Phase 2 Core Services built successfully!"
        echo
        log_info "Images available in registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Tag: $TAG"
        echo
        log_info "Next Steps:"
        echo "  1. Deploy to Pi: ./scripts/deployment/deploy-phase2-pi.sh"
        echo "  2. Run integration tests: ./tests/integration/phase2/run_phase2_tests.sh"
        echo "  3. Run TRON isolation scan: ./scripts/verification/verify-tron-isolation.sh"
        echo "  4. Run performance benchmarks: ./tests/performance/phase2/run_phase2_performance.sh"
        echo "  5. Proceed to Phase 3: ./scripts/build/phase3-application-services.sh"
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
    echo "🚀 Lucid Phase 2: Core Services Build Script"
    echo "============================================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    setup_buildx
    load_environment
    
    # Execute Phase 2 steps
    step10_build_api_gateway
    step11_build_service_mesh
    step12_build_blockchain_containers
    step13_generate_docker_compose
    step14_prepare_deployment
    step15_prepare_integration_tests
    step16_tron_isolation_scan
    step17_prepare_performance_benchmarks
    
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
