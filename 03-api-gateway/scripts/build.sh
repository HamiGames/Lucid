#!/bin/bash
# Build script for API Gateway
# File: 03-api-gateway/scripts/build.sh
# Build Host: Windows 11 console
# Target Host: Raspberry Pi

set -e

echo "=========================================="
echo "Building Lucid API Gateway"
echo "=========================================="

# Set build arguments
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-1.0.0}
BUILDPLATFORM=${BUILDPLATFORM:-linux/amd64}

echo "Build Date: $BUILD_DATE"
echo "Version: $VERSION"
echo "Platform: $BUILDPLATFORM"
echo ""

# Navigate to project directory
cd "$(dirname "$0")/.."

# Build Docker image
echo "Building distroless container..."
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILDPLATFORM="$BUILDPLATFORM" \
    --tag lucid-api-gateway:latest \
    --tag lucid-api-gateway:$VERSION \
    .

# Verify image
echo ""
echo "Verifying distroless container..."
docker run --rm lucid-api-gateway:latest python -c "print('Container is working')"

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "=========================================="
echo "Image: lucid-api-gateway:$VERSION"
echo "Size: $(docker images lucid-api-gateway:latest --format '{{.Size}}')"
echo ""

