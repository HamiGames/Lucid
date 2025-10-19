#!/bin/bash
# Build script for Lucid Session API Docker image
# Target: pickme/lucid-session-api:latest-arm64
# Port: 8087

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
IMAGE_NAME="pickme/lucid-session-api"
TAG="latest-arm64"
DOCKERFILE="sessions/Dockerfile.api"
BUILD_CONTEXT="."
SERVICE_PORT="8087"

print_status "Building Lucid Session API Docker image..."
print_status "Image: ${IMAGE_NAME}:${TAG}"
print_status "Dockerfile: ${DOCKERFILE}"
print_status "Context: ${BUILD_CONTEXT}"
print_status "Port: ${SERVICE_PORT}"

# Validate required files exist
if [[ ! -f "$DOCKERFILE" ]]; then
    print_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

if [[ ! -d "$BUILD_CONTEXT" ]]; then
    print_error "Build context not found: $BUILD_CONTEXT"
    exit 1
fi

# Check if required source directories exist
if [[ ! -d "sessions/api" ]]; then
    print_error "Source directory not found: sessions/api"
    exit 1
fi

if [[ ! -d "sessions/core" ]]; then
    print_error "Core directory not found: sessions/core"
    exit 1
fi

# Build for ARM64 platform
print_status "Starting Docker build for ARM64 platform..."
if docker build \
    --platform linux/arm64 \
    --tag "${IMAGE_NAME}:${TAG}" \
    --file "${DOCKERFILE}" \
    "${BUILD_CONTEXT}"; then
    print_success "Build completed successfully!"
    print_success "Image: ${IMAGE_NAME}:${TAG}"
    
    # Display image information
    print_status "Image details:"
    docker images "${IMAGE_NAME}:${TAG}"
    
    # Show image size
    IMAGE_SIZE=$(docker images --format "table {{.Size}}" "${IMAGE_NAME}:${TAG}" | tail -n 1)
    print_status "Image size: $IMAGE_SIZE"
    
    print_success "Session API service ready on port $SERVICE_PORT"
    print_success "Build script completed: build-session-api.sh"
else
    print_error "Build failed for ${IMAGE_NAME}:${TAG}"
    exit 1
fi
