#!/bin/bash
# Phase 3 Session Management Containers Build Script
# Step 18-20: Session Management Containers
# Builds all 5 session management containers for ARM64 platform
# Target: Raspberry Pi deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_phase() {
    echo -e "${PURPLE}[PHASE 3]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running or not accessible"
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if buildx is available
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        print_warning "Docker buildx not available, using standard docker build"
        return 1
    fi
    print_success "Docker buildx is available"
    return 0
}

# Function to validate required files exist
validate_build_files() {
    local dockerfile="$1"
    local context="$2"
    
    if [[ ! -f "$dockerfile" ]]; then
        print_error "Dockerfile not found: $dockerfile"
        return 1
    fi
    
    if [[ ! -d "$context" ]]; then
        print_error "Build context not found: $context"
        return 1
    fi
    
    return 0
}

# Function to build image with error handling
build_image() {
    local script_name="$1"
    local script_path="$2"
    
    print_status "Building $script_name..."
    
    if [[ ! -f "$script_path" ]]; then
        print_error "Build script not found: $script_path"
        return 1
    fi
    
    if bash "$script_path"; then
        print_success "$script_name built successfully"
        return 0
    else
        print_error "$script_name build failed"
        return 1
    fi
}

echo "=========================================="
print_phase "Building Phase 3 Session Management Containers"
echo "=========================================="
echo "Target Platform: ARM64 (Raspberry Pi)"
echo "Build Date: $(date)"
echo "Build Host: Windows 11"
echo "Target Host: Raspberry Pi"
echo "Phase: 3 - Application Services"
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to project root
cd "$PROJECT_ROOT"

print_status "Project Root: $PROJECT_ROOT"
print_status "Script Directory: $SCRIPT_DIR"
echo ""

# Pre-build checks
print_status "Performing pre-build checks..."
check_docker

if check_buildx; then
    USE_BUILDX=true
else
    USE_BUILDX=false
fi

echo ""

# Build counter and error tracking
BUILD_COUNT=0
FAILED_BUILDS=()
SUCCESSFUL_BUILDS=()

# Phase 3 Session Management Containers (Step 18-20)
print_phase "Step 18-20: Session Management Containers"
echo ""

# Build Session Pipeline
BUILD_COUNT=$((BUILD_COUNT + 1))
print_status "Step $BUILD_COUNT/5: Building Session Pipeline..."
if build_image "Session Pipeline" "$SCRIPT_DIR/build-session-pipeline.sh"; then
    SUCCESSFUL_BUILDS+=("Session Pipeline")
else
    FAILED_BUILDS+=("Session Pipeline")
fi
echo ""

# Build Session Recorder
BUILD_COUNT=$((BUILD_COUNT + 1))
print_status "Step $BUILD_COUNT/5: Building Session Recorder..."
if build_image "Session Recorder" "$SCRIPT_DIR/build-session-recorder.sh"; then
    SUCCESSFUL_BUILDS+=("Session Recorder")
else
    FAILED_BUILDS+=("Session Recorder")
fi
echo ""

# Build Chunk Processor
BUILD_COUNT=$((BUILD_COUNT + 1))
print_status "Step $BUILD_COUNT/5: Building Chunk Processor..."
if build_image "Chunk Processor" "$SCRIPT_DIR/build-chunk-processor.sh"; then
    SUCCESSFUL_BUILDS+=("Chunk Processor")
else
    FAILED_BUILDS+=("Chunk Processor")
fi
echo ""

# Build Session Storage
BUILD_COUNT=$((BUILD_COUNT + 1))
print_status "Step $BUILD_COUNT/5: Building Session Storage..."
if build_image "Session Storage" "$SCRIPT_DIR/build-session-storage.sh"; then
    SUCCESSFUL_BUILDS+=("Session Storage")
else
    FAILED_BUILDS+=("Session Storage")
fi
echo ""

# Build Session API
BUILD_COUNT=$((BUILD_COUNT + 1))
print_status "Step $BUILD_COUNT/5: Building Session API..."
if build_image "Session API" "$SCRIPT_DIR/build-session-api.sh"; then
    SUCCESSFUL_BUILDS+=("Session API")
else
    FAILED_BUILDS+=("Session API")
fi
echo ""

# Build Summary
echo "=========================================="
if [[ ${#FAILED_BUILDS[@]} -eq 0 ]]; then
    print_success "All Phase 3 Session Management Containers Built Successfully!"
    echo "=========================================="
    echo ""
    print_success "Built Images:"
    echo "- pickme/lucid-session-pipeline:latest-arm64 (Port: 8083)"
    echo "- pickme/lucid-session-recorder:latest-arm64 (Port: 8084)"
    echo "- pickme/lucid-chunk-processor:latest-arm64 (Port: 8085)"
    echo "- pickme/lucid-session-storage:latest-arm64 (Port: 8086)"
    echo "- pickme/lucid-session-api:latest-arm64 (Port: 8087)"
    echo ""
    print_success "Total successful builds: ${#SUCCESSFUL_BUILDS[@]}/5"
    echo ""
    print_status "Phase 3 Session Management containers are ready for deployment"
    print_status "Next: Create Phase 3 Docker Compose and deploy to Pi"
    echo ""
    print_success "Phase 3 Session Management build completed successfully!"
    exit 0
else
    print_error "Phase 3 Session Management build completed with errors!"
    echo "=========================================="
    echo ""
    print_success "Successful builds (${#SUCCESSFUL_BUILDS[@]}):"
    for build in "${SUCCESSFUL_BUILDS[@]}"; do
        echo "  ✓ $build"
    done
    echo ""
    print_error "Failed builds (${#FAILED_BUILDS[@]}):"
    for build in "${FAILED_BUILDS[@]}"; do
        echo "  ✗ $build"
    done
    echo ""
    print_error "Phase 3 Session Management build completed with errors!"
    exit 1
fi
