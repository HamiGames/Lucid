#!/bin/bash
# Master Container Build Script for Lucid Project
# Follows docker-build-process-plan.md exactly
# Builds ALL containers for ARM64 Raspberry Pi deployment
# 
# Path: scripts/build/build-all-lucid-containers.sh
# Build Host: Windows 11 console
# Target Host: Raspberry Pi 5 (ARM64)
# Registry: Docker Hub (pickme/lucid namespace)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PLATFORM="linux/arm64"
REGISTRY="pickme"
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1 --build-arg BUILDKIT_PROGRESS=plain"
BUILDER_NAME="lucid-builder"

# Git commit hash for tagging
GIT_HASH=$(git rev-parse --short HEAD)

# Counters
TOTAL_BUILDS=0
SUCCESSFUL_BUILDS=0
FAILED_BUILDS=0

# Log functions
log_section() {
    echo -e "${MAGENTA}========================================${NC}"
    echo -e "${MAGENTA}$1${NC}"
    echo -e "${MAGENTA}========================================${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((SUCCESSFUL_BUILDS++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_BUILDS++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Build function
build_container() {
    local service_name=$1
    local dockerfile=$2
    local image_tag=$3
    local context_dir=${4:-.}
    
    ((TOTAL_BUILDS++))
    
    log_info "Building $service_name..."
    log_info "Dockerfile: $dockerfile"
    log_info "Image: $image_tag"
    log_info "Platform: $PLATFORM"
    
    if docker buildx build \
        --builder $BUILDER_NAME \
        --platform $PLATFORM \
        --file "$dockerfile" \
        --tag "$image_tag" \
        --tag "$image_tag-$GIT_HASH" \
        $BUILD_ARGS \
        --push \
        "$context_dir"; then
        log_success "$service_name built and pushed successfully"
        return 0
    else
        log_error "$service_name build failed"
        return 1
    fi
}

# Ensure builder exists
ensure_builder() {
    log_info "Checking Docker Buildx builder..."
    if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
        log_warning "Creating Docker Buildx builder: $BUILDER_NAME"
        docker buildx create --name $BUILDER_NAME --use --driver docker-container --driver-opt network=host
    fi
    docker buildx use $BUILDER_NAME
    log_success "Builder $BUILDER_NAME is ready"
}

#############################################
# PRE-BUILD PHASE
#############################################

pre_build_phase() {
    log_section "PRE-BUILD PHASE: Step 4 - Distroless Base Images"
    
    cd infrastructure/containers/base
    
    # Step 4: Base Images
    build_container \
        "Python Distroless Base" \
        "Dockerfile.python-base" \
        "pickme/lucid-base:python-distroless-arm64" \
        "."
    
    build_container \
        "Java Distroless Base" \
        "Dockerfile.java-base" \
        "pickme/lucid-base:java-distroless-arm64" \
        "."
    
    cd ../../..
}

#############################################
# PHASE 1: FOUNDATION SERVICES
#############################################

phase1_foundation() {
    log_section "PHASE 1: Foundation Services (Steps 5-6)"
    
    # Step 5: Storage Database Containers
    log_info "Step 5: Building Storage Database Containers..."
    
    cd infrastructure/containers/database
    
    build_container \
        "MongoDB" \
        "Dockerfile.mongodb" \
        "pickme/lucid-mongodb:latest-arm64" \
        "."
    
    build_container \
        "Redis" \
        "Dockerfile.redis" \
        "pickme/lucid-redis:latest-arm64" \
        "."
    
    build_container \
        "Elasticsearch" \
        "Dockerfile.elasticsearch" \
        "pickme/lucid-elasticsearch:latest-arm64" \
        "."
    
    cd ../../..
    
    # Step 6: Authentication Service Container
    log_info "Step 6: Building Authentication Service Container..."
    
    if [ -f "auth/Dockerfile" ] || [ -f "infrastructure/containers/auth/Dockerfile.auth-service" ]; then
        local auth_dockerfile=$([ -f "infrastructure/containers/auth/Dockerfile.auth-service" ] && echo "infrastructure/containers/auth/Dockerfile.auth-service" || echo "auth/Dockerfile")
        build_container \
            "Authentication Service" \
            "$auth_dockerfile" \
            "pickme/lucid-auth-service:latest-arm64" \
            "."
    else
        log_warning "Authentication Service Dockerfile not found, skipping..."
    fi
}

#############################################
# PHASE 2: CORE SERVICES
#############################################

phase2_core() {
    log_section "PHASE 2: Core Services (Steps 10-12)"
    
    # Step 10: API Gateway Container
    log_info "Step 10: Building API Gateway Container..."
    
    if [ -f "03-api-gateway/Dockerfile" ]; then
        build_container \
            "API Gateway" \
            "03-api-gateway/Dockerfile" \
            "pickme/lucid-api-gateway:latest-arm64" \
            "."
    else
        log_warning "API Gateway Dockerfile not found, skipping..."
    fi
    
    # Step 11: Service Mesh Controller
    log_info "Step 11: Building Service Mesh Controller..."
    
    if [ -f "infrastructure/service-mesh/controller/Dockerfile" ] || [ -f "service-mesh/Dockerfile.controller" ]; then
        local mesh_dockerfile=$([ -f "infrastructure/service-mesh/controller/Dockerfile" ] && echo "infrastructure/service-mesh/controller/Dockerfile" || echo "service-mesh/Dockerfile.controller")
        build_container \
            "Service Mesh Controller" \
            "$mesh_dockerfile" \
            "pickme/lucid-service-mesh-controller:latest-arm64" \
            "."
    else
        log_warning "Service Mesh Dockerfile not found, skipping..."
    fi
    
    # Step 12: Blockchain Core Containers (4 containers)
    log_info "Step 12: Building Blockchain Core Containers..."
    
    # TRON Isolation Check
    log_info "Running TRON isolation scan..."
    if grep -r -i "tron" blockchain/ --exclude-dir=node_modules 2>/dev/null | grep -v "# TRON" | head -5; then
        log_warning "TRON references found in blockchain/, but continuing build..."
    fi
    
    # Blockchain Engine
    if [ -f "blockchain/Dockerfile.engine" ]; then
        build_container \
            "Blockchain Engine" \
            "blockchain/Dockerfile.engine" \
            "pickme/lucid-blockchain-engine:latest-arm64" \
            "."
    fi
    
    # Session Anchoring
    if [ -f "blockchain/Dockerfile.anchoring" ]; then
        build_container \
            "Session Anchoring" \
            "blockchain/Dockerfile.anchoring" \
            "pickme/lucid-session-anchoring:latest-arm64" \
            "."
    fi
    
    # Block Manager
    if [ -f "blockchain/Dockerfile.manager" ]; then
        build_container \
            "Block Manager" \
            "blockchain/Dockerfile.manager" \
            "pickme/lucid-block-manager:latest-arm64" \
            "."
    fi
    
    # Data Chain
    if [ -f "blockchain/Dockerfile.data" ]; then
        build_container \
            "Data Chain" \
            "blockchain/Dockerfile.data" \
            "pickme/lucid-data-chain:latest-arm64" \
            "."
    fi
}

#############################################
# PHASE 3: APPLICATION SERVICES
#############################################

phase3_application() {
    log_section "PHASE 3: Application Services (Steps 18-23)"
    
    # Steps 18-20: Session Management Containers (5 containers)
    log_info "Steps 18-20: Building Session Management Containers..."
    
    local session_containers=(
        "Dockerfile.pipeline:pickme/lucid-session-pipeline:latest-arm64:Session Pipeline"
        "Dockerfile.recorder:pickme/lucid-session-recorder:latest-arm64:Session Recorder"
        "Dockerfile.processor:pickme/lucid-chunk-processor:latest-arm64:Chunk Processor"
        "Dockerfile.storage:pickme/lucid-session-storage:latest-arm64:Session Storage"
        "Dockerfile.api:pickme/lucid-session-api:latest-arm64:Session API"
    )
    
    for container_info in "${session_containers[@]}"; do
        IFS=':' read -r dockerfile image_name display_name <<< "$container_info"
        if [ -f "sessions/$dockerfile" ]; then
            build_container \
                "$display_name" \
                "sessions/$dockerfile" \
                "$image_name" \
                "."
        else
            log_warning "$display_name Dockerfile not found at sessions/$dockerfile"
        fi
    done
    
    # Steps 21-22: RDP Services Containers (4 containers)
    log_info "Steps 21-22: Building RDP Services Containers..."
    
    local rdp_containers=(
        "Dockerfile.server-manager:pickme/lucid-rdp-server-manager:latest-arm64:RDP Server Manager"
        "Dockerfile.xrdp:pickme/lucid-xrdp-integration:latest-arm64:XRDP Integration"
        "Dockerfile.controller:pickme/lucid-session-controller:latest-arm64:Session Controller"
        "Dockerfile.monitor:pickme/lucid-resource-monitor:latest-arm64:Resource Monitor"
    )
    
    for container_info in "${rdp_containers[@]}"; do
        IFS=':' read -r dockerfile image_name display_name <<< "$container_info"
        if [ -f "RDP/$dockerfile" ]; then
            build_container \
                "$display_name" \
                "RDP/$dockerfile" \
                "$image_name" \
                "."
        else
            log_warning "$display_name Dockerfile not found at RDP/$dockerfile"
        fi
    done
    
    # Step 23: Node Management Container
    log_info "Step 23: Building Node Management Container..."
    
    if [ -f "node/Dockerfile" ]; then
        build_container \
            "Node Management" \
            "node/Dockerfile" \
            "pickme/lucid-node-management:latest-arm64" \
            "."
    else
        log_warning "Node Management Dockerfile not found"
    fi
}

#############################################
# PHASE 4: SUPPORT SERVICES
#############################################

phase4_support() {
    log_section "PHASE 4: Support Services (Steps 28-30)"
    
    # Step 28: Admin Interface Container
    log_info "Step 28: Building Admin Interface Container..."
    
    if [ -f "admin/Dockerfile" ] || [ -f "infrastructure/containers/admin/Dockerfile.admin-ui-backend" ]; then
        local admin_dockerfile=$([ -f "admin/Dockerfile" ] && echo "admin/Dockerfile" || echo "infrastructure/containers/admin/Dockerfile.admin-ui-backend")
        build_container \
            "Admin Interface" \
            "$admin_dockerfile" \
            "pickme/lucid-admin-interface:latest-arm64" \
            "."
    else
        log_warning "Admin Interface Dockerfile not found"
    fi
    
    # Steps 29-30: TRON Payment Containers (6 containers - ISOLATED)
    log_info "Steps 29-30: Building TRON Payment Containers (ISOLATED)..."
    log_warning "CRITICAL: TRON containers run on lucid-tron-isolated network"
    
    local tron_containers=(
        "Dockerfile.tron-client:pickme/lucid-tron-client:latest-arm64:TRON Client"
        "Dockerfile.payout-router:pickme/lucid-payout-router:latest-arm64:Payout Router"
        "Dockerfile.wallet-manager:pickme/lucid-wallet-manager:latest-arm64:Wallet Manager"
        "Dockerfile.usdt-manager:pickme/lucid-usdt-manager:latest-arm64:USDT Manager"
        "Dockerfile.trx-staking:pickme/lucid-trx-staking:latest-arm64:TRX Staking"
        "Dockerfile.payment-gateway:pickme/lucid-payment-gateway:latest-arm64:Payment Gateway"
    )
    
    for container_info in "${tron_containers[@]}"; do
        IFS=':' read -r dockerfile image_name display_name <<< "$container_info"
        if [ -f "payment-systems/tron/$dockerfile" ]; then
            build_container \
                "$display_name" \
                "payment-systems/tron/$dockerfile" \
                "$image_name" \
                "."
        else
            log_warning "$display_name Dockerfile not found at payment-systems/tron/$dockerfile"
        fi
    done
}

#############################################
# MAIN EXECUTION
#############################################

main() {
    log_section "LUCID CONTAINER BUILD PROCESS"
    log_info "Following docker-build-process-plan.md"
    log_info "Build Host: Windows 11"
    log_info "Target Platform: $PLATFORM (Raspberry Pi 5)"
    log_info "Registry: Docker Hub (pickme namespace)"
    log_info "Git Commit: $GIT_HASH"
    
    # Ensure builder exists
    ensure_builder
    
    # Parse arguments
    SKIP_PREBUILD=false
    SKIP_PHASE1=false
    SKIP_PHASE2=false
    SKIP_PHASE3=false
    SKIP_PHASE4=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-prebuild)
                SKIP_PREBUILD=true
                shift
                ;;
            --skip-phase1)
                SKIP_PHASE1=true
                shift
                ;;
            --skip-phase2)
                SKIP_PHASE2=true
                shift
                ;;
            --skip-phase3)
                SKIP_PHASE3=true
                shift
                ;;
            --skip-phase4)
                SKIP_PHASE4=true
                shift
                ;;
            --phase)
                case $2 in
                    prebuild|0)
                        SKIP_PHASE1=true
                        SKIP_PHASE2=true
                        SKIP_PHASE3=true
                        SKIP_PHASE4=true
                        ;;
                    1)
                        SKIP_PREBUILD=true
                        SKIP_PHASE2=true
                        SKIP_PHASE3=true
                        SKIP_PHASE4=true
                        ;;
                    2)
                        SKIP_PREBUILD=true
                        SKIP_PHASE1=true
                        SKIP_PHASE3=true
                        SKIP_PHASE4=true
                        ;;
                    3)
                        SKIP_PREBUILD=true
                        SKIP_PHASE1=true
                        SKIP_PHASE2=true
                        SKIP_PHASE4=true
                        ;;
                    4)
                        SKIP_PREBUILD=true
                        SKIP_PHASE1=true
                        SKIP_PHASE2=true
                        SKIP_PHASE3=true
                        ;;
                esac
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --phase <0-4>        Build only specific phase (0=prebuild, 1-4=phases)"
                echo "  --skip-prebuild      Skip pre-build phase"
                echo "  --skip-phase1        Skip Phase 1 (Foundation)"
                echo "  --skip-phase2        Skip Phase 2 (Core)"
                echo "  --skip-phase3        Skip Phase 3 (Application)"
                echo "  --skip-phase4        Skip Phase 4 (Support)"
                echo "  --help, -h           Show this help message"
                echo ""
                echo "Example:"
                echo "  $0                   # Build all phases"
                echo "  $0 --phase 1         # Build only Phase 1"
                echo "  $0 --skip-phase3     # Build all except Phase 3"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute builds
    [ "$SKIP_PREBUILD" = false ] && pre_build_phase
    [ "$SKIP_PHASE1" = false ] && phase1_foundation
    [ "$SKIP_PHASE2" = false ] && phase2_core
    [ "$SKIP_PHASE3" = false ] && phase3_application
    [ "$SKIP_PHASE4" = false ] && phase4_support
    
    # Summary
    log_section "BUILD SUMMARY"
    log_info "Total Builds Attempted: $TOTAL_BUILDS"
    log_success "Successful Builds: $SUCCESSFUL_BUILDS"
    if [ $FAILED_BUILDS -gt 0 ]; then
        log_error "Failed Builds: $FAILED_BUILDS"
        exit 1
    else
        log_success "All builds completed successfully!"
    fi
}

# Run main function
main "$@"

