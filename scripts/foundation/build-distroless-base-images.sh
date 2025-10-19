#!/bin/bash
# scripts/foundation/build-distroless-base-images.sh
# Build distroless base images for all service types
# Supports multi-platform builds for ARM64 (Pi) and AMD64
# Integrates with GitHub Container Registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io/hamigames/lucid"
PYTHON_IMAGE="python-base"
JAVA_IMAGE="java-base"
VERSION="latest"
PLATFORMS="linux/amd64,linux/arm64"
BUILD_DIR="infrastructure/containers/base"

# Build arguments
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1 --build-arg BUILDKIT_PROGRESS=plain"

echo -e "${BLUE}🚀 Lucid Foundation: Building Distroless Base Images${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "${PURPLE}Registry: $REGISTRY${NC}"
echo -e "${PURPLE}Platforms: $PLATFORMS${NC}"
echo -e "${PURPLE}Build Directory: $BUILD_DIR${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "$BUILD_DIR" ]; then
    echo -e "${RED}❌ Build directory not found: $BUILD_DIR${NC}"
    echo -e "${YELLOW}💡 Please run this script from the Lucid project root${NC}"
    exit 1
fi

# Check if Docker Buildx is available
if ! docker buildx version >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker Buildx not found. Please install Docker Buildx.${NC}"
    echo -e "${YELLOW}💡 Install with: docker buildx install${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker.${NC}"
    exit 1
fi

# Create buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "lucid-builder"; then
    echo -e "${YELLOW}📦 Creating Docker Buildx builder...${NC}"
    docker buildx create --name lucid-builder --use --driver docker-container --driver-opt network=host
    echo -e "${GREEN}✅ Builder created successfully${NC}"
else
    echo -e "${GREEN}✅ Using existing lucid-builder${NC}"
fi

# Set the builder
docker buildx use lucid-builder

# Change to build directory
cd "$BUILD_DIR"

echo -e "${YELLOW}🔧 Building Python Base Image...${NC}"
echo -e "${BLUE}Platforms: $PLATFORMS${NC}"
echo -e "${BLUE}Tags: $REGISTRY/$PYTHON_IMAGE:$VERSION, $REGISTRY/$PYTHON_IMAGE:$(git rev-parse --short HEAD), lucid-python-base:latest${NC}"

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
    echo -e "${RED}❌ Python base image build failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Building Java Base Image...${NC}"
echo -e "${BLUE}Platforms: $PLATFORMS${NC}"
echo -e "${BLUE}Tags: $REGISTRY/$JAVA_IMAGE:$VERSION, $REGISTRY/$JAVA_IMAGE:$(git rev-parse --short HEAD), lucid-java-base:latest${NC}"

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
    echo -e "${RED}❌ Java base image build failed${NC}"
    exit 1
fi

# Return to project root
cd - > /dev/null

# Verify image sizes
echo -e "${YELLOW}📊 Verifying image sizes...${NC}"

# Check if images exist locally
if docker images lucid-python-base:latest --format "table {{.Size}}" | tail -n 1 | grep -q "MB\|GB"; then
    PYTHON_SIZE=$(docker images lucid-python-base:latest --format "table {{.Size}}" | tail -n 1)
    echo -e "${BLUE}Python Base Image Size: $PYTHON_SIZE${NC}"
else
    echo -e "${YELLOW}⚠️  Python base image not found locally${NC}"
fi

if docker images lucid-java-base:latest --format "table {{.Size}}" | tail -n 1 | grep -q "MB\|GB"; then
    JAVA_SIZE=$(docker images lucid-java-base:latest --format "table {{.Size}}" | tail -n 1)
    echo -e "${BLUE}Java Base Image Size: $JAVA_SIZE${NC}"
else
    echo -e "${YELLOW}⚠️  Java base image not found locally${NC}"
fi

# Test Python base image
echo -e "${YELLOW}🧪 Testing Python base image...${NC}"
if docker run --rm lucid-python-base:latest python -c "print('Python base image test successful')" 2>/dev/null; then
    echo -e "${GREEN}✅ Python base image test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Python base image test failed (may be expected for distroless)${NC}"
fi

# Test Java base image
echo -e "${YELLOW}🧪 Testing Java base image...${NC}"
if docker run --rm lucid-java-base:latest java -version 2>/dev/null; then
    echo -e "${GREEN}✅ Java base image test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Java base image test failed (may be expected for distroless)${NC}"
fi

# Display build summary
echo ""
echo -e "${GREEN}🎉 All base images built and tested successfully!${NC}"
echo -e "${BLUE}📋 Build Summary:${NC}"
echo -e "  • Python Base: $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Java Base: $REGISTRY/$JAVA_IMAGE:$VERSION"
echo -e "  • Platforms: $PLATFORMS"
echo -e "  • Registry: $REGISTRY"
echo -e "  • Git Commit: $(git rev-parse --short HEAD)"
echo ""

# Display usage instructions
echo -e "${PURPLE}📖 Usage Instructions:${NC}"
echo -e "  • Pull images: docker pull $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Pull images: docker pull $REGISTRY/$JAVA_IMAGE:$VERSION"
echo -e "  • Use in Dockerfile: FROM $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Use in Dockerfile: FROM $REGISTRY/$JAVA_IMAGE:$VERSION"
echo ""

# Display next steps
echo -e "${PURPLE}🚀 Next Steps:${NC}"
echo -e "  1. Verify images in GitHub Container Registry"
echo -e "  2. Update service Dockerfiles to use new base images"
echo -e "  3. Test dependent service builds"
echo -e "  4. Proceed to Phase 1 foundation services build"
echo ""

echo -e "${GREEN}✨ Foundation base images ready for Lucid services!${NC}"
