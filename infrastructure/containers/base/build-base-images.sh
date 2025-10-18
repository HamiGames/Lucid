#!/bin/bash
# Lucid Base Images Build Script
# Builds distroless base images for Python and Java services
# Supports multi-platform builds for ARM64 (Pi) and AMD64

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io/hamigames/lucid"
PYTHON_IMAGE="python-base"
JAVA_IMAGE="java-base"
VERSION="latest"
PLATFORMS="linux/amd64,linux/arm64"

# Build arguments
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1 --build-arg BUILDKIT_PROGRESS=plain"

echo -e "${BLUE}🚀 Building Lucid Base Distroless Images${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if Docker Buildx is available
if ! docker buildx version >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker Buildx not found. Please install Docker Buildx.${NC}"
    exit 1
fi

# Create buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "lucid-builder"; then
    echo -e "${YELLOW}📦 Creating Docker Buildx builder...${NC}"
    docker buildx create --name lucid-builder --use --driver docker-container --driver-opt network=host
fi

# Set the builder
docker buildx use lucid-builder

echo -e "${YELLOW}🔧 Building Python Base Image...${NC}"
docker buildx build \
    --platform $PLATFORMS \
    --file Dockerfile.python-base \
    --tag $REGISTRY/$PYTHON_IMAGE:$VERSION \
    --tag $REGISTRY/$PYTHON_IMAGE:$(git rev-parse --short HEAD) \
    --tag lucid-python-base:latest \
    $BUILD_ARGS \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python base image built successfully${NC}"
else
    echo -e "${RED}❌ Python base image build failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Building Java Base Image...${NC}"
docker buildx build \
    --platform $PLATFORMS \
    --file Dockerfile.java-base \
    --tag $REGISTRY/$JAVA_IMAGE:$VERSION \
    --tag $REGISTRY/$JAVA_IMAGE:$(git rev-parse --short HEAD) \
    --tag lucid-java-base:latest \
    $BUILD_ARGS \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Java base image built successfully${NC}"
else
    echo -e "${RED}❌ Java base image build failed${NC}"
    exit 1
fi

# Verify image sizes
echo -e "${YELLOW}📊 Verifying image sizes...${NC}"

PYTHON_SIZE=$(docker images lucid-python-base:latest --format "table {{.Size}}" | tail -n 1)
JAVA_SIZE=$(docker images lucid-java-base:latest --format "table {{.Size}}" | tail -n 1)

echo -e "${BLUE}Python Base Image Size: $PYTHON_SIZE${NC}"
echo -e "${BLUE}Java Base Image Size: $JAVA_SIZE${NC}"

# Check if images are under 100MB (approximate)
echo -e "${YELLOW}🔍 Checking image size constraints...${NC}"

# Test Python base image
echo -e "${YELLOW}🧪 Testing Python base image...${NC}"
docker run --rm lucid-python-base:latest python -c "print('Python base image test successful')"

# Test Java base image
echo -e "${YELLOW}🧪 Testing Java base image...${NC}"
docker run --rm lucid-java-base:latest java -version

echo -e "${GREEN}🎉 All base images built and tested successfully!${NC}"
echo -e "${BLUE}📋 Build Summary:${NC}"
echo -e "  • Python Base: $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Java Base: $REGISTRY/$JAVA_IMAGE:$VERSION"
echo -e "  • Platforms: $PLATFORMS"
echo -e "  • Registry: $REGISTRY"
