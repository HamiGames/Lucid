#!/bin/bash
# Build Base Distroless Images Script
# Bash script for Linux/macOS development environment
# Builds base distroless images for Lucid project

set -euo pipefail

# Configuration
PLATFORM="${PLATFORM:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-false}"
NO_CACHE="${NO_CACHE:-false}"
REGISTRY="${REGISTRY:-lucid}"
TAG="${TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

build_image() {
    local dockerfile="$1"
    local image_name="$2"
    local context="${3:-.}"
    
    log_info "Building $image_name..."
    
    local build_args=(
        "buildx" "build"
        "--platform" "$PLATFORM"
        "--file" "$dockerfile"
        "--tag" "$REGISTRY/$image_name:$TAG"
    )
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=("--no-cache")
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        build_args+=("--push")
    else
        build_args+=("--load")
    fi
    
    build_args+=("$context")
    
    if docker "${build_args[@]}"; then
        log_success "Successfully built $image_name"
    else
        log_error "Failed to build $image_name"
        exit 1
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
    docker buildx create --name lucid-builder --use 2>/dev/null || true
    docker buildx inspect --bootstrap
}

cleanup_buildx() {
    log_info "Cleaning up buildx builder..."
    docker buildx rm lucid-builder 2>/dev/null || true
}

main() {
    log_info "🚀 Starting Lucid Base Distroless Build Process"
    log_info "Platform: $PLATFORM"
    log_info "Registry: $REGISTRY"
    log_info "Tag: $TAG"
    log_info "Push: $PUSH"
    log_info "No Cache: $NO_CACHE"
    echo
    
    # Check Docker
    check_docker
    
    # Setup buildx
    setup_buildx
    
    # Change to build directory
    cd "$BUILD_DIR"
    
    # Build images
    build_image "Dockerfile.base.distroless" "lucid-base"
    build_image "Dockerfile.python-base.distroless" "lucid-python-base"
    build_image "Dockerfile.alpine-base.distroless" "lucid-alpine-base"
    
    echo
    log_success "🎉 All base distroless images built successfully!"
    
    if [[ "$PUSH" == "true" ]]; then
        log_success "📤 Images pushed to registry: $REGISTRY"
    else
        log_success "📦 Images available locally"
        log_warning "To push images, set PUSH=true environment variable"
    fi
    
    # Cleanup
    cleanup_buildx
    
    log_success "✨ Build process completed!"
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
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --platform PLATFORM    Target platforms (default: linux/amd64,linux/arm64)"
            echo "  --push                  Push images to registry"
            echo "  --no-cache             Build without cache"
            echo "  --registry REGISTRY    Registry name (default: lucid)"
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
