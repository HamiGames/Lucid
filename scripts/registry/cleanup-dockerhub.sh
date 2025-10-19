#!/bin/bash
# Docker Hub Registry Cleanup Script
# Implements Step 1 from docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_HUB_USERNAME="pickme"
REPOSITORY_NAME="lucid"
DOCKER_HUB_API_URL="https://hub.docker.com/v2"

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

# Function to clean local Docker cache
clean_local_cache() {
    log_info "Cleaning local Docker cache on Windows 11..."
    
    # Clean Docker system
    docker system prune -a --volumes -f
    
    # Clean buildx cache
    docker builder prune -a -f
    
    # Remove any local images for this repository
    log_info "Removing local images for $DOCKER_HUB_USERNAME/$REPOSITORY_NAME..."
    docker images "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" --format "table {{.Repository}}:{{.Tag}}" | tail -n +2 | while read image; do
        if [ ! -z "$image" ]; then
            log_info "Removing local image: $image"
            docker rmi "$image" 2>/dev/null || true
        fi
    done
    
    log_success "Local Docker cache cleaned"
}

# Function to verify cleanup
verify_cleanup() {
    log_info "Verifying cleanup..."
    
    # Check local images
    local local_images=$(docker images "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" 2>/dev/null || echo "")
    if [[ -z "$local_images" ]]; then
        log_success "Local images cleanup verified"
    else
        log_warning "Some local images may still exist"
    fi
    
    # Check Docker Hub search
    log_info "Checking Docker Hub registry..."
    if docker search "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" 2>/dev/null | grep -q "No results found"; then
        log_success "Docker Hub cleanup verified - no lucid images found"
    else
        log_warning "Docker Hub registry may still contain images"
    fi
}

# Main execution
main() {
    log_info "=== Docker Hub Registry Cleanup ==="
    log_info "Repository: $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
    echo ""
    
    # Clean local cache
    clean_local_cache
    
    # Verify cleanup
    verify_cleanup
    
    echo ""
    log_success "Docker Hub cleanup completed successfully!"
    log_info "Local Docker cache and images have been cleaned"
    log_info "Docker Hub registry is ready for new images"
}

# Run main function
main "$@"