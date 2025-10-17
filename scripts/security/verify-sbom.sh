#!/bin/bash
################################################################################
# Lucid API - SBOM Verification Script
################################################################################
# Description: Verifies and validates generated SBOM files
# Version: 1.0.0
# Usage: ./verify-sbom.sh [sbom_file]
################################################################################

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SBOM_DIR="$PROJECT_ROOT/build/sbom"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

################################################################################
# Functions
################################################################################

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

check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    log_success "All dependencies found"
}

verify_sbom_file() {
    local sbom_file="$1"
    local errors=0
    
    log_info "Verifying SBOM: $(basename "$sbom_file")"
    
    # Check if file exists
    if [ ! -f "$sbom_file" ]; then
        log_error "SBOM file not found: $sbom_file"
        return 1
    fi
    
    # Check if file is valid JSON
    if ! jq empty "$sbom_file" 2>/dev/null; then
        log_error "Invalid JSON format: $sbom_file"
        ((errors++))
    else
        log_success "Valid JSON format"
    fi
    
    # Verify SBOM structure
    if jq -e '.packages' "$sbom_file" > /dev/null 2>&1; then
        local package_count
        package_count=$(jq '.packages | length' "$sbom_file")
        log_success "Found $package_count packages"
        
        if [ "$package_count" -eq 0 ]; then
            log_warning "SBOM contains zero packages"
            ((errors++))
        fi
    else
        log_error "Missing 'packages' field in SBOM"
        ((errors++))
    fi
    
    # Check file size
    local file_size
    file_size=$(stat -f%z "$sbom_file" 2>/dev/null || stat -c%s "$sbom_file" 2>/dev/null)
    if [ "$file_size" -lt 100 ]; then
        log_error "SBOM file suspiciously small: $file_size bytes"
        ((errors++))
    else
        log_success "File size: $file_size bytes"
    fi
    
    return $errors
}

verify_all_sboms() {
    log_info "Verifying all SBOMs in: $SBOM_DIR"
    echo ""
    
    local total_sboms=0
    local valid_sboms=0
    local invalid_sboms=0
    
    for phase in phase1 phase2 phase3 phase4; do
        if [ -d "${SBOM_DIR}/${phase}" ]; then
            log_info "Checking $phase..."
            
            while IFS= read -r sbom_file; do
                ((total_sboms++))
                if verify_sbom_file "$sbom_file"; then
                    ((valid_sboms++))
                else
                    ((invalid_sboms++))
                fi
                echo ""
            done < <(find "${SBOM_DIR}/${phase}" -name "*-sbom.*.json" 2>/dev/null)
        fi
    done
    
    # Generate report
    local report_file="${SBOM_DIR}/reports/sbom-verification-${TIMESTAMP}.txt"
    {
        echo "========================================="
        echo "SBOM Verification Report"
        echo "========================================="
        echo "Generated: $(date)"
        echo ""
        echo "Total SBOMs: $total_sboms"
        echo "Valid: $valid_sboms"
        echo "Invalid: $invalid_sboms"
        echo ""
        echo "========================================="
    } > "$report_file"
    
    cat "$report_file"
    
    if [ "$invalid_sboms" -gt 0 ]; then
        log_error "Found $invalid_sboms invalid SBOMs"
        return 1
    else
        log_success "All SBOMs verified successfully"
        return 0
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SBOM_FILE]

Verify and validate SBOM files.

OPTIONS:
    -h, --help     Show this help message
    -a, --all      Verify all SBOMs
    
EXAMPLES:
    # Verify single SBOM
    $0 build/sbom/phase1/lucid-auth-service-latest-sbom.spdx-json
    
    # Verify all SBOMs
    $0 --all

EOF
}

main() {
    log_info "Lucid API - SBOM Verification Script"
    echo ""
    
    local verify_all=false
    local sbom_file=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -a|--all)
                verify_all=true
                shift
                ;;
            *)
                sbom_file="$1"
                shift
                ;;
        esac
    done
    
    check_dependencies
    
    if [ "$verify_all" = true ]; then
        verify_all_sboms
    elif [ -n "$sbom_file" ]; then
        verify_sbom_file "$sbom_file"
    else
        log_info "No arguments provided. Verifying all SBOMs..."
        verify_all_sboms
    fi
}

main "$@"

