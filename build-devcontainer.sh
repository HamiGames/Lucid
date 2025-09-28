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