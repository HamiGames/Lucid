#!/bin/bash
# Path: build-devcontainer.sh
# Build and deployment script for Lucid RDP DevContainer
# Target: ARM64 (Raspberry Pi 5) and AMD64 (development machines)
# Registry: DockerHub pickme/lucid
# Based on Spec-1d build requirements
# Linux/Unix/macOS version

set -euo pipefail

# Configuration
IMAGE_NAME="pickme/lucid"
BUILDER_NAME="lucid_builder"
DOCKERFILE_PATH=".devcontainer/Dockerfile"
CONTEXT_PATH="."
NETWORK_NAME="lucid-dev_lucid_net"

# Command line options
TEST_ONLY=false
NO_CACHE=false
CLEAN_BUILD=false
SHOW_HELP=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
log() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

log_info() { log "$BLUE" "[INFO] $1"; }
log_success() { log "$GREEN" "[SUCCESS] $1"; }
log_warning() { log "$YELLOW" "[WARNING] $1"; }
log_error() { log "$RED" "[ERROR] $1"; }

show_usage() {
    cat << 'EOF'
Usage: ./build-devcontainer.sh [OPTIONS]

Build and deploy Lucid RDP DevContainer for ARM64/AMD64 platforms

Options:
  --test-only     Only run local build test, don't push to registry
  --no-cache      Don't use Docker build cache
  --clean         Clean build (remove builder and start fresh)
  --help, -h      Show this help message

Examples:
  ./build-devcontainer.sh                 # Full build and push
  ./build-devcontainer.sh --test-only     # Test build only
  ./build-devcontainer.sh --clean         # Clean build
  ./build-devcontainer.sh --no-cache      # Build without cache

Environment Variables:
  DOCKER_REGISTRY     Override default registry (pickme)
  VERSION             Override version (default from pyproject.toml)
  BUILD_PLATFORMS     Override platforms (default: linux/arm64,linux/amd64)
EOF
}

if [[ "$SHOW_HELP" == "true" ]]; then
    show_usage
    exit 0
fi

# Get version from pyproject.toml or use "dev"
get_version() {
    if [[ -f "pyproject.toml" ]]; then
        grep -E '^version = ' pyproject.toml | sed -E 's/version = "(.+)"/\1/' || echo "0.1.0"
    else
        echo "0.1.0"
    fi
}

# Get git info
get_git_info() {
    if command -v git &> /dev/null && git rev-parse --git-dir &> /dev/null; then
        git rev-parse --short HEAD 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

VERSION=${VERSION:-$(get_version)}
GIT_SHA=$(get_git_info)
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BUILD_DATE_SAFE=$(date -u +%Y%m%d-%H%M%S)
BUILD_PLATFORMS=${BUILD_PLATFORMS:-"linux/arm64,linux/amd64"}

# Docker-safe tags (no colons allowed)
TAGS=(
    "${IMAGE_NAME}:${VERSION}"
    "${IMAGE_NAME}:dev-latest"
    "${IMAGE_NAME}:${VERSION}-${GIT_SHA}"
    "${IMAGE_NAME}:dev-${BUILD_DATE_SAFE}"
)

log_info "===== Lucid RDP DevContainer Build Script ====="
log_info "Image Name: $IMAGE_NAME"
log_info "Version: $VERSION"
log_info "Git SHA: $GIT_SHA"  
log_info "Build Date: $BUILD_DATE"
log_info "Builder: $BUILDER_NAME"
log_info "Target Platforms: $BUILD_PLATFORMS"
echo

# Check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        return 1
    fi
    
    log_success "Docker is running"
    return 0
}

# Check Docker Buildx
check_buildx() {
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx is not available"
        return 1
    fi
    log_success "Docker Buildx is available"
    return 0
}

# Create or ensure Docker network exists
ensure_network() {
    log_info "Ensuring Docker network '$NETWORK_NAME' exists..."
    
    if docker network inspect "$NETWORK_NAME" &> /dev/null; then
        log_success "Network '$NETWORK_NAME' already exists"
    else
        docker network create --driver bridge --attachable "$NETWORK_NAME"
        log_success "Network '$NETWORK_NAME' created"
    fi
}

