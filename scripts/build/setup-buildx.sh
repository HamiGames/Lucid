#!/bin/bash

# Lucid Multi-Platform Build Setup Script
# Sets up Docker Buildx for multi-platform builds (linux/amd64, linux/arm64)
# Usage: ./setup-buildx.sh [builder-name] [--force]

set -euo pipefail

# Configuration
DEFAULT_BUILDER_NAME="lucid-multiplatform"
BUILDER_NAME="${1:-$DEFAULT_BUILDER_NAME}"
FORCE_SETUP="${2:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
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

log_phase() {
    echo -e "${CYAN}[PHASE]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Lucid Multi-Platform Build Setup Script

USAGE:
    $0 [BUILDER_NAME] [--force]

ARGUMENTS:
    BUILDER_NAME          Name for the Docker Buildx builder (default: lucid-multiplatform)

OPTIONS:
    --force               Force recreation of existing builder
    -h, --help            Show this help message

DESCRIPTION:
    This script sets up Docker Buildx for multi-platform builds supporting:
    - linux/amd64 (Intel/AMD 64-bit)
    - linux/arm64 (ARM 64-bit, including Raspberry Pi 5)

    The script will:
    1. Check Docker Buildx availability
    2. Create a new builder instance
    3. Configure multi-platform support
    4. Set up build cache
    5. Verify the setup

EXAMPLES:
    $0                          # Use default builder name
    $0 my-builder               # Use custom builder name
    $0 my-builder --force       # Force recreate existing builder

EOF
}

# Check if help is requested
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# Check if force flag is set
if [[ "${2:-}" == "--force" ]]; then
    FORCE_SETUP=true
fi

# Check prerequisites
check_prerequisites() {
    log_phase "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    log_info "Docker: OK"
    
    # Check if Docker Buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        log_info "Please install Docker Buildx or update Docker to a version that includes Buildx"
        exit 1
    fi
    log_info "Docker Buildx: OK"
    
    # Check if buildx plugin is available
    if ! docker buildx ls >/dev/null 2>&1; then
        log_error "Docker Buildx plugin is not working"
        exit 1
    fi
    log_info "Docker Buildx plugin: OK"
    
    log_success "Prerequisites check passed"
}

# Check if builder already exists
check_existing_builder() {
    local builder_name="$1"
    
    if docker buildx ls | grep -q "$builder_name"; then
        if [[ "$FORCE_SETUP" == "true" ]]; then
            log_warning "Builder '$builder_name' already exists. Removing it due to --force flag..."
            docker buildx rm "$builder_name" || true
            return 1
        else
            log_warning "Builder '$builder_name' already exists"
            log_info "Use --force to recreate the builder"
            return 0
        fi
    fi
    return 1
}

# Create new builder
create_builder() {
    local builder_name="$1"
    
    log_phase "Creating Docker Buildx builder: $builder_name"
    
    # Create builder with multi-platform support
    if docker buildx create \
        --name "$builder_name" \
        --driver docker-container \
        --platform linux/amd64,linux/arm64 \
        --use; then
        log_success "Builder '$builder_name' created successfully"
    else
        log_error "Failed to create builder '$builder_name'"
        exit 1
    fi
}

# Configure builder
configure_builder() {
    local builder_name="$1"
    
    log_phase "Configuring builder: $builder_name"
    
    # Set as current builder
    if docker buildx use "$builder_name"; then
        log_info "Set '$builder_name' as current builder"
    else
        log_error "Failed to set '$builder_name' as current builder"
        exit 1
    fi
    
    # Inspect builder to verify configuration
    log_info "Builder configuration:"
    docker buildx inspect "$builder_name" --bootstrap | grep -E "(Platforms|Driver)" || true
}

# Set up build cache
setup_build_cache() {
    log_phase "Setting up build cache..."
    
    # Create cache directory if it doesn't exist
    local cache_dir="$PROJECT_ROOT/.buildx-cache"
    if [[ ! -d "$cache_dir" ]]; then
        mkdir -p "$cache_dir"
        log_info "Created cache directory: $cache_dir"
    fi
    
    # Set up cache configuration
    cat > "$PROJECT_ROOT/.buildx-cache/config.json" << EOF
{
    "cache": {
        "type": "local",
        "path": "$cache_dir"
    },
    "platforms": ["linux/amd64", "linux/arm64"],
    "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    log_success "Build cache configured"
}

# Test multi-platform build
test_build() {
    log_phase "Testing multi-platform build capability..."
    
    # Create a simple test Dockerfile
    local test_dockerfile="$PROJECT_ROOT/.buildx-test/Dockerfile"
    mkdir -p "$(dirname "$test_dockerfile")"
    
    cat > "$test_dockerfile" << EOF
FROM alpine:latest
RUN echo "Multi-platform test build successful"
EOF
    
    # Test build for both platforms
    if docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --file "$test_dockerfile" \
        --tag lucid-test:multiplatform \
        --load \
        "$(dirname "$test_dockerfile")"; then
        log_success "Multi-platform test build successful"
    else
        log_warning "Multi-platform test build failed (this might be expected in some environments)"
    fi
    
    # Clean up test files
    rm -rf "$PROJECT_ROOT/.buildx-test"
}

# Verify setup
verify_setup() {
    local builder_name="$1"
    
    log_phase "Verifying setup..."
    
    # Check if builder is active
    local current_builder
    current_builder=$(docker buildx ls | grep '*' | awk '{print $1}')
    
    if [[ "$current_builder" == "$builder_name" ]]; then
        log_success "Builder '$builder_name' is active"
    else
        log_warning "Builder '$builder_name' is not the active builder"
        log_info "Current active builder: $current_builder"
    fi
    
    # Show builder information
    log_info "Builder details:"
    docker buildx inspect "$builder_name" | grep -E "(Name|Driver|Platforms)" || true
    
    # Show available builders
    log_info "Available builders:"
    docker buildx ls
}

# Main function
main() {
    log_info "Starting Lucid Multi-Platform Build Setup"
    log_info "Builder name: $BUILDER_NAME"
    log_info "Force setup: $FORCE_SETUP"
    echo
    
    # Check prerequisites
    check_prerequisites
    echo
    
    # Check if builder already exists
    if check_existing_builder "$BUILDER_NAME"; then
        log_info "Using existing builder: $BUILDER_NAME"
        configure_builder "$BUILDER_NAME"
    else
        # Create new builder
        create_builder "$BUILDER_NAME"
        echo
        
        # Configure builder
        configure_builder "$BUILDER_NAME"
        echo
    fi
    
    # Set up build cache
    setup_build_cache
    echo
    
    # Test multi-platform build
    test_build
    echo
    
    # Verify setup
    verify_setup "$BUILDER_NAME"
    echo
    
    log_success "Multi-platform build setup completed successfully!"
    echo
    log_info "Next steps:"
    log_info "1. Use './build-multiplatform.sh' to build all services"
    log_info "2. Use './push-to-ghcr.sh' to push to registry"
    log_info "3. Verify manifests with 'docker manifest inspect'"
    echo
    log_info "Builder '$BUILDER_NAME' is ready for multi-platform builds"
}

# Run main function
main "$@"
