#!/bin/bash

# Lucid Container Registry Push Script
# Pushes distroless containers to GitHub Container Registry (GHCR)
# Usage: ./push-to-ghcr.sh [service-name] [tag] [platform]

set -euo pipefail

# Configuration
REGISTRY="ghcr.io"
REPOSITORY="hamigames/lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
SERVICE_NAME=""
TAG="latest"
PLATFORM="linux/amd64,linux/arm64"
PUSH_LATEST=false
DRY_RUN=false

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

# Help function
show_help() {
    cat << EOF
Lucid Container Registry Push Script

USAGE:
    $0 [OPTIONS] SERVICE_NAME

ARGUMENTS:
    SERVICE_NAME          Name of the service to push (e.g., api-gateway, blockchain-core)

OPTIONS:
    -t, --tag TAG         Tag to use (default: latest)
    -p, --platform PLAT   Target platform (default: linux/amd64,linux/arm64)
    -l, --latest          Also push as 'latest' tag
    -d, --dry-run         Show what would be pushed without actually pushing
    -h, --help            Show this help message

EXAMPLES:
    $0 api-gateway
    $0 blockchain-core -t v1.0.0 -l
    $0 session-management -p linux/amd64 -d

SERVICES:
    Phase 1 (Foundation):
    - auth-service
    - storage-database
    - mongodb
    - redis
    - elasticsearch

    Phase 2 (Core Services):
    - api-gateway
    - blockchain-core
    - blockchain-engine
    - session-anchoring
    - block-manager
    - data-chain
    - service-mesh-controller

    Phase 3 (Application Services):
    - session-pipeline
    - session-recorder
    - session-processor
    - session-storage
    - session-api
    - rdp-server-manager
    - rdp-xrdp
    - rdp-controller
    - rdp-monitor
    - node-management

    Phase 4 (Support Services):
    - admin-interface
    - tron-client
    - tron-payout-router
    - tron-wallet-manager
    - tron-usdt-manager
    - tron-staking
    - tron-payment-gateway

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -l|--latest)
                PUSH_LATEST=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$SERVICE_NAME" ]]; then
                    SERVICE_NAME="$1"
                else
                    log_error "Multiple service names provided: $SERVICE_NAME and $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$SERVICE_NAME" ]]; then
        log_error "Service name is required"
        show_help
        exit 1
    fi
}