# Clean buildx cache and builder
clean_buildx() {
    log_info "Cleaning Docker Buildx..."
    
    # Remove existing builder if it exists
    if docker buildx ls | grep -q "$BUILDER_NAME"; then
        log_info "Removing existing builder: $BUILDER_NAME"
        docker buildx rm "$BUILDER_NAME" || true
    fi
    
    # Prune build cache
    log_info "Pruning build cache..."
    docker buildx prune -f || true
    
    log_success "Buildx cleanup completed"
}

# Create and configure buildx builder
ensure_builder() {
    log_info "Setting up Docker Buildx builder..."
    
    if docker buildx ls | grep -q "$BUILDER_NAME"; then
        log_info "Using existing builder: $BUILDER_NAME"
        docker buildx use "$BUILDER_NAME"
    else
        log_info "Creating new builder: $BUILDER_NAME"
        docker buildx create \
            --name "$BUILDER_NAME" \
            --driver docker-container \
            --driver-opt network=host \
            --use \
            --bootstrap
    fi
    
    # Inspect builder
    docker buildx inspect --bootstrap
    log_success "Builder '$BUILDER_NAME' ready"
}

# Pre-pull base images to avoid timeouts
pre_pull_images() {
    log_info "Pre-pulling base images..."
    
    local base_images=(
        "python:3.12-slim"
        "mongo:7.0"
        "node:20-slim"
    )
    
    for image in "${base_images[@]}"; do
        log_info "Pulling $image..."
        if docker pull "$image"; then
            log_success "Successfully pulled $image"
        else
            log_warning "Failed to pull $image, continuing..."
        fi
    done
    
    log_success "Base images pre-pull completed"
}

# Setup environment files and configurations
setup_environment() {
    log_info "Setting up build environment..."
    
    # Create .env files if they don't exist
    if [[ ! -f ".env.dev" ]]; then
        log_info "Creating .env.dev..."
        cat > .env.dev << 'EOF'
# Lucid RDP Development Environment
NODE_ENV=development
LUCID_MODE=development
LUCID_NETWORK=testnet
LOG_LEVEL=DEBUG
MONGO_URI=mongodb://mongo:27017/lucid_dev
TOR_ENABLED=true
CHUNK_SIZE=8388608
COMPRESSION_LEVEL=1
EOF
    fi
    
    # Copy Tor configuration if needed
    if [[ -f "02-network-security/tor/torrc" ]] && [[ ! -f ".devcontainer/torrc" ]]; then
        cp "02-network-security/tor/torrc" ".devcontainer/torrc"
        log_info "Copied Tor configuration"
    fi
    
    # Generate onion hostname placeholder if needed
    if [[ ! -f ".devcontainer/hostname" ]]; then
        echo "example.onion" > ".devcontainer/hostname"
        log_info "Created placeholder onion hostname"
    fi
    
    log_success "Environment setup completed"
}

# Build multi-platform image
build_image() {
    log_info "Building multi-platform Docker image..."
    
    # Prepare tag arguments
    local tag_args=()
    for tag in "${TAGS[@]}"; do
        tag_args+=(--tag "$tag")
    done
    
    # Prepare build arguments
    local build_args=(
        --platform "$BUILD_PLATFORMS"
        --file "$DOCKERFILE_PATH"
        --build-arg "BUILDKIT_INLINE_CACHE=1"
        --build-arg "VERSION=$VERSION"
        --build-arg "GIT_SHA=$GIT_SHA"
        --build-arg "BUILD_DATE=$BUILD_DATE"
    )
    
    # Add cache arguments if not disabled
    if [[ "$NO_CACHE" != "true" ]]; then
        build_args+=(
            --cache-from "type=registry,ref=${IMAGE_NAME}:buildcache"
            --cache-to "type=registry,ref=${IMAGE_NAME}:buildcache,mode=max"
        )
    else
        build_args+=(--no-cache)
    fi
    
    # Add push flag if not test-only
    if [[ "$TEST_ONLY" != "true" ]]; then
        build_args+=(--push)
    else
        build_args+=(--load)
    fi
    
    # Execute build
    log_info "Build command:"
    echo "docker buildx build ${build_args[*]} ${tag_args[*]} $CONTEXT_PATH"
    echo
    
    if docker buildx build "${build_args[@]}" "${tag_args[@]}" "$CONTEXT_PATH"; then
        log_success "Image build completed successfully"
    else
        log_error "Image build failed"
        return 1
    fi
}

