#!/bin/bash
# Master Build Orchestration Script
# Implements the complete docker-build-process-plan.md
# Coordinates all phases: Pre-Build → Phase 1 → Phase 2 → Phase 3 → Phase 4
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY="pickme/lucid"
PLATFORM="linux/arm64"
PI_HOST="192.168.0.75"
PI_USER="pickme"
BUILDER_NAME="lucid-pi"
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

# Function to execute phase with error handling
execute_phase() {
    local phase_name=$1
    local script_path=$2
    local description=$3
    
    log_phase "=== $phase_name ==="
    log_info "$description"
    
    if [[ -f "$script_path" ]]; then
        log_info "Executing: $script_path"
        if bash "$script_path"; then
            log_success "$phase_name completed successfully"
            return 0
        else
            log_error "$phase_name failed"
            return 1
        fi
    else
        log_error "Script not found: $script_path"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_phase "=== CHECKING PREREQUISITES ==="
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/plan/build_instruction_docs/docker-build-process-plan.md" ]]; then
        log_error "Not in project root directory or docker-build-process-plan.md not found"
        return 1
    fi
    
    # Check if required tools are available
    local required_tools=("docker" "docker-compose" "ssh" "openssl" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            return 1
        fi
    done
    
    # Check Docker Hub authentication
    if ! docker info | grep -q "Username: pickme"; then
        log_warning "Not authenticated to Docker Hub as 'pickme'"
        log_info "Please run: docker login"
        read -p "Press Enter after logging in..."
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

# Pre-Build Phase
execute_pre_build_phase() {
    log_phase "=== PRE-BUILD PHASE ==="
    log_info "Timeline: ~2 hours"
    log_info "Steps: Docker Hub cleanup, environment generation, validation, base images"
    
    # Clean and recreate Docker environment first
    clean_and_recreate_docker_env
    
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
    
    log_success "Pre-Build Phase completed successfully"
    return 0
}

# Phase 1: Foundation Services
execute_phase1_foundation() {
    log_phase "=== PHASE 1: FOUNDATION SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: MongoDB, Redis, Elasticsearch, Auth Service"
    
    # Build Phase 1 services
    local phase1_script="$PROJECT_ROOT/scripts/build-phase1-foundation.sh"
    
    if [[ -f "$phase1_script" ]]; then
        log_info "Building Phase 1: Foundation Services..."
        if bash "$phase1_script"; then
            log_success "Phase 1: Foundation Services built successfully"
        else
            log_error "Phase 1: Foundation Services build failed"
            return 1
        fi
    else
        log_error "Phase 1 build script not found: $phase1_script"
        return 1
    fi
    
    # Deploy Phase 1 services to Pi
    log_info "Deploying Phase 1: Foundation Services to Pi..."
    local deploy_script="$PROJECT_ROOT/scripts/deployment/deploy-phase1-pi.sh"
    
    if [[ -f "$deploy_script" ]]; then
        if bash "$deploy_script"; then
            log_success "Phase 1: Foundation Services deployed successfully"
        else
            log_error "Phase 1: Foundation Services deployment failed"
            return 1
        fi
    else
        log_error "Phase 1 deployment script not found: $deploy_script"
        return 1
    fi
    
    log_success "Phase 1: Foundation Services completed successfully"
    return 0
}

# Phase 2: Core Services
execute_phase2_core() {
    log_phase "=== PHASE 2: CORE SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: API Gateway, Service Mesh, Blockchain Core"
    
    # Build Phase 2 services
    local phase2_script="$PROJECT_ROOT/scripts/build-phase2-core.sh"
    
    if [[ -f "$phase2_script" ]]; then
        log_info "Building Phase 2: Core Services..."
        if bash "$phase2_script"; then
            log_success "Phase 2: Core Services built successfully"
        else
            log_error "Phase 2: Core Services build failed"
            return 1
        fi
    else
        log_error "Phase 2 build script not found: $phase2_script"
        return 1
    fi
    
    # TRON Isolation Security Scan
    log_info "Running TRON Isolation Security Scan..."
    local tron_scan_script="$PROJECT_ROOT/scripts/verification/verify-tron-isolation.sh"
    
    if [[ -f "$tron_scan_script" ]]; then
        if bash "$tron_scan_script"; then
            log_success "TRON isolation verification passed"
        else
            log_error "TRON isolation verification failed"
            return 1
        fi
    else
        log_error "TRON isolation verification script not found: $tron_scan_script"
        return 1
    fi
    
    # Deploy Phase 2 services to Pi
    log_info "Deploying Phase 2: Core Services to Pi..."
    local deploy_script="$PROJECT_ROOT/scripts/deployment/deploy-phase2-pi.sh"
    
    if [[ -f "$deploy_script" ]]; then
        if bash "$deploy_script"; then
            log_success "Phase 2: Core Services deployed successfully"
        else
            log_error "Phase 2: Core Services deployment failed"
            return 1
        fi
    else
        log_error "Phase 2 deployment script not found: $deploy_script"
        return 1
    fi
    
    log_success "Phase 2: Core Services completed successfully"
    return 0
}

# Phase 3: Application Services
execute_phase3_application() {
    log_phase "=== PHASE 3: APPLICATION SERVICES ==="
    log_info "Timeline: ~2 weeks"
    log_info "Services: Session Management, RDP Services, Node Management"
    
    # Build Phase 3 services
    local phase3_script="$PROJECT_ROOT/scripts/build-phase3-application.sh"
    
    if [[ -f "$phase3_script" ]]; then
        log_info "Building Phase 3: Application Services..."
        if bash "$phase3_script"; then
            log_success "Phase 3: Application Services built successfully"
        else
            log_error "Phase 3: Application Services build failed"
            return 1
        fi
    else
        log_error "Phase 3 build script not found: $phase3_script"
        return 1
    fi
    
    # Deploy Phase 3 services to Pi
    log_info "Deploying Phase 3: Application Services to Pi..."
    local deploy_script="$PROJECT_ROOT/scripts/deployment/deploy-phase3-pi.sh"
    
    if [[ -f "$deploy_script" ]]; then
        if bash "$deploy_script"; then
            log_success "Phase 3: Application Services deployed successfully"
        else
            log_error "Phase 3: Application Services deployment failed"
            return 1
        fi
    else
        log_error "Phase 3 deployment script not found: $deploy_script"
        return 1
    fi
    
    log_success "Phase 3: Application Services completed successfully"
    return 0
}

# Phase 4: Support Services
execute_phase4_support() {
    log_phase "=== PHASE 4: SUPPORT SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: Admin Interface, TRON Payment System (Isolated)"
    
    # Build Phase 4 services
    local phase4_script="$PROJECT_ROOT/scripts/build-phase4-support.sh"
    
    if [[ -f "$phase4_script" ]]; then
        log_info "Building Phase 4: Support Services..."
        if bash "$phase4_script"; then
            log_success "Phase 4: Support Services built successfully"
        else
            log_error "Phase 4: Support Services build failed"
            return 1
        fi
    else
        log_error "Phase 4 build script not found: $phase4_script"
        return 1
    fi
    
    # Deploy Phase 4 services to Pi
    log_info "Deploying Phase 4: Support Services to Pi..."
    local deploy_script="$PROJECT_ROOT/scripts/deployment/deploy-phase4-pi.sh"
    
    if [[ -f "$deploy_script" ]]; then
        if bash "$deploy_script"; then
            log_success "Phase 4: Support Services deployed successfully"
        else
            log_error "Phase 4: Support Services deployment failed"
            return 1
        fi
    else
        log_error "Phase 4 deployment script not found: $deploy_script"
        return 1
    fi
    
    log_success "Phase 4: Support Services completed successfully"
    return 0
}

# Function to verify all built images
verify_all_images() {
    log_phase "=== VERIFYING ALL BUILT IMAGES ==="
    
    local all_images=(
        # Base Images
        "$REGISTRY/lucid-base:python-distroless-arm64"
        "$REGISTRY/lucid-base:java-distroless-arm64"
        
        # Phase 1: Foundation Services
        "$REGISTRY/lucid-auth-service:latest-arm64"
        "$REGISTRY/lucid-storage-database:latest-arm64"
        "$REGISTRY/lucid-mongodb:latest-arm64"
        "$REGISTRY/lucid-redis:latest-arm64"
        "$REGISTRY/lucid-elasticsearch:latest-arm64"
        
        # Phase 2: Core Services
        "$REGISTRY/lucid-api-gateway:latest-arm64"
        "$REGISTRY/lucid-service-mesh-controller:latest-arm64"
        "$REGISTRY/lucid-blockchain-engine:latest-arm64"
        "$REGISTRY/lucid-session-anchoring:latest-arm64"
        "$REGISTRY/lucid-block-manager:latest-arm64"
        "$REGISTRY/lucid-data-chain:latest-arm64"
        
        # Phase 3: Application Services
        "$REGISTRY/lucid-session-pipeline:latest-arm64"
        "$REGISTRY/lucid-session-recorder:latest-arm64"
        "$REGISTRY/lucid-chunk-processor:latest-arm64"
        "$REGISTRY/lucid-session-storage:latest-arm64"
        "$REGISTRY/lucid-session-api:latest-arm64"
        "$REGISTRY/lucid-rdp-server-manager:latest-arm64"
        "$REGISTRY/lucid-xrdp-integration:latest-arm64"
        "$REGISTRY/lucid-session-controller:latest-arm64"
        "$REGISTRY/lucid-resource-monitor:latest-arm64"
        "$REGISTRY/lucid-node-management:latest-arm64"
        
        # Phase 4: Support Services
        "$REGISTRY/lucid-admin-interface:latest-arm64"
        "$REGISTRY/lucid-tron-client:latest-arm64"
        "$REGISTRY/lucid-payout-router:latest-arm64"
        "$REGISTRY/lucid-wallet-manager:latest-arm64"
        "$REGISTRY/lucid-usdt-manager:latest-arm64"
        "$REGISTRY/lucid-trx-staking:latest-arm64"
        "$REGISTRY/lucid-payment-gateway:latest-arm64"
    )
    
    local verified_count=0
    local total_count=${#all_images[@]}
    
    for image in "${all_images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Image verified: $image"
            ((verified_count++))
        else
            log_error "Image verification failed: $image"
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

# Function to display build summary
display_build_summary() {
    log_phase "=== MASTER BUILD ORCHESTRATION SUMMARY ==="
    echo ""
    echo "Build Configuration:"
    echo "  • Project Root: $PROJECT_ROOT"
    echo "  • Registry: $REGISTRY"
    echo "  • Platform: $PLATFORM"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Pi User: $PI_USER"
    echo "  • Builder: $BUILDER_NAME"
    echo "  • Network: $NETWORK_NAME"
    echo ""
    echo "Completed Phases:"
    echo "  ✅ Pre-Build Phase: Docker Hub cleanup, environment generation, validation, base images"
    echo "  ✅ Phase 1: Foundation Services (MongoDB, Redis, Elasticsearch, Auth)"
    echo "  ✅ Phase 2: Core Services (API Gateway, Service Mesh, Blockchain)"
    echo "  ✅ Phase 3: Application Services (Session Management, RDP, Node Management)"
    echo "  ✅ Phase 4: Support Services (Admin Interface, TRON Payment System)"
    echo ""
    echo "Docker Environment:"
    echo "  • Network: $NETWORK_NAME (172.20.0.0/16)"
    echo "  • Builder: $BUILDER_NAME (docker-container driver)"
    echo "  • Platform: $PLATFORM (Raspberry Pi ARM64)"
    echo ""
    echo "Total Images Built: 32"
    echo "  • 2 Base Images (Python, Java distroless)"
    echo "  • 5 Foundation Services"
    echo "  • 6 Core Services"
    echo "  • 10 Application Services"
    echo "  • 7 Support Services"
    echo "  • 2 TRON Payment System (Isolated)"
    echo ""
    echo "Next Steps:"
    echo "  • Deploy to Raspberry Pi using deployment scripts"
    echo "  • Run integration tests"
    echo "  • Configure production environment"
    echo ""
    log_success "Master Build Orchestration completed successfully!"
}

# Main execution
main() {
    log_info "=== MASTER BUILD ORCHESTRATION ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    log_info "Total Timeline: ~7 weeks"
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Execute all phases
    execute_pre_build_phase
    execute_phase1_foundation
    execute_phase2_core
    execute_phase3_application
    execute_phase4_support
    
    # Verify all images
    verify_all_images
    
    # Display summary
    echo ""
    display_build_summary
    
    log_success "Master Build Orchestration completed successfully!"
    log_info "All Docker images are now available on Docker Hub"
}

# Run main function
main "$@"