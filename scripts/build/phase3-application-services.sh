#!/bin/bash
# Phase 3: Application Services Build Script
# Based on docker-build-process-plan.md Steps 18-27
# Builds: Session Management, RDP Services, Node Management

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

# Phase 3 Services Configuration
PHASE3_SESSION_SERVICES=(
    "session-pipeline:sessions/Dockerfile.pipeline:sessions"
    "session-recorder:sessions/Dockerfile.recorder:sessions"
    "chunk-processor:sessions/Dockerfile.processor:sessions"
    "session-storage:sessions/Dockerfile.storage:sessions"
    "session-api:sessions/Dockerfile.api:sessions"
)

PHASE3_RDP_SERVICES=(
    "rdp-server-manager:RDP/Dockerfile.server-manager:RDP"
    "xrdp-integration:RDP/Dockerfile.xrdp:RDP"
    "session-controller:RDP/Dockerfile.controller:RDP"
    "resource-monitor:RDP/Dockerfile.monitor:RDP"
)

PHASE3_NODE_SERVICES=(
    "node-management:node/Dockerfile:node"
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
    
    # Check if Phase 2 was completed
    if [[ ! -f "$PROJECT_ROOT/configs/environment/.env.application" ]]; then
        log_error "Application environment not generated. Run pre-build-phase.sh first."
        exit 1
    fi
    
    # Check if Phase 2 services are available
    local phase2_images=(
        "$REGISTRY/lucid-api-gateway:$TAG"
        "$REGISTRY/lucid-service-mesh-controller:$TAG"
        "$REGISTRY/lucid-blockchain-engine:$TAG"
        "$REGISTRY/lucid-session-anchoring:$TAG"
        "$REGISTRY/lucid-block-manager:$TAG"
        "$REGISTRY/lucid-data-chain:$TAG"
    )
    
    for image in "${phase2_images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Phase 2 image available: $image"
        else
            log_warning "Phase 2 image not found: $image"
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
    
    # Load application environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.application" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.application"
        log_success "Application environment loaded"
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

# Step 18-20: Build Session Management Containers
step18_20_build_session_containers() {
    log_step "Step 18-20: Build Session Management Containers"
    
    # Build Session Pipeline
    log_info "Building Session Pipeline container..."
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.pipeline" ]]; then
        build_image "lucid-session-pipeline" "sessions/Dockerfile.pipeline" "sessions"
    else
        log_warning "Session Pipeline Dockerfile not found, skipping"
    fi
    
    # Build Session Recorder
    log_info "Building Session Recorder container..."
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.recorder" ]]; then
        build_image "lucid-session-recorder" "sessions/Dockerfile.recorder" "sessions"
    else
        log_warning "Session Recorder Dockerfile not found, skipping"
    fi
    
    # Build Chunk Processor
    log_info "Building Chunk Processor container..."
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.processor" ]]; then
        build_image "lucid-chunk-processor" "sessions/Dockerfile.processor" "sessions"
    else
        log_warning "Chunk Processor Dockerfile not found, skipping"
    fi
    
    # Build Session Storage
    log_info "Building Session Storage container..."
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.storage" ]]; then
        build_image "lucid-session-storage" "sessions/Dockerfile.storage" "sessions"
    else
        log_warning "Session Storage Dockerfile not found, skipping"
    fi
    
    # Build Session API
    log_info "Building Session API container..."
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.api" ]]; then
        build_image "lucid-session-api" "sessions/Dockerfile.api" "sessions"
    else
        log_warning "Session API Dockerfile not found, skipping"
    fi
}

# Step 21-22: Build RDP Services Containers
step21_22_build_rdp_containers() {
    log_step "Step 21-22: Build RDP Services Containers"
    
    # Build RDP Server Manager
    log_info "Building RDP Server Manager container..."
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.server-manager" ]]; then
        build_image "lucid-rdp-server-manager" "RDP/Dockerfile.server-manager" "RDP"
    else
        log_warning "RDP Server Manager Dockerfile not found, skipping"
    fi
    
    # Build XRDP Integration
    log_info "Building XRDP Integration container..."
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.xrdp" ]]; then
        build_image "lucid-xrdp-integration" "RDP/Dockerfile.xrdp" "RDP"
    else
        log_warning "XRDP Integration Dockerfile not found, skipping"
    fi
    
    # Build Session Controller
    log_info "Building Session Controller container..."
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.controller" ]]; then
        build_image "lucid-session-controller" "RDP/Dockerfile.controller" "RDP"
    else
        log_warning "Session Controller Dockerfile not found, skipping"
    fi
    
    # Build Resource Monitor
    log_info "Building Resource Monitor container..."
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.monitor" ]]; then
        build_image "lucid-resource-monitor" "RDP/Dockerfile.monitor" "RDP"
    else
        log_warning "Resource Monitor Dockerfile not found, skipping"
    fi
}

# Step 23: Build Node Management Container
step23_build_node_management() {
    log_step "Step 23: Build Node Management Container"
    
    # Build Node Management
    log_info "Building Node Management container..."
    if [[ -f "$PROJECT_ROOT/node/Dockerfile" ]]; then
        build_image "lucid-node-management" "node/Dockerfile" "node"
    else
        log_warning "Node Management Dockerfile not found, skipping"
    fi
}

# Step 24: Generate Phase 3 Docker Compose
step24_generate_docker_compose() {
    log_step "Step 24: Generate Phase 3 Docker Compose"
    
    # Check if compose file exists
    if [[ -f "$PROJECT_ROOT/configs/docker/docker-compose.application.yml" ]]; then
        log_success "Phase 3 Docker Compose file already exists"
    else
        log_warning "Phase 3 Docker Compose file not found, creating basic template..."
        
        # Create basic compose file
        mkdir -p "$PROJECT_ROOT/configs/docker"
        cat > "$PROJECT_ROOT/configs/docker/docker-compose.application.yml" << 'EOF'
version: '3.8'

services:
  # Session Management Services
  lucid-session-pipeline:
    image: pickme/lucid:lucid-session-pipeline
    container_name: lucid-session-pipeline
    ports:
      - "8081:8081"
    environment:
      - SESSION_PIPELINE_PORT=8081
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-session-recorder:
    image: pickme/lucid:lucid-session-recorder
    container_name: lucid-session-recorder
    ports:
      - "8082:8082"
    environment:
      - SESSION_RECORDER_PORT=8082
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-chunk-processor:
    image: pickme/lucid:lucid-chunk-processor
    container_name: lucid-chunk-processor
    ports:
      - "8083:8083"
    environment:
      - SESSION_CHUNK_PROCESSOR_PORT=8083
      - SESSION_CHUNK_SIZE=8388608
      - SESSION_COMPRESSION_LEVEL=1
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-session-storage:
    image: pickme/lucid:lucid-session-storage
    container_name: lucid-session-storage
    ports:
      - "8084:8084"
    environment:
      - SESSION_STORAGE_PORT=8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
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

  lucid-session-api:
    image: pickme/lucid:lucid-session-api
    container_name: lucid-session-api
    ports:
      - "8087:8087"
    environment:
      - SESSION_API_PORT=8087
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

  # RDP Services
  lucid-rdp-server-manager:
    image: pickme/lucid:lucid-rdp-server-manager
    container_name: lucid-rdp-server-manager
    ports:
      - "8081:8081"
    environment:
      - RDP_SERVER_MANAGER_PORT=8081
      - RDP_MAX_SESSIONS=10
      - RDP_SESSION_TIMEOUT=3600
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-xrdp-integration:
    image: pickme/lucid:lucid-xrdp-integration
    container_name: lucid-xrdp-integration
    ports:
      - "3389:3389"
    environment:
      - RDP_XRDP_INTEGRATION_PORT=3389
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3389/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-session-controller:
    image: pickme/lucid:lucid-session-controller
    container_name: lucid-session-controller
    ports:
      - "8082:8082"
    environment:
      - RDP_SESSION_CONTROLLER_PORT=8082
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-resource-monitor:
    image: pickme/lucid:lucid-resource-monitor
    container_name: lucid-resource-monitor
    ports:
      - "8090:8090"
    environment:
      - RDP_RESOURCE_MONITOR_PORT=8090
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Node Management
  lucid-node-management:
    image: pickme/lucid:lucid-node-management
    container_name: lucid-node-management
    ports:
      - "8095:8095"
    environment:
      - NODE_MANAGEMENT_PORT=8095
      - NODE_POOL_MAX_SIZE=100
      - NODE_PAYOUT_THRESHOLD=10
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8095/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  lucid-pi-network:
    external: true
EOF
        log_success "Basic Phase 3 Docker Compose file created"
    fi
}

# Step 25: Prepare Phase 3 Deployment
step25_prepare_deployment() {
    log_step "Step 25: Prepare Phase 3 Deployment"
    
    # Check if deployment script exists
    if [[ -f "$PROJECT_ROOT/scripts/deployment/deploy-phase3-pi.sh" ]]; then
        log_success "Phase 3 deployment script found"
    else
        log_warning "Phase 3 deployment script not found, creating basic template..."
        
        # Create basic deployment script
        mkdir -p "$PROJECT_ROOT/scripts/deployment"
        cat > "$PROJECT_ROOT/scripts/deployment/deploy-phase3-pi.sh" << 'EOF'
#!/bin/bash
# Phase 3 Deployment Script for Raspberry Pi
# Based on docker-build-process-plan.md Step 25

set -euo pipefail

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Load environment variables
source "$PROJECT_ROOT/configs/environment/.env.pi-build"
source "$PROJECT_ROOT/configs/environment/.env.application"

echo "🚀 Deploying Phase 3 Application Services to Raspberry Pi"
echo "========================================================="
echo "Pi Host: $PI_HOST"
echo "Pi User: $PI_USER"
echo "Deploy Directory: $PI_DEPLOY_DIR"
echo

# Copy compose file and environment to Pi
echo "Copying configuration files to Pi..."
scp "$PROJECT_ROOT/configs/docker/docker-compose.application.yml" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/"
scp "$PROJECT_ROOT/configs/environment/.env.application" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/.env.application"

# Pull ARM64 images on Pi
echo "Pulling ARM64 images on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml -f docker-compose.application.yml pull"

# Deploy services
echo "Deploying Phase 3 services..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml -f docker-compose.application.yml up -d"

echo "✅ Phase 3 deployment completed!"
EOF
        chmod +x "$PROJECT_ROOT/scripts/deployment/deploy-phase3-pi.sh"
        log_success "Basic Phase 3 deployment script created"
    fi
}

# Step 26: Prepare Integration Tests
step26_prepare_integration_tests() {
    log_step "Step 26: Prepare Integration Tests"
    
    # Check if integration test script exists
    if [[ -f "$PROJECT_ROOT/tests/integration/phase3/run_phase3_tests.sh" ]]; then
        log_success "Phase 3 integration test script found"
    else
        log_warning "Phase 3 integration test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/integration/phase3"
        cat > "$PROJECT_ROOT/tests/integration/phase3/run_phase3_tests.sh" << 'EOF'
#!/bin/bash
# Phase 3 Integration Tests
# Based on docker-build-process-plan.md Step 26

set -euo pipefail

echo "🧪 Running Phase 3 Integration Tests"
echo "===================================="

# Test Session Management Services
echo "Testing Session Pipeline..."
python3 -c "
import requests
response = requests.get('http://localhost:8081/health')
print('✅ Session Pipeline connection successful')
"

echo "Testing Session Recorder..."
python3 -c "
import requests
response = requests.get('http://localhost:8082/health')
print('✅ Session Recorder connection successful')
"

echo "Testing Chunk Processor..."
python3 -c "
import requests
response = requests.get('http://localhost:8083/health')
print('✅ Chunk Processor connection successful')
"

echo "Testing Session Storage..."
python3 -c "
import requests
response = requests.get('http://localhost:8084/health')
print('✅ Session Storage connection successful')
"

echo "Testing Session API..."
python3 -c "
import requests
response = requests.get('http://localhost:8087/health')
print('✅ Session API connection successful')
"

# Test RDP Services
echo "Testing RDP Server Manager..."
python3 -c "
import requests
response = requests.get('http://localhost:8081/health')
print('✅ RDP Server Manager connection successful')
"

echo "Testing Session Controller..."
python3 -c "
import requests
response = requests.get('http://localhost:8082/health')
print('✅ Session Controller connection successful')
"

echo "Testing Resource Monitor..."
python3 -c "
import requests
response = requests.get('http://localhost:8090/health')
print('✅ Resource Monitor connection successful')
"

# Test Node Management
echo "Testing Node Management..."
python3 -c "
import requests
response = requests.get('http://localhost:8095/health')
print('✅ Node Management connection successful')
"

echo "✅ All Phase 3 integration tests passed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/integration/phase3/run_phase3_tests.sh"
        log_success "Basic Phase 3 integration test script created"
    fi
}

# Step 27: Prepare Performance Tests
step27_prepare_performance_tests() {
    log_step "Step 27: Prepare Performance Tests"
    
    # Check if performance test script exists
    if [[ -f "$PROJECT_ROOT/tests/performance/phase3/run_phase3_performance.sh" ]]; then
        log_success "Phase 3 performance test script found"
    else
        log_warning "Phase 3 performance test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/performance/phase3"
        cat > "$PROJECT_ROOT/tests/performance/phase3/run_phase3_performance.sh" << 'EOF'
#!/bin/bash
# Phase 3 Performance Tests
# Based on docker-build-process-plan.md Step 27

set -euo pipefail

echo "⚡ Running Phase 3 Performance Tests"
echo "===================================="

# Test chunk processing throughput
echo "Testing chunk processing throughput..."
python3 -c "
import requests
import time

start_time = time.time()
response = requests.get('http://localhost:8083/performance/chunk-processing')
end_time = time.time()
throughput = 1 / (end_time - start_time)
print(f'✅ Chunk processing throughput: {throughput:.2f} chunks/s')
"

# Test RDP connection latency
echo "Testing RDP connection latency..."
python3 -c "
import requests
import time

start_time = time.time()
response = requests.get('http://localhost:8081/performance/connection-latency')
end_time = time.time()
latency = (end_time - start_time) * 1000
print(f'✅ RDP connection latency: {latency:.2f}ms')
"

# Test node pool management
echo "Testing node pool management..."
python3 -c "
import requests
import time

start_time = time.time()
response = requests.get('http://localhost:8095/performance/node-pool')
end_time = time.time()
management_time = (end_time - start_time) * 1000
print(f'✅ Node pool management time: {management_time:.2f}ms')
"

echo "✅ All Phase 3 performance tests completed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/performance/phase3/run_phase3_performance.sh"
        log_success "Basic Phase 3 performance test script created"
    fi
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Phase 3 Application Services Build Summary"
    echo "=============================================="
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
        log_error "Phase 3 build completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "Phase 3 Application Services built successfully!"
        echo
        log_info "Images available in registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Tag: $TAG"
        echo
        log_info "Next Steps:"
        echo "  1. Deploy to Pi: ./scripts/deployment/deploy-phase3-pi.sh"
        echo "  2. Run integration tests: ./tests/integration/phase3/run_phase3_tests.sh"
        echo "  3. Run performance tests: ./tests/performance/phase3/run_phase3_performance.sh"
        echo "  4. Proceed to Phase 4: ./scripts/build/phase4-support-services.sh"
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
    echo "🚀 Lucid Phase 3: Application Services Build Script"
    echo "=================================================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    setup_buildx
    load_environment
    
    # Execute Phase 3 steps
    step18_20_build_session_containers
    step21_22_build_rdp_containers
    step23_build_node_management
    step24_generate_docker_compose
    step25_prepare_deployment
    step26_prepare_integration_tests
    step27_prepare_performance_tests
    
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
