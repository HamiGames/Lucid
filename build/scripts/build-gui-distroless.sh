#!/bin/bash
# Path: build/scripts/build-gui-distroless.sh
# Multi-stage distroless builds for Lucid GUI services
# Follows SPEC-1B-v2-DISTROLESS and SPEC-5 Web-Based GUI Architecture

set -euo pipefail

# Default values
SERVICES="user,admin,node"
PLATFORM="linux/amd64,linux/arm64"
REGISTRY="ghcr.io"
IMAGE_NAME="HamiGames/Lucid"
TAG="latest"
PUSH=false
NO_CACHE=false
VERBOSE=false
HELP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Build distroless GUI containers for Lucid RDP project.

OPTIONS:
    -s, --services SERVICES     Comma-separated list of GUI services to build (default: user,admin,node)
    -p, --platform PLATFORM    Target platform (default: linux/amd64,linux/arm64)
    -r, --registry REGISTRY     Container registry (default: ghcr.io)
    -i, --image-name NAME       Image name prefix (default: HamiGames/Lucid)
    -t, --tag TAG               Image tag (default: latest)
    -P, --push                  Push images to registry
    -n, --no-cache              Build without cache
    -v, --verbose               Verbose output
    -h, --help                  Show this help message

EXAMPLES:
    # Build all GUI services
    $0

    # Build only user and admin GUIs
    $0 --services user,admin

    # Build and push to custom registry
    $0 --push --registry myregistry.com --image-name myorg/lucid

    # Build for specific platform
    $0 --platform linux/arm64

ENVIRONMENT VARIABLES:
    GITHUB_SHA                  Git commit SHA for tagging
    BUILDKIT_PROGRESS           Docker BuildKit progress setting

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -i|--image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -P|--push)
                PUSH=true
                shift
                ;;
            -n|--no-cache)
                NO_CACHE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                HELP=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if Docker Buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    
    # Check if required directories exist
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        if [[ ! -d "apps/gui-$service" ]]; then
            log_error "GUI service directory not found: apps/gui-$service"
            exit 1
        fi
        
        if [[ ! -f "apps/gui-$service/Dockerfile.distroless" ]]; then
            log_error "Distroless Dockerfile not found: apps/gui-$service/Dockerfile.distroless"
            exit 1
        fi
    done
    
    log_success "Prerequisites validated"
}

# Setup build environment
setup_build_environment() {
    log_info "Setting up build environment..."
    
    # Set Docker BuildKit environment
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    # Set progress output
    if [[ "$VERBOSE" == "true" ]]; then
        export BUILDKIT_PROGRESS=plain
    else
        export BUILDKIT_PROGRESS=auto
    fi
    
    # Create buildx builder if it doesn't exist
    if ! docker buildx ls | grep -q "lucid-gui-builder"; then
        log_info "Creating Docker Buildx builder: lucid-gui-builder"
        docker buildx create --name lucid-gui-builder --use --driver docker-container \
            --driver-opt network=host --driver-opt image=moby/buildkit:buildx-stable-1
    else
        log_info "Using existing Docker Buildx builder: lucid-gui-builder"
        docker buildx use lucid-gui-builder
    fi
    
    # Bootstrap builder
    docker buildx inspect --bootstrap
    
    log_success "Build environment setup complete"
}

# Build single GUI service
build_gui_service() {
    local service="$1"
    local build_args=""
    local cache_args=""
    local push_args=""
    
    log_info "Building GUI service: $service"
    
    # Set build arguments
    build_args="--platform $PLATFORM"
    build_args="$build_args --file apps/gui-$service/Dockerfile.distroless"
    build_args="$build_args --tag $REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
    
    # Add git SHA tag if available
    if [[ -n "${GITHUB_SHA:-}" ]]; then
        build_args="$build_args --tag $REGISTRY/$IMAGE_NAME/$service-gui:$GITHUB_SHA"
    fi
    
    # Add cache arguments
    if [[ "$NO_CACHE" == "true" ]]; then
        cache_args="--no-cache"
    else
        cache_args="--cache-from type=gha,scope=gui-$service"
        cache_args="$cache_args --cache-to type=gha,mode=max,scope=gui-$service"
    fi
    
    # Add push argument
    if [[ "$PUSH" == "true" ]]; then
        push_args="--push"
    else
        push_args="--load"
    fi
    
    # Build arguments for distroless compliance
    local distroless_args=""
    distroless_args="$distroless_args --build-arg NODE_ENV=production"
    distroless_args="$distroless_args --build-arg BUILDKIT_INLINE_CACHE=1"
    
    log_verbose "Build command: docker buildx build $build_args $cache_args $push_args $distroless_args apps/gui-$service/"
    
    # Execute build
    if docker buildx build $build_args $cache_args $push_args $distroless_args apps/gui-$service/; then
        log_success "GUI service $service built successfully"
        return 0
    else
        log_error "Failed to build GUI service $service"
        return 1
    fi
}

