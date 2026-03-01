#!/bin/bash
# RDP/scripts/build-on-pi.sh
# Build script optimized for Raspberry Pi console
# Handles network retries and provides clear error messages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE="$PROJECT_ROOT/RDP/Dockerfile.xrdp"
IMAGE_NAME="pickme/lucid-rdp-xrdp:latest-arm64"

echo "🔨 Building RDP XRDP container for Raspberry Pi"
echo "================================================"
echo "Dockerfile: $DOCKERFILE"
echo "Image: $IMAGE_NAME"
echo "Platform: linux/arm64"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Start Docker with: sudo systemctl start docker"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo "❌ Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

# Pre-pull base image to avoid timeout issues
echo "📥 Pre-pulling base image (python:3.11-slim-bookworm)..."
if ! docker pull --platform linux/arm64 python:3.11-slim-bookworm; then
    echo "⚠️  Warning: Failed to pre-pull base image, continuing anyway..."
    echo "   Build will attempt to pull during build process"
fi

echo ""
echo "🔨 Starting build process..."
echo "   This may take several minutes on Pi hardware..."
echo ""

# Build with retry logic
cd "$PROJECT_ROOT"

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker build \
        --platform linux/arm64 \
        -f "$DOCKERFILE" \
        -t "$IMAGE_NAME" \
        --build-arg TARGETPLATFORM=linux/arm64 \
        --build-arg BUILDPLATFORM=linux/arm64 \
        --no-cache \
        .; then
        echo ""
        echo "✅ Build successful!"
        echo "   Image: $IMAGE_NAME"
        echo ""
        echo "📋 To verify the image:"
        echo "   docker images | grep lucid-rdp-xrdp"
        echo ""
        echo "🚀 To run the container:"
        echo "   docker run --rm -it $IMAGE_NAME python3 --version"
        exit 0
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo ""
            echo "⚠️  Build failed, retrying ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 5
        else
            echo ""
            echo "❌ Build failed after $MAX_RETRIES attempts"
            echo ""
            echo "🔍 Troubleshooting:"
            echo "   1. Check network connectivity: ping 8.8.8.8"
            echo "   2. Check Docker Hub access: docker pull python:3.11-slim-bookworm"
            echo "   3. Check disk space: df -h"
            echo "   4. Check Docker logs: journalctl -u docker.service"
            exit 1
        fi
    fi
done

