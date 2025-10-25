#!/bin/bash

# =============================================================================
# LUCID Environment File Permission Verification Script
# =============================================================================
# 
# This script verifies that all .env files have the correct permissions
# based on security requirements and file sensitivity.
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
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
SECRETS_DIR="/mnt/myssd/Lucid/Lucid/configs/secrets"

# Expected permissions
REGULAR_PERMISSIONS="664"
SECURE_PERMISSIONS="600"

# Counters
total_files=0
correct_permissions=0
incorrect_permissions=0
missing_files=0

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

# Function to check file permissions
check_file_permissions() {
    local file_path="$1"
    local expected_perms="$2"
    local file_type="$3"
    
    if [[ -f "$file_path" ]]; then
        local actual_perms=$(stat -c "%a" "$file_path" 2>/dev/null || echo "N/A")
        total_files=$((total_files + 1))
        
        if [[ "$actual_perms" == "$expected_perms" ]]; then
            log_success "$file_type: $file_path - $actual_perms ✓"
            correct_permissions=$((correct_permissions + 1))
            return 0
        else
            log_error "$file_type: $file_path - $actual_perms (expected $expected_perms) ✗"
            incorrect_permissions=$((incorrect_permissions + 1))
            return 1
        fi
    else
        log_warning "File not found: $file_path"
        missing_files=$((missing_files + 1))
        return 1
    fi
}

# Function to check directory permissions
check_directory_permissions() {
    local dir_path="$1"
    local expected_perms="$2"
    local dir_type="$3"
    
    if [[ -d "$dir_path" ]]; then
        local actual_perms=$(stat -c "%a" "$dir_path" 2>/dev/null || echo "N/A")
        total_files=$((total_files + 1))
        
        if [[ "$actual_perms" == "$expected_perms" ]]; then
            log_success "$dir_type: $dir_path - $actual_perms ✓"
            correct_permissions=$((correct_permissions + 1))
        else
            log_error "$dir_type: $dir_path - $actual_perms (expected $expected_perms) ✗"
            incorrect_permissions=$((incorrect_permissions + 1))
        fi
        
        # Check files within directory
        find "$dir_path" -type f -name "*.env*" 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                local file_perms=$(stat -c "%a" "$file" 2>/dev/null || echo "N/A")
                total_files=$((total_files + 1))
                
                if [[ "$file_perms" == "$expected_perms" ]]; then
                    log_success "  └─ $file - $file_perms ✓"
                    correct_permissions=$((correct_permissions + 1))
                else
                    log_error "  └─ $file - $file_perms (expected $expected_perms) ✗"
                    incorrect_permissions=$((incorrect_permissions + 1))
                fi
            fi
        done
    else
        log_warning "Directory not found: $dir_path"
        missing_files=$((missing_files + 1))
    fi
}

# Main verification function
main() {
    log "Starting LUCID Environment File Permission Verification"
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
    
    log "Checking Regular Environment Files (should be 664)..."
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
        check_file_permissions "$file" "$REGULAR_PERMISSIONS" "Regular Environment"
    done
    
    # Check environment subdirectories
    env_subdirs=(
        "$ENV_DIR/development"
        "$ENV_DIR/production"
        "$ENV_DIR/staging"
        "$ENV_DIR/pi"
    )
    
    for dir in "${env_subdirs[@]}"; do
        check_directory_permissions "$dir" "$REGULAR_PERMISSIONS" "Environment Subdirectory"
    done
    
    echo
    log "Checking Secure Secret Files (should be 600)..."
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
        check_file_permissions "$file" "$SECURE_PERMISSIONS" "Secure Secret"
    done
    
    # Check for files with "secrets" in the name
    log "Checking for files with 'secrets' in the name..."
    find "$PROJECT_ROOT" -type f -name "*secrets*" -path "*/configs/*" 2>/dev/null | while read -r file; do
        if [[ -f "$file" ]]; then
            check_file_permissions "$file" "$SECURE_PERMISSIONS" "Secret File"
        fi
    done
    
    # Check secrets directory
    if [[ -d "$SECRETS_DIR" ]]; then
        check_directory_permissions "$SECRETS_DIR" "$SECURE_PERMISSIONS" "Secrets Directory"
    fi
    
    echo
    log "Checking Service-Specific Environment Files (should be 664)..."
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
        check_file_permissions "$file" "$REGULAR_PERMISSIONS" "Service Environment"
    done
    
    # Check API Gateway specific files
    api_gateway_env_dir="$PROJECT_ROOT/03-api-gateway/api"
    if [[ -d "$api_gateway_env_dir" ]]; then
        log "Checking API Gateway environment files..."
        find "$api_gateway_env_dir" -name "*.env*" -type f 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                check_file_permissions "$file" "$REGULAR_PERMISSIONS" "API Gateway Environment"
            fi
        done
    fi
    
    # Check session management files
    sessions_env_dir="$PROJECT_ROOT/sessions/core"
    if [[ -d "$sessions_env_dir" ]]; then
        log "Checking session management environment files..."
        find "$sessions_env_dir" -name "*.env*" -type f 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                check_file_permissions "$file" "$REGULAR_PERMISSIONS" "Session Management Environment"
            fi
        done
    fi
    
    echo
    log "Permission Verification Summary"
    echo "=========================================="
    log "Total files checked: $total_files"
    log_success "Files with correct permissions: $correct_permissions"
    
    if [[ $incorrect_permissions -gt 0 ]]; then
        log_error "Files with incorrect permissions: $incorrect_permissions"
    else
        log_success "Files with incorrect permissions: $incorrect_permissions"
    fi
    
    if [[ $missing_files -gt 0 ]]; then
        log_warning "Missing files: $missing_files"
    else
        log_success "Missing files: $missing_files"
    fi
    
    echo
    if [[ $incorrect_permissions -eq 0 && $missing_files -eq 0 ]]; then
        log_success "All environment file permissions are correctly set!"
        exit 0
    else
        log_error "Some environment file permissions need attention."
        log "Run 'scripts/set-env-permissions.sh' to fix permission issues."
        exit 1
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
