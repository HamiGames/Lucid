#!/bin/bash
# Lucid Full Build Script - Complete Docker Build Process
# Based on docker-build-process-plan.md
# Builds all distroless images for Raspberry Pi deployment

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

# Build phases configuration
PHASE1_SERVICES=("auth-service" "mongodb" "redis" "elasticsearch")
PHASE2_SERVICES=("api-gateway" "blockchain-engine" "session-anchoring" "block-manager" "data-chain" "service-mesh-controller")
PHASE3_SERVICES=("session-pipeline" "session-recorder" "session-processor" "session-storage" "session-api" "rdp-server-manager" "rdp-xrdp" "rdp-controller" "rdp-monitor" "node-management")
PHASE4_SERVICES=("admin-interface" "tron-client" "tron-payout-router" "tron-wallet-manager" "tron-usdt-manager" "tron-staking" "tron-payment-gateway")

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
    
    # Check Docker
    if ! docker version >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    log_success "Docker is running"
    
    # Check Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    log_success "Docker Buildx is available"
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/README.md" ]]; then
        log_error "Not in Lucid project root directory"
        exit 1
    fi
    log_success "In correct project directory"
}

# Create Docker networks
create_networks() {
    log_info "Creating Docker networks..."
    
    # Main Lucid network
    if ! docker network ls | grep -q "lucid-pi-network"; then
        docker network create --driver bridge --attachable --subnet=172.20.0.0/16 --gateway=172.20.0.1 lucid-pi-network
        log_success "Created lucid-pi-network"
    else
        log_info "lucid-pi-network already exists"
    fi
    
    # TRON isolated network
    if ! docker network ls | grep -q "lucid-tron-isolated"; then
        docker network create --driver bridge --attachable --subnet=172.21.0.0/16 --gateway=172.21.0.1 lucid-tron-isolated
        log_success "Created lucid-tron-isolated network"
    else
        log_info "lucid-tron-isolated network already exists"
    fi
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
    
    # Build the image
    local build_cmd=(
        "buildx" "build"
        "--platform" "$PLATFORM"
        "--file" "$dockerfile_path"
        "--tag" "$full_image"
        "--push"
        "$context_path"
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

# Build base images
build_base_images() {
    log_phase "Phase 0: Building Base Images"
    
    # Python base
    build_image "lucid-base-python" "$PROJECT_ROOT/build/distroless/base/Dockerfile.python-base" "$PROJECT_ROOT/build/distroless/base"
    
    # Base distroless
    build_image "lucid-base" "$PROJECT_ROOT/build/distroless/base/Dockerfile.base" "$PROJECT_ROOT/build/distroless/base"
}

# Build Phase 1: Foundation Services
build_phase1() {
    log_phase "Phase 1: Foundation Services"
    
    # Auth Service
    if [[ -f "$PROJECT_ROOT/auth/Dockerfile" ]]; then
        build_image "auth-service" "$PROJECT_ROOT/auth/Dockerfile" "$PROJECT_ROOT/auth"
    else
        log_warning "Auth service Dockerfile not found, skipping"
    fi
    
    # Storage services
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.mongodb" ]]; then
        build_image "mongodb" "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.mongodb" "$PROJECT_ROOT/infrastructure/containers/storage"
    fi
    
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.redis" ]]; then
        build_image "redis" "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.redis" "$PROJECT_ROOT/infrastructure/containers/storage"
    fi
    
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.elasticsearch" ]]; then
        build_image "elasticsearch" "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.elasticsearch" "$PROJECT_ROOT/infrastructure/containers/storage"
    fi
}

# Build Phase 2: Core Services
build_phase2() {
    log_phase "Phase 2: Core Services"
    
    # API Gateway
    if [[ -f "$PROJECT_ROOT/03-api-gateway/Dockerfile" ]]; then
        build_image "api-gateway" "$PROJECT_ROOT/03-api-gateway/Dockerfile" "$PROJECT_ROOT/03-api-gateway"
    fi
    
    # Blockchain services
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.engine" ]]; then
        build_image "blockchain-engine" "$PROJECT_ROOT/blockchain/Dockerfile.engine" "$PROJECT_ROOT/blockchain"
    fi
    
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.anchoring" ]]; then
        build_image "session-anchoring" "$PROJECT_ROOT/blockchain/Dockerfile.anchoring" "$PROJECT_ROOT/blockchain"
    fi
    
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.manager" ]]; then
        build_image "block-manager" "$PROJECT_ROOT/blockchain/Dockerfile.manager" "$PROJECT_ROOT/blockchain"
    fi
    
    if [[ -f "$PROJECT_ROOT/blockchain/Dockerfile.data" ]]; then
        build_image "data-chain" "$PROJECT_ROOT/blockchain/Dockerfile.data" "$PROJECT_ROOT/blockchain"
    fi
    
    # Service Mesh
    if [[ -f "$PROJECT_ROOT/infrastructure/service-mesh/Dockerfile.controller" ]]; then
        build_image "service-mesh-controller" "$PROJECT_ROOT/infrastructure/service-mesh/Dockerfile.controller" "$PROJECT_ROOT/infrastructure/service-mesh"
    fi
}

# Build Phase 3: Application Services
build_phase3() {
    log_phase "Phase 3: Application Services"
    
    # Session services
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.pipeline" ]]; then
        build_image "session-pipeline" "$PROJECT_ROOT/sessions/Dockerfile.pipeline" "$PROJECT_ROOT/sessions"
    fi
    
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.recorder" ]]; then
        build_image "session-recorder" "$PROJECT_ROOT/sessions/Dockerfile.recorder" "$PROJECT_ROOT/sessions"
    fi
    
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.processor" ]]; then
        build_image "session-processor" "$PROJECT_ROOT/sessions/Dockerfile.processor" "$PROJECT_ROOT/sessions"
    fi
    
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.storage" ]]; then
        build_image "session-storage" "$PROJECT_ROOT/sessions/Dockerfile.storage" "$PROJECT_ROOT/sessions"
    fi
    
    if [[ -f "$PROJECT_ROOT/sessions/Dockerfile.api" ]]; then
        build_image "session-api" "$PROJECT_ROOT/sessions/Dockerfile.api" "$PROJECT_ROOT/sessions"
    fi
    
    # RDP services
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.server-manager" ]]; then
        build_image "rdp-server-manager" "$PROJECT_ROOT/RDP/Dockerfile.server-manager" "$PROJECT_ROOT/RDP"
    fi
    
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.xrdp" ]]; then
        build_image "rdp-xrdp" "$PROJECT_ROOT/RDP/Dockerfile.xrdp" "$PROJECT_ROOT/RDP"
    fi
    
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.controller" ]]; then
        build_image "rdp-controller" "$PROJECT_ROOT/RDP/Dockerfile.controller" "$PROJECT_ROOT/RDP"
    fi
    
    if [[ -f "$PROJECT_ROOT/RDP/Dockerfile.monitor" ]]; then
        build_image "rdp-monitor" "$PROJECT_ROOT/RDP/Dockerfile.monitor" "$PROJECT_ROOT/RDP"
    fi
    
    # Node management
    if [[ -f "$PROJECT_ROOT/node/Dockerfile" ]]; then
        build_image "node-management" "$PROJECT_ROOT/node/Dockerfile" "$PROJECT_ROOT/node"
    fi
}

# Build Phase 4: Support Services
build_phase4() {
    log_phase "Phase 4: Support Services"
    
    # Admin interface
    if [[ -f "$PROJECT_ROOT/admin/Dockerfile" ]]; then
        build_image "admin-interface" "$PROJECT_ROOT/admin/Dockerfile" "$PROJECT_ROOT/admin"
    fi
    
    # TRON payment services
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.tron-client" ]]; then
        build_image "tron-client" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.tron-client" "$PROJECT_ROOT/payment-systems/tron"
    fi
    
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payout-router" ]]; then
        build_image "tron-payout-router" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payout-router" "$PROJECT_ROOT/payment-systems/tron"
    fi
    
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.wallet-manager" ]]; then
        build_image "tron-wallet-manager" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.wallet-manager" "$PROJECT_ROOT/payment-systems/tron"
    fi
    
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.usdt-manager" ]]; then
        build_image "tron-usdt-manager" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.usdt-manager" "$PROJECT_ROOT/payment-systems/tron"
    fi
    
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.trx-staking" ]]; then
        build_image "tron-staking" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.trx-staking" "$PROJECT_ROOT/payment-systems/tron"
    fi
    
    if [[ -f "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payment-gateway" ]]; then
        build_image "tron-payment-gateway" "$PROJECT_ROOT/payment-systems/tron/Dockerfile.payment-gateway" "$PROJECT_ROOT/payment-systems/tron"
    fi
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Build Summary"
    echo "=================================="
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
        log_error "Build completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "All services built successfully!"
        echo
        log_info "Images available in registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Tag: $TAG"
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
    echo "🚀 Lucid Full Build Script"
    echo "=========================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Tag: $TAG"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    create_networks
    setup_buildx
    
    # Build phases
    build_base_images
    build_phase1
    build_phase2
    build_phase3
    build_phase4
    
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
