#!/bin/bash
# Phase 3 Application Services Build Script
# Builds: Session Management, RDP Services, Node Management containers
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
        docker buildx create --name lucid-pi-app --use --driver docker-container --platform "$PLATFORM" || true
        docker buildx use lucid-pi-app
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

# Build Session Pipeline
build_session_pipeline() {
    log_info "Building Session Pipeline..."
    
    local session_dir="$PROJECT_ROOT/sessions"
    
    if [[ ! -d "$session_dir" ]]; then
        log_error "Session directory not found: $session_dir"
        exit 1
    fi
    
    cd "$session_dir"
    
    # Build Session Pipeline with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-pipeline:latest-arm64" \
        -t "$REGISTRY/lucid-session-pipeline:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.pipeline \
        --push \
        .
    
    log_success "Session Pipeline built successfully"
}

# Build Session Recorder
build_session_recorder() {
    log_info "Building Session Recorder..."
    
    local session_dir="$PROJECT_ROOT/sessions"
    
    cd "$session_dir"
    
    # Build Session Recorder with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-recorder:latest-arm64" \
        -t "$REGISTRY/lucid-session-recorder:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.recorder \
        --push \
        .
    
    log_success "Session Recorder built successfully"
}

# Build Chunk Processor
build_chunk_processor() {
    log_info "Building Chunk Processor..."
    
    local session_dir="$PROJECT_ROOT/sessions"
    
    cd "$session_dir"
    
    # Build Chunk Processor with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-chunk-processor:latest-arm64" \
        -t "$REGISTRY/lucid-chunk-processor:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.chunk-processor \
        --push \
        .
    
    log_success "Chunk Processor built successfully"
}

# Build Session Storage
build_session_storage() {
    log_info "Building Session Storage..."
    
    local session_dir="$PROJECT_ROOT/sessions"
    
    cd "$session_dir"
    
    # Build Session Storage with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-storage:latest-arm64" \
        -t "$REGISTRY/lucid-session-storage:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.storage \
        --push \
        .
    
    log_success "Session Storage built successfully"
}

# Build Session API
build_session_api() {
    log_info "Building Session API..."
    
    local session_dir="$PROJECT_ROOT/sessions"
    
    cd "$session_dir"
    
    # Build Session API with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-api:latest-arm64" \
        -t "$REGISTRY/lucid-session-api:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.api \
        --push \
        .
    
    log_success "Session API built successfully"
}

# Build RDP Server Manager
build_rdp_server_manager() {
    log_info "Building RDP Server Manager..."
    
    local rdp_dir="$PROJECT_ROOT/RDP"
    
    if [[ ! -d "$rdp_dir" ]]; then
        log_error "RDP directory not found: $rdp_dir"
        exit 1
    fi
    
    cd "$rdp_dir"
    
    # Build RDP Server Manager with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-rdp-server-manager:latest-arm64" \
        -t "$REGISTRY/lucid-rdp-server-manager:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.server-manager \
        --push \
        .
    
    log_success "RDP Server Manager built successfully"
}

# Build XRDP Integration
build_xrdp_integration() {
    log_info "Building XRDP Integration..."
    
    local rdp_dir="$PROJECT_ROOT/RDP"
    
    cd "$rdp_dir"
    
    # Build XRDP Integration with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-xrdp-integration:latest-arm64" \
        -t "$REGISTRY/lucid-xrdp-integration:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.xrdp-integration \
        --push \
        .
    
    log_success "XRDP Integration built successfully"
}

# Build Session Controller
build_session_controller() {
    log_info "Building Session Controller..."
    
    local rdp_dir="$PROJECT_ROOT/RDP"
    
    cd "$rdp_dir"
    
    # Build Session Controller with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-session-controller:latest-arm64" \
        -t "$REGISTRY/lucid-session-controller:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.session-controller \
        --push \
        .
    
    log_success "Session Controller built successfully"
}

# Build Resource Monitor
build_resource_monitor() {
    log_info "Building Resource Monitor..."
    
    local rdp_dir="$PROJECT_ROOT/RDP"
    
    cd "$rdp_dir"
    
    # Build Resource Monitor with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-resource-monitor:latest-arm64" \
        -t "$REGISTRY/lucid-resource-monitor:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.resource-monitor \
        --push \
        .
    
    log_success "Resource Monitor built successfully"
}

# Build Node Management
build_node_management() {
    log_info "Building Node Management..."
    
    local node_dir="$PROJECT_ROOT/node"
    
    if [[ ! -d "$node_dir" ]]; then
        log_error "Node directory not found: $node_dir"
        exit 1
    fi
    
    cd "$node_dir"
    
    # Build Node Management with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-node-management:latest-arm64" \
        -t "$REGISTRY/lucid-node-management:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "Node Management built successfully"
}

# Verify built images
verify_images() {
    log_info "Verifying built images..."
    
    local images=(
        "$REGISTRY/lucid-session-pipeline:latest-arm64"
        "$REGISTRY/lucid-session-recorder:latest-arm64"
        "$REGISTRY/lucid-chunk-processor:latest-arm64"
        "$REGISTRY/lucid-session-storage:latest-arm64"
        "$REGISTRY/lucid-session-api:latest-arm64"
        "$REGISTRY/lucid-rdp-server-manager:latest-arm64"
        "$REGISTRY/lucid-xrdp-integration:latest-arm64"
        "$REGISTRY/lucid-session-controller:latest-arm64"
        "$REGISTRY/lucid-resource-monitor:latest-arm64"
        "$REGISTRY/lucid-node-management:latest-arm64"
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
    log_info "Starting Phase 3 Application Services Build"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Validate environment
    validate_environment
    
    # Authenticate to Docker Hub
    authenticate_dockerhub
    
    # Build Session Management containers
    build_session_pipeline
    build_session_recorder
    build_chunk_processor
    build_session_storage
    build_session_api
    
    # Build RDP Services containers
    build_rdp_server_manager
    build_xrdp_integration
    build_session_controller
    build_resource_monitor
    
    # Build Node Management container
    build_node_management
    
    # Verify all images
    verify_images
    
    log_success "Phase 3 Application Services build completed successfully!"
    log_info "Built images:"
    log_info "  - $REGISTRY/lucid-session-pipeline:latest-arm64"
    log_info "  - $REGISTRY/lucid-session-recorder:latest-arm64"
    log_info "  - $REGISTRY/lucid-chunk-processor:latest-arm64"
    log_info "  - $REGISTRY/lucid-session-storage:latest-arm64"
    log_info "  - $REGISTRY/lucid-session-api:latest-arm64"
    log_info "  - $REGISTRY/lucid-rdp-server-manager:latest-arm64"
    log_info "  - $REGISTRY/lucid-xrdp-integration:latest-arm64"
    log_info "  - $REGISTRY/lucid-session-controller:latest-arm64"
    log_info "  - $REGISTRY/lucid-resource-monitor:latest-arm64"
    log_info "  - $REGISTRY/lucid-node-management:latest-arm64"
}

# Run main function
main "$@"
