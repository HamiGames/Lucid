#!/bin/bash
# infrastructure/containers/storage/build-storage-containers.sh
# Build storage database containers for Lucid system

set -e

echo "Building storage database containers..."

# Set build context
cd infrastructure/containers/storage

# Build MongoDB container
echo "Building MongoDB container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f Dockerfile.mongodb \
  --push .

# Build Redis container
echo "Building Redis container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-redis:latest-arm64 \
  -f Dockerfile.redis \
  --push .

# Build Elasticsearch container
echo "Building Elasticsearch container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-elasticsearch:latest-arm64 \
  -f Dockerfile.elasticsearch \
  --push .

echo "Storage containers built and pushed successfully"
