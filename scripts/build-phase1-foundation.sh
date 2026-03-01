#!/bin/bash
# Phase 1 Foundation Services Build Script
# Builds: auth-service, storage-database, mongodb, redis, elasticsearch
# Target: Raspberry Pi (linux/arm64)
# Registry: pickme/lucid namespace

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="pickme/lucid"
PLATFORM="linux/arm64"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation functions
validate_environment() {
    log_info "Validating build environment..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker BuildKit
    if ! docker buildx version &> /dev/null; then
        log_error "Docker BuildKit is not available"
        exit 1
    fi
    
    # Check platform support
    if ! docker buildx inspect --bootstrap | grep -q "$PLATFORM"; then
        log_warning "Platform $PLATFORM not found in buildx, creating builder..."
        docker buildx create --name lucid-pi --use --driver docker-container --platform "$PLATFORM" || true
        docker buildx use lucid-pi
    fi
    
    log_success "Environment validation complete"
}

# Docker Hub authentication
authenticate_dockerhub() {
    log_info "Authenticating to Docker Hub..."
    
    if ! docker info | grep -q "Username: pickme"; then
        log_warning "Not authenticated to Docker Hub as 'pickme'"
        log_info "Please run: docker login"
        read -p "Press Enter after logging in..."
    fi
    
    log_success "Docker Hub authentication verified"
}

# Build base images
build_base_images() {
    log_info "Building distroless base images..."
    
    local base_dir="$PROJECT_ROOT/infrastructure/containers/base"
    
    if [[ ! -d "$base_dir" ]]; then
        log_error "Base images directory not found: $base_dir"
        exit 1
    fi
    
    cd "$base_dir"
    
    # Build Python distroless base
    log_info "Building Python distroless base image..."
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.python-base \
        --push \
        .
    
    # Build Java distroless base
    log_info "Building Java distroless base image..."
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-base:java-distroless-arm64" \
        -f Dockerfile.java-base \
        --push \
        .
    
    log_success "Base images built successfully"
}

# Build auth service
build_auth_service() {
    log_info "Building auth service..."
    
    local auth_dir="$PROJECT_ROOT/auth"
    
    if [[ ! -d "$auth_dir" ]]; then
        log_error "Auth service directory not found: $auth_dir"
        exit 1
    fi
    
    cd "$auth_dir"
    
    # Build auth service with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-auth-service:latest-arm64" \
        -t "$REGISTRY/lucid-auth-service:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "Auth service built successfully"
}

# Build storage database
build_storage_database() {
    log_info "Building storage database..."
    
    local db_dir="$PROJECT_ROOT/database"
    
    if [[ ! -d "$db_dir" ]]; then
        log_error "Database directory not found: $db_dir"
        exit 1
    fi
    
    cd "$db_dir"
    
    # Build storage database with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-storage-database:latest-arm64" \
        -t "$REGISTRY/lucid-storage-database:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "Storage database built successfully"
}

# Build MongoDB container
build_mongodb() {
    log_info "Building MongoDB container..."
    
    local mongo_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$mongo_dir" ]]; then
        log_error "MongoDB container directory not found: $mongo_dir"
        exit 1
    fi
    
    cd "$mongo_dir"
    
    # Build MongoDB with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-mongodb:latest-arm64" \
        -t "$REGISTRY/lucid-mongodb:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="gcr.io/distroless/base-debian12:arm64" \
        -f Dockerfile.mongodb \
        --push \
        .
    
    log_success "MongoDB container built successfully"
}

# Build Redis container
build_redis() {
    log_info "Building Redis container..."
    
    local redis_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$redis_dir" ]]; then
        log_error "Redis container directory not found: $redis_dir"
        exit 1
    fi
    
    cd "$redis_dir"
    
    # Build Redis with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-redis:latest-arm64" \
        -t "$REGISTRY/lucid-redis:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="gcr.io/distroless/base-debian12:arm64" \
        -f Dockerfile.redis \
        --push \
        .
    
    log_success "Redis container built successfully"
}

# Build Elasticsearch container
build_elasticsearch() {
    log_info "Building Elasticsearch container..."
    
    local es_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$es_dir" ]]; then
        log_error "Elasticsearch container directory not found: $es_dir"
        exit 1
    fi
    
    cd "$es_dir"
    
    # Build Elasticsearch with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-elasticsearch:latest-arm64" \
        -t "$REGISTRY/lucid-elasticsearch:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="gcr.io/distroless/base-debian12:arm64" \
        -f Dockerfile.elasticsearch \
        --push \
        .
    
    log_success "Elasticsearch container built successfully"
}

# Verify built images
verify_images() {
    log_info "Verifying built images..."
    
    local images=(
        "$REGISTRY/lucid-base:python-distroless-arm64"
        "$REGISTRY/lucid-base:java-distroless-arm64"
        "$REGISTRY/lucid-auth-service:latest-arm64"
        "$REGISTRY/lucid-storage-database:latest-arm64"
        "$REGISTRY/lucid-mongodb:latest-arm64"
        "$REGISTRY/lucid-redis:latest-arm64"
        "$REGISTRY/lucid-elasticsearch:latest-arm64"
    )
    
    for image in "${images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Image verified: $image"
        else
            log_error "Image verification failed: $image"
            exit 1
        fi
    done
    
    log_success "All images verified successfully"
}

# Main execution
main() {
    log_info "Starting Phase 1 Foundation Services Build"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Validate environment
    validate_environment
    
    # Authenticate to Docker Hub
    authenticate_dockerhub
    
    # Build base images first
    build_base_images
    
    # Build Phase 1 services
    build_auth_service
    build_storage_database
    build_mongodb
    build_redis
    build_elasticsearch
    
    # Verify all images
    verify_images
    
    log_success "Phase 1 Foundation Services build completed successfully!"
    log_info "Built images:"
    log_info "  - $REGISTRY/lucid-base:python-distroless-arm64"
    log_info "  - $REGISTRY/lucid-base:java-distroless-arm64"
    log_info "  - $REGISTRY/lucid-auth-service:latest-arm64"
    log_info "  - $REGISTRY/lucid-storage-database:latest-arm64"
    log_info "  - $REGISTRY/lucid-mongodb:latest-arm64"
    log_info "  - $REGISTRY/lucid-redis:latest-arm64"
    log_info "  - $REGISTRY/lucid-elasticsearch:latest-arm64"
}

# Run main function
main "$@"
