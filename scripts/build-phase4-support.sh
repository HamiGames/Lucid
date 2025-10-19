#!/bin/bash
# Phase 4 Support Services Build Script
# Builds: Admin Interface, TRON Payment System (Isolated) containers
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
        docker buildx create --name lucid-pi-support --use --driver docker-container --platform "$PLATFORM" || true
        docker buildx use lucid-pi-support
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

# Build Admin Interface
build_admin_interface() {
    log_info "Building Admin Interface..."
    
    local admin_dir="$PROJECT_ROOT/admin"
    
    if [[ ! -d "$admin_dir" ]]; then
        log_error "Admin directory not found: $admin_dir"
        exit 1
    fi
    
    cd "$admin_dir"
    
    # Build Admin Interface with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-admin-interface:latest-arm64" \
        -t "$REGISTRY/lucid-admin-interface:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile \
        --push \
        .
    
    log_success "Admin Interface built successfully"
}

# Build TRON Client
build_tron_client() {
    log_info "Building TRON Client..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    if [[ ! -d "$tron_dir" ]]; then
        log_error "TRON directory not found: $tron_dir"
        exit 1
    fi
    
    cd "$tron_dir"
    
    # Build TRON Client with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-tron-client:latest-arm64" \
        -t "$REGISTRY/lucid-tron-client:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.tron-client \
        --push \
        .
    
    log_success "TRON Client built successfully"
}

# Build Payout Router
build_payout_router() {
    log_info "Building Payout Router..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    cd "$tron_dir"
    
    # Build Payout Router with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-payout-router:latest-arm64" \
        -t "$REGISTRY/lucid-payout-router:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.payout-router \
        --push \
        .
    
    log_success "Payout Router built successfully"
}

# Build Wallet Manager
build_wallet_manager() {
    log_info "Building Wallet Manager..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    cd "$tron_dir"
    
    # Build Wallet Manager with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-wallet-manager:latest-arm64" \
        -t "$REGISTRY/lucid-wallet-manager:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.wallet-manager \
        --push \
        .
    
    log_success "Wallet Manager built successfully"
}

# Build USDT Manager
build_usdt_manager() {
    log_info "Building USDT Manager..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    cd "$tron_dir"
    
    # Build USDT Manager with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-usdt-manager:latest-arm64" \
        -t "$REGISTRY/lucid-usdt-manager:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.usdt-manager \
        --push \
        .
    
    log_success "USDT Manager built successfully"
}

# Build TRX Staking
build_trx_staking() {
    log_info "Building TRX Staking..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    cd "$tron_dir"
    
    # Build TRX Staking with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-trx-staking:latest-arm64" \
        -t "$REGISTRY/lucid-trx-staking:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.trx-staking \
        --push \
        .
    
    log_success "TRX Staking built successfully"
}

# Build Payment Gateway
build_payment_gateway() {
    log_info "Building Payment Gateway..."
    
    local tron_dir="$PROJECT_ROOT/payment-systems/tron"
    
    cd "$tron_dir"
    
    # Build Payment Gateway with distroless base
    docker buildx build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/lucid-payment-gateway:latest-arm64" \
        -t "$REGISTRY/lucid-payment-gateway:$GIT_COMMIT-arm64" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="1.0.0" \
        --build-arg BASE_IMAGE="$REGISTRY/lucid-base:python-distroless-arm64" \
        -f Dockerfile.payment-gateway \
        --push \
        .
    
    log_success "Payment Gateway built successfully"
}

# Verify built images
verify_images() {
    log_info "Verifying built images..."
    
    local images=(
        "$REGISTRY/lucid-admin-interface:latest-arm64"
        "$REGISTRY/lucid-tron-client:latest-arm64"
        "$REGISTRY/lucid-payout-router:latest-arm64"
        "$REGISTRY/lucid-wallet-manager:latest-arm64"
        "$REGISTRY/lucid-usdt-manager:latest-arm64"
        "$REGISTRY/lucid-trx-staking:latest-arm64"
        "$REGISTRY/lucid-payment-gateway:latest-arm64"
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
    log_info "Starting Phase 4 Support Services Build"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    log_info "Build Date: $BUILD_DATE"
    log_info "Git Commit: $GIT_COMMIT"
    
    # Validate environment
    validate_environment
    
    # Authenticate to Docker Hub
    authenticate_dockerhub
    
    # Build Admin Interface
    build_admin_interface
    
    # Build TRON Payment System containers (ISOLATED)
    build_tron_client
    build_payout_router
    build_wallet_manager
    build_usdt_manager
    build_trx_staking
    build_payment_gateway
    
    # Verify all images
    verify_images
    
    log_success "Phase 4 Support Services build completed successfully!"
    log_info "Built images:"
    log_info "  - $REGISTRY/lucid-admin-interface:latest-arm64"
    log_info "  - $REGISTRY/lucid-tron-client:latest-arm64"
    log_info "  - $REGISTRY/lucid-payout-router:latest-arm64"
    log_info "  - $REGISTRY/lucid-wallet-manager:latest-arm64"
    log_info "  - $REGISTRY/lucid-usdt-manager:latest-arm64"
    log_info "  - $REGISTRY/lucid-trx-staking:latest-arm64"
    log_info "  - $REGISTRY/lucid-payment-gateway:latest-arm64"
}

# Run main function
main "$@"
