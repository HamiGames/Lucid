#!/bin/bash

# =============================================================================
# LUCID Environment File Permission Display Script
# =============================================================================
# 
# This script displays the current permissions for all .env files
# in a readable format for quick reference.
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
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
SECRETS_DIR="/mnt/myssd/Lucid/Lucid/configs/secrets"

# Expected permissions
REGULAR_PERMISSIONS="664"
SECURE_PERMISSIONS="600"

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

# Function to display file permissions with color coding
display_file_permissions() {
    local file_path="$1"
    local expected_perms="$2"
    local file_type="$3"
    
    if [[ -f "$file_path" ]]; then
        local actual_perms=$(stat -c "%a" "$file_path" 2>/dev/null || echo "N/A")
        local file_size=$(stat -c "%s" "$file_path" 2>/dev/null || echo "N/A")
        local file_owner=$(stat -c "%U:%G" "$file_path" 2>/dev/null || echo "N/A")
        
        if [[ "$actual_perms" == "$expected_perms" ]]; then
            echo -e "${GREEN}✓${NC} ${CYAN}$file_type${NC}: ${file_path}"
            echo -e "    Permissions: ${GREEN}$actual_perms${NC} (${expected_perms}) | Size: ${file_size} bytes | Owner: ${file_owner}"
        else
            echo -e "${RED}✗${NC} ${CYAN}$file_type${NC}: ${file_path}"
            echo -e "    Permissions: ${RED}$actual_perms${NC} (expected ${expected_perms}) | Size: ${file_size} bytes | Owner: ${file_owner}"
        fi
    else
        echo -e "${YELLOW}⚠${NC} ${CYAN}$file_type${NC}: ${file_path} (FILE NOT FOUND)"
    fi
}

# Function to display directory permissions
display_directory_permissions() {
    local dir_path="$1"
    local expected_perms="$2"
    local dir_type="$3"
    
    if [[ -d "$dir_path" ]]; then
        local actual_perms=$(stat -c "%a" "$dir_path" 2>/dev/null || echo "N/A")
        local file_count=$(find "$dir_path" -type f -name "*.env*" 2>/dev/null | wc -l)
        local dir_owner=$(stat -c "%U:%G" "$dir_path" 2>/dev/null || echo "N/A")
        
        if [[ "$actual_perms" == "$expected_perms" ]]; then
            echo -e "${GREEN}✓${NC} ${CYAN}$dir_type${NC}: ${dir_path}"
            echo -e "    Permissions: ${GREEN}$actual_perms${NC} (${expected_perms}) | Files: ${file_count} | Owner: ${dir_owner}"
        else
            echo -e "${RED}✗${NC} ${CYAN}$dir_type${NC}: ${dir_path}"
            echo -e "    Permissions: ${RED}$actual_perms${NC} (expected ${expected_perms}) | Files: ${file_count} | Owner: ${dir_owner}"
        fi
        
        # Show files within directory
        find "$dir_path" -type f -name "*.env*" 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                local file_perms=$(stat -c "%a" "$file" 2>/dev/null || echo "N/A")
                local file_size=$(stat -c "%s" "$file" 2>/dev/null || echo "N/A")
                
                if [[ "$file_perms" == "$expected_perms" ]]; then
                    echo -e "    └─ ${GREEN}✓${NC} $(basename "$file") - ${GREEN}$file_perms${NC} (${file_size} bytes)"
                else
                    echo -e "    └─ ${RED}✗${NC} $(basename "$file") - ${RED}$file_perms${NC} (expected ${expected_perms}) (${file_size} bytes)"
                fi
            fi
        done
    else
        echo -e "${YELLOW}⚠${NC} ${CYAN}$dir_type${NC}: ${dir_path} (DIRECTORY NOT FOUND)"
    fi
}

# Main display function
main() {
    log "LUCID Environment File Permission Display"
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
    
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}REGULAR ENVIRONMENT FILES (664 permissions)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
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
        display_file_permissions "$file" "$REGULAR_PERMISSIONS" "Regular Environment"
    done
    
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}ENVIRONMENT SUBDIRECTORIES (664 permissions)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
    # Environment subdirectories
    env_subdirs=(
        "$ENV_DIR/development"
        "$ENV_DIR/production"
        "$ENV_DIR/staging"
        "$ENV_DIR/pi"
    )
    
    for dir in "${env_subdirs[@]}"; do
        display_directory_permissions "$dir" "$REGULAR_PERMISSIONS" "Environment Subdirectory"
    done
    
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}SECURE SECRET FILES (600 permissions)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
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
        display_file_permissions "$file" "$SECURE_PERMISSIONS" "Secure Secret"
    done
    
    # Check for files with "secrets" in the name
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}FILES WITH 'SECRETS' IN NAME (600 permissions)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
    find "$PROJECT_ROOT" -type f -name "*secrets*" -path "*/configs/*" 2>/dev/null | while read -r file; do
        if [[ -f "$file" ]]; then
            display_file_permissions "$file" "$SECURE_PERMISSIONS" "Secret File"
        fi
    done
    
    # Check secrets directory
    if [[ -d "$SECRETS_DIR" ]]; then
        display_directory_permissions "$SECRETS_DIR" "$SECURE_PERMISSIONS" "Secrets Directory"
    fi
    
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}SERVICE-SPECIFIC ENVIRONMENT FILES (664 permissions)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
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
        display_file_permissions "$file" "$REGULAR_PERMISSIONS" "Service Environment"
    done
    
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}ADDITIONAL LOCATIONS${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    
    # Check API Gateway specific files
    api_gateway_env_dir="$PROJECT_ROOT/03-api-gateway/api"
    if [[ -d "$api_gateway_env_dir" ]]; then
        echo -e "${CYAN}API Gateway Environment Files:${NC}"
        find "$api_gateway_env_dir" -name "*.env*" -type f 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                display_file_permissions "$file" "$REGULAR_PERMISSIONS" "API Gateway Environment"
            fi
        done
    fi
    
    # Check session management files
    sessions_env_dir="$PROJECT_ROOT/sessions/core"
    if [[ -d "$sessions_env_dir" ]]; then
        echo -e "${CYAN}Session Management Environment Files:${NC}"
        find "$sessions_env_dir" -name "*.env*" -type f 2>/dev/null | while read -r file; do
            if [[ -f "$file" ]]; then
                display_file_permissions "$file" "$REGULAR_PERMISSIONS" "Session Management Environment"
            fi
        done
    fi
    
    echo
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}PERMISSION SUMMARY${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
    echo -e "${GREEN}✓${NC} = Correct permissions"
    echo -e "${RED}✗${NC} = Incorrect permissions"
    echo -e "${YELLOW}⚠${NC} = File/Directory not found"
    echo
    echo -e "${CYAN}Expected Permissions:${NC}"
    echo -e "  Regular Environment Files: ${GREEN}664${NC} (rw-rw-r--)"
    echo -e "  Secure Secret Files: ${GREEN}600${NC} (rw-------)"
    echo
    echo -e "${CYAN}To fix permission issues, run:${NC}"
    echo -e "  ${YELLOW}./scripts/set-env-permissions.sh${NC}"
    echo
    echo -e "${CYAN}To verify permissions, run:${NC}"
    echo -e "  ${YELLOW}./scripts/verify-env-permissions.sh${NC}"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
