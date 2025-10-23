#!/bin/bash
# auth/build-auth-service.sh
# Build authentication service container

set -e

echo "Building authentication service container..."

# Set build context
cd auth

# Build auth service container
echo "Building auth service container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f Dockerfile \
  --push .

echo "Authentication service container built and pushed successfully"
