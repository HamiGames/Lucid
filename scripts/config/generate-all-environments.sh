#!/bin/bash
# Generate All Environment Files for Lucid Project
# Based on: distro-deployment-plan.md requirements
# Generated: 2025-01-14

set -euo pipefail

# Project root configuration - Dynamic detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  Lucid Environment Configuration Generator${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

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

# Function to check if script exists and is executable
check_script() {
    local script_path="$1"
    local script_name="$(basename "$script_path")"
    
    if [ ! -f "$script_path" ]; then
        log_error "Script not found: $script_name"
        return 1
    fi
    
    if [ ! -x "$script_path" ]; then
        log_warning "Script not executable: $script_name"
        chmod +x "$script_path"
        log_success "Made $script_name executable"
    fi
    
    return 0
}

# Function to run script with error handling
run_script() {
    local script_path="$1"
    local script_name="$(basename "$script_path")"
    
    log_info "Running $script_name..."
    
    if bash "$script_path"; then
        log_success "$script_name completed successfully"
        return 0
    else
        log_error "$script_name failed with exit code $?"
        return 1
    fi
}

# Function to validate generated files
validate_generated_files() {
    log_info "Validating generated environment files..."
    
    local env_files=(
        ".env.distroless"
        ".env.foundation"
        ".env.core"
        ".env.application"
        ".env.support"
    )
    
    local configs_dir="configs/environment"
    local all_valid=true
    
    for env_file in "${env_files[@]}"; do
        local file_path="$configs_dir/$env_file"
        
        if [[ -f "$file_path" ]]; then
            # Check for placeholder values
            if grep -q '\${' "$file_path"; then
                log_error "Placeholder values found in $env_file"
                all_valid=false
            else
                log_success "$env_file validated"
            fi
            
            # Check file size
            local file_size=$(wc -c < "$file_path")
            if [[ $file_size -lt 100 ]]; then
                log_error "File $env_file is too small ($file_size bytes)"
                all_valid=false
            fi
        else
            log_error "File not found: $env_file"
            all_valid=false
        fi
    done
    
    if [ "$all_valid" = true ]; then
        log_success "All environment files validated successfully"
        return 0
    else
        log_error "Some environment files failed validation"
        return 1
    fi
}

# Function to display summary
display_summary() {
    log_info "Environment Configuration Generation Summary:"
    echo ""
    echo "Generated Files:"
    echo "  • configs/environment/.env.distroless (Main distroless environment)"
    echo "  • configs/environment/.env.foundation (Phase 1 Foundation Services)"
    echo "  • configs/environment/.env.core (Phase 2 Core Services)"
    echo "  • configs/environment/.env.application (Phase 3 Application Services)"
    echo "  • configs/environment/.env.support (Phase 4 Support Services)"
    echo ""
    echo "Configuration Details:"
    echo "  • All files generated with secure random values"
    echo "  • Distroless runtime configuration included"
    echo "  • Network configuration for Raspberry Pi deployment"
    echo "  • Security keys generated with cryptographic strength"
    echo "  • Container configuration optimized for distroless runtime"
    echo ""
    log_success "Environment configuration generation completed successfully!"
}

# Main execution function
main() {
    log_info "=== Lucid Environment Configuration Generator ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Script Directory: $SCRIPT_DIR"
    echo ""
    
    # Define scripts to run in order
    local scripts=(
        "scripts/config/generate-secure-keys.sh"
        "scripts/config/generate-distroless-env.sh"
        "scripts/config/generate-foundation-env.sh"
        "scripts/config/generate-core-env.sh"
        "scripts/config/generate-application-env.sh"
        "scripts/config/generate-support-env.sh"
    )
    
    # Check all scripts exist and are executable
    log_info "Checking required scripts..."
    for script in "${scripts[@]}"; do
        if ! check_script "$script"; then
            log_error "Required script not found or not executable: $script"
            exit 1
        fi
    done
    log_success "All required scripts are available and executable"
    echo ""
    
    # Run scripts in order
    log_info "Generating environment configurations..."
    local failed_scripts=()
    
    for script in "${scripts[@]}"; do
        if ! run_script "$script"; then
            failed_scripts+=("$(basename "$script")")
        fi
        echo ""
    done
    
    # Check for failed scripts
    if [ ${#failed_scripts[@]} -gt 0 ]; then
        log_error "The following scripts failed:"
        for failed_script in "${failed_scripts[@]}"; do
            echo "  • $failed_script"
        done
        exit 1
    fi
    
    # Validate generated files
    echo ""
    if ! validate_generated_files; then
        log_error "Environment file validation failed"
        exit 1
    fi
    
    # Display summary
    echo ""
    display_summary
}

# Run main function
main "$@"
