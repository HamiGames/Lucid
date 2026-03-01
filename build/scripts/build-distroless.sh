#!/bin/bash
# Path: build/scripts/build-distroless.sh
# Linux shell script for building distroless images
# Multi-stage distroless builds for Lucid project

set -euo pipefail

# Default values
SERVICES="all"
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
Lucid Distroless Build Script (Linux)

USAGE:
    ./build-distroless.sh [OPTIONS]

OPTIONS:
    -s, --services <services>    Services to build (comma-separated or 'all')
                                Default: all
                                Options: gui,blockchain,rdp,node,storage,database,vm
    
    -p, --platform <platform>   Target platforms (comma-separated)
                                Default: linux/amd64,linux/arm64
                                Options: linux/amd64, linux/arm64, linux/amd64,linux/arm64
    
    -r, --registry <registry>   Container registry
                                Default: ghcr.io
    
    -i, --image-name <name>     Image name prefix
                                Default: HamiGames/Lucid
    
    -t, --tag <tag>             Image tag
                                Default: latest
    
    --push                      Push images to registry
                                Default: false
    
    --no-cache                  Disable build cache
                                Default: false
    
    -v, --verbose               Enable verbose output
                                Default: false
    
    -h, --help                  Show this help message

EXAMPLES:
    ./build-distroless.sh
    ./build-distroless.sh --services "gui,blockchain" --push
    ./build-distroless.sh --platform "linux/arm64" --tag "v1.0.0" --push
    ./build-distroless.sh --services "rdp" --no-cache --verbose

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
            --push)
                PUSH=true
                shift
                ;;
            --no-cache)
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    docker_version=$(docker --version 2>/dev/null)
    log_success "Docker found: $docker_version"
    
    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx is required but not installed"
        exit 1
    fi
    
    buildx_version=$(docker buildx version 2>/dev/null)
    log_success "Docker Buildx found: $buildx_version"
    
    # Check if we're in the right directory
    if [[ ! -d "infrastructure" ]]; then
        log_error "Please run this script from the project root or ensure infrastructure directory exists"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Initialize Docker Buildx
initialize_buildx() {
    log_info "Initializing Docker Buildx..."
    
    local builder_name="lucid-distroless-builder"
    
    # Check if builder exists
    if ! docker buildx ls --format "{{.Name}}" | grep -q "^$builder_name$"; then
        log_info "Creating new builder instance: $builder_name"
        docker buildx create --name "$builder_name" --driver docker-container --use
        if [[ $? -ne 0 ]]; then
            log_error "Failed to create builder instance"
            exit 1
        fi
    else
        log_info "Using existing builder instance: $builder_name"
        docker buildx use "$builder_name"
        if [[ $? -ne 0 ]]; then
            log_error "Failed to use builder instance"
            exit 1
        fi
    fi
    
    # Bootstrap the builder
    log_info "Bootstrapping builder..."
    docker buildx inspect --bootstrap
    if [[ $? -ne 0 ]]; then
        log_error "Failed to bootstrap builder"
        exit 1
    fi
    
    log_success "Buildx initialization completed"
}