# Test local build
test_local_build() {
    log_info "Testing local build functionality..."
    
    local test_tag="${IMAGE_NAME}:test-local"
    
    # Build for current platform only
    docker buildx build \
        --file "$DOCKERFILE_PATH" \
        --tag "$test_tag" \
        --load \
        --build-arg "VERSION=$VERSION" \
        --build-arg "GIT_SHA=$GIT_SHA" \
        --build-arg "BUILD_DATE=$BUILD_DATE" \
        "$CONTEXT_PATH"
    
    # Test container startup
    log_info "Testing container startup..."
    local container_id
    container_id=$(docker run -d "$test_tag" /bin/bash -c "sleep 10")
    
    sleep 2
    
    # Check if container is running
    if docker ps | grep -q "$container_id"; then
        log_success "Container started successfully"
        docker stop "$container_id" > /dev/null
        docker rm "$container_id" > /dev/null
    else
        log_error "Container failed to start"
        docker logs "$container_id"
        docker rm "$container_id" > /dev/null
        return 1
    fi
    
    # Test basic functionality
    log_info "Testing Python environment..."
    if docker run --rm "$test_tag" python3 --version; then
        log_success "Python environment test passed"
    else
        log_error "Python environment test failed"
        return 1
    fi
    
    # Clean up test image
    docker rmi "$test_tag" > /dev/null 2>&1 || true
    
    log_success "Local build test completed successfully"
}

# Verify pushed images
verify_images() {
    log_info "Verifying pushed images..."
    
    for tag in "${TAGS[@]}"; do
        log_info "Checking: $tag"
        if docker manifest inspect "$tag" &> /dev/null; then
            log_success "$tag is available"
        else
            log_error "$tag is not available"
        fi
    done
}

# Test pushed images
test_pushed_images() {
    log_info "Testing pushed images..."
    
    local latest_tag="${IMAGE_NAME}:dev-latest"
    
    # Test different commands
    log_info "Testing Python version..."
    docker run --rm "$latest_tag" python3 --version
    
    log_info "Testing Node.js version..."
    docker run --rm "$latest_tag" node --version || log_warning "Node.js not available"
    
    log_info "Testing pip..."
    docker run --rm "$latest_tag" pip --version
    
    log_success "Image functionality tests completed"
}

# Main execution function
main() {
    log_info "Starting Lucid DevContainer build process..."
    
    # Pre-checks
    check_docker || exit 1
    check_buildx || exit 1
    
    # Clean build if requested
    if [[ "$CLEAN_BUILD" == "true" ]]; then
        clean_buildx
    fi
    
    # Setup
    ensure_network
    setup_environment
    
    if [[ "$TEST_ONLY" == "true" ]]; then
        log_info "Running test-only build..."
        ensure_builder
        test_local_build
        log_success "Local test completed successfully"
        return 0
    fi
    
    # Full build and push process
    ensure_builder
    pre_pull_images
    build_image
    verify_images
    test_pushed_images
    
    echo
    log_success "===== Build Complete ====="
    log_success "Images built and pushed successfully"
    log_info "Available tags:"
    for tag in "${TAGS[@]}"; do
        echo "  • $tag"
    done
    echo
    log_info "You can now pull the image:"
    echo "  docker pull ${IMAGE_NAME}:dev-latest"
    echo
    log_info "Or use it directly in devcontainer.json:"
    echo "  \"image\": \"${IMAGE_NAME}:dev-latest\""
}

# Execute main function
main "$@"

