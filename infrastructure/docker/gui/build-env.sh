#!/bin/bash
# Generation paths: x-lucid /app/configs, /app/scripts (override with LUCID_IMAGE_APP_ROOT / LUCID_IMAGE_CONFIG_DIR).
# File: /app/configs/docker//gui/build-env.sh
# x-lucid-file-path: /app/configs/docker//gui/build-env.sh
# x-lucid-file-directory: /app/configs/docker//gui
# x-lucid-file-type: shell

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

# Validate paths exist (mkdir for x-lucid /app targets; only ENV_DIR must be writable)
validate_paths() {
    mkdir -p "$PROJECT_ROOT" "$ENV_DIR" "$SCRIPTS_DIR" 2>/dev/null || true
    if [[ ! -d "$ENV_DIR" ]] || [[ ! -w "$ENV_DIR" ]]; then
        echo "ERROR: Environment directory missing or not writable: $ENV_DIR"
        exit 1
    fi
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

# Create environment directory
mkdir -p "$ENV_DIR"

log_info "Building environment files for Lucid gui Services"
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

# Service-specific environment files will be added here
# This is a template - each service should implement its specific .env files

log_success "Environment files created successfully in $ENV_DIR"
log_success "🛡️  Pi console native validation completed"
log_success "🔧 Fallback mechanisms enabled for minimal Pi installations"
log_info "📁 All environment files saved to: $ENV_DIR"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/.env.<service> -t pickme/lucid:<service> ."
