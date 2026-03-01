#!/bin/bash
# Master Build Orchestration Script
# Runs all phases of the Docker build process in sequence
# Based on docker-build-process-plan.md

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
MASTER_START_TIME=$(date +%s)
FAILED_PHASES=()
SUCCESSFUL_PHASES=()

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/README.md" ]]; then
        log_error "Not in Lucid project root directory"
        exit 1
    fi
    
    # Check if all build scripts exist
    local build_scripts=(
        "scripts/build/pre-build-phase.sh"
        "scripts/build/phase1-foundation-services.sh"
        "scripts/build/phase2-core-services.sh"
        "scripts/build/phase3-application-services.sh"
        "scripts/build/phase4-support-services.sh"
    )
    
    for script in "${build_scripts[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$script" ]]; then
            log_error "Build script not found: $script"
            exit 1
        fi
    done
    
    log_success "All build scripts found"
}

# Run a phase script
run_phase() {
    local phase_name="$1"
    local script_path="$2"
    local description="$3"
    
    log_phase "Starting $phase_name: $description"
    echo "=================================================="
    
    local phase_start_time=$(date +%s)
    
    if bash "$PROJECT_ROOT/$script_path"; then
        local phase_end_time=$(date +%s)
        local phase_duration=$((phase_end_time - phase_start_time))
        local duration_minutes=$((phase_duration / 60))
        local duration_seconds=$((phase_duration % 60))
        
        log_success "$phase_name completed successfully in ${duration_minutes}m ${duration_seconds}s"
        SUCCESSFUL_PHASES+=("$phase_name")
    else
        local phase_end_time=$(date +%s)
        local phase_duration=$((phase_end_time - phase_start_time))
        local duration_minutes=$((phase_duration / 60))
        local duration_seconds=$((phase_duration % 60))
        
        log_error "$phase_name failed after ${duration_minutes}m ${duration_seconds}s"
        FAILED_PHASES+=("$phase_name")
        
        # Ask user if they want to continue
        echo
        log_warning "Phase $phase_name failed. Do you want to continue with the remaining phases?"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Build process stopped by user"
            exit 1
        fi
    fi
    
    echo
}

# Generate master summary
generate_master_summary() {
    local master_end_time=$(date +%s)
    local master_duration=$((master_end_time - MASTER_START_TIME))
    local duration_hours=$((master_duration / 3600))
    local duration_minutes=$(((master_duration % 3600) / 60))
    local duration_seconds=$((master_duration % 60))
    
    echo
    log_phase "Master Build Orchestration Summary"
    echo "======================================"
    echo "Total Duration: ${duration_hours}h ${duration_minutes}m ${duration_seconds}s"
    echo "Total Phases: $((${#SUCCESSFUL_PHASES[@]} + ${#FAILED_PHASES[@]}))"
    echo "Successful: ${#SUCCESSFUL_PHASES[@]}"
    echo "Failed: ${#FAILED_PHASES[@]}"
    echo
    
    if [[ ${#SUCCESSFUL_PHASES[@]} -gt 0 ]]; then
        log_success "Successfully completed phases:"
        for phase in "${SUCCESSFUL_PHASES[@]}"; do
            echo "  - $phase"
        done
    fi
    
    if [[ ${#FAILED_PHASES[@]} -gt 0 ]]; then
        log_error "Failed phases:"
        for phase in "${FAILED_PHASES[@]}"; do
            echo "  - $phase"
        done
        echo
        log_error "Master build completed with errors."
        log_info "You can retry individual phases:"
        for phase in "${FAILED_PHASES[@]}"; do
            case $phase in
                "Pre-Build Phase")
                    echo "  ./scripts/build/pre-build-phase.sh"
                    ;;
                "Phase 1: Foundation Services")
                    echo "  ./scripts/build/phase1-foundation-services.sh"
                    ;;
                "Phase 2: Core Services")
                    echo "  ./scripts/build/phase2-core-services.sh"
                    ;;
                "Phase 3: Application Services")
                    echo "  ./scripts/build/phase3-application-services.sh"
                    ;;
                "Phase 4: Support Services")
                    echo "  ./scripts/build/phase4-support-services.sh"
                    ;;
            esac
        done
        exit 1
    else
        log_success "🎉 All phases completed successfully!"
        echo
        log_info "Lucid system is ready for production deployment!"
        echo
        log_info "Next Steps:"
        echo "  1. Deploy to Pi: ./scripts/deployment/deploy-phase4-pi.sh"
        echo "  2. Run final integration tests: ./tests/integration/final/run_final_integration_test.sh"
        echo "  3. Use master compose: ./configs/docker/docker-compose.master.yml"
        echo
        log_success "Build process completed successfully!"
    fi
}

# Main execution
main() {
    echo "🚀 Lucid Master Build Orchestration"
    echo "==================================="
    echo "This script will run all build phases in sequence:"
    echo "  1. Pre-Build Phase (Environment setup, base images)"
    echo "  2. Phase 1: Foundation Services (MongoDB, Redis, Elasticsearch, Auth)"
    echo "  3. Phase 2: Core Services (API Gateway, Service Mesh, Blockchain)"
    echo "  4. Phase 3: Application Services (Sessions, RDP, Node Management)"
    echo "  5. Phase 4: Support Services (Admin, TRON Payment)"
    echo
    echo "Estimated total time: 3-4 hours"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Ask user for confirmation
    log_warning "This will build and push all Lucid containers to Docker Hub."
    log_warning "Make sure you have:"
    log_warning "  - Docker Hub credentials configured"
    log_warning "  - Sufficient disk space (20GB+)"
    log_warning "  - Stable internet connection"
    echo
    read -p "Continue with master build? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Build process cancelled by user"
        exit 0
    fi
    
    echo
    log_phase "Starting Master Build Process"
    echo "================================="
    
    # Run all phases
    run_phase "Pre-Build Phase" "scripts/build/pre-build-phase.sh" "Environment setup and base images"
    run_phase "Phase 1: Foundation Services" "scripts/build/phase1-foundation-services.sh" "MongoDB, Redis, Elasticsearch, Auth"
    run_phase "Phase 2: Core Services" "scripts/build/phase2-core-services.sh" "API Gateway, Service Mesh, Blockchain"
    run_phase "Phase 3: Application Services" "scripts/build/phase3-application-services.sh" "Sessions, RDP, Node Management"
    run_phase "Phase 4: Support Services" "scripts/build/phase4-support-services.sh" "Admin Interface, TRON Payment"
    
    # Generate summary
    generate_master_summary
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --help                 Show this help message"
            echo
            echo "This script orchestrates the complete Lucid build process:"
            echo "  1. Pre-Build Phase: Environment setup and base images"
            echo "  2. Phase 1: Foundation Services (MongoDB, Redis, Elasticsearch, Auth)"
            echo "  3. Phase 2: Core Services (API Gateway, Service Mesh, Blockchain)"
            echo "  4. Phase 3: Application Services (Sessions, RDP, Node Management)"
            echo "  5. Phase 4: Support Services (Admin Interface, TRON Payment)"
            echo
            echo "Individual phases can be run separately:"
            echo "  ./scripts/build/pre-build-phase.sh"
            echo "  ./scripts/build/phase1-foundation-services.sh"
            echo "  ./scripts/build/phase2-core-services.sh"
            echo "  ./scripts/build/phase3-application-services.sh"
            echo "  ./scripts/build/phase4-support-services.sh"
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