# Validate service name
validate_service() {
    local service="$1"
    local valid_services=(
        # Phase 1
        "auth-service" "storage-database" "mongodb" "redis" "elasticsearch"
        # Phase 2
        "api-gateway" "blockchain-core" "blockchain-engine" "session-anchoring" 
        "block-manager" "data-chain" "service-mesh-controller"
        # Phase 3
        "session-pipeline" "session-recorder" "session-processor" "session-storage"
        "session-api" "rdp-server-manager" "rdp-xrdp" "rdp-controller" "rdp-monitor"
        "node-management"
        # Phase 4
        "admin-interface" "tron-client" "tron-payout-router" "tron-wallet-manager"
        "tron-usdt-manager" "tron-staking" "tron-payment-gateway"
    )

    for valid_service in "${valid_services[@]}"; do
        if [[ "$service" == "$valid_service" ]]; then
            return 0
        fi
    done

    log_error "Invalid service name: $service"
    log_info "Valid services: ${valid_services[*]}"
    return 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi

    # Check if Docker Buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi

    # Check if logged into GHCR
    if ! docker info | grep -q "ghcr.io"; then
        log_warning "Not logged into GHCR. Attempting to login..."
        if ! echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin; then
            log_error "Failed to login to GHCR. Please set GITHUB_TOKEN environment variable"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Find Dockerfile for service
find_dockerfile() {
    local service="$1"
    local dockerfile=""

    # Check common locations for Dockerfiles
    local locations=(
        "$PROJECT_ROOT/$service/Dockerfile"
        "$PROJECT_ROOT/$service/Dockerfile.$service"
        "$PROJECT_ROOT/infrastructure/containers/$service/Dockerfile"
        "$PROJECT_ROOT/infrastructure/containers/$service/Dockerfile.$service"
        "$PROJECT_ROOT/build/distroless/$service.distroless"
    )

    for location in "${locations[@]}"; do
        if [[ -f "$location" ]]; then
            dockerfile="$location"
            break
        fi
    done

    if [[ -z "$dockerfile" ]]; then
        log_error "Dockerfile not found for service: $service"
        log_info "Searched locations:"
        for location in "${locations[@]}"; do
            log_info "  - $location"
        done
        exit 1
    fi

    echo "$dockerfile"
}

# Build and push image
build_and_push() {
    local service="$1"
    local tag="$2"
    local platform="$3"
    local push_latest="$4"
    local dry_run="$5"

    log_info "Building and pushing $service:$tag for platform(s): $platform"

    # Find Dockerfile
    local dockerfile
    dockerfile=$(find_dockerfile "$service")
    log_info "Using Dockerfile: $dockerfile"

    # Determine context directory
    local context_dir
    context_dir=$(dirname "$dockerfile")

    # Build tags
    local tags=()
    tags+=("$REGISTRY/$REPOSITORY/$service:$tag")
    
    if [[ "$push_latest" == "true" ]]; then
        tags+=("$REGISTRY/$REPOSITORY/$service:latest")
    fi

    # Create tag string
    local tag_string=""
    for tag_item in "${tags[@]}"; do
        if [[ -n "$tag_string" ]]; then
            tag_string="$tag_string,$tag_item"
        else
            tag_string="$tag_item"
        fi
    done

    # Build command
    local build_cmd="docker buildx build"
    build_cmd="$build_cmd --platform $platform"
    build_cmd="$build_cmd --file $dockerfile"
    build_cmd="$build_cmd --tag $tag_string"
    build_cmd="$build_cmd --cache-from type=gha,scope=$service"
    build_cmd="$build_cmd --cache-to type=gha,mode=max,scope=$service"
    
    if [[ "$dry_run" == "false" ]]; then
        build_cmd="$build_cmd --push"
    else
        build_cmd="$build_cmd --load"
    fi
    
    build_cmd="$build_cmd $context_dir"

    log_info "Build command: $build_cmd"

    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would execute: $build_cmd"
        return 0
    fi

    # Execute build
    if eval "$build_cmd"; then
        log_success "Successfully built and pushed $service:$tag"
        
        # Show pushed tags
        for tag_item in "${tags[@]}"; do
            log_info "Pushed: $tag_item"
        done
    else
        log_error "Failed to build and push $service:$tag"
        exit 1
    fi
}

# Verify image exists in registry
verify_push() {
    local service="$1"
    local tag="$2"
    local image="$REGISTRY/$REPOSITORY/$service:$tag"

    log_info "Verifying image exists in registry: $image"

    # Wait a moment for registry to update
    sleep 5

    if docker manifest inspect "$image" >/dev/null 2>&1; then
        log_success "Image verified in registry: $image"
        
        # Show image details
        log_info "Image details:"
        docker manifest inspect "$image" | jq -r '.manifests[] | "  - \(.platform.os)/\(.platform.architecture): \(.digest)"' 2>/dev/null || true
    else
        log_warning "Could not verify image in registry: $image"
        log_info "This might be normal if the image was just pushed"
    fi
}

# Main function
main() {
    log_info "Starting Lucid container registry push process"
    log_info "Service: $SERVICE_NAME"
    log_info "Tag: $TAG"
    log_info "Platform: $PLATFORM"
    log_info "Push latest: $PUSH_LATEST"
    log_info "Dry run: $DRY_RUN"

    # Parse arguments
    parse_args "$@"

    # Validate service
    validate_service "$SERVICE_NAME"

    # Check prerequisites
    check_prerequisites

    # Build and push
    build_and_push "$SERVICE_NAME" "$TAG" "$PLATFORM" "$PUSH_LATEST" "$DRY_RUN"

    # Verify push (only if not dry run)
    if [[ "$DRY_RUN" == "false" ]]; then
        verify_push "$SERVICE_NAME" "$TAG"
    fi

    log_success "Registry push process completed successfully"
}

# Run main function with all arguments
main "$@"
