
#!/bin/bash
# Lucid Node Management Container - Build Script
# Port: 8095
# Features: Node pool management, PoOT calculation, payout threshold (10 USDT), max 100 nodes

set -euo pipefail

# Configuration
IMAGE_NAME="pickme/lucid-node-management"
TAG="latest-arm64"
PLATFORM="linux/arm64"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION="1.0.0"

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

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Check if Docker Buildx is available
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available. Please install Docker Buildx."
        exit 1
    fi
    log_success "Docker Buildx is available"
}

# Create buildx builder if it doesn't exist
setup_buildx() {
    local builder_name="lucid-pi"
    
    if ! docker buildx ls | grep -q "$builder_name"; then
        log_info "Creating buildx builder: $builder_name"
        docker buildx create --name "$builder_name" --driver docker-container --platform linux/arm64,linux/amd64
    fi
    
    log_info "Using buildx builder: $builder_name"
    docker buildx use "$builder_name"
    docker buildx inspect --bootstrap
}

# Build the container
build_container() {
    log_info "Building Lucid Node Management container..."
    log_info "Image: $IMAGE_NAME:$TAG"
    log_info "Platform: $PLATFORM"
    log_info "Build Date: $BUILD_DATE"
    log_info "VCS Ref: $VCS_REF"
    log_info "Version: $VERSION"
    
    # Build arguments
    local build_args=(
        --platform "$PLATFORM"
        --tag "$IMAGE_NAME:$TAG"
        --build-arg "BUILD_DATE=$BUILD_DATE"
        --build-arg "VCS_REF=$VCS_REF"
        --build-arg "VERSION=$VERSION"
        --target "distroless"
        --push
        .
    )
    
    # Execute build
    if docker buildx build "${build_args[@]}"; then
        log_success "Container built successfully"
    else
        log_error "Container build failed"
        exit 1
    fi
}

# Verify the build
verify_build() {
    log_info "Verifying build..."
    
    # Check if image exists
    if docker buildx imagetools inspect "$IMAGE_NAME:$TAG" >/dev/null 2>&1; then
        log_success "Image exists and is accessible"
        
        # Display image information
        log_info "Image details:"
        docker buildx imagetools inspect "$IMAGE_NAME:$TAG" --format "{{json .}}" | jq -r '
            "  Name: " + .name + "\n" +
            "  Architecture: " + .architecture + "\n" +
            "  OS: " + .os + "\n" +
            "  Created: " + .created + "\n" +
            "  Size: " + (.size | tostring) + " bytes"
        ' 2>/dev/null || log_warning "Could not retrieve detailed image information"
    else
        log_error "Image verification failed"
        exit 1
    fi
}

# Test the container locally (optional)
test_container() {
    if [[ "${TEST_CONTAINER:-false}" == "true" ]]; then
        log_info "Testing container locally..."
        
        # Pull the image
        docker pull "$IMAGE_NAME:$TAG"
        
        # Run container in background
        local container_id
        container_id=$(docker run -d \
            --name "node-management-test" \
            --rm \
            -p 8095:8095 \
            -e NODE_MANAGEMENT_PORT=8095 \
            -e MAX_NODES_PER_POOL=100 \
            -e PAYOUT_THRESHOLD_USDT=10.0 \
            "$IMAGE_NAME:$TAG")
        
        # Wait for container to start
        sleep 10
        
        # Test health endpoint
        if curl -f http://localhost:8095/health >/dev/null 2>&1; then
            log_success "Container health check passed"
        else
            log_warning "Container health check failed"
        fi
        
        # Stop container
        docker stop "$container_id"
        log_info "Container test completed"
    fi
}

# Main execution
main() {
    log_info "Starting Lucid Node Management container build"
    log_info "=============================================="
    
    # Pre-build checks
    check_docker
    check_buildx
    setup_buildx
    
    # Build container
    build_container
    
    # Verify build
    verify_build
    
    # Test container (optional)
    test_container
    
    log_success "Lucid Node Management container build completed successfully"
    log_info "Image: $IMAGE_NAME:$TAG"
    log_info "Platform: $PLATFORM"
    log_info "Ready for deployment to Raspberry Pi"
}

# Handle script arguments
case "${1:-build}" in
    "build")
        main
        ;;
    "test")
        TEST_CONTAINER=true
        main
        ;;
    "clean")
        log_info "Cleaning up build artifacts..."
        docker buildx prune -f
        log_success "Cleanup completed"
        ;;
    "help")
        echo "Usage: $0 [build|test|clean|help]"
        echo "  build - Build the container (default)"
        echo "  test  - Build and test the container locally"
        echo "  clean - Clean up build artifacts"
        echo "  help  - Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
