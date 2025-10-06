#!/bin/bash
# LUCID Layer 2 Build Script - Distroless Images
# Builds all Layer 2 Service Integration components with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

set -euo pipefail

# Configuration
REGISTRY="${REGISTRY:-pickme}"
TAG="${TAG:-latest}"
PUSH="${PUSH:-false}"
NO_CACHE="${NO_CACHE:-false}"

# Build arguments
BUILD_ARGS=(
    "--platform" "linux/amd64,linux/arm64"
    "--tag" "${REGISTRY}/lucid:rdp-server-manager-${TAG}"
    "--tag" "${REGISTRY}/lucid:rdp-server-manager"
    "--file" "RDP/server/Dockerfile.server-manager"
    "."
)

if [ "$NO_CACHE" = "true" ]; then
    BUILD_ARGS+=("--no-cache")
fi

if [ "$PUSH" = "true" ]; then
    BUILD_ARGS+=("--push")
fi

echo "=== LUCID Layer 2 Distroless Build ==="
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Push: $PUSH"
echo "No Cache: $NO_CACHE"
echo ""

# Build RDP Server Manager
echo "Building RDP Server Manager..."
if docker buildx build "${BUILD_ARGS[@]}"; then
    echo "✅ RDP Server Manager built successfully"
else
    echo "❌ RDP Server Manager build failed"
    exit 1
fi

# Build xrdp Integration
echo "Building xrdp Integration..."
BUILD_ARGS[3]="${REGISTRY}/lucid:xrdp-integration-${TAG}"
BUILD_ARGS[4]="${REGISTRY}/lucid:xrdp-integration"
BUILD_ARGS[6]="RDP/server/Dockerfile.xrdp-integration"

if docker buildx build "${BUILD_ARGS[@]}"; then
    echo "✅ xrdp Integration built successfully"
else
    echo "❌ xrdp Integration build failed"
    exit 1
fi

# Build Contract Deployment
echo "Building Contract Deployment..."
BUILD_ARGS[3]="${REGISTRY}/lucid:contract-deployment-${TAG}"
BUILD_ARGS[4]="${REGISTRY}/lucid:contract-deployment"
BUILD_ARGS[6]="blockchain/deployment/Dockerfile.contract-deployment"

if docker buildx build "${BUILD_ARGS[@]}"; then
    echo "✅ Contract Deployment built successfully"
else
    echo "❌ Contract Deployment build failed"
    exit 1
fi

echo ""
echo "=== Layer 2 Build Complete ==="
echo "Built images:"
echo "  - ${REGISTRY}/lucid:rdp-server-manager"
echo "  - ${REGISTRY}/lucid:xrdp-integration"
echo "  - ${REGISTRY}/lucid:contract-deployment"

if [ "$PUSH" = "true" ]; then
    echo ""
    echo "All images pushed to registry"
else
    echo ""
    echo "To push images, set PUSH=true"
fi
