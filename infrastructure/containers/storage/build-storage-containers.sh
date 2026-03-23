#!/bin/bash
# infrastructure/containers/storage/build-storage-containers.sh
# Build Lucid STORAGE PLANE images (capacity + durability paths). Context = repository root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "Building Lucid storage plane container images (context: $PROJECT_ROOT)..."

# Check if images already exist
check_existing_images() {
    echo "Checking for existing images..."
    
    if docker images | grep -q "pickme/lucid-mongodb.*latest-arm64"; then
        echo "✓ MongoDB image already exists"
        MONGODB_EXISTS=true
    else
        echo "✗ MongoDB image not found"
        MONGODB_EXISTS=false
    fi
    
    if docker images | grep -q "pickme/lucid-redis.*latest-arm64"; then
        echo "✓ Redis image already exists"
        REDIS_EXISTS=true
    else
        echo "✗ Redis image not found"
        REDIS_EXISTS=false
    fi
    
    if docker images | grep -q "pickme/lucid-elasticsearch.*latest-arm64"; then
        echo "✓ Elasticsearch image already exists"
        ELASTICSEARCH_EXISTS=true
    else
        echo "✗ Elasticsearch image not found"
        ELASTICSEARCH_EXISTS=false
    fi
}

# Build MongoDB container
build_mongodb() {
    if [ "$MONGODB_EXISTS" = true ]; then
        echo "Skipping MongoDB build - image already exists"
        return 0
    fi
    
    echo "Building MongoDB container..."
    
    # Try comprehensive Dockerfile first
    if [ -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.mongodb" ]; then
        echo "Using comprehensive MongoDB Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-mongodb:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.mongodb" \
          --push \
          "$PROJECT_ROOT"
    elif [ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.mongodb" ]; then
        echo "Using storage-plane MongoDB Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-mongodb:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.mongodb" \
          --push \
          "$PROJECT_ROOT"
    else
        echo "ERROR: No MongoDB Dockerfile found"
        exit 1
    fi
}

# Build Redis container
build_redis() {
    if [ "$REDIS_EXISTS" = true ]; then
        echo "Skipping Redis build - image already exists"
        return 0
    fi
    
    echo "Building Redis container..."
    
    # Try comprehensive Dockerfile first
    if [ -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.redis" ]; then
        echo "Using comprehensive Redis Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-redis:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.redis" \
          --push \
          "$PROJECT_ROOT"
    elif [ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.redis" ]; then
        echo "Using storage-plane Redis Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-redis:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.redis" \
          --push \
          "$PROJECT_ROOT"
    else
        echo "ERROR: No Redis Dockerfile found"
        exit 1
    fi
}

# Build Elasticsearch container
build_elasticsearch() {
    if [ "$ELASTICSEARCH_EXISTS" = true ]; then
        echo "Skipping Elasticsearch build - image already exists"
        return 0
    fi
    
    echo "Building Elasticsearch container..."
    
    # Try comprehensive Dockerfile first
    if [ -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.elasticsearch" ]; then
        echo "Using comprehensive Elasticsearch Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-elasticsearch:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/docker/databases/Dockerfile.elasticsearch" \
          --push \
          "$PROJECT_ROOT"
    elif [ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.elasticsearch" ]; then
        echo "Using storage-plane Elasticsearch Dockerfile..."
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-elasticsearch:latest-arm64 \
          -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.elasticsearch" \
          --push \
          "$PROJECT_ROOT"
    else
        echo "ERROR: No Elasticsearch Dockerfile found"
        exit 1
    fi
}

build_storage_orchestrator() {
    echo "Building storage plane orchestrator (layout / capacity watchdog)..."
    if [ ! -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.storage" ]; then
        echo "WARNING: Dockerfile.storage not found, skipping"
        return 0
    fi
    docker buildx build \
      --platform linux/arm64 \
      -t pickme/lucid-system-storage:latest-arm64 \
      -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.storage" \
      --push \
      "$PROJECT_ROOT"
}

# Main execution
echo "=== Lucid Storage Plane Images Build ==="
echo "Target: ARM64 (Raspberry Pi)"
echo "Registry: Docker Hub (pickme/lucid-*)"
echo ""

# Check existing images
check_existing_images

echo ""
echo "=== Building storage plane images ==="

build_mongodb
build_redis
build_elasticsearch
build_storage_orchestrator

echo ""
echo "=== Build Summary ==="
echo "✓ Storage plane images build completed successfully"
echo "✓ All images pushed to Docker Hub"
echo "✓ Ready for Phase 1 Foundation Services deployment"
