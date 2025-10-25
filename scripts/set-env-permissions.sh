#!/bin/bash

# =============================================================================
# LUCID Environment File Permission Setting Script
# =============================================================================
# 
# This script sets appropriate permissions for all .env files in the Lucid project
# based on security requirements and file sensitivity.
#
# Permission Categories:
# - Regular Environment Files (664): Standard env files for development, staging, production, test
# - Secure Secret Files (600): Files containing secrets, passwords, or sensitive data
#
# Target Platform: Raspberry Pi (linux/arm64)
# Base Path: /mnt/myssd/Lucid/Lucid/
#
# =============================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_NAME="set-env-permissions.sh"
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
SECRETS_DIR="/mnt/myssd/Lucid/Lucid/configs/secrets"

# Permission settings
REGULAR_PERMISSIONS="664"  # rw-rw-r--
SECURE_PERMISSIONS="600"   # rw-------

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Function to set permissions for a file
set_file_permissions() {
    local file_path="$1"
    local permissions="$2"
    local file_type="$3"
    
    if [[ -f "$file_path" ]]; then
        if chmod "$permissions" "$file_path" 2>/dev/null; then
            log_success "Set $permissions permissions for $file_type: $file_path"
            return 0
        else
            log_error "Failed to set permissions for: $file_path"
            return 1
        fi
    else
        log_warning "File not found: $file_path"
        return 1
    fi
}

# Function to set permissions for directory and all files within
set_directory_permissions() {
    local dir_path="$1"
    local permissions="$2"
    local file_type="$3"
    
    if [[ -d "$dir_path" ]]; then
        # Set directory permissions
        if chmod "$permissions" "$dir_path" 2>/dev/null; then
            log_success "Set $permissions permissions for $file_type directory: $dir_path"
        else
            log_error "Failed to set directory permissions for: $dir_path"
            return 1
        fi
        
        # Set permissions for all files in directory
        find "$dir_path" -type f -name "*.env*" -exec chmod "$permissions" {} \; 2>/dev/null || true
        find "$dir_path" -type f -name "*.yml" -exec chmod "$permissions" {} \; 2>/dev/null || true
        find "$dir_path" -type f -name "*.yaml" -exec chmod "$permissions" {} \; 2>/dev/null || true
    else
        log_warning "Directory not found: $dir_path"
        return 1
    fi
}

