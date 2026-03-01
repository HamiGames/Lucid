#!/bin/bash
# Execute Pre-Build Phase from docker-build-process-plan.md
# Implements Steps 1-4 from the build plan

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

# Function to execute step with error handling
execute_step() {
    local step_name=$1
    local script_path=$2
    local description=$3
    
    log_info "=== $step_name ==="
    log_info "$description"
    
    if [[ -f "$script_path" ]]; then
        log_info "Executing: $script_path"
        if bash "$script_path"; then
            log_success "$step_name completed successfully"
            return 0
        else
            log_error "$step_name failed"
            return 1
        fi
    else
        log_error "Script not found: $script_path"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for Pre-Build Phase..."
    
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
    
    log_success "Prerequisites check passed"
    return 0
}

# Step 1: Docker Hub Cleanup
step1_docker_hub_cleanup() {
    log_info "=== STEP 1: DOCKER HUB CLEANUP ==="
    log_info "Cleaning up pickme/lucid Docker Hub registry"
    
    local cleanup_script="$PROJECT_ROOT/scripts/registry/cleanup-dockerhub.sh"
    
    if [[ -f "$cleanup_script" ]]; then
        log_info "Executing Docker Hub cleanup..."
        if bash "$cleanup_script"; then
            log_success "Docker Hub cleanup completed successfully"
        else
            log_warning "Docker Hub cleanup completed with warnings"
        fi
    else
        log_warning "Docker Hub cleanup script not found: $cleanup_script"
        log_info "Skipping Docker Hub cleanup (manual cleanup may be required)"
    fi
    
    # Verify cleanup
    log_info "Verifying cleanup..."
    if docker search pickme/lucid 2>/dev/null | grep -q "No results found"; then
        log_success "Docker Hub cleanup verified - no lucid images found"
    else
        log_warning "Docker Hub cleanup verification failed - images may still exist"
    fi
}

# Step 2: Environment Configuration Generation
step2_environment_configuration() {
    log_info "=== STEP 2: ENVIRONMENT CONFIGURATION GENERATION ==="
    log_info "Generating 6 environment files in configs/environment/"
    
    local env_script="$PROJECT_ROOT/scripts/config/generate-all-env.sh"
    
    if [[ -f "$env_script" ]]; then
        log_info "Executing environment configuration generation..."
        if bash "$env_script"; then
            log_success "Environment configuration generation completed successfully"
        else
            log_error "Environment configuration generation failed"
            return 1
        fi
    else
        log_error "Environment configuration script not found: $env_script"
        return 1
    fi
    
    # Verify environment files
    log_info "Verifying environment files..."
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
            log_success "Environment file exists: $env_file"
        else
            log_error "Environment file not found: $env_file"
            return 1
        fi
    done
    
    # Check for placeholders
    log_info "Checking for placeholder values..."
    for env_file in "${env_files[@]}"; do
        if grep -q '\${' "$PROJECT_ROOT/$env_file"; then
            log_error "Placeholder values found in $env_file"
            return 1
        fi
    done
    
    log_success "Environment files validated - no placeholders found"
}

# Step 3: Build Environment Validation
step3_build_environment_validation() {
    log_info "=== STEP 3: BUILD ENVIRONMENT VALIDATION ==="
    log_info "Validating build environment for Windows 11 console and Pi deployment"
    
    local validation_script="$PROJECT_ROOT/scripts/foundation/validate-build-environment.sh"
    
    if [[ -f "$validation_script" ]]; then
        log_info "Executing build environment validation..."
        if bash "$validation_script"; then
            log_success "Build environment validation completed successfully"
        else
            log_error "Build environment validation failed"
            return 1
        fi
    else
        log_error "Build environment validation script not found: $validation_script"
        return 1
    fi
}

# Step 4: Distroless Base Images
step4_distroless_base_images() {
    log_info "=== STEP 4: DISTROLESS BASE IMAGES ==="
    log_info "Building 2 base images in infrastructure/containers/base/"
    
    local base_images_script="$PROJECT_ROOT/infrastructure/containers/base/build-base-images.sh"
    
    if [[ -f "$base_images_script" ]]; then
        log_info "Executing distroless base images build..."
        if bash "$base_images_script"; then
            log_success "Distroless base images build completed successfully"
        else
            log_error "Distroless base images build failed"
            return 1
        fi
    else
        log_error "Distroless base images script not found: $base_images_script"
        return 1
    fi
    
    # Verify base images
    log_info "Verifying base images in registry..."
    local base_images=(
        "pickme/lucid-base:python-distroless-arm64"
        "pickme/lucid-base:java-distroless-arm64"
    )
    
    for image in "${base_images[@]}"; do
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "Base image verified: $image"
        else
            log_error "Base image verification failed: $image"
            return 1
        fi
    done
}

# Function to display pre-build summary
display_pre_build_summary() {
    log_info "Pre-Build Phase Summary:"
    echo ""
    echo "Completed Steps:"
    echo "  ✅ Step 1: Docker Hub Cleanup"
    echo "  ✅ Step 2: Environment Configuration Generation"
    echo "  ✅ Step 3: Build Environment Validation"
    echo "  ✅ Step 4: Distroless Base Images"
    echo ""
    echo "Generated Files:"
    echo "  • configs/environment/.env.pi-build"
    echo "  • configs/environment/.env.foundation"
    echo "  • configs/environment/.env.core"
    echo "  • configs/environment/.env.application"
    echo "  • configs/environment/.env.support"
    echo "  • configs/environment/.env.gui"
    echo ""
    echo "Built Images:"
    echo "  • pickme/lucid-base:python-distroless-arm64"
    echo "  • pickme/lucid-base:java-distroless-arm64"
    echo ""
    echo "Next Phase: Phase 1 Foundation Services"
    echo "  • MongoDB, Redis, Elasticsearch containers"
    echo "  • Auth service container"
    echo ""
    log_success "Pre-Build Phase completed successfully!"
}

# Main execution
main() {
    log_info "=== EXECUTING PRE-BUILD PHASE ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Timeline: ~2 hours"
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Execute all pre-build steps
    step1_docker_hub_cleanup
    step2_environment_configuration
    step3_build_environment_validation
    step4_distroless_base_images
    
    # Display summary
    echo ""
    display_pre_build_summary
    
    log_success "Pre-Build Phase execution completed successfully!"
    log_info "Ready to proceed with Phase 1: Foundation Services"
}

# Run main function
main "$@"