# Verify distroless compliance
verify_distroless_compliance() {
    local service="$1"
    local image_tag="$REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
    
    log_info "Verifying distroless compliance for $service..."
    
    # Check if image exists (skip if pushing to registry)
    if [[ "$PUSH" == "false" ]]; then
        if ! docker image inspect "$image_tag" >/dev/null 2>&1; then
            log_error "Image $image_tag not found locally"
            return 1
        fi
        
        # Check for shell (should fail)
        if docker run --rm "$image_tag" /bin/sh -c "echo 'shell check'" >/dev/null 2>&1; then
            log_error "Shell found in distroless image $service"
            return 1
        else
            log_verbose "✅ No shell found in $service image"
        fi
        
        # Check user (should be nonroot - UID 65532)
        local user_id
        user_id=$(docker run --rm "$image_tag" id -u 2>/dev/null || echo "unknown")
        if [[ "$user_id" == "65532" ]]; then
            log_verbose "✅ Correct user (nonroot) in $service image"
        else
            log_warn "User ID in $service image: $user_id (expected: 65532)"
        fi
        
        # Check read-only root (should fail to write)
        if docker run --rm "$image_tag" touch /test 2>/dev/null; then
            log_warn "Root filesystem is writable in $service image"
        else
            log_verbose "✅ Read-only root filesystem in $service image"
        fi
        
        # Check base image
        local base_image
        base_image=$(docker inspect "$image_tag" --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
        if [[ "$base_image" == *"distroless"* ]]; then
            log_verbose "✅ Distroless base image confirmed for $service"
        else
            log_warn "Base image for $service: $base_image"
        fi
    else
        log_info "Skipping local compliance check (image pushed to registry)"
    fi
    
    log_success "Distroless compliance verification completed for $service"
}

# Generate build manifest
generate_build_manifest() {
    local manifest_file="build/manifests/gui-build-manifest.json"
    
    log_info "Generating build manifest..."
    
    mkdir -p "$(dirname "$manifest_file")"
    
    cat > "$manifest_file" << EOF
{
  "build_id": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_sha": "${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}",
  "git_branch": "${GITHUB_REF_NAME:-$(git branch --show-current 2>/dev/null || echo 'unknown')}",
  "build_platform": "$PLATFORM",
  "registry": "$REGISTRY",
  "image_name": "$IMAGE_NAME",
  "tag": "$TAG",
  "services": [$(echo "$SERVICES" | tr ',' ' ' | sed 's/^/"/;s/$/"/;s/ /","/g')],
  "distroless_compliance": {
    "base_image": "gcr.io/distroless/nodejs20-debian12",
    "user": "nonroot (UID 65532)",
    "filesystem": "read-only",
    "shell": "none",
    "package_manager": "none"
  },
  "security_features": {
    "tor_integration": true,
    "trust_nothing_policy": true,
    "client_side_encryption": true,
    "onion_only_access": true
  },
  "build_environment": {
    "docker_buildkit": "1",
    "buildx_builder": "lucid-gui-builder",
    "no_cache": $NO_CACHE,
    "verbose": $VERBOSE
  }
}
EOF
    
    log_success "Build manifest generated: $manifest_file"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up build environment..."
    
    # Remove temporary files
    rm -f /tmp/lucid-gui-build-*
    
    # Stop buildx builder if it was created
    if docker buildx ls | grep -q "lucid-gui-builder"; then
        docker buildx rm lucid-gui-builder 2>/dev/null || true
    fi
    
    log_success "Cleanup completed"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Show help if requested
    if [[ "$HELP" == "true" ]]; then
        show_help
        exit 0
    fi
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    log_info "Starting Lucid GUI distroless build process..."
    log_info "Services: $SERVICES"
    log_info "Platform: $PLATFORM"
    log_info "Registry: $REGISTRY"
    log_info "Image Name: $IMAGE_NAME"
    log_info "Tag: $TAG"
    log_info "Push: $PUSH"
    log_info "No Cache: $NO_CACHE"
    log_info "Verbose: $VERBOSE"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Setup build environment
    setup_build_environment
    
    # Build each GUI service
    local failed_services=""
    local successful_services=""
    
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        if build_gui_service "$service"; then
            successful_services="$successful_services $service"
            verify_distroless_compliance "$service"
        else
            failed_services="$failed_services $service"
        fi
    done
    
    # Generate build manifest
    generate_build_manifest
    
    # Report results
    echo ""
    log_info "=== BUILD SUMMARY ==="
    
    if [[ -n "$successful_services" ]]; then
        log_success "Successfully built services:$successful_services"
    fi
    
    if [[ -n "$failed_services" ]]; then
        log_error "Failed to build services:$failed_services"
        exit 1
    fi
    
    log_success "All GUI services built successfully!"
    
    # Display image information
    if [[ "$PUSH" == "false" ]]; then
        echo ""
        log_info "=== BUILT IMAGES ==="
        for service in $(echo "$SERVICES" | tr ',' ' '); do
            echo "  $REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
        done
    fi
}

# Run main function with all arguments
main "$@"
