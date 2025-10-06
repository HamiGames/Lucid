#!/bin/bash
# LUCID Layer 2 Simple Build Script
# Builds Layer 2 components with standard Docker images
# Multi-platform build for ARM64 Pi and AMD64 development

set -euo pipefail

# Configuration
REGISTRY="${REGISTRY:-pickme}"
TAG="${TAG:-latest}"
PUSH="${PUSH:-false}"

echo "=== LUCID Layer 2 Simple Build ==="
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Push: $PUSH"
echo ""

# Build RDP Server Manager
echo "Building RDP Server Manager..."
if docker build -t "${REGISTRY}/lucid:rdp-server-manager-${TAG}" -f RDP/server/Dockerfile.server-manager.simple .; then
    echo "✅ RDP Server Manager built successfully"
    docker tag "${REGISTRY}/lucid:rdp-server-manager-${TAG}" "${REGISTRY}/lucid:rdp-server-manager"
else
    echo "❌ RDP Server Manager build failed"
    exit 1
fi

# Build Contract Deployment
echo "Building Contract Deployment..."
if docker build -t "${REGISTRY}/lucid:contract-deployment-${TAG}" -f blockchain/deployment/Dockerfile.contract-deployment.simple .; then
    echo "✅ Contract Deployment built successfully"
    docker tag "${REGISTRY}/lucid:contract-deployment-${TAG}" "${REGISTRY}/lucid:contract-deployment"
else
    echo "❌ Contract Deployment build failed"
    exit 1
fi

# Push images if requested
if [ "$PUSH" = "true" ]; then
    echo "Pushing images to registry..."
    docker push "${REGISTRY}/lucid:rdp-server-manager-${TAG}"
    docker push "${REGISTRY}/lucid:rdp-server-manager"
    docker push "${REGISTRY}/lucid:contract-deployment-${TAG}"
    docker push "${REGISTRY}/lucid:contract-deployment"
    echo "✅ All images pushed to registry"
fi

echo ""
echo "=== Layer 2 Simple Build Complete ==="
echo "Built images:"
echo "  - ${REGISTRY}/lucid:rdp-server-manager"
echo "  - ${REGISTRY}/lucid:contract-deployment"

if [ "$PUSH" = "true" ]; then
    echo ""
    echo "All images pushed to registry"
else
    echo ""
    echo "To push images, set PUSH=true"
fi
