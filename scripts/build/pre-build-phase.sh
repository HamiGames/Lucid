#!/bin/bash
# Pre-Build Phase Script - Docker Build Process
# Based on docker-build-process-plan.md Steps 1-4
# Implements: Docker Hub cleanup, environment generation, validation, base images

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
    
    # Check Docker
    if ! docker version >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    log_success "Docker is running"
    
    # Check Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi
    log_success "Docker Buildx is available"
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/README.md" ]]; then
        log_error "Not in Lucid project root directory"
        exit 1
    fi
    log_success "In correct project directory"
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

# Step 1: Docker Hub Cleanup
step1_docker_hub_cleanup() {
    log_step "Step 1: Docker Hub Cleanup"
    
    # Run the cleanup script if it exists
    if [[ -f "$PROJECT_ROOT/scripts/registry/cleanup-dockerhub.sh" ]]; then
        log_info "Running Docker Hub cleanup script..."
        bash "$PROJECT_ROOT/scripts/registry/cleanup-dockerhub.sh"
        log_success "Docker Hub cleanup completed"
    else
        log_warning "Docker Hub cleanup script not found, skipping..."
    fi
}

# Step 2: Environment Configuration Generation
step2_environment_generation() {
    log_step "Step 2: Environment Configuration Generation"
    
    # Run the environment generation script
    if [[ -f "$PROJECT_ROOT/scripts/config/generate-all-env.sh" ]]; then
        log_info "Running environment generation script..."
        bash "$PROJECT_ROOT/scripts/config/generate-all-env.sh"
        log_success "Environment configuration generated"
    else
        log_error "Environment generation script not found: $PROJECT_ROOT/scripts/config/generate-all-env.sh"
        exit 1
    fi
    
    # Verify environment files were created
    local env_files=(
        "configs/environment/.env.pi-build"
        "configs/environment/.env.foundation"
        "configs/environment/.env.core"
        "configs/environment/.env.application"
        "configs/environment/.env.support"
        "configs/environment/.env.gui"
    )
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$env_file" ]]; then
            log_success "Environment file created: $env_file"
        else
            log_error "Environment file not found: $env_file"
            exit 1
        fi
    done
}

# Step 3: Build Environment Validation
step3_build_environment_validation() {
    log_step "Step 3: Build Environment Validation"
    
    # Run the validation script if it exists
    if [[ -f "$PROJECT_ROOT/scripts/foundation/validate-build-environment.sh" ]]; then
        log_info "Running build environment validation..."
        bash "$PROJECT_ROOT/scripts/foundation/validate-build-environment.sh"
        log_success "Build environment validation completed"
    else
        log_warning "Build environment validation script not found, performing basic checks..."
        
        # Basic validation
        log_info "Checking Docker BuildKit..."
        if docker buildx version >/dev/null 2>&1; then
            log_success "Docker BuildKit is available"
        else
            log_error "Docker BuildKit is not available"
            exit 1
        fi
        
        # Check base images accessibility
        log_info "Checking base images accessibility..."
        local base_images=(
            "python:3.11-slim"
            "gcr.io/distroless/python3-debian12:arm64"
            "gcr.io/distroless/base-debian12:arm64"
        )
        
        for image in "${base_images[@]}"; do
            if docker manifest inspect "$image" >/dev/null 2>&1; then
                log_success "Base image accessible: $image"
            else
                log_warning "Base image not accessible: $image"
            fi
        done
    fi
}

