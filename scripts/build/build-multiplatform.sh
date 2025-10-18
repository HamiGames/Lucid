#!/bin/bash

# Lucid Multi-Platform Build Script
# Builds all Lucid containers for multiple platforms (linux/amd64, linux/arm64)
# Usage: ./build-multiplatform.sh [options]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILDER_NAME="lucid-multiplatform"
REGISTRY="ghcr.io"
REPOSITORY="hamigames/lucid"

# Default values
PLATFORMS="linux/amd64,linux/arm64"
TAG="latest"
PUSH=false
CLEAN_BUILD=false
DRY_RUN=false
SERVICES="all"
BUILD_CACHE=true
PARALLEL_BUILDS=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Service definitions by phase
declare -A PHASE_SERVICES
PHASE_SERVICES[phase1]="auth-service storage-database mongodb redis elasticsearch"
PHASE_SERVICES[phase2]="api-gateway blockchain-core blockchain-engine session-anchoring block-manager data-chain service-mesh-controller"
PHASE_SERVICES[phase3]="session-pipeline session-recorder session-processor session-storage session-api rdp-server-manager rdp-xrdp rdp-controller rdp-monitor node-management"
PHASE_SERVICES[phase4]="admin-interface tron-client tron-payout-router tron-wallet-manager tron-usdt-manager tron-staking tron-payment-gateway"

# All services
ALL_SERVICES=""
for phase in "${!PHASE_SERVICES[@]}"; do
    ALL_SERVICES="$ALL_SERVICES ${PHASE_SERVICES[$phase]}"
done

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

log_build() {
    echo -e "${MAGENTA}[BUILD]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Lucid Multi-Platform Build Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -s, --services SERVICES    Services to build (default: all)
                               Options: all, phase1, phase2, phase3, phase4, or comma-separated list
    -p, --platforms PLAT      Target platforms (default: linux/amd64,linux/arm64)
    -t, --tag TAG             Tag to use (default: latest)
    --push                    Push images to registry after building
    --clean                   Clean build (no cache)
    --dry-run                 Show what would be built without building
    --no-cache                Disable build cache
    --parallel N              Number of parallel builds (default: 2)
    -h, --help                Show this help message

SERVICES:
    Phase 1 (Foundation):
    - auth-service, storage-database, mongodb, redis, elasticsearch
    
    Phase 2 (Core Services):
    - api-gateway, blockchain-core, blockchain-engine, session-anchoring
    - block-manager, data-chain, service-mesh-controller
    
    Phase 3 (Application Services):
    - session-pipeline, session-recorder, session-processor, session-storage
    - session-api, rdp-server-manager, rdp-xrdp, rdp-controller, rdp-monitor
    - node-management
    
    Phase 4 (Support Services):
    - admin-interface, tron-client, tron-payout-router, tron-wallet-manager
    - tron-usdt-manager, tron-staking, tron-payment-gateway

EXAMPLES:
    $0                                    # Build all services
    $0 --services phase1                 # Build Phase 1 services only
    $0 --services api-gateway,blockchain-core  # Build specific services
    $0 --push --tag v1.0.0               # Build and push with version tag
    $0 --clean --no-cache                # Clean build without cache
    $0 --dry-run                         # Show what would be built

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
            -p|--platforms)
                PLATFORMS="$2"
                shift 2
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            --push)
                PUSH=true
                shift
                ;;
            --clean)
                CLEAN_BUILD=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-cache)
                BUILD_CACHE=false
                shift
                ;;
            --parallel)
                PARALLEL_BUILDS="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

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
        exit 1
    fi
    log_info "Docker Buildx: OK"
    
    # Check if builder exists
    if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
        log_warning "Builder '$BUILDER_NAME' not found"
        log_info "Run './setup-buildx.sh' to create the builder"
        exit 1
    fi
    log_info "Builder '$BUILDER_NAME': OK"
    
    # Check if logged into registry (if pushing)
    if [[ "$PUSH" == "true" ]]; then
        if ! docker info | grep -q "$REGISTRY"; then
            log_warning "Not logged into $REGISTRY"
            log_info "Please login to $REGISTRY before pushing"
            if [[ "$DRY_RUN" == "false" ]]; then
                exit 1
            fi
        else
            log_info "Registry authentication: OK"
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Get services to build
get_services_to_build() {
    local services_input="$1"
    local services=()
    
    case "$services_input" in
        all)
            services=($ALL_SERVICES)
            ;;
        phase1|phase2|phase3|phase4)
            services=(${PHASE_SERVICES[$services_input]})
            ;;
        *)
            # Comma-separated list
            IFS=',' read -ra services <<< "$services_input"
            ;;
    esac
    
    # Validate services
    local valid_services=($ALL_SERVICES)
    for service in "${services[@]}"; do
        local valid=false
        for valid_service in "${valid_services[@]}"; do
            if [[ "$service" == "$valid_service" ]]; then
                valid=true
                break
            fi
        done
        if [[ "$valid" == "false" ]]; then
            log_error "Invalid service: $service"
            log_info "Valid services: ${valid_services[*]}"
            exit 1
        fi
    done
    
    echo "${services[@]}"
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
        "$PROJECT_ROOT/payment-systems/tron/Dockerfile.$service"
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
        return 1
    fi
    
    echo "$dockerfile"
}

