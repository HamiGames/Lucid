#!/bin/bash
# Quick Dockerfile path validation test
# Focus on key Dockerfiles to identify main issues

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Key Dockerfiles to test
KEY_DOCKERFILES=(
    "infrastructure/docker/admin/Dockerfile.admin-ui"
    "infrastructure/docker/blockchain/Dockerfile.blockchain-api"
    "infrastructure/docker/auth/Dockerfile.authentication"
    "infrastructure/docker/common/Dockerfile.common"
    "infrastructure/docker/databases/Dockerfile.mongodb"
    "src/api/Dockerfile"
)

# Check if path exists
check_path_exists() {
    local path="$1"
    if [[ -e "$path" ]]; then
        return 0
    else
        return 1
    fi
}

# Validate COPY paths in a Dockerfile
validate_copy_paths() {
    local dockerfile="$1"
    local errors=0
    
    echo "Checking COPY paths in $dockerfile..."
    
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
            continue
        fi
        
        # Handle COPY with various flags
        if [[ "$line" =~ ^COPY[[:space:]]+.*[[:space:]]+([^[:space:]]+)[[:space:]]+([^[:space:]]+) ]]; then
            local source_path="${BASH_REMATCH[1]}"
            local dest_path="${BASH_REMATCH[2]}"
            
            # Skip if source is a build stage (contains --from)
            if [[ "$line" =~ --from= ]]; then
                continue
            fi
            
            # Skip if source contains variables
            if [[ "$source_path" =~ \$ ]]; then
                continue
            fi
            
            # Skip if source starts with -- (it's a flag, not a path)
            if [[ "$source_path" =~ ^-- ]]; then
                continue
            fi
            
            # Check if source path exists
            local dockerfile_dir=$(dirname "$dockerfile")
            local full_source_path="$dockerfile_dir/$source_path"
            
            # Handle relative paths from project root
            if [[ "$source_path" =~ ^\.\./ ]]; then
                full_source_path="$(dirname "$dockerfile_dir")/$source_path"
            elif [[ "$source_path" =~ ^\./ ]]; then
                full_source_path="$dockerfile_dir/$source_path"
            elif [[ ! "$source_path" =~ ^/ ]]; then
                full_source_path="$dockerfile_dir/$source_path"
            fi
            
            if ! check_path_exists "$full_source_path"; then
                log_error "COPY source path does not exist: $source_path -> $full_source_path"
                ((errors++))
            else
                echo "  ✓ $source_path -> $dest_path"
            fi
        fi
    done < "$dockerfile"
    
    return $errors
}

# Test docker-compose syntax
test_compose_syntax() {
    local compose_file="$1"
    
    echo "Testing docker-compose syntax: $compose_file"
    
    if command -v docker-compose &> /dev/null; then
        if docker-compose -f "$compose_file" config >/dev/null 2>&1; then
            log_success "Compose file syntax is valid"
            return 0
        else
            log_error "Compose file syntax is invalid"
            return 1
        fi
    else
        log_warn "docker-compose not available, skipping syntax check"
        return 0
    fi
}

# Main test function
main() {
    log_info "Starting quick Dockerfile path validation test"
    echo "=================================================="
    
    local total_errors=0
    
    # Test key Dockerfiles
    for dockerfile in "${KEY_DOCKERFILES[@]}"; do
        if [[ -f "$dockerfile" ]]; then
            echo
            log_info "Testing $dockerfile"
            echo "----------------------------------------"
            
            if validate_copy_paths "$dockerfile"; then
                log_success "All COPY paths are valid"
            else
                log_error "COPY path validation failed"
                ((total_errors++))
            fi
        else
            log_warn "Dockerfile not found: $dockerfile"
        fi
    done
    
    # Test docker-compose files
    echo
    log_info "Testing docker-compose files"
    echo "----------------------------------------"
    
    local compose_files=(
        "infrastructure/docker/compose/docker-compose.yml"
        "infrastructure/docker/compose/docker-compose.dev.yml"
        ".devcontainer/docker-compose.dev.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            if test_compose_syntax "$compose_file"; then
                log_success "Compose file syntax is valid: $compose_file"
            else
                log_error "Compose file syntax is invalid: $compose_file"
                ((total_errors++))
            fi
        else
            log_warn "Compose file not found: $compose_file"
        fi
    done
    
    # Summary
    echo
    echo "=================================================="
    if [[ $total_errors -eq 0 ]]; then
        log_success "All tests passed! No path issues found."
        exit 0
    else
        log_error "$total_errors error(s) found. Please fix the issues above."
        exit 1
    fi
}

# Run main function
main "$@"
