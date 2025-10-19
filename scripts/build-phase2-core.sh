#!/bin/bash
# Phase 2 Core Services Build Script
# Builds: API Gateway, Service Mesh Controller, Blockchain Core containers
# Target: Raspberry Pi (linux/arm64)
# Registry: pickme/lucid namespace

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="pickme/lucid"
PLATFORM="linux/arm64"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation functions
validate_environment() {
    log_info "Validating build environment..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker BuildKit
    if ! docker buildx version &> /dev/null; then
        log_error "Docker BuildKit is not available"
        exit 1
    fi
    
    # Check platform support
    if ! docker buildx inspect --bootstrap | grep -q "$PLATFORM"; then
        log_warning "Platform $PLATFORM not found in buildx, creating builder..."
        docker buildx create --name lucid-pi-core --use --driver docker-container --platform "$PLATFORM" || true
        docker buildx use lucid-pi-core
    fi
    
    log_success "Environment validation complete"
}

# Docker Hub authentication
authenticate_dockerhub() {
    log_info "Authenticating to Docker Hub..."
    
    if ! docker info | grep -q "Username: pickme"; then
        log_warning "Not authenticated to Docker Hub as 'pickme'"
        log_info "Please run: docker login"
        read -p "Press Enter after logging in..."
    fi
    
    log_success "Docker Hub authentication verified"
}

# TRON Isolation Verification
verify_tron_isolation() {
    log_info "Verifying TRON isolation in blockchain core..."
    
    local blockchain_dir="$PROJECT_ROOT/blockchain"
    
    if [[ -d "$blockchain_dir" ]]; then
        # Scan for TRON references
        local tron_refs=$(grep -r "tron" "$blockchain_dir" --exclude-dir=node_modules 2>/dev/null || true)
        local tronweb_refs=$(grep -r "TronWeb" "$blockchain_dir" 2>/dev/null || true)
        local payment_refs=$(grep -r "payment" "$blockchain_dir/core" 2>/dev/null || true)
        
        if [[ -n "$tron_refs" ]]; then
            log_error "TRON references found in blockchain core:"
            echo "$tron_refs"
            exit 1
        fi
        
        if [[ -n "$tronweb_refs" ]]; then
            log_error "TronWeb references found in blockchain core:"
            echo "$tronweb_refs"
            exit 1
        fi
        
        if [[ -n "$payment_refs" ]]; then
            log_error "Payment references found in blockchain core:"
            echo "$payment_refs"
            exit 1
        fi
        
        log_success "TRON isolation verification passed"
    else
        log_warning "Blockchain directory not found: $blockchain_dir"
    fi
}

# Build API Gateway
build_api_gateway() {
    log_info "Building API Gateway..."
    
    local api_gateway_dir="$PROJECT_ROOT/03-api-gateway"
    
    if [[ ! -d "$api_gateway_dir" ]]; then
        log_error "API Gateway directory not found: $api_gateway_dir"
        exit 1
    fi
    
    cd "$api_gateway_dir"
    
    # Build API Gateway with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-api-gateway:latest-arm64" \
        -t "$REGISTRY/lucid-api-gateway:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "API Gateway built successfully"
}

# Build Service Mesh Controller
build_service_mesh_controller() {
    log_info "Building Service Mesh Controller..."
    
    local service_mesh_dir="$PROJECT_ROOT/service-mesh"
    
    if [[ ! -d "$service_mesh_dir" ]]; then
        log_error "Service Mesh directory not found: $service_mesh_dir"
        exit 1
    fi
    
    cd "$service_mesh_dir"
    
    # Build Service Mesh Controller with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-service-mesh-controller:latest-arm64" \
        -t "$REGISTRY/lucid-service-mesh-controller:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "Service Mesh Controller built successfully"
}

# Build Blockchain Engine
build_blockchain_engine() {
    log_info "Building Blockchain Engine..."
    
    local blockchain_dir="$PROJECT_ROOT/blockchain"
    
    if [[ ! -d "$blockchain_dir" ]]; then
        log_error "Blockchain directory not found: $blockchain_dir"
        exit 1
    fi
    
    cd "$blockchain_dir"
    
    # Build Blockchain Engine with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-blockchain-engine:latest-arm64" \
        -t "$REGISTRY/lucid-blockchain-engine:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.engine \
        --push \
        .
    
    log_success "Blockchain Engine built successfully"
}

# Build Session Anchoring
build_session_anchoring() {
    log_info "Building Session Anchoring..."
    
    local blockchain_dir="$PROJECT_ROOT/blockchain"
    
    cd "$blockchain_dir"
    
    # Build Session Anchoring with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-anchoring:latest-arm64" \
        -t "$REGISTRY/lucid-session-anchoring:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.session-anchoring \
        --push \
        .
    
    log_success "Session Anchoring built successfully"
}

# Build Block Manager
build_block_manager() {
    log_info "Building Block Manager..."
    
    local blockchain_dir="$PROJECT_ROOT/blockchain"
    
    cd "$blockchain_dir"
    
    # Build Block Manager with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-block-manager:latest-arm64" \
        -t "$REGISTRY/lucid-block-manager:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.block-manager \
        --push \
        .
    
    log_success "Block Manager built successfully"
}

# Build Data Chain
build_data_chain() {
    log_info "Building Data Chain..."
    
    local blockchain_dir="$PROJECT_ROOT/blockchain"
    
    cd "$blockchain_dir"
    
    # Build Data Chain with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-data-chain:latest-arm64" \
        -t "$REGISTRY/lucid-data-chain:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.data-chain \
        --push \
        .
    
    log_success "Data Chain built successfully"
}

# Verify built images
verify_images() {
    log_info "Verifying built images..."
    
    local images=(
        "$REGISTRY/lucid-api-gateway:latest-arm64"
        "$REGISTRY/lucid-service-mesh-controller:latest-arm64"
        "$REGISTRY/lucid-blockchain-engine:latest-arm64"
        "$REGISTRY/lucid-session-anchoring:latest-arm64"
        "$REGISTRY/lucid-block-manager:latest-arm64"
        "$REGISTRY/lucid-data-chain:latest-arm64"
    )
    
    for image in "${images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Image verified: $image"
        else
            log_error "Image verification failed: $image"
            exit 1
        fi
    done
    
    log_success "All images verified successfully"
}

# Main execution
main() {
    log_info "Starting Phase 2 Core Services Build"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Validate environment
    validate_environment
    
    # Authenticate to Docker Hub
    authenticate_dockerhub
    
    # Verify TRON isolation
    verify_tron_isolation
    
    # Build Phase 2 services
    build_api_gateway
    build_service_mesh_controller
    build_blockchain_engine
    build_session_anchoring
    build_block_manager
    build_data_chain
    
    # Verify all images
    verify_images
    
    log_success "Phase 2 Core Services build completed successfully!"
    log_info "Built images:"
    log_info "  - $REGISTRY/lucid-api-gateway:latest-arm64"
    log_info "  - $REGISTRY/lucid-service-mesh-controller:latest-arm64"
    log_info "  - $REGISTRY/lucid-blockchain-engine:latest-arm64"
    log_info "  - $REGISTRY/lucid-session-anchoring:latest-arm64"
    log_info "  - $REGISTRY/lucid-block-manager:latest-arm64"
    log_info "  - $REGISTRY/lucid-data-chain:latest-arm64"
}

# Run main function
main "$@"
