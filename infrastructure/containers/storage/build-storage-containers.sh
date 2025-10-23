#!/bin/bash
# infrastructure/containers/storage/build-storage-containers.sh
# Build storage database containers for Lucid system

set -e

echo "Building storage database containers..."

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
    if [ -f "infrastructure/docker/databases/Dockerfile.mongodb" ]; then
        echo "Using comprehensive MongoDB Dockerfile..."
        cd infrastructure/docker/databases
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-mongodb:latest-arm64 \
          -f Dockerfile.mongodb \
          --push .
        cd - > /dev/null
    elif [ -f "infrastructure/containers/storage/Dockerfile.mongodb" ]; then
        echo "Using storage MongoDB Dockerfile..."
        cd infrastructure/containers/storage
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-mongodb:latest-arm64 \
          -f Dockerfile.mongodb \
          --push .
        cd - > /dev/null
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
    if [ -f "infrastructure/docker/databases/Dockerfile.redis" ]; then
        echo "Using comprehensive Redis Dockerfile..."
        cd infrastructure/docker/databases
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-redis:latest-arm64 \
          -f Dockerfile.redis \
          --push .
        cd - > /dev/null
    elif [ -f "infrastructure/containers/storage/Dockerfile.redis" ]; then
        echo "Using storage Redis Dockerfile..."
        cd infrastructure/containers/storage
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-redis:latest-arm64 \
          -f Dockerfile.redis \
          --push .
        cd - > /dev/null
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
    if [ -f "infrastructure/docker/databases/Dockerfile.elasticsearch" ]; then
        echo "Using comprehensive Elasticsearch Dockerfile..."
        cd infrastructure/docker/databases
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-elasticsearch:latest-arm64 \
          -f Dockerfile.elasticsearch \
          --push .
        cd - > /dev/null
    elif [ -f "infrastructure/containers/storage/Dockerfile.elasticsearch" ]; then
        echo "Using storage Elasticsearch Dockerfile..."
        cd infrastructure/containers/storage
        docker buildx build \
          --platform linux/arm64 \
          -t pickme/lucid-elasticsearch:latest-arm64 \
          -f Dockerfile.elasticsearch \
          --push .
        cd - > /dev/null
    else
        echo "ERROR: No Elasticsearch Dockerfile found"
        exit 1
    fi
}

# Main execution
echo "=== Lucid Storage Containers Build ==="
echo "Target: ARM64 (Raspberry Pi)"
echo "Registry: Docker Hub (pickme/lucid-*)"
echo ""

# Check existing images
check_existing_images

echo ""
echo "=== Building Storage Containers ==="

# Build containers
build_mongodb
build_redis
build_elasticsearch

echo ""
echo "=== Build Summary ==="
echo "✓ Storage containers build completed successfully"
echo "✓ All images pushed to Docker Hub"
echo "✓ Ready for Phase 1 Foundation Services deployment"