# Build single service
build_service() {
    local service="$1"
    local tag="$2"
    local platforms="$3"
    local push="$4"
    local clean="$5"
    local cache="$6"
    local dry_run="$7"
    
    log_build "Building $service:$tag for platforms: $platforms"
    
    # Find Dockerfile
    local dockerfile
    if ! dockerfile=$(find_dockerfile "$service"); then
        log_error "Failed to find Dockerfile for $service"
        return 1
    fi
    log_info "Using Dockerfile: $dockerfile"
    
    # Determine context directory
    local context_dir
    context_dir=$(dirname "$dockerfile")
    
    # Build tags
    local tags=()
    tags+=("$REGISTRY/$REPOSITORY/$service:$tag")
    
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
    build_cmd="$build_cmd --platform $platforms"
    build_cmd="$build_cmd --file $dockerfile"
    build_cmd="$build_cmd --tag $tag_string"
    
    # Add cache options
    if [[ "$cache" == "true" ]]; then
        build_cmd="$build_cmd --cache-from type=gha,scope=$service"
        build_cmd="$build_cmd --cache-to type=gha,mode=max,scope=$service"
    fi
    
    # Add clean build options
    if [[ "$clean" == "true" ]]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    # Add push or load
    if [[ "$push" == "true" ]]; then
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
        log_success "Successfully built $service:$tag"
        return 0
    else
        log_error "Failed to build $service:$tag"
        return 1
    fi
}

# Build services in parallel
build_services_parallel() {
    local services=("$@")
    local pids=()
    local results=()
    local max_parallel="$PARALLEL_BUILDS"
    local current_parallel=0
    
    log_phase "Building ${#services[@]} services with $max_parallel parallel builds"
    
    for service in "${services[@]}"; do
        # Wait if we've reached the parallel limit
        while [[ $current_parallel -ge $max_parallel ]]; do
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    wait "${pids[$i]}"
                    results[$i]=$?
                    unset pids[$i]
                    ((current_parallel--))
                fi
            done
            sleep 1
        done
        
        # Start build in background
        (
            build_service "$service" "$TAG" "$PLATFORMS" "$PUSH" "$CLEAN_BUILD" "$BUILD_CACHE" "$DRY_RUN"
        ) &
        
        local pid=$!
        pids+=($pid)
        ((current_parallel++))
        
        log_info "Started build for $service (PID: $pid)"
    done
    
    # Wait for all builds to complete
    log_info "Waiting for all builds to complete..."
    for i in "${!pids[@]}"; do
        wait "${pids[$i]}"
        results[$i]=$?
    done
    
    # Report results
    local success_count=0
    local failure_count=0
    
    for i in "${!results[@]}"; do
        if [[ ${results[$i]} -eq 0 ]]; then
            ((success_count++))
        else
            ((failure_count++))
        fi
    done
    
    log_phase "Build results: $success_count successful, $failure_count failed"
    
    if [[ $failure_count -gt 0 ]]; then
        return 1
    fi
    return 0
}

# Verify builds
verify_builds() {
    local services=("$@")
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Skipping verification in dry-run mode"
        return 0
    fi
    
    log_phase "Verifying builds..."
    
    for service in "${services[@]}"; do
        local image="$REGISTRY/$REPOSITORY/$service:$TAG"
        
        if [[ "$PUSH" == "true" ]]; then
            # Verify image exists in registry
            if docker manifest inspect "$image" >/dev/null 2>&1; then
                log_success "Verified $service in registry"
                
                # Show platform details
                local platforms
                platforms=$(docker manifest inspect "$image" | jq -r '.manifests[] | "\(.platform.os)/\(.platform.architecture)"' 2>/dev/null || echo "unknown")
                log_info "  Platforms: $platforms"
            else
                log_warning "Could not verify $service in registry"
            fi
        else
            # Verify local image
            if docker image inspect "$image" >/dev/null 2>&1; then
                log_success "Verified $service locally"
            else
                log_warning "Could not verify $service locally"
            fi
        fi
    done
}

# Main function
main() {
    log_info "Starting Lucid Multi-Platform Build"
    log_info "Services: $SERVICES"
    log_info "Platforms: $PLATFORMS"
    log_info "Tag: $TAG"
    log_info "Push: $PUSH"
    log_info "Clean: $CLEAN_BUILD"
    log_info "Cache: $BUILD_CACHE"
    log_info "Dry run: $DRY_RUN"
    log_info "Parallel builds: $PARALLEL_BUILDS"
    echo
    
    # Parse arguments
    parse_args "$@"
    
    # Check prerequisites
    check_prerequisites
    echo
    
    # Get services to build
    local services_to_build
    services_to_build=($(get_services_to_build "$SERVICES"))
    
    log_phase "Services to build: ${services_to_build[*]}"
    echo
    
    # Build services
    if build_services_parallel "${services_to_build[@]}"; then
        log_success "All builds completed successfully"
    else
        log_error "Some builds failed"
        exit 1
    fi
    echo
    
    # Verify builds
    verify_builds "${services_to_build[@]}"
    echo
    
    log_success "Multi-platform build process completed!"
    echo
    log_info "Summary:"
    log_info "  Services built: ${#services_to_build[@]}"
    log_info "  Platforms: $PLATFORMS"
    log_info "  Tag: $TAG"
    if [[ "$PUSH" == "true" ]]; then
        log_info "  Registry: $REGISTRY/$REPOSITORY"
    else
        log_info "  Local images created"
    fi
}

# Run main function with all arguments
main "$@"