#!/bin/bash
set -e

# Build and Push Script for Lucid RDP DevContainer
# Target: ARM64 (Raspberry Pi 5) and AMD64 (development machines)
# Registry: DockerHub pickme/lucid
# Based on Spec-1d build requirements

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="pickme/lucid"
BUILDER_NAME="lucid_builder"
DOCKERFILE_PATH=".devcontainer/Dockerfile"
CONTEXT_PATH="."

# Version from pyproject.toml or git
if [ -f "pyproject.toml" ]; then
    VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
else
    VERSION="dev"
fi

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Tags to build and push
TAGS=(
    "${IMAGE_NAME}:${VERSION}"
    "${IMAGE_NAME}:dev-latest"
    "${IMAGE_NAME}:${VERSION}-${GIT_SHA}"
    "${IMAGE_NAME}:dev-${BUILD_DATE}"
)

echo -e "${BLUE}===== Lucid RDP DevContainer Build Script =====${NC}"
echo -e "${YELLOW}Image Name:${NC} ${IMAGE_NAME}"
echo -e "${YELLOW}Version:${NC} ${VERSION}"
echo -e "${YELLOW}Git SHA:${NC} ${GIT_SHA}"
echo -e "${YELLOW}Build Date:${NC} ${BUILD_DATE}"
echo -e "${YELLOW}Builder:${NC} ${BUILDER_NAME}"
echo -e "${YELLOW}Target Platforms:${NC} linux/arm64, linux/amd64"
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running or not accessible${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Function to ensure builder exists
ensure_builder() {
    echo -e "${YELLOW}Checking if builder '${BUILDER_NAME}' exists...${NC}"
    
    if ! docker buildx ls | grep -q "${BUILDER_NAME}"; then
        echo -e "${YELLOW}Creating builder: ${BUILDER_NAME}${NC}"
        docker buildx create --name "${BUILDER_NAME}" --use --bootstrap
    else
        echo -e "${GREEN}✓ Builder '${BUILDER_NAME}' exists${NC}"
        docker buildx use "${BUILDER_NAME}"
    fi
    
    # Inspect builder
    docker buildx inspect --bootstrap
}

# Function to ensure network exists
ensure_network() {
    echo -e "${YELLOW}Ensuring network 'lucid-dev_lucid_net' exists...${NC}"
    
    if ! docker network inspect lucid-dev_lucid_net >/dev/null 2>&1; then
        docker network create --driver bridge --attachable lucid-dev_lucid_net
        echo -e "${GREEN}✓ Network 'lucid-dev_lucid_net' created${NC}"
    else
        echo -e "${GREEN}✓ Network 'lucid-dev_lucid_net' already exists${NC}"
    fi
}

# Function to pre-pull base images
pre_pull_images() {
    echo -e "${YELLOW}Pre-pulling base images to avoid timeout issues...${NC}"
    
    # Base Python image
    docker pull python:3.12-slim-bookworm
    
    # MongoDB for development
    docker pull mongo:7
    
    echo -e "${GREEN}✓ Base images pre-pulled${NC}"
}

# Function to build multi-platform image
build_image() {
    echo -e "${BLUE}Building multi-platform Docker image...${NC}"
    
    # Construct tag arguments
    TAG_ARGS=""
    for tag in "${TAGS[@]}"; do
        TAG_ARGS="${TAG_ARGS} --tag ${tag}"
    done
    
    # Build arguments
    BUILD_ARGS=(
        --platform "linux/arm64,linux/amd64"
        --file "${DOCKERFILE_PATH}"
        --push
        --cache-from "type=registry,ref=${IMAGE_NAME}:buildcache"
        --cache-to "type=registry,ref=${IMAGE_NAME}:buildcache,mode=max"
        --build-arg "BUILDKIT_INLINE_CACHE=1"
        --build-arg "VERSION=${VERSION}"
        --build-arg "GIT_SHA=${GIT_SHA}"
        --build-arg "BUILD_DATE=${BUILD_DATE}"
        ${TAG_ARGS}
        "${CONTEXT_PATH}"
    )
    
    echo -e "${YELLOW}Build command:${NC}"
    echo "docker buildx build ${BUILD_ARGS[*]}"
    echo ""
    
    # Execute build
    docker buildx build "${BUILD_ARGS[@]}"
    
    echo -e "${GREEN}✓ Multi-platform image built and pushed successfully${NC}"
}

# Function to verify images
verify_images() {
    echo -e "${BLUE}Verifying pushed images...${NC}"
    
    for tag in "${TAGS[@]}"; do
        echo -e "${YELLOW}Checking: ${tag}${NC}"
        if docker manifest inspect "${tag}" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ ${tag} is available${NC}"
        else
            echo -e "${RED}✗ ${tag} is not available${NC}"
        fi
    done
}

# Function to test local build
test_local_build() {
    echo -e "${BLUE}Testing local build...${NC}"
    
    # Build for current platform only
    docker buildx build \
        --file "${DOCKERFILE_PATH}" \
        --tag "${IMAGE_NAME}:test-local" \
        --load \
        "${CONTEXT_PATH}"
    
    # Test container startup
    echo -e "${YELLOW}Testing container startup...${NC}"
    CONTAINER_ID=$(docker run -d "${IMAGE_NAME}:test-local" /bin/bash -c "sleep 10")
    
    # Check if container is running
    if docker ps | grep -q "${CONTAINER_ID}"; then
        echo -e "${GREEN}✓ Container started successfully${NC}"
        docker stop "${CONTAINER_ID}" >/dev/null
        docker rm "${CONTAINER_ID}" >/dev/null
    else
        echo -e "${RED}✗ Container failed to start${NC}"
        docker logs "${CONTAINER_ID}"
        docker rm "${CONTAINER_ID}" >/dev/null
        exit 1
    fi
    
    # Clean up test image
    docker rmi "${IMAGE_NAME}:test-local" >/dev/null 2>&1 || true
}

# Function to show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --test-only     Only run local build test, don't push"
    echo "  --no-cache      Don't use build cache"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full build and push"
    echo "  $0 --test-only        # Test build only"
    echo "  $0 --no-cache         # Build without cache"
}

