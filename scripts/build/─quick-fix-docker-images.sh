#!/bin/bash
# Quick fix to build and push Docker images immediately
# This script bypasses the full orchestration and builds images directly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(pwd)"
REGISTRY="pickme"
PLATFORM="linux/arm64"
BUILD_TAG="latest-arm64"
PUSH_TO_REGISTRY=false

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
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
    
    # Check if logged in to Docker Hub
    if ! docker info | grep -q "Username:"; then
        log_warning "Not authenticated to Docker Hub"
        log_info "Please run: docker login"
        log_info "Or continue without authentication to build locally only"
        echo "Continuing with local build only..."
    fi
    
    log_success "Prerequisites check passed"
}

# Function to create buildx builder
setup_buildx_builder() {
    log_info "Setting up Docker Buildx builder..."
    
    local builder_name="lucid-quick-fix-builder"
    
    # Create builder if it doesn't exist
    if ! docker buildx ls | grep -q "$builder_name"; then
        log_info "Creating builder: $builder_name"
        docker buildx create --name "$builder_name" --use --driver docker-container --platform "$PLATFORM"
    else
        log_info "Using existing builder: $builder_name"
        docker buildx use "$builder_name"
    fi
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap
    
    log_success "Buildx builder setup completed"
}

# Function to build and push base images
build_base_images() {
    log_info "Building base images..."
    
    local base_dir="$PROJECT_ROOT/infrastructure/containers/base"
    
    if [[ ! -d "$base_dir" ]]; then
        log_error "Base images directory not found: $base_dir"
        return 1
    fi
    
    cd "$base_dir"
    
    # Build Python distroless base
    log_info "Building Python distroless base image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-base:python-distroless-arm64 -f Dockerfile.python-base"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Python base image built and pushed successfully"
    else
        log_error "Python base image build failed"
        return 1
    fi
    
    # Build Java distroless base
    log_info "Building Java distroless base image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-base:java-distroless-arm64 -f Dockerfile.java-base"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Java base image built and pushed successfully"
    else
        log_error "Java base image build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push auth service
build_auth_service() {
    log_info "Building auth service..."
    
    local auth_dir="$PROJECT_ROOT/auth"
    
    if [[ ! -d "$auth_dir" ]]; then
        log_error "Auth service directory not found: $auth_dir"
        return 1
    fi
    
    cd "$auth_dir"
    
    # Build auth service
    log_info "Building auth service image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-auth-service:$BUILD_TAG -f Dockerfile"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Auth service built and pushed successfully"
    else
        log_error "Auth service build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push storage database
build_storage_database() {
    log_info "Building storage database..."
    
    local db_dir="$PROJECT_ROOT/database"
    
    if [[ ! -d "$db_dir" ]]; then
        log_error "Database directory not found: $db_dir"
        return 1
    fi
    
    cd "$db_dir"
    
    # Build storage database
    log_info "Building storage database image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-storage-database:$BUILD_TAG -f Dockerfile"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Storage database built and pushed successfully"
    else
        log_error "Storage database build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push MongoDB
build_mongodb() {
    log_info "Building MongoDB container..."
    
    local mongo_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$mongo_dir" ]]; then
        log_error "MongoDB container directory not found: $mongo_dir"
        return 1
    fi
    
    cd "$mongo_dir"
    
    # Build MongoDB
    log_info "Building MongoDB image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-mongodb:$BUILD_TAG -f Dockerfile.mongodb"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "MongoDB built and pushed successfully"
    else
        log_error "MongoDB build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push Redis
build_redis() {
    log_info "Building Redis container..."
    
    local redis_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$redis_dir" ]]; then
        log_error "Redis container directory not found: $redis_dir"
        return 1
    fi
    
    cd "$redis_dir"
    
    # Build Redis
    log_info "Building Redis image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-redis:$BUILD_TAG -f Dockerfile.redis"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Redis built and pushed successfully"
    else
        log_error "Redis build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push Elasticsearch
build_elasticsearch() {
    log_info "Building Elasticsearch container..."
    
    local es_dir="$PROJECT_ROOT/infrastructure/containers/database"
    
    if [[ ! -d "$es_dir" ]]; then
        log_error "Elasticsearch container directory not found: $es_dir"
        return 1
    fi
    
    cd "$es_dir"
    
    # Build Elasticsearch
    log_info "Building Elasticsearch image..."
    local build_args="--platform $PLATFORM -t $REGISTRY/lucid-elasticsearch:$BUILD_TAG -f Dockerfile.elasticsearch"
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if docker buildx build $build_args .; then
        log_success "Elasticsearch built and pushed successfully"
    else
        log_error "Elasticsearch build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to verify built images
verify_built_images() {
    log_info "Verifying built images..."
    
    local images=(
        "$REGISTRY/lucid-base:python-distroless-arm64"
        "$REGISTRY/lucid-base:java-distroless-arm64"
        "$REGISTRY/lucid-auth-service:$BUILD_TAG"
        "$REGISTRY/lucid-storage-database:$BUILD_TAG"
        "$REGISTRY/lucid-mongodb:$BUILD_TAG"
        "$REGISTRY/lucid-redis:$BUILD_TAG"
        "$REGISTRY/lucid-elasticsearch:$BUILD_TAG"
    )
    
    for image in "${images[@]}"; do
        log_info "Verifying image: $image"
        if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
            if docker manifest inspect "$image" >/dev/null 2>&1; then
                log_success "Image verified: $image"
            else
                log_error "Image verification failed: $image"
                return 1
            fi
        else
            if docker image inspect "$image" >/dev/null 2>&1; then
                log_success "Local image verified: $image"
            else
                log_error "Local image verification failed: $image"
                return 1
            fi
        fi
    done
    
    log_success "All images verified successfully"
}

# Function to display quick fix summary
display_quick_fix_summary() {
    log_info "Quick Fix Summary:"
    echo ""
    echo "Built and Pushed Images:"
    echo "  • $REGISTRY/lucid-base:python-distroless-arm64"
    echo "  • $REGISTRY/lucid-base:java-distroless-arm64"
    echo "  • $REGISTRY/lucid-auth-service:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-storage-database:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-mongodb:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-redis:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-elasticsearch:$BUILD_TAG"
    echo ""
    echo "Platform: $PLATFORM (Raspberry Pi ARM64)"
    echo "Registry: $REGISTRY"
    echo ""
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        log_success "Quick fix completed successfully!"
        log_info "Images are now available on Docker Hub"
    else
        log_success "Quick fix completed successfully!"
        log_info "Images are built locally and ready for use"
    fi
}

# Main execution
main() {
    log_info "=== QUICK FIX: BUILDING DOCKER IMAGES ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    echo ""
    
    # Execute quick fix steps
    check_prerequisites
    setup_buildx_builder
    build_base_images
    build_auth_service
    build_storage_database
    build_mongodb
    build_redis
    build_elasticsearch
    verify_built_images
    
    # Display summary
    echo ""
    display_quick_fix_summary
    
    if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
        log_success "Quick fix completed successfully!"
        log_info "All images are now available on Docker Hub"
    else
        log_success "Quick fix completed successfully!"
        log_info "All images are built locally and ready for use"
    fi
}

# Run main function
main "$@"
