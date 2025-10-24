#!/bin/bash
# Build Infrastructure Base Distroless Images Script
# Bash script for Linux/macOS development environment
# Builds infrastructure base distroless images for Lucid project

set -euo pipefail

# Configuration
PLATFORM="${PLATFORM:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-false}"
NO_CACHE="${NO_CACHE:-false}"
REGISTRY="${REGISTRY:-lucid}"
TAG="${TAG:-latest}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR"

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

log_test() {
    echo -e "${CYAN}🧪 $1${NC}"
}

build_infrastructure_image() {
    local dockerfile="$1"
    local image_name="$2"
    local context="${3:-.}"
    local build_args="${4:-}"
    
    log_info "Building infrastructure image: $image_name..."
    
    local build_args_array=(
        "buildx" "build"
        "--platform" "$PLATFORM"
        "--file" "$dockerfile"
        "--tag" "$REGISTRY/$image_name:$TAG"
        "--build-arg" "BUILD_ENVIRONMENT=$ENVIRONMENT"
    )
    
    # Add custom build args
    if [[ -n "$build_args" ]]; then
        IFS=' ' read -ra ARGS <<< "$build_args"
        for arg in "${ARGS[@]}"; do
            build_args_array+=("--build-arg" "$arg")
        done
    fi
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args_array+=("--no-cache")
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        build_args_array+=("--push")
    else
        build_args_array+=("--load")
    fi
    
    build_args_array+=("$context")
    
    if docker "${build_args_array[@]}"; then
        log_success "Successfully built $image_name"
    else
        log_error "Failed to build $image_name"
        exit 1
    fi
}

test_infrastructure_image() {
    local image_name="$1"
    
    log_test "Testing infrastructure image: $image_name..."
    
    local container_id
    if container_id=$(docker run -d --rm "$REGISTRY/$image_name:$TAG" 2>/dev/null); then
        sleep 5
        
        local health_status
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "unknown")
        docker stop "$container_id" >/dev/null 2>&1
        
        if [[ "$health_status" == "healthy" ]]; then
            log_success "Health check passed for $image_name"
        else
            log_warning "Health check status: $health_status for $image_name"
        fi
    else
        log_error "Failed to test $image_name"
    fi
}

check_docker() {
    if ! docker version >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    log_success "Docker is running"
}

setup_buildx() {
    log_info "Setting up Docker buildx..."
    docker buildx create --name lucid-infrastructure-builder --use 2>/dev/null || true
    docker buildx inspect --bootstrap
}

cleanup_buildx() {
    log_info "Cleaning up buildx builder..."
    docker buildx rm lucid-infrastructure-builder 2>/dev/null || true
}

main() {
    log_info "🚀 Starting Lucid Infrastructure Base Distroless Build Process"
    log_info "Platform: $PLATFORM"
    log_info "Registry: $REGISTRY"
    log_info "Tag: $TAG"
    log_info "Environment: $ENVIRONMENT"
    log_info "Push: $PUSH"
    log_info "No Cache: $NO_CACHE"
    echo
    
    # Check Docker
    check_docker
    
    # Setup buildx
    setup_buildx
    
    # Change to build directory
    cd "$BUILD_DIR"
    
    # Build infrastructure images
    build_infrastructure_image "Dockerfile.base" "infrastructure-base"
    build_infrastructure_image "Dockerfile.minimal-base" "infrastructure-minimal-base"
    build_infrastructure_image "Dockerfile.arm64-base" "infrastructure-arm64-base"
    
    echo
    log_test "Testing infrastructure images..."
    
    # Test images if not pushing
    if [[ "$PUSH" != "true" ]]; then
        test_infrastructure_image "infrastructure-base"
        test_infrastructure_image "infrastructure-minimal-base"
        test_infrastructure_image "infrastructure-arm64-base"
    fi
    
    echo
    log_success "🎉 All infrastructure base distroless images built successfully!"
    
    if [[ "$PUSH" == "true" ]]; then
        log_success "📤 Images pushed to registry: $REGISTRY"
    else
        log_success "📦 Images available locally"
        log_warning "To push images, set PUSH=true environment variable"
    fi
    
    # Cleanup
    cleanup_buildx
    
    log_success "✨ Infrastructure build process completed!"
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        --no-cache)
            NO_CACHE="true"
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --platform PLATFORM    Target platforms (default: linux/amd64,linux/arm64)"
            echo "  --push                  Push images to registry"
            echo "  --no-cache             Build without cache"
            echo "  --registry REGISTRY    Registry name (default: lucid)"
            echo "  --tag TAG              Image tag (default: latest)"
            echo "  --environment ENV      Build environment (default: production)"
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