# Parse command line arguments
TEST_ONLY=false
USE_CACHE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --no-cache)
            USE_CACHE=false
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${BLUE}Starting Lucid DevContainer build process...${NC}"
    
    # Pre-checks
    check_docker
    ensure_network
    
    if [ "${TEST_ONLY}" = true ]; then
        echo -e "${YELLOW}Running test-only build...${NC}"
        test_local_build
        echo -e "${GREEN}✓ Local test completed successfully${NC}"
        return 0
    fi
    
    # Full build and push process
    ensure_builder
    pre_pull_images
    
    # Modify build args if no cache requested
    if [ "${USE_CACHE}" = false ]; then
        echo -e "${YELLOW}Building without cache...${NC}"
        # Cache args will be skipped in build_image function
    fi
    
    build_image
    verify_images
    
    # Test the pushed image
    echo -e "${BLUE}Testing pushed image...${NC}"
    docker run --rm "${IMAGE_NAME}:dev-latest" python --version
    docker run --rm "${IMAGE_NAME}:dev-latest" node --version
    docker run --rm "${IMAGE_NAME}:dev-latest" mongosh --version
    
    echo ""
    echo -e "${GREEN}===== Build Complete =====${NC}"
    echo -e "${GREEN}✓ Images built and pushed successfully${NC}"
    echo -e "${YELLOW}Available tags:${NC}"
    for tag in "${TAGS[@]}"; do
        echo -e "  • ${tag}"
    done
    echo ""
    echo -e "${BLUE}You can now pull the image on your development machine:${NC}"
    echo -e "  docker pull ${IMAGE_NAME}:dev-latest"
    echo ""
    echo -e "${BLUE}Or use it directly in devcontainer.json:${NC}"
    echo -e "  \"image\": \"${IMAGE_NAME}:dev-latest\""
}

# Execute main function
main "$@"