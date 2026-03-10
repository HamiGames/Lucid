# Lucid Electron-GUI Distroless Build Script
# Builds all 3 Electron-GUI distroless packages for Raspberry Pi (linux/arm64)
# Date: 2025-01-24

#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="pickme"
PROJECT="lucid-electron-gui"
TAG="latest-arm64"
PLATFORM="linux/arm64"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Lucid Electron-GUI Distroless Build  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to build and push image
build_and_push() {
    local profile=$1
    local dockerfile=$2
    local image_name="${REGISTRY}/${PROJECT}-${profile}:${TAG}"
    
    echo -e "${YELLOW}Building ${profile} distroless package...${NC}"
    echo "Image: ${image_name}"
    echo "Dockerfile: ${dockerfile}"
    echo ""
    
    # Build the image
    docker build \
        --platform ${PLATFORM} \
        --file ${dockerfile} \
        --tag ${image_name} \
        --tag ${REGISTRY}/${PROJECT}-${profile}:latest \
        .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully built ${profile} package${NC}"
        
        # Push to registry (uncomment if needed)
        # echo -e "${YELLOW}Pushing ${profile} image to registry...${NC}"
        # docker push ${image_name}
        # docker push ${REGISTRY}/${PROJECT}-${profile}:latest
        
        echo -e "${GREEN}✓ ${profile} package ready${NC}"
    else
        echo -e "${RED}✗ Failed to build ${profile} package${NC}"
        exit 1
    fi
    
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: package.json not found. Please run this script from the electron-gui directory${NC}"
    exit 1
fi

echo -e "${BLUE}Building distroless packages for Raspberry Pi (linux/arm64)${NC}"
echo "Registry: ${REGISTRY}"
echo "Project: ${PROJECT}"
echo "Tag: ${TAG}"
echo "Platform: ${PLATFORM}"
echo ""

# Build Admin package
build_and_push "admin" "distroless/Dockerfile.admin"

# Build User package
build_and_push "user" "distroless/Dockerfile.user"

# Build Node Operator package
build_and_push "node" "distroless/Dockerfile.node"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All distroless packages built successfully!  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Display built images
echo -e "${BLUE}Built Images:${NC}"
docker images | grep "${REGISTRY}/${PROJECT}" | head -6

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Create the lucid-pi-network:"
echo "   docker network create lucid-pi-network --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1"
echo ""
echo "2. Deploy with docker-compose:"
echo "   docker-compose -f distroless/docker-compose.electron-gui.yml up -d"
echo ""
echo "3. Check service status:"
echo "   docker-compose -f distroless/docker-compose.electron-gui.yml ps"
echo ""
echo -e "${GREEN}Electron-GUI distroless packages are ready for deployment!${NC}"
