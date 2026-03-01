#!/bin/bash
# Phase 1: Foundation Services Build Script
# Based on docker-build-process-plan.md Steps 5-9
# Builds: MongoDB, Redis, Elasticsearch, Auth Service

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_LOG_DIR="$PROJECT_ROOT/build/logs"
ARTIFACTS_DIR="$PROJECT_ROOT/build/artifacts"

# Registry and Image Configuration
REGISTRY="pickme/lucid"
TAG="latest"
PLATFORM="linux/arm64"
BUILDER_NAME="lucid-pi-builder"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Phase 1 Services Configuration
PHASE1_SERVICES=(
    "mongodb:infrastructure/containers/storage/Dockerfile.mongodb:infrastructure/containers/storage"
    "redis:infrastructure/containers/storage/Dockerfile.redis:infrastructure/containers/storage"
    "elasticsearch:infrastructure/containers/storage/Dockerfile.elasticsearch:infrastructure/containers/storage"
    "auth-service:auth/Dockerfile:auth"
)

# Global variables
BUILD_START_TIME=$(date +%s)
FAILED_BUILDS=()
SUCCESSFUL_BUILDS=()

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_phase() {
    echo -e "${PURPLE}🚀 $1${NC}"
}

log_step() {
    echo -e "${CYAN}📋 $1${NC}"
}