# Step 4: Build Base Images
step4_build_base_images() {
    log_step "Step 4: Build Base Images"
    
    # Check if base images directory exists
    if [[ ! -d "$PROJECT_ROOT/infrastructure/containers/base" ]]; then
        log_error "Base images directory not found: $PROJECT_ROOT/infrastructure/containers/base"
        exit 1
    fi
    
    # Run the base images build script if it exists
    if [[ -f "$PROJECT_ROOT/infrastructure/containers/base/build-base-images.sh" ]]; then
        log_info "Running base images build script..."
        cd "$PROJECT_ROOT/infrastructure/containers/base"
        bash build-base-images.sh
        log_success "Base images build completed"
    else
        log_warning "Base images build script not found, building manually..."
        
        # Build Python Distroless Base
        log_info "Building Python Distroless Base..."
        local python_base_image="$REGISTRY/lucid-base:python-distroless-arm64"
        if docker buildx build \
            --platform "$PLATFORM" \
            -t "$python_base_image" \
            -f "$PROJECT_ROOT/infrastructure/containers/base/Dockerfile.python-base" \
            --push \
            "$PROJECT_ROOT/infrastructure/containers/base" 2>&1 | tee "$BUILD_LOG_DIR/python-base-build.log"; then
            log_success "Python Distroless Base built and pushed: $python_base_image"
            SUCCESSFUL_BUILDS+=("lucid-base-python")
        else
            log_error "Python Distroless Base build failed"
            FAILED_BUILDS+=("lucid-base-python")
        fi
        
        # Build Java Distroless Base
        log_info "Building Java Distroless Base..."
        local java_base_image="$REGISTRY/lucid-base:java-distroless-arm64"
        if docker buildx build \
            --platform "$PLATFORM" \
            -t "$java_base_image" \
            -f "$PROJECT_ROOT/infrastructure/containers/base/Dockerfile.java-base" \
            --push \
            "$PROJECT_ROOT/infrastructure/containers/base" 2>&1 | tee "$BUILD_LOG_DIR/java-base-build.log"; then
            log_success "Java Distroless Base built and pushed: $java_base_image"
            SUCCESSFUL_BUILDS+=("lucid-base-java")
        else
            log_error "Java Distroless Base build failed"
            FAILED_BUILDS+=("lucid-base-java")
        fi
    fi
    
    # Verify base images were pushed
    local base_images=(
        "$REGISTRY/lucid-base:python-distroless-arm64"
        "$REGISTRY/lucid-base:java-distroless-arm64"
    )
    
    for image in "${base_images[@]}"; do
        sleep 5
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Base image verified in registry: $image"
        else
            log_error "Base image verification failed: $image"
            FAILED_BUILDS+=("$(basename "$image")")
        fi
    done
}

# Generate build summary
generate_summary() {
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - BUILD_START_TIME))
    local duration_minutes=$((build_duration / 60))
    local duration_seconds=$((build_duration % 60))
    
    echo
    log_phase "Pre-Build Phase Summary"
    echo "=================================="
    echo "Build Duration: ${duration_minutes}m ${duration_seconds}s"
    echo "Total Components: $((${#SUCCESSFUL_BUILDS[@]} + ${#FAILED_BUILDS[@]}))"
    echo "Successful: ${#SUCCESSFUL_BUILDS[@]}"
    echo "Failed: ${#FAILED_BUILDS[@]}"
    echo
    
    if [[ ${#SUCCESSFUL_BUILDS[@]} -gt 0 ]]; then
        log_success "Successfully completed components:"
        for component in "${SUCCESSFUL_BUILDS[@]}"; do
            echo "  - $component"
        done
    fi
    
    if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
        log_error "Failed components:"
        for component in "${FAILED_BUILDS[@]}"; do
            echo "  - $component"
        done
        echo
        log_error "Pre-Build phase completed with errors. Check logs in $BUILD_LOG_DIR"
        exit 1
    else
        log_success "Pre-Build phase completed successfully!"
        echo
        log_info "Ready for Phase 1: Foundation Services"
        log_info "Registry: $REGISTRY"
        log_info "Platform: $PLATFORM"
        log_info "Builder: $BUILDER_NAME"
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
    echo "🚀 Lucid Pre-Build Phase Script"
    echo "==============================="
    echo "Registry: $REGISTRY"
    echo "Platform: $PLATFORM"
    echo "Builder: $BUILDER_NAME"
    echo
    
    # Setup
    setup_directories
    check_prerequisites
    setup_buildx
    
    # Execute pre-build steps
    step1_docker_hub_cleanup
    step2_environment_generation
    step3_build_environment_validation
    step4_build_base_images
    
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
