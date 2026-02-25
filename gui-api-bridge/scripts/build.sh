#!/bin/bash
# Build script for GUI API Bridge
# File: gui-api-bridge/scripts/build.sh
# Build Host: Windows 11 console
# Target Host: Raspberry Pi
# No hardcoded values - all from environment or defaults

set -e

echo "=========================================="
echo "Building Lucid GUI API Bridge"
echo "=========================================="

# Set build arguments (no hardcoded values)
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-1.0.0}
BUILDPLATFORM=${BUILDPLATFORM:-linux/amd64}
TARGETPLATFORM=${TARGETPLATFORM:-linux/arm64}

echo "Build Date: $BUILD_DATE"
echo "Version: $VERSION"
echo "Build Platform: $BUILDPLATFORM"
echo "Target Platform: $TARGETPLATFORM"
echo ""

# Navigate to project directory (script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Script Dir: $SCRIPT_DIR"
echo "Project Dir: $PROJECT_DIR"
echo "Workspace Dir: $WORKSPACE_DIR"
echo ""

# Navigate to workspace root (where Dockerfile is)
cd "$WORKSPACE_DIR"

# Verify Dockerfile exists
DOCKERFILE="${PROJECT_DIR}/Dockerfile.gui-api-bridge"
if [ ! -f "$DOCKERFILE" ]; then
    echo "Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

echo "Using Dockerfile: $DOCKERFILE"
echo ""

# Build Docker image
echo "Building distroless container..."
docker build \
    --file "$DOCKERFILE" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILDPLATFORM="$BUILDPLATFORM" \
    --build-arg TARGETPLATFORM="$TARGETPLATFORM" \
    --tag lucid-gui-api-bridge:latest \
    --tag lucid-gui-api-bridge:$VERSION \
    --tag lucid-gui-api-bridge:latest-arm64 \
    "$WORKSPACE_DIR"

# Verify image was created
if ! docker images lucid-gui-api-bridge:latest --quiet > /dev/null 2>&1; then
    echo "Error: Docker image was not created successfully"
    exit 1
fi

# Verify image is functional (distroless check)
echo ""
echo "Verifying distroless container..."
docker run --rm lucid-gui-api-bridge:latest python3 -c "import fastapi, uvicorn, pydantic; print('✅ Container verification passed')" || {
    echo "Error: Container verification failed"
    exit 1
}

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "=========================================="
IMAGE_ID=$(docker images lucid-gui-api-bridge:latest --format '{{.ID}}')
IMAGE_SIZE=$(docker images lucid-gui-api-bridge:latest --format '{{.Size}}')
echo "Image: lucid-gui-api-bridge:$VERSION"
echo "Image ID: $IMAGE_ID"
echo "Size: $IMAGE_SIZE"
echo ""
echo "To run the container:"
echo "  docker run -p 8102:8102 lucid-gui-api-bridge:latest"
echo ""