# Get services to build
get_services_to_build() {
    local services_input="$1"
    local all_services=("gui" "blockchain" "rdp" "node" "storage" "database" "vm")
    
    if [[ "$services_input" == "all" ]]; then
        echo "${all_services[@]}"
        return
    fi
    
    IFS=',' read -ra requested_services <<< "$services_input"
    local valid_services=()
    
    for service in "${requested_services[@]}"; do
        service=$(echo "$service" | xargs) # trim whitespace
        if [[ " ${all_services[*]} " =~ " ${service} " ]]; then
            valid_services+=("$service")
        else
            log_warn "Unknown service '$service', skipping"
        fi
    done
    
    if [[ ${#valid_services[@]} -eq 0 ]]; then
        log_error "No valid services specified"
        exit 1
    fi
    
    echo "${valid_services[@]}"
}

# Build base image
build_base_image() {
    local platform="$1"
    local registry="$2"
    local image_name="$3"
    local tag="$4"
    
    log_info "Building base distroless image..."
    log_info "Platform: $platform"
    
    local base_image_dir="infrastructure/docker/distroless/base"
    if [[ ! -d "$base_image_dir" ]]; then
        log_error "Base image directory not found: $base_image_dir"
        return 1
    fi
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local base_tags=(
        "$registry/$image_name/base:$tag"
        "$registry/$image_name/base:$timestamp"
    )
    
    local build_args=(
        "buildx" "build"
        "--platform" "$platform"
        "--file" "$base_image_dir/Dockerfile"
        "--tag" "${base_tags[0]}"
        "--tag" "${base_tags[1]}"
    )
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=("--no-cache")
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        build_args+=("--push")
    else
        build_args+=("--load")
    fi
    
    build_args+=("$base_image_dir")
    
    log_verbose "Running: docker ${build_args[*]}"
    
    if [[ "$VERBOSE" == "true" ]]; then
        docker "${build_args[@]}"
    else
        docker "${build_args[@]}" 2>&1 | while IFS= read -r line; do
            if [[ "$line" =~ (error|failed|ERROR|FAILED) ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ "$line" =~ (success|completed|SUCCESS|COMPLETED) ]]; then
                echo -e "${GREEN}$line${NC}"
            else
                echo "$line"
            fi
        done
    fi
    
    if [[ $? -eq 0 ]]; then
        log_success "Base image built successfully"
        return 0
    else
        log_error "Base image build failed"
        return 1
    fi
}

# Build service image
build_service_image() {
    local service="$1"
    local platform="$2"
    local registry="$3"
    local image_name="$4"
    local tag="$5"
    
    log_info "Building $service service image..."
    log_info "Platform: $platform"
    
    local dockerfile_path="infrastructure/docker/multi-stage/Dockerfile.$service"
    if [[ ! -f "$dockerfile_path" ]]; then
        log_error "Dockerfile not found: $dockerfile_path"
        return 1
    fi
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local service_tags=(
        "$registry/$image_name/$service:$tag"
        "$registry/$image_name/$service:$timestamp"
    )
    
    local build_args=(
        "buildx" "build"
        "--platform" "$platform"
        "--file" "$dockerfile_path"
        "--tag" "${service_tags[0]}"
        "--tag" "${service_tags[1]}"
        "--build-arg" "BASE_IMAGE=$registry/$image_name/base:$tag"
    )
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=("--no-cache")
    else
        build_args+=("--cache-from" "type=local,src=build/cache")
        build_args+=("--cache-to" "type=local,dest=build/cache,mode=max")
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        build_args+=("--push")
    else
        build_args+=("--load")
    fi
    
    build_args+=(".")
    
    log_verbose "Running: docker ${build_args[*]}"
    
    if [[ "$VERBOSE" == "true" ]]; then
        docker "${build_args[@]}"
    else
        docker "${build_args[@]}" 2>&1 | while IFS= read -r line; do
            if [[ "$line" =~ (error|failed|ERROR|FAILED) ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ "$line" =~ (success|completed|SUCCESS|COMPLETED) ]]; then
                echo -e "${GREEN}$line${NC}"
            else
                echo "$line"
            fi
        done
    fi
    
    if [[ $? -eq 0 ]]; then
        log_success "$service service image built successfully"
        return 0
    else
        log_error "$service service image build failed"
        return 1
    fi
}

# Test image
test_image() {
    local image_tag="$1"
    
    log_info "Testing image: $image_tag"
    
    # Test basic image functionality
    if docker run --rm "$image_tag" /bin/sh -c "echo 'Image test successful'" &>/dev/null; then
        log_success "Image test passed: $image_tag"
        return 0
    else
        log_error "Image test failed: $image_tag"
        return 1
    fi
}

# Show build summary
show_build_summary() {
    local services=("$@")
    local results=()
    
    log_info "Build Summary"
    log_info "============"
    log_info "Services: ${services[*]}"
    log_info "Platform: $PLATFORM"
    log_info "Registry: $REGISTRY"
    log_info "Image Name: $IMAGE_NAME"
    log_info "Tag: $TAG"
    log_info "Push: $PUSH"
    echo
    
    log_info "Results:"
    local success_count=0
    local total_count=${#services[@]}
    
    for service in "${services[@]}"; do
        # Check if service build was successful
        local image_tag="$REGISTRY/$IMAGE_NAME/$service:$TAG"
        if docker images "$image_tag" --format "{{.Repository}}:{{.Tag}}" | grep -q "^$image_tag$"; then
            echo -e "  ${GREEN}$service : SUCCESS${NC}"
            ((success_count++))
        else
            echo -e "  ${RED}$service : FAILED${NC}"
        fi
    done
    
    echo
    log_info "Total: $success_count/$total_count services built successfully"
    
    if [[ $success_count -eq $total_count ]]; then
        log_success "All builds completed successfully!"
        exit 0
    else
        log_error "Some builds failed. Check the logs above for details."
        exit 1
    fi
}

# Main execution
main() {
    # Show help if requested
    if [[ "$HELP" == "true" ]]; then
        show_help
        exit 0
    fi
    
    log_info "Starting Lucid Distroless Build Process"
    log_info "========================================"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate inputs
    log_info "Validating inputs..."
    read -ra services_to_build <<< "$(get_services_to_build "$SERVICES")"
    log_info "Services to build: ${services_to_build[*]}"
    
    # Check prerequisites
    check_prerequisites
    
    # Initialize buildx
    initialize_buildx
    
    # Create cache directory
    if [[ ! -d "build/cache" ]]; then
        mkdir -p "build/cache"
        log_info "Created cache directory: build/cache"
    fi
    
    # Build base image first
    log_info "Building base distroless image..."
    if ! build_base_image "$PLATFORM" "$REGISTRY" "$IMAGE_NAME" "$TAG"; then
        log_error "Base image build failed, aborting"
        exit 1
    fi
    
    # Build service images
    for service in "${services_to_build[@]}"; do
        log_info "Building $service service..."
        build_service_image "$service" "$PLATFORM" "$REGISTRY" "$IMAGE_NAME" "$TAG"
    done
    
    # Test images if not pushing
    if [[ "$PUSH" != "true" ]]; then
        for service in "${services_to_build[@]}"; do
            local image_tag="$REGISTRY/$IMAGE_NAME/$service:$TAG"
            test_image "$image_tag"
        done
    fi
    
    # Show summary
    show_build_summary "${services_to_build[@]}"
}

# Trap to ensure cleanup on exit
cleanup() {
    log_info "Build process completed"
}

trap cleanup EXIT

# Run main function
main "$@"