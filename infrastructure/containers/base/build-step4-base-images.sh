#!/bin/bash
# Step 4: Distroless Base Image Preparation
# File: /app/configs/base/build-step4-base-images.sh
# x-lucid-file-path: /app/configs/base/build-step4-base-images.sh
# x-lucid-file-directory: /app/configs/base
# x-lucid-file-type: shell
# Build foundation distroless base images for all service types
# Raspberry Pi ARM64 deployment optimized

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Step 4: Distroless Base Image Preparation${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Target: Raspberry Pi ARM64 deployment${NC}"
echo -e "${BLUE}Registry: pickme/lucid-base${NC}"

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

echo -e "${YELLOW}🔧 Building Python distroless base image...${NC}"
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.python-base \
  --push .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python distroless base image built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Python distroless base image build/push failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Building Java distroless base image...${NC}"
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:java-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.java-base \
  --push .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Java distroless base image built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Java distroless base image build/push failed${NC}"
    exit 1
fi

# Verify base images are available for dependent builds
echo -e "${YELLOW}🔍 Verifying base images availability...${NC}"

echo -e "${BLUE}Testing Python base image pull...${NC}"
docker pull pickme/lucid-base:python-distroless-arm64

echo -e "${BLUE}Testing Java base image pull...${NC}"
docker pull pickme/lucid-base:java-distroless-arm64

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Base images verification successful - available for dependent builds${NC}"
else
    echo -e "${RED}❌ Base images verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Step 4 Complete: Distroless Base Image Preparation${NC}"
echo -e "${BLUE}📋 Build Summary:${NC}"
echo -e "  • Python Base: pickme/lucid-base:python-distroless-arm64"
echo -e "  • Java Base: pickme/lucid-base:java-distroless-arm64"
echo -e "  • Platform: linux/arm64 (Raspberry Pi optimized)"
echo -e "  • Registry: Docker Hub (pickme/lucid-base)"
echo -e ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo -e "  • Base images are now available for dependent builds"
echo -e "  • Proceed to Phase 1: Foundation Services Build"
echo -e "  • All future containers will use these distroless bases"
