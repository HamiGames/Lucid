#!/bin/bash
# Test build script for Lucid Session Docker images
# Tests building a single image to verify configuration

set -e

# Configuration
TEST_IMAGE="pickme/lucid-session-pipeline"
TEST_TAG="test-arm64"
TEST_DOCKERFILE="sessions/Dockerfile.pipeline"

echo "=========================================="
echo "Testing Lucid Session Docker Build"
echo "=========================================="
echo "Test Image: ${TEST_IMAGE}:${TEST_TAG}"
echo "Dockerfile: ${TEST_DOCKERFILE}"
echo "Platform: linux/arm64"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "✗ Docker is not running or not accessible"
    exit 1
fi

echo "✓ Docker is running"

# Check if buildx is available
if ! docker buildx version >/dev/null 2>&1; then
    echo "⚠ Docker buildx not available, using standard build"
    BUILD_CMD="docker build"
else
    echo "✓ Docker buildx is available"
    BUILD_CMD="docker buildx build"
fi

# Check if Dockerfile exists
if [[ ! -f "$TEST_DOCKERFILE" ]]; then
    echo "✗ Dockerfile not found: $TEST_DOCKERFILE"
    exit 1
fi

echo "✓ Dockerfile exists: $TEST_DOCKERFILE"

# Test build
echo ""
echo "Starting test build..."
echo "This may take several minutes..."

# Build the test image
if $BUILD_CMD \
    --platform linux/arm64 \
    --tag "${TEST_IMAGE}:${TEST_TAG}" \
    --file "${TEST_DOCKERFILE}" \
    . > build-test.log 2>&1; then
    
    echo "✓ Test build completed successfully!"
    
    # Check image details
    echo ""
    echo "Image details:"
    docker images "${TEST_IMAGE}:${TEST_TAG}"
    
    # Check platform
    platform=$(docker image inspect "${TEST_IMAGE}:${TEST_TAG}" --format '{{.Architecture}}')
    echo "Architecture: $platform"
    
    # Check size
    size=$(docker image inspect "${TEST_IMAGE}:${TEST_TAG}" --format '{{.Size}}')
    size_mb=$((size / 1024 / 1024))
    echo "Size: ${size_mb}MB"
    
    # Clean up test image
    echo ""
    echo "Cleaning up test image..."
    docker rmi "${TEST_IMAGE}:${TEST_TAG}" >/dev/null 2>&1 || true
    
    echo "✓ Test build successful - configuration is correct"
    echo "✓ Ready to build all session images"
    
else
    echo "✗ Test build failed!"
    echo ""
    echo "Build log:"
    cat build-test.log
    echo ""
    echo "Please check the build log above for errors"
    exit 1
fi

# Clean up log file
rm -f build-test.log

echo ""
echo "=========================================="
echo "Test Build Complete"
echo "=========================================="
echo "✓ Docker configuration is working"
echo "✓ ARM64 builds are supported"
echo "✓ Ready to build all session images"
echo ""
echo "Next steps:"
echo "1. Run: ./build/scripts/build-all-session-images.sh"
echo "2. Or run individual build scripts as needed"
