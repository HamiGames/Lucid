#!/bin/bash
# LUCID RDP Services Container Build Script
# Step 21-22: RDP Services Containers Build Process
# Build Environment: Windows 11 console with Docker Desktop + BuildKit
# Target Host: Raspberry Pi 5 (192.168.0.75) via SSH
# Platform: linux/arm64 (aarch64)
# Registry: Docker Hub (pickme/lucid namespace)

set -euo pipefail

# Configuration
REGISTRY="pickme"
NAMESPACE="lucid"
PLATFORM="linux/arm64"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION="latest"

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

# Build function
build_container() {
    local service_name=$1
    local dockerfile_path=$2
    local context_path=$3
    local port=$4
    
    log_info "Building ${service_name} container..."
    
    # Build and push the container
    docker buildx build \
        --platform ${PLATFORM} \
        --tag ${REGISTRY}/${NAMESPACE}-${service_name}:${VERSION}-arm64 \
        --tag ${REGISTRY}/${NAMESPACE}-${service_name}:latest \
        --file ${dockerfile_path} \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg VERSION="${VERSION}" \
        --build-arg PLATFORM="${PLATFORM}" \
        --build-arg PORT="${port}" \
        --push \
        ${context_path}
    
    if [ $? -eq 0 ]; then
        log_success "${service_name} container built and pushed successfully"
    else
        log_error "Failed to build ${service_name} container"
        exit 1
    fi
}

# Verify Docker Hub authentication
verify_docker_auth() {
    log_info "Verifying Docker Hub authentication..."
    
    # Test authentication by attempting to access Docker Hub registry
    if ! docker manifest inspect hello-world:latest > /dev/null 2>&1; then
        log_error "Docker Hub authentication required. Please run: docker login"
        exit 1
    fi
    
    log_success "Docker Hub authentication verified"
}

# Verify build environment
verify_build_env() {
    log_info "Verifying build environment..."
    
    # Check Docker BuildKit
    if ! docker buildx version > /dev/null 2>&1; then
        log_error "Docker BuildKit not available"
        exit 1
    fi
    
    # Check platform support
    if ! docker buildx inspect | grep -q "linux/arm64"; then
        log_error "ARM64 platform not supported by buildx"
        exit 1
    fi
    
    log_success "Build environment verified"
}

# Main build process
main() {
    log_info "Starting RDP Services Container Build Process"
    log_info "Target Platform: ${PLATFORM}"
    log_info "Registry: ${REGISTRY}/${NAMESPACE}"
    log_info "Build Date: ${BUILD_DATE}"
    
    # Verify environment
    verify_docker_auth
    verify_build_env
    
    # Build RDP Server Manager (Port 8081)
    build_container \
        "rdp-server-manager" \
        "Dockerfile.server-manager" \
        "." \
        "8081"
    
    # Build XRDP Integration (Port 3389)
    build_container \
        "xrdp-integration" \
        "Dockerfile.xrdp" \
        "." \
        "3389"
    
    # Build Session Controller (Port 8082)
    build_container \
        "session-controller" \
        "Dockerfile.controller" \
        "." \
        "8082"
    
    # Build Resource Monitor (Port 8090)
    build_container \
        "resource-monitor" \
        "Dockerfile.monitor" \
        "." \
        "8090"
    
    log_success "All RDP Services containers built and pushed successfully!"
    
    # Display built images
    log_info "Built Images:"
    echo "  - ${REGISTRY}/${NAMESPACE}-rdp-server-manager:${VERSION}-arm64"
    echo "  - ${REGISTRY}/${NAMESPACE}-xrdp-integration:${VERSION}-arm64"
    echo "  - ${REGISTRY}/${NAMESPACE}-session-controller:${VERSION}-arm64"
    echo "  - ${REGISTRY}/${NAMESPACE}-resource-monitor:${VERSION}-arm64"
    
    log_info "Build process completed successfully!"
}

# Run main function
main "$@"
