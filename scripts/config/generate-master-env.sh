#!/bin/bash
# Master Environment Generation Script for Lucid Project
# Coordinates all environment generation scripts to ensure alignment
# Generated: 2025-01-14

set -euo pipefail

# Project root configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo -e "${BLUE}🔧 Master Environment Generation for Lucid Project${NC}"
echo "=================================================="
echo "Project Root: $PROJECT_ROOT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Function to check if script exists and is executable
check_script() {
    local script_path="$1"
    if [ ! -f "$script_path" ]; then
        log_error "Script not found: $script_path"
        exit 1
    fi
    if [ ! -x "$script_path" ]; then
        log_warning "Making script executable: $script_path"
        chmod +x "$script_path"
    fi
}

# Function to run script with error handling
run_script() {
    local script_name="$1"
    local script_path="$2"
    
    log_info "Running $script_name..."
    
    if bash "$script_path"; then
        log_success "$script_name completed successfully"
    else
        log_error "$script_name failed with exit code $?"
        exit 1
    fi
}

# Function to validate generated files
validate_generated_files() {
    log_info "Validating generated environment files..."
    
    local env_files=(
        "configs/environment/.env.secure"
        "configs/environment/.env.distroless"
        "configs/environment/env.foundation"
        "configs/environment/env.core"
        "configs/environment/env.application"
        "configs/environment/env.support"
    )
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            # Check file size
            local file_size=$(wc -c < "$env_file")
            if [[ $file_size -lt 100 ]]; then
                log_error "File $env_file is too small ($file_size bytes)"
                exit 1
            fi
            
            # Check for placeholder values that shouldn't be there
            if grep -q '\${[A-Z_]*}' "$env_file" && ! grep -q 'MONGODB_PASSWORD=\${MONGODB_PASSWORD}' "$env_file"; then
                log_warning "Potential placeholder values found in $env_file"
            fi
            
            log_success "$env_file validated"
        else
            log_error "File not found: $env_file"
            exit 1
        fi
    done
    
    log_success "All environment files validated"
}

# Function to display summary
display_summary() {
    log_info "Environment Generation Summary:"
    echo ""
    echo "Generated Files:"
    echo "  • configs/environment/.env.secure (Master secure keys)"
    echo "  • configs/environment/.env.distroless (Distroless deployment)"
    echo "  • configs/environment/env.foundation (Foundation services)"
    echo "  • configs/environment/env.core (Core services)"
    echo "  • configs/environment/env.application (Application services)"
    echo "  • configs/environment/env.support (Support services)"
    echo ""
    echo "Key Features:"
    echo "  • All scripts use consistent project root: $PROJECT_ROOT"
    echo "  • Secure key generation aligned across all scripts"
    echo "  • Environment variables properly referenced"
    echo "  • Distroless configuration optimized for Raspberry Pi"
    echo "  • Network configuration for 6 Docker networks"
    echo ""
    log_success "Master environment generation completed successfully!"
}

# Main execution
main() {
    log_info "=== Master Environment Generation ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Script Directory: $SCRIPT_DIR"
    echo ""
    
    # Check all required scripts exist
    log_info "Checking required scripts..."
    check_script "$SCRIPT_DIR/generate-secure-keys.sh"
    check_script "$SCRIPT_DIR/generate-distroless-env.sh"
    check_script "$SCRIPT_DIR/generate-all-env.sh"
    
    # Run scripts in order
    log_info "Running environment generation scripts..."
    echo ""
    
    # Step 1: Generate secure keys (master source)
    run_script "Secure Keys Generation" "$SCRIPT_DIR/generate-secure-keys.sh"
    echo ""
    
    # Step 2: Generate distroless environment
    run_script "Distroless Environment Generation" "$SCRIPT_DIR/generate-distroless-env.sh"
    echo ""
    
    # Step 3: Generate all other environments
    run_script "All Environment Generation" "$SCRIPT_DIR/generate-all-env.sh"
    echo ""
    
    # Validate all generated files
    validate_generated_files
    
    # Display summary
    echo ""
    display_summary
}

# Run main function
main "$@"
