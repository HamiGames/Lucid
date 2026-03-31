#!/bin/bash
# =============================================================================
# File: /app/scripts/generate-env.sh
# x-lucid-file-path: /app/scripts/generate-env.sh
# x-lucid-file-directory: /app/scripts
# x-lucid-file-type: shell
# Lucid Environment Generation Wrapper - Pi Console Native
# =============================================================================
# This script is a wrapper for the master environment generator
# Provides a simple interface for generating all environment configurations
# =============================================================================

set -euo pipefail

# =============================================================================
# GLOBAL PATH CONFIGURATION
# =============================================================================
_lucid_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_lucid_scripts="$_lucid_here"
while [[ "$_lucid_scripts" != "/" && "$(basename "$_lucid_scripts")" != "scripts" ]]; do
    _lucid_scripts="$(dirname "$_lucid_scripts")"
done
# shellcheck source=lib/lucid-repo-paths.sh
source "$_lucid_scripts/lib/lucid-repo-paths.sh"

PROJECT_ROOT="$LUCID_REPO_ROOT"
ENV_CONFIG_DIR="$LUCID_ENV_CONFIG_DIR"
SCRIPTS_CONFIG_DIR="$LUCID_SCRIPTS_DIR/config"
SCRIPTS_DIR="$LUCID_SCRIPTS_DIR"

SCRIPT_DIR="$_lucid_here"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }

# =============================================================================
# PI CONSOLE NATIVE VALIDATION
# =============================================================================
# Check if running on Pi console
check_pi_console() {
    log_info "Validating Pi console environment..."
    
    # Check if we're on a Pi
    if [ -f "/proc/device-tree/model" ]; then
        local model=$(cat /proc/device-tree/model 2>/dev/null || echo "unknown")
        if [[ "$model" == *"Raspberry Pi"* ]]; then
            log_success "Running on Raspberry Pi: $model"
            return 0
        fi
    fi
    
    # Check for Pi-specific hardware
    if [ -d "/sys/class/gpio" ] && [ -f "/proc/cpuinfo" ]; then
        if grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
            log_success "Running on Pi-compatible hardware"
            return 0
        fi
    fi
    
    log_warning "Not running on Pi console - some features may be limited"
    return 1
}

# Validate Pi mount points
validate_pi_mounts() {
    log_info "Validating Pi mount points..."
    
    local pi_mount_points=(
        "/mnt/myssd"
        "/mnt/usb"
        "/mnt/sdcard"
        "/opt"
        "/var"
        "/tmp"
    )
    
    local valid_mounts=0
    local total_mounts=${#pi_mount_points[@]}
    
    for mount_point in "${pi_mount_points[@]}"; do
        if [ -d "$mount_point" ] && [ -w "$mount_point" ]; then
            log_success "Mount point accessible: $mount_point"
            ((valid_mounts++))
        else
            log_warning "Mount point not accessible: $mount_point"
        fi
    done
    
    if [ $valid_mounts -eq 0 ]; then
        log_error "No valid mount points found! Cannot proceed."
        return 1
    elif [ $valid_mounts -lt $((total_mounts / 2)) ]; then
        log_warning "Limited mount points available - using fallback mechanisms"
    fi
    
    return 0
}

# Check required packages
check_pi_packages() {
    log_info "Checking required packages for Pi console..."
    
    local required_packages=(
        "openssl"
        "coreutils"
        "util-linux"
        "procps"
        "grep"
        "sed"
        "awk"
        "bash"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if command -v "$package" >/dev/null 2>&1; then
            log_success "Package available: $package"
        else
            log_warning "Package missing: $package"
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_warning "Missing packages: ${missing_packages[*]}"
        log_info "Attempting to install missing packages..."
        
        # Try to install missing packages
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update >/dev/null 2>&1 || true
            for package in "${missing_packages[@]}"; do
                if sudo apt-get install -y "$package" >/dev/null 2>&1; then
                    log_success "Installed: $package"
                else
                    log_warning "Failed to install: $package - using fallback"
                fi
            done
        else
            log_warning "Package manager not available - using fallback mechanisms"
        fi
    fi
    
    return 0
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    log_info "==================================================================="
    log_info "LUCID ENVIRONMENT GENERATION WRAPPER - PI CONSOLE NATIVE"
    log_info "==================================================================="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Environment Config: $ENV_CONFIG_DIR"
    log_info "Scripts Config: $SCRIPTS_CONFIG_DIR"
    echo ""
    
    # Pi console native validation
    log_info "Step 1: Pi Console Native Validation"
    if ! check_pi_console; then
        log_warning "Not running on Pi console - some features may be limited"
    fi
    
    if ! validate_pi_mounts; then
        log_error "Pi mount validation failed!"
        exit 1
    fi
    
    if ! check_pi_packages; then
        log_warning "Package validation completed with warnings"
    fi
    
    log_success "Pi console native validation completed"
    echo ""
    
    # Change to project root if not already there
    if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
        log_info "Changing to project root: $PROJECT_ROOT"
        cd "$PROJECT_ROOT"
    fi
    
    # Run the master environment generation script
    log_info "Step 2: Running Master Environment Generator"
    if [ -f "$SCRIPTS_CONFIG_DIR/generate-env.sh" ]; then
        log_info "Executing master environment generator..."
        bash "$SCRIPTS_CONFIG_DIR/generate-env.sh"
        log_success "Master environment generation completed"
    else
        log_error "Master environment generator not found: $SCRIPTS_CONFIG_DIR/generate-env.sh"
        exit 1
    fi
    
    echo ""
    
    # Run service-specific generators
    log_info "Step 3: Running Service-Specific Generators"
    
    # Session Core Generator
    if [ -f "$PROJECT_ROOT/sessions/core/generate-env.sh" ]; then
        log_info "Running Session Core environment generator..."
        bash "$PROJECT_ROOT/sessions/core/generate-env.sh"
        log_success "Session Core environment generation completed"
    else
        log_warning "Session Core generator not found"
    fi
    
    # API Gateway Generator (repo dir: 03_api_gateway — x-lucid: /app/03_api_gateway/api)
    if [ -f "$PROJECT_ROOT/03_api_gateway/api/generate-env.sh" ]; then
        log_info "Running API Gateway environment generator..."
        bash "$PROJECT_ROOT/03_api_gateway/api/generate-env.sh"
        log_success "API Gateway environment generation completed"
    else
        log_warning "API Gateway generator not found"
    fi
    
    echo ""
    
    # Final summary
    log_info "==================================================================="
    log_info "ENVIRONMENT GENERATION COMPLETE!"
    log_info "==================================================================="
    echo ""
    log_info "Generated environment files:"
    if [ -d "$ENV_CONFIG_DIR" ]; then
        for env_file in "$ENV_CONFIG_DIR"/.env.*; do
            if [ -f "$env_file" ]; then
                local filename=$(basename "$env_file")
                log_info "  • $filename"
            fi
        done
    fi
    echo ""
    log_success "All environment generation completed successfully!"
    echo ""
    log_warning "SECURITY NOTICE:"
    log_warning "  • Keep .env.secrets file secure (chmod 600)"
    log_warning "  • Never commit .env.secrets to version control"
    log_warning "  • Backup secrets file to secure location"
    log_warning "  • Rotate keys regularly in production"
}

# Run main function
main "$@"
