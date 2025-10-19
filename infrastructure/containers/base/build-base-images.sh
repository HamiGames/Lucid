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

# Configuration (Step 4: Distroless Base Image Preparation)
REGISTRY="pickme/lucid-base"
PYTHON_IMAGE="python-distroless-arm64"
JAVA_IMAGE="java-distroless-arm64"
VERSION="latest"
PLATFORMS="linux/arm64"

# Build arguments
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1 --build-arg BUILDKIT_PROGRESS=plain"

echo -e "${BLUE}🚀 Step 4: Building Lucid Base Distroless Images for Pi Deployment${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}Registry: $REGISTRY${NC}"
echo -e "${BLUE}Platform: $PLATFORMS (ARM64 Raspberry Pi)${NC}"

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
    echo -e "${GREEN}✅ Python base image built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Python base image build/push failed${NC}"
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
    echo -e "${GREEN}✅ Java base image built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Java base image build/push failed${NC}"
    exit 1
fi

# Verify images are available in registry
echo -e "${YELLOW}📊 Verifying images in Docker Hub registry...${NC}"

echo -e "${BLUE}Python Base Image: $REGISTRY/$PYTHON_IMAGE:$VERSION${NC}"
echo -e "${BLUE}Java Base Image: $REGISTRY/$JAVA_IMAGE:$VERSION${NC}"

# Verify registry access
echo -e "${YELLOW}🔍 Verifying registry access...${NC}"
docker pull $REGISTRY/$PYTHON_IMAGE:$VERSION
docker pull $REGISTRY/$JAVA_IMAGE:$VERSION

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Registry verification successful - images available for dependent builds${NC}"
else
    echo -e "${RED}❌ Registry verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 All base images built and tested successfully!${NC}"
echo -e "${BLUE}📋 Build Summary:${NC}"
echo -e "  • Python Base: $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Java Base: $REGISTRY/$JAVA_IMAGE:$VERSION"
echo -e "  • Platforms: $PLATFORMS"
echo -e "  • Registry: $REGISTRY"
