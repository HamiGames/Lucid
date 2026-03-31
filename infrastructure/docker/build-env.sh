#!/bin/bash
# Master Build Environment Script for Lucid Docker Services
# File: /app/configs/docker//build-env.sh
# x-lucid-file-path: /app/configs/docker//build-env.sh
# x-lucid-file-directory: /app/configs/docker/
# x-lucid-file-type: shell
# Orchestrates all service-specific build-env scripts
# Generation paths: x-lucid /app/configs, /app/scripts (override with LUCID_IMAGE_APP_ROOT / LUCID_IMAGE_CONFIG_DIR).

set -euo pipefail

# =============================================================================
# PATH CONFIGURATION (x-lucid / container generation targets)
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_IMAGE_APP_ROOT="${LUCID_IMAGE_APP_ROOT:-/app}"
LUCID_IMAGE_CONFIG_DIR="${LUCID_IMAGE_CONFIG_DIR:-/app/configs}"
PROJECT_ROOT="$LUCID_IMAGE_APP_ROOT"
ENV_DIR="$LUCID_IMAGE_CONFIG_DIR"
SCRIPTS_DIR="$LUCID_IMAGE_APP_ROOT/scripts"
CONFIG_SCRIPTS_DIR="$SCRIPTS_DIR/config"

# Optional Pi mounts do not gate writes to ENV_DIR.
validate_pi_mounts() {
    if [[ -d "/mnt/myssd" ]] || [[ -d "/mnt/usb" ]] || [[ -d "/mnt/sdcard" ]]; then
        return 0
    fi
    echo "NOTE: No Pi SSD/USB mount detected; writing env files to $ENV_DIR"
    return 0
}

# Check required packages for Pi console
check_pi_packages() {
    local required_packages=(
        "openssl"
        "git"
        "bash"
        "coreutils"
        "find"
        "grep"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! command -v "$package" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        echo "ERROR: Missing required packages: ${missing_packages[*]}"
        echo "Please install missing packages:"
        echo "sudo apt update && sudo apt install -y ${missing_packages[*]}"
        exit 1
    fi
}

# Validate paths exist (mkdir for x-lucid /app targets; ENV_DIR must be writable)
validate_paths() {
    mkdir -p "$PROJECT_ROOT" "$ENV_DIR" "$SCRIPTS_DIR" "$CONFIG_SCRIPTS_DIR" "$SCRIPT_DIR" 2>/dev/null || true
    if [[ ! -d "$ENV_DIR" ]] || [[ ! -w "$ENV_DIR" ]]; then
        echo "ERROR: Environment directory missing or not writable: $ENV_DIR"
        exit 1
    fi
}

# Check Pi-specific requirements
check_pi_requirements() {
    # Check if running on Pi architecture
    if [[ $(uname -m) != "aarch64" && $(uname -m) != "arm64" ]]; then
        echo "WARNING: Not running on ARM64 architecture. This script is optimized for Raspberry Pi."
    fi
    
    # Check available memory (Pi-specific)
    local available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [[ $available_memory -lt 1024 ]]; then
        echo "WARNING: Low memory detected (${available_memory}MB). Consider closing other applications."
    fi
    
    # Check disk space
    local available_space=$(df /mnt/myssd | awk 'NR==2{print $4}')
    if [[ $available_space -lt 1048576 ]]; then  # 1GB in KB
        echo "WARNING: Low disk space on /mnt/myssd (${available_space}KB available)"
    fi
}

# Enhanced fallback mechanisms for minimal Pi installations
setup_fallback_mechanisms() {
    # Create fallback directories if they don't exist
    local fallback_dirs=(
        "$ENV_DIR"
        "$SCRIPTS_DIR/backup"
        "$SCRIPTS_DIR/logs"
        "$PROJECT_ROOT/data"
        "$PROJECT_ROOT/logs"
    )
    
    for dir in "${fallback_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            echo "Creating fallback directory: $dir"
            mkdir -p "$dir"
        fi
    done
    
    # Set up fallback environment variables
    export LUCID_FALLBACK_MODE=true
    export LUCID_MINIMAL_INSTALL=true
}

# Script Configuration
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# VALIDATION AND INITIALIZATION
# =============================================================================

# Run all validations
validate_pi_mounts
check_pi_packages
validate_paths
check_pi_requirements
setup_fallback_mechanisms

# Create environment directory
mkdir -p "$ENV_DIR"

log_info "Building environment files for Lucid Docker Services"
log_info "Project Root: $PROJECT_ROOT"
log_info "Environment Directory: $ENV_DIR"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Common environment variables for all services
COMMON_ENV_VARS=(
    "PYTHONDONTWRITEBYTECODE=1"
    "PYTHONUNBUFFERED=1"
    "PYTHONPATH=/app"
    "BUILD_TIMESTAMP=$BUILD_TIMESTAMP"
    "GIT_SHA=$GIT_SHA"
    "LUCID_ENV=dev"
    "LUCID_NETWORK=testnet"
    "LUCID_PLANE=ops"
    "LUCID_CLUSTER_ID=dev-core"
    "LOG_LEVEL=DEBUG"
    "PROJECT_ROOT=$PROJECT_ROOT"
    "ENV_DIR=$ENV_DIR"
    "SCRIPTS_DIR=$SCRIPTS_DIR"
    "CONFIG_SCRIPTS_DIR=$CONFIG_SCRIPTS_DIR"
)

# Function to run all service build-env scripts
run_service_scripts() {
    local service_dirs=(
        "blockchain"
        "tools"
        "auth"
        "admin"
        "common"
        "sessions"
        "rdp"
        "users"
        "wallet"
        "gui"
        "vm"
        "node"
        "payment-systems"
        "databases"
    )
    
    for service in "${service_dirs[@]}"; do
        local script_path="$SCRIPT_DIR/$service/build-env.sh"
        if [[ -f "$script_path" ]]; then
            log_info "Running build-env script for $service..."
            if bash "$script_path"; then
                log_success "✅ $service build-env completed successfully"
            else
                log_error "❌ $service build-env failed"
                return 1
            fi
        else
            log_warning "⚠️  Build-env script not found for $service: $script_path"
        fi
    done
}

# Main execution
log_info "Starting master build environment generation..."

if run_service_scripts; then
    log_success "🎉 All service build-env scripts completed successfully"
    log_success "🛡️  Pi console native validation completed"
    log_success "🔧 Fallback mechanisms enabled for minimal Pi installations"
    log_info "📁 All environment files saved to: $ENV_DIR"
    
    # List all generated .env files
    log_info "Generated environment files:"
    find "$ENV_DIR" -name ".env.*" -type f | sort | while read -r file; do
        log_info "  - $(basename "$file")"
    done
    
    echo
    log_info "To use these environment files in Docker builds:"
    log_info "  docker build --env-file $ENV_DIR/.env.<service> -t pickme/lucid:<service> ."
    
else
    log_error "❌ Master build environment generation failed"
    exit 1
fi
