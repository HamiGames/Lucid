#!/bin/bash
# Quick fix to build and push Docker images immediately
# This script bypasses the full orchestration and builds images directly
# Fixed to properly recreate Docker network and buildx after deletion

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(pwd)"
REGISTRY="pickme"
PLATFORM="linux/arm64"
BUILD_TAG="latest-arm64"
PUSH_TO_REGISTRY=false
BUILDER_NAME="lucid-quick-fix-builder"
NETWORK_NAME="lucid-pi-network"

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

log_phase() {
    echo -e "${MAGENTA}[PHASE]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_phase "=== CHECKING PREREQUISITES ==="
    
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

# Function to execute pre-build phase scripts
execute_pre_build_phase() {
    log_phase "=== EXECUTING PRE-BUILD PHASE ==="
    
    # Step 1: Docker Hub Cleanup
    log_info "Step 1: Docker Hub Cleanup"
    local cleanup_script="$PROJECT_ROOT/scripts/registry/cleanup-dockerhub.sh"
    if [[ -f "$cleanup_script" ]]; then
        if bash "$cleanup_script"; then
            log_success "Docker Hub cleanup completed"
        else
            log_error "Docker Hub cleanup failed"
            return 1
        fi
    else
        log_error "Docker Hub cleanup script not found: $cleanup_script"
        return 1
    fi
    
    # Step 2: Environment Configuration Generation
    log_info "Step 2: Environment Configuration Generation"
    local env_script="$PROJECT_ROOT/scripts/config/generate-all-env.sh"
    if [[ -f "$env_script" ]]; then
        if bash "$env_script"; then
            log_success "Environment configuration generated"
        else
            log_error "Environment configuration generation failed"
            return 1
        fi
    else
        log_error "Environment generation script not found: $env_script"
        return 1
    fi
    
    # Step 3: Build Environment Validation
    log_info "Step 3: Build Environment Validation"
    local validation_script="$PROJECT_ROOT/scripts/foundation/validate-build-environment.sh"
    if [[ -f "$validation_script" ]]; then
        if bash "$validation_script"; then
            log_success "Build environment validation passed"
        else
            log_error "Build environment validation failed"
            return 1
        fi
    else
        log_error "Build environment validation script not found: $validation_script"
        return 1
    fi
    
    log_success "Pre-build phase completed successfully"
}

# Function to clean and recreate Docker environment
clean_and_recreate_docker_env() {
    log_phase "=== CLEANING AND RECREATING DOCKER ENVIRONMENT ==="
    
    # Clean Docker system
    log_info "Cleaning Docker system..."
    docker system prune -a -f || log_warning "Docker system prune failed"
    
    # Clean buildx cache
    log_info "Cleaning buildx cache..."
    docker buildx prune -a -f || log_warning "Buildx prune failed"
    
    # Remove existing buildx builder if it exists
    log_info "Removing existing buildx builder..."
    if docker buildx ls | grep -q "$BUILDER_NAME"; then
        docker buildx rm "$BUILDER_NAME" || log_warning "Failed to remove existing builder"
    fi
    
    # Remove existing network if it exists
    log_info "Removing existing network..."
    if docker network ls | grep -q "$NETWORK_NAME"; then
        docker network rm "$NETWORK_NAME" || log_warning "Failed to remove existing network"
    fi
    
    # Create new buildx builder
    log_info "Creating new buildx builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --use --driver docker-container --platform "$PLATFORM"
    
    # Bootstrap the builder
    log_info "Bootstrapping buildx builder..."
    docker buildx inspect --bootstrap
    
    # Create new network
    log_info "Creating new network: $NETWORK_NAME"
    docker network create --driver bridge --attachable --subnet=172.20.0.0/16 --gateway=172.20.0.1 "$NETWORK_NAME"
    
    # Verify network creation
    if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
        log_success "Network $NETWORK_NAME created successfully"
    else
        log_error "Failed to create network $NETWORK_NAME"
        return 1
    fi
    
    # Verify builder creation
    if docker buildx ls | grep -q "$BUILDER_NAME"; then
        log_success "Builder $BUILDER_NAME created successfully"
    else
        log_error "Failed to create builder $BUILDER_NAME"
        return 1
    fi
    
    log_success "Docker environment cleaned and recreated successfully"
}

# Function to build and push base images
build_base_images() {
    log_phase "=== BUILDING BASE IMAGES ==="
    
    # Step 4: Distroless Base Images
    log_info "Step 4: Building Distroless Base Images"
    local base_script="$PROJECT_ROOT/infrastructure/containers/base/build-base-images.sh"
    
    if [[ -f "$base_script" ]]; then
        if bash "$base_script"; then
            log_success "Base images built successfully"
        else
            log_error "Base images build failed"
            return 1
        fi
    else
        log_error "Base images build script not found: $base_script"
        return 1
    fi
}

# Function to build and push auth service
build_auth_service() {
    log_phase "=== BUILDING AUTH SERVICE ==="
    
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
        log_success "Auth service built successfully"
    else
        log_error "Auth service build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push storage database
build_storage_database() {
    log_phase "=== BUILDING STORAGE DATABASE ==="
    
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
        log_success "Storage database built successfully"
    else
        log_error "Storage database build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push MongoDB
build_mongodb() {
    log_phase "=== BUILDING MONGODB ==="
    
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
        log_success "MongoDB built successfully"
    else
        log_error "MongoDB build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push Redis
build_redis() {
    log_phase "=== BUILDING REDIS ==="
    
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
        log_success "Redis built successfully"
    else
        log_error "Redis build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to build and push Elasticsearch
build_elasticsearch() {
    log_phase "=== BUILDING ELASTICSEARCH ==="
    
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
        log_success "Elasticsearch built successfully"
    else
        log_error "Elasticsearch build failed"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to verify built images
verify_built_images() {
    log_phase "=== VERIFYING BUILT IMAGES ==="
    
    local images=(
        "$REGISTRY/lucid-base:python-distroless-arm64"
        "$REGISTRY/lucid-base:java-distroless-arm64"
        "$REGISTRY/lucid-auth-service:$BUILD_TAG"
        "$REGISTRY/lucid-storage-database:$BUILD_TAG"
        "$REGISTRY/lucid-mongodb:$BUILD_TAG"
        "$REGISTRY/lucid-redis:$BUILD_TAG"
        "$REGISTRY/lucid-elasticsearch:$BUILD_TAG"
    )
    
    local verified_count=0
    local total_count=${#images[@]}
    
    for image in "${images[@]}"; do
        log_info "Verifying image: $image"
        if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
            if docker manifest inspect "$image" >/dev/null 2>&1; then
                log_success "Image verified: $image"
                ((verified_count++))
            else
                log_error "Image verification failed: $image"
            fi
        else
            if docker image inspect "$image" >/dev/null 2>&1; then
                log_success "Local image verified: $image"
                ((verified_count++))
            else
                log_error "Local image verification failed: $image"
            fi
        fi
    done
    
    log_info "Image verification summary: $verified_count/$total_count images verified"
    
    if [[ $verified_count -eq $total_count ]]; then
        log_success "All images verified successfully"
        return 0
    else
        log_error "Some images failed verification"
        return 1
    fi
}

# Function to display quick fix summary
display_quick_fix_summary() {
    log_phase "=== QUICK FIX SUMMARY ==="
    echo ""
    echo "Build Configuration:"
    echo "  • Project Root: $PROJECT_ROOT"
    echo "  • Registry: $REGISTRY"
    echo "  • Platform: $PLATFORM"
    echo "  • Builder: $BUILDER_NAME"
    echo "  • Network: $NETWORK_NAME"
    echo ""
    echo "Built Images:"
    echo "  • $REGISTRY/lucid-base:python-distroless-arm64"
    echo "  • $REGISTRY/lucid-base:java-distroless-arm64"
    echo "  • $REGISTRY/lucid-auth-service:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-storage-database:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-mongodb:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-redis:$BUILD_TAG"
    echo "  • $REGISTRY/lucid-elasticsearch:$BUILD_TAG"
    echo ""
    echo "Docker Environment:"
    echo "  • Network: $NETWORK_NAME (172.20.0.0/16)"
    echo "  • Builder: $BUILDER_NAME (docker-container driver)"
    echo "  • Platform: $PLATFORM (Raspberry Pi ARM64)"
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
    execute_pre_build_phase
    clean_and_recreate_docker_env
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