# Main execution function
main() {
    log "Starting LUCID Environment File Permission Setting"
    log "Project Root: $PROJECT_ROOT"
    log "Environment Directory: $ENV_DIR"
    log "Secrets Directory: $SECRETS_DIR"
    echo
    
    # Check if running on correct platform
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "Project root directory not found: $PROJECT_ROOT"
        log_error "Please ensure you're running this script on the Raspberry Pi"
        exit 1
    fi
    
    # Change to project root directory
    cd "$PROJECT_ROOT" || {
        log_error "Failed to change to project root directory"
        exit 1
    }
    
    log "Setting permissions for Regular Environment Files (664)..."
    echo "=========================================="
    
    # Regular Environment Files (664 permissions)
    regular_files=(
        # env.* files (without dot prefix)
        "$ENV_DIR/env.development"
        "$ENV_DIR/env.staging" 
        "$ENV_DIR/env.production"
        "$ENV_DIR/env.test"
        "$ENV_DIR/env.coordination.yml"
        "$ENV_DIR/env.foundation"
        "$ENV_DIR/env.core"
        "$ENV_DIR/env.application"
        "$ENV_DIR/env.support"
        "$ENV_DIR/env.gui"
        "$ENV_DIR/env.pi-build"
        "$ENV_DIR/layer2.env"
        "$ENV_DIR/layer2-simple.env"
        # .env.* files (with dot prefix)
        "$ENV_DIR/.env.application"
        "$ENV_DIR/.env.core"
        "$ENV_DIR/.env.distroless"
        "$ENV_DIR/.env.foundation"
        "$ENV_DIR/.env.gui"
        "$ENV_DIR/.env.pi-build"
        "$ENV_DIR/.env.support"
        "$ENV_DIR/.env.api"
        "$ENV_DIR/.env.user"
    )
    
    for file in "${regular_files[@]}"; do
        set_file_permissions "$file" "$REGULAR_PERMISSIONS" "Regular Environment"
    done
    
    # Set permissions for environment subdirectories
    env_subdirs=(
        "$ENV_DIR/development"
        "$ENV_DIR/production"
        "$ENV_DIR/staging"
        "$ENV_DIR/pi"
    )
    
    for dir in "${env_subdirs[@]}"; do
        set_directory_permissions "$dir" "$REGULAR_PERMISSIONS" "Environment Subdirectory"
    done
    
    echo
    log "Setting permissions for Secure Secret Files (600)..."
    echo "=========================================="
    
    # Secure Secret Files (600 permissions)
    secure_files=(
        "$ENV_DIR/.env.secure"
        "$ENV_DIR/.env.secrets"
        "$ENV_DIR/.env.tron-secrets"
        "$SECRETS_DIR/.env.secrets"
        "$SECRETS_DIR/.env.secure"
        "$SECRETS_DIR/.env.tron-secrets"
    )
    
    for file in "${secure_files[@]}"; do
        set_file_permissions "$file" "$SECURE_PERMISSIONS" "Secure Secret"
    done
    
    # Find and set permissions for any files with "secrets" in the name
    log "Searching for files with 'secrets' in the name..."
    find "$PROJECT_ROOT" -type f -name "*secrets*" -path "*/configs/*" 2>/dev/null | while read -r file; do
        if [[ -f "$file" ]]; then
            set_file_permissions "$file" "$SECURE_PERMISSIONS" "Secret File"
        fi
    done
    
    # Set permissions for secrets directory
    if [[ -d "$SECRETS_DIR" ]]; then
        set_directory_permissions "$SECRETS_DIR" "$SECURE_PERMISSIONS" "Secrets Directory"
    fi
    
    echo
    log "Setting permissions for Service-Specific Environment Files..."
    echo "=========================================="
    
    # Service-specific environment files (664 permissions)
    service_files=(
        "$ENV_DIR/.env.api-gateway"
        "$ENV_DIR/.env.api-server"
        "$ENV_DIR/.env.authentication"
        "$ENV_DIR/.env.authentication-service-distroless"
        "$ENV_DIR/.env.orchestrator"
        "$ENV_DIR/.env.chunker"
        "$ENV_DIR/.env.merkle-builder"
        "$ENV_DIR/.env.tor-proxy"
        "$ENV_DIR/.env.tunnel-tools"
        "$ENV_DIR/.env.server-tools"
        "$ENV_DIR/.env.openapi-gateway"
        "$ENV_DIR/.env.openapi-server"
        "$ENV_DIR/.env.blockchain-api"
        "$ENV_DIR/.env.blockchain-governance"
        "$ENV_DIR/.env.tron-client"
        "$ENV_DIR/.env.tron-payout-router"
        "$ENV_DIR/.env.tron-wallet-manager"
        "$ENV_DIR/.env.tron-usdt-manager"
        "$ENV_DIR/.env.tron-staking"
        "$ENV_DIR/.env.tron-payment-gateway"
    )
    
    for file in "${service_files[@]}"; do
        set_file_permissions "$file" "$REGULAR_PERMISSIONS" "Service Environment"
    done
    
    # Set permissions for API Gateway specific files
    api_gateway_env_dir="$PROJECT_ROOT/03-api-gateway/api"
    if [[ -d "$api_gateway_env_dir" ]]; then
        find "$api_gateway_env_dir" -name "*.env*" -type f -exec chmod "$REGULAR_PERMISSIONS" {} \; 2>/dev/null || true
        log_success "Set permissions for API Gateway environment files"
    fi
    
    # Set permissions for session management files
    sessions_env_dir="$PROJECT_ROOT/sessions/core"
    if [[ -d "$sessions_env_dir" ]]; then
        find "$sessions_env_dir" -name "*.env*" -type f -exec chmod "$REGULAR_PERMISSIONS" {} \; 2>/dev/null || true
        log_success "Set permissions for session management environment files"
    fi
    
    echo
    log "Verifying permissions..."
    echo "=========================================="
    
    # Verify regular environment files
    log "Regular Environment Files (should be 664):"
    for file in "${regular_files[@]}"; do
        if [[ -f "$file" ]]; then
            perms=$(stat -c "%a" "$file" 2>/dev/null || echo "N/A")
            if [[ "$perms" == "664" ]]; then
                log_success "$file: $perms ✓"
            else
                log_warning "$file: $perms (expected 664)"
            fi
        fi
    done
    
    # Verify secure files
    log "Secure Secret Files (should be 600):"
    for file in "${secure_files[@]}"; do
        if [[ -f "$file" ]]; then
            perms=$(stat -c "%a" "$file" 2>/dev/null || echo "N/A")
            if [[ "$perms" == "600" ]]; then
                log_success "$file: $perms ✓"
            else
                log_warning "$file: $perms (expected 600)"
            fi
        fi
    done
    
    echo
    log_success "Environment file permission setting completed!"
    log "Summary:"
    log "- Regular environment files: 664 (rw-rw-r--)"
    log "- Secure secret files: 600 (rw-------)"
    log "- All files processed according to security requirements"
    
    echo
    log "Script completed successfully!"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