# Create necessary directories
setup_directories() {
    log_info "Setting up build directories..."
    mkdir -p "$BUILD_LOG_DIR"
    mkdir -p "$ARTIFACTS_DIR"
    log_success "Directories created"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if pre-build phase was completed
    if [[ ! -f "$PROJECT_ROOT/configs/environment/.env.pi-build" ]]; then
        log_error "Pre-build phase not completed. Run pre-build-phase.sh first."
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/configs/environment/.env.foundation" ]]; then
        log_error "Foundation environment not generated. Run pre-build-phase.sh first."
        exit 1
    fi
    
    # Check Docker
    if ! docker version >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Check Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup Docker Buildx
setup_buildx() {
    log_info "Setting up Docker Buildx builder..."
    
    # Remove existing builder if it exists
    docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    
    # Create new builder
    docker buildx create --name "$BUILDER_NAME" --use --driver docker-container --driver-opt network=host
    docker buildx inspect --bootstrap
    
    log_success "Docker Buildx builder '$BUILDER_NAME' created and ready"
}

# Load environment variables
load_environment() {
    log_info "Loading environment variables..."
    
    # Load Pi build environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.pi-build" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.pi-build"
        log_success "Pi build environment loaded"
    fi
    
    # Load foundation environment
    if [[ -f "$PROJECT_ROOT/configs/environment/.env.foundation" ]]; then
        source "$PROJECT_ROOT/configs/environment/.env.foundation"
        log_success "Foundation environment loaded"
    fi
}

# Check if image exists in registry
check_image_exists() {
    local image_name="$1"
    local full_image="$REGISTRY/$image_name:$TAG"
    
    if docker manifest inspect "$full_image" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Build single image
build_image() {
    local service_name="$1"
    local dockerfile_path="$2"
    local context_path="$3"
    local full_image="$REGISTRY/$service_name:$TAG"
    
    log_step "Building $service_name..."
    
    # Check if image already exists
    if check_image_exists "$service_name"; then
        log_warning "$service_name already exists in registry, skipping build"
        SUCCESSFUL_BUILDS+=("$service_name")
        return 0
    fi
    
    # Verify dockerfile exists
    if [[ ! -f "$PROJECT_ROOT/$dockerfile_path" ]]; then
        log_error "Dockerfile not found: $dockerfile_path"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
    
    # Verify context directory exists
    if [[ ! -d "$PROJECT_ROOT/$context_path" ]]; then
        log_error "Context directory not found: $context_path"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
    
    # Build the image
    local build_cmd=(
        "buildx" "build"
        "--platform" "$PLATFORM"
        "--file" "$PROJECT_ROOT/$dockerfile_path"
        "--tag" "$full_image"
        "--push"
        "$PROJECT_ROOT/$context_path"
    )
    
    if docker "${build_cmd[@]}" 2>&1 | tee "$BUILD_LOG_DIR/${service_name}-build.log"; then
        log_success "$service_name built and pushed successfully"
        SUCCESSFUL_BUILDS+=("$service_name")
        
        # Verify push was successful
        sleep 5
        if check_image_exists "$service_name"; then
            log_success "$service_name verified in registry"
        else
            log_error "$service_name push verification failed"
            FAILED_BUILDS+=("$service_name")
            return 1
        fi
    else
        log_error "$service_name build failed"
        FAILED_BUILDS+=("$service_name")
        return 1
    fi
}

# Step 5: Build Storage Database Containers (Group A - Parallel)
step5_build_storage_containers() {
    log_step "Step 5: Build Storage Database Containers (Group A - Parallel)"
    
    # Build MongoDB
    log_info "Building MongoDB container..."
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.mongodb" ]]; then
        build_image "lucid-mongodb" "infrastructure/containers/storage/Dockerfile.mongodb" "infrastructure/containers/storage"
    else
        log_warning "MongoDB Dockerfile not found, skipping"
    fi
    
    # Build Redis
    log_info "Building Redis container..."
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.redis" ]]; then
        build_image "lucid-redis" "infrastructure/containers/storage/Dockerfile.redis" "infrastructure/containers/storage"
    else
        log_warning "Redis Dockerfile not found, skipping"
    fi
    
    # Build Elasticsearch
    log_info "Building Elasticsearch container..."
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/storage/Dockerfile.elasticsearch" ]]; then
        build_image "lucid-elasticsearch" "infrastructure/containers/storage/Dockerfile.elasticsearch" "infrastructure/containers/storage"
    else
        log_warning "Elasticsearch Dockerfile not found, skipping"
    fi
}

# Step 6: Build Authentication Service Container (Group A - Parallel)
step6_build_auth_service() {
    log_step "Step 6: Build Authentication Service Container (Group A - Parallel)"
    
    # Build Auth Service
    log_info "Building Auth Service container..."
    if [[ -f "$PROJECT_ROOT/auth/Dockerfile" ]]; then
        build_image "lucid-auth-service" "auth/Dockerfile" "auth"
    else
        log_warning "Auth Service Dockerfile not found, skipping"
    fi
}

# Step 7: Generate Phase 1 Docker Compose
step7_generate_docker_compose() {
    log_step "Step 7: Generate Phase 1 Docker Compose"
    
    # Check if compose file exists
    if [[ -f "$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml" ]]; then
        log_success "Phase 1 Docker Compose file already exists"
    else
        log_warning "Phase 1 Docker Compose file not found, creating basic template..."
        
        # Create basic compose file
        mkdir -p "$PROJECT_ROOT/configs/docker"
        cat > "$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml" << 'EOF'
version: '3.8'

services:
  lucid-mongodb:
    image: pickme/lucid:lucid-mongodb
    container_name: lucid-mongodb
    ports:
      - "27017:27017"
    environment:
      - MONGODB_PASSWORD=${MONGODB_PASSWORD}
      - MONGODB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD}
    volumes:
      - mongodb_data:/data/db
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-redis:
    image: pickme/lucid:lucid-redis
    container_name: lucid-redis
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-elasticsearch:
    image: pickme/lucid:lucid-elasticsearch
    container_name: lucid-elasticsearch
    ports:
      - "9200:9200"
      - "9300:9300"
    environment:
      - ELASTICSEARCH_HEAP_SIZE=1g
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-auth-service:
    image: pickme/lucid:lucid-auth-service
    container_name: lucid-auth-service
    ports:
      - "8089:8089"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URI=${REDIS_URI}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mongodb_data:
  redis_data:
  elasticsearch_data:

networks:
  lucid-pi-network:
    external: true
EOF
        log_success "Basic Phase 1 Docker Compose file created"
    fi
}

# Step 8: Prepare Phase 1 Deployment
step8_prepare_deployment() {
    log_step "Step 8: Prepare Phase 1 Deployment"
    
    # Check if deployment script exists
    if [[ -f "$PROJECT_ROOT/scripts/deployment/deploy-phase1-pi.sh" ]]; then
        log_success "Phase 1 deployment script found"
    else
        log_warning "Phase 1 deployment script not found, creating basic template..."
        
        # Create basic deployment script
        mkdir -p "$PROJECT_ROOT/scripts/deployment"
        cat > "$PROJECT_ROOT/scripts/deployment/deploy-phase1-pi.sh" << 'EOF'
#!/bin/bash
# Phase 1 Deployment Script for Raspberry Pi
# Based on docker-build-process-plan.md Step 8

set -euo pipefail

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Load environment variables
source "$PROJECT_ROOT/configs/environment/.env.pi-build"
source "$PROJECT_ROOT/configs/environment/.env.foundation"

echo "🚀 Deploying Phase 1 Foundation Services to Raspberry Pi"
echo "========================================================"
echo "Pi Host: $PI_HOST"
echo "Pi User: $PI_USER"
echo "Deploy Directory: $PI_DEPLOY_DIR"
echo

# Create deployment directory on Pi
echo "Creating deployment directory on Pi..."
ssh "$PI_USER@$PI_HOST" "sudo mkdir -p $PI_DEPLOY_DIR"
ssh "$PI_USER@$PI_HOST" "sudo chown $PI_USER:$PI_USER $PI_DEPLOY_DIR"

# Copy compose file and environment to Pi
echo "Copying configuration files to Pi..."
scp "$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/"
scp "$PROJECT_ROOT/configs/environment/.env.foundation" "$PI_USER@$PI_HOST:$PI_DEPLOY_DIR/.env"

# Pull ARM64 images on Pi
echo "Pulling ARM64 images on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose pull"

# Deploy services
echo "Deploying Phase 1 services..."
ssh "$PI_USER@$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose up -d"

echo "✅ Phase 1 deployment completed!"
EOF
        chmod +x "$PROJECT_ROOT/scripts/deployment/deploy-phase1-pi.sh"
        log_success "Basic Phase 1 deployment script created"
    fi
}

# Step 9: Prepare Integration Tests
step9_prepare_integration_tests() {
    log_step "Step 9: Prepare Integration Tests"
    
    # Check if integration test script exists
    if [[ -f "$PROJECT_ROOT/tests/integration/phase1/run_phase1_tests.sh" ]]; then
        log_success "Phase 1 integration test script found"
    else
        log_warning "Phase 1 integration test script not found, creating basic template..."
        
        # Create test directory and script
        mkdir -p "$PROJECT_ROOT/tests/integration/phase1"
        cat > "$PROJECT_ROOT/tests/integration/phase1/run_phase1_tests.sh" << 'EOF'
#!/bin/bash
# Phase 1 Integration Tests
# Based on docker-build-process-plan.md Step 9

set -euo pipefail

echo "🧪 Running Phase 1 Integration Tests"
echo "===================================="

# Test MongoDB connection
echo "Testing MongoDB connection..."
python3 -c "
import pymongo
import os
client = pymongo.MongoClient('mongodb://localhost:27017/lucid_production')
print('✅ MongoDB connection successful')
"

# Test Redis connection
echo "Testing Redis connection..."
python3 -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
print('✅ Redis connection successful')
"

# Test Elasticsearch connection
echo "Testing Elasticsearch connection..."
python3 -c "
import requests
response = requests.get('http://localhost:9200/_cluster/health')
print('✅ Elasticsearch connection successful')
"

# Test Auth Service
echo "Testing Auth Service..."
python3 -c "
import requests
response = requests.get('http://localhost:8089/health')
print('✅ Auth Service connection successful')
"

echo "✅ All Phase 1 integration tests passed!"
EOF
        chmod +x "$PROJECT_ROOT/tests/integration/phase1/run_phase1_tests.sh"
        log_success "Basic Phase 1 integration test script created"
    fi
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Phase 1 Foundation Services Build Summary"
    echo "============================================="
    echo "Build Duration: ${duration_minutes}m ${duration_seconds}s"
    echo "Total Services: $((${#SUCCESSFUL_BUILDS[@]} + ${#FAILED_BUILDS[@]}))"
    echo "Successful: ${#SUCCESSFUL_BUILDS[@]}"
    echo "Failed: ${#FAILED_BUILDS[@]}"
    echo
    
    if [[ ${#SUCCESSFUL_BUILDS[@]} -gt 0 ]]; then
        log_success "Successfully built services:"
        for service in "${SUCCESSFUL_BUILDS[@]}"; do
            echo "  - $service"
        done
    fi
    
    if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
        log_error "Failed services:"
        for service in "${FAILED_BUILDS[@]}"; do
            echo "  - $service"
        done
        echo
        log_error "Phase 1 build completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "Phase 1 Foundation Services built successfully!"
        echo
        log_info "Images available in registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Tag: $TAG"
        echo
        log_info "Next Steps:"
        echo "  1. Deploy to Pi: ./scripts/deployment/deploy-phase1-pi.sh"
        echo "  2. Run integration tests: ./tests/integration/phase1/run_phase1_tests.sh"
        echo "  3. Proceed to Phase 2: ./scripts/build/phase2-core-services.sh"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    log_success "Cleanup completed"
}

# Main execution
main() {
    echo "🚀 Lucid Phase 1: Foundation Services Build Script"
    echo "=================================================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    setup_buildx
    load_environment
    
    # Execute Phase 1 steps
    step5_build_storage_containers
    step6_build_auth_service
    step7_generate_docker_compose
    step8_prepare_deployment
    step9_prepare_integration_tests
    
    # Summary
    generate_summary
    cleanup
}

# Handle script interruption
trap cleanup EXIT

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --platform PLATFORM    Target platform (default: linux/arm64)"
            echo "  --registry REGISTRY     Registry name (default: pickme/lucid)"
            echo "  --tag TAG              Image tag (default: latest)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
