#!/bin/bash
# Master Build Orchestration Script
# Implements the complete docker-build-process-plan.md
# Coordinates all phases: Pre-Build → Phase 1 → Phase 2 → Phase 3 → Phase 4

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
    log_info "Checking prerequisites for Master Build Orchestration..."
    
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
    
    local pre_build_script="$PROJECT_ROOT/scripts/build/execute-pre-build-phase.sh"
    
    if [[ -f "$pre_build_script" ]]; then
        log_info "Executing Pre-Build Phase..."
        if bash "$pre_build_script"; then
            log_success "Pre-Build Phase completed successfully"
            return 0
        else
            log_error "Pre-Build Phase failed"
            return 1
        fi
    else
        log_error "Pre-Build Phase script not found: $pre_build_script"
        return 1
    fi
}

# Phase 1: Foundation Services
execute_phase1_foundation() {
    log_phase "=== PHASE 1: FOUNDATION SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: MongoDB, Redis, Elasticsearch, Auth Service"
    
    local phase1_script="$PROJECT_ROOT/scripts/build-phase1-foundation.sh"
    
    if [[ -f "$phase1_script" ]]; then
        log_info "Executing Phase 1: Foundation Services..."
        if bash "$phase1_script"; then
            log_success "Phase 1: Foundation Services completed successfully"
            return 0
        else
            log_error "Phase 1: Foundation Services failed"
            return 1
        fi
    else
        log_error "Phase 1 script not found: $phase1_script"
        return 1
    fi
}

# Phase 2: Core Services
execute_phase2_core() {
    log_phase "=== PHASE 2: CORE SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: API Gateway, Service Mesh, Blockchain Core"
    
    local phase2_script="$PROJECT_ROOT/scripts/build-phase2-core.sh"
    
    if [[ -f "$phase2_script" ]]; then
        log_info "Executing Phase 2: Core Services..."
        if bash "$phase2_script"; then
            log_success "Phase 2: Core Services completed successfully"
            return 0
        else
            log_error "Phase 2: Core Services failed"
            return 1
        fi
    else
        log_error "Phase 2 script not found: $phase2_script"
        return 1
    fi
}

# Phase 3: Application Services
execute_phase3_application() {
    log_phase "=== PHASE 3: APPLICATION SERVICES ==="
    log_info "Timeline: ~2 weeks"
    log_info "Services: Session Management, RDP Services, Node Management"
    
    local phase3_script="$PROJECT_ROOT/scripts/build-phase3-application.sh"
    
    if [[ -f "$phase3_script" ]]; then
        log_info "Executing Phase 3: Application Services..."
        if bash "$phase3_script"; then
            log_success "Phase 3: Application Services completed successfully"
            return 0
        else
            log_error "Phase 3: Application Services failed"
            return 1
        fi
    else
        log_error "Phase 3 script not found: $phase3_script"
        return 1
    fi
}

# Phase 4: Support Services
execute_phase4_support() {
    log_phase "=== PHASE 4: SUPPORT SERVICES ==="
    log_info "Timeline: ~1 week"
    log_info "Services: Admin Interface, TRON Payment System (Isolated)"
    
    local phase4_script="$PROJECT_ROOT/scripts/build-phase4-support.sh"
    
    if [[ -f "$phase4_script" ]]; then
        log_info "Executing Phase 4: Support Services..."
        if bash "$phase4_script"; then
            log_success "Phase 4: Support Services completed successfully"
            return 0
        else
            log_error "Phase 4: Support Services failed"
            return 1
        fi
    else
        log_error "Phase 4 script not found: $phase4_script"
        return 1
    fi
}

# Function to verify all built images
verify_all_images() {
    log_info "Verifying all built images..."
    
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
    log_info "Master Build Orchestration Summary:"
    echo ""
    echo "Build Configuration:"
    echo "  • Project Root: $PROJECT_ROOT"
    echo "  • Registry: $REGISTRY"
    echo "  • Platform: $PLATFORM"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Pi User: $PI_USER"
    echo ""
    echo "Completed Phases:"
    echo "  ✅ Pre-Build Phase: Docker Hub cleanup, environment generation, validation, base images"
    echo "  ✅ Phase 1: Foundation Services (MongoDB, Redis, Elasticsearch, Auth)"
    echo "  ✅ Phase 2: Core Services (API Gateway, Service Mesh, Blockchain)"
    echo "  ✅ Phase 3: Application Services (Session Management, RDP, Node Management)"
    echo "  ✅ Phase 4: Support Services (Admin Interface, TRON Payment System)"
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
