#!/bin/bash
# Lucid API - SBOM Verification Script
# Verifies generated SBOM files for compliance and completeness

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SBOM_DIR="$PROJECT_ROOT/build/sbom"
PHASE_DIR="$SBOM_DIR/phase1"

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

# Check if jq is installed
check_jq() {
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt-get install jq"
        echo "  macOS: brew install jq"
        echo "  CentOS/RHEL: sudo yum install jq"
        exit 1
    fi
}

# Verify SPDX JSON format
verify_spdx_json() {
    local sbom_file="$1"
    
    log_info "Verifying SPDX JSON format: $(basename "$sbom_file")"
    
    # Check if file exists and is readable
    if [ ! -f "$sbom_file" ] || [ ! -r "$sbom_file" ]; then
        log_error "SBOM file not found or not readable: $sbom_file"
        return 1
    fi
    
    # Check if file is valid JSON
    if ! jq empty "$sbom_file" 2>/dev/null; then
        log_error "Invalid JSON format: $sbom_file"
        return 1
    fi
    
    # Check required SPDX fields
    local required_fields=("spdxVersion" "dataLicense" "SPDXID" "name" "packages")
    
    for field in "${required_fields[@]}"; do
        if ! jq -e ".$field" "$sbom_file" > /dev/null 2>&1; then
            log_error "Missing required SPDX field: $field in $sbom_file"
            return 1
        fi
    done
    
    # Check packages array
    local package_count=$(jq '.packages | length' "$sbom_file")
    if [ "$package_count" -eq 0 ]; then
        log_warning "No packages found in SBOM: $sbom_file"
    else
        log_success "Found $package_count packages in $sbom_file"
    fi
    
    # Check for critical package information
    local critical_packages=("python" "openssl" "glibc" "bash")
    local found_critical=0
    
    for package in "${critical_packages[@]}"; do
        if jq -e ".packages[] | select(.name | contains(\"$package\"))" "$sbom_file" > /dev/null 2>&1; then
            ((found_critical++))
        fi
    done
    
    log_info "Found $found_critical critical packages in $sbom_file"
    
    return 0
}

# Verify CycloneDX JSON format
verify_cyclonedx_json() {
    local sbom_file="$1"
    
    log_info "Verifying CycloneDX JSON format: $(basename "$sbom_file")"
    
    # Check if file exists and is readable
    if [ ! -f "$sbom_file" ] || [ ! -r "$sbom_file" ]; then
        log_error "SBOM file not found or not readable: $sbom_file"
        return 1
    fi
    
    # Check if file is valid JSON
    if ! jq empty "$sbom_file" 2>/dev/null; then
        log_error "Invalid JSON format: $sbom_file"
        return 1
    fi
    
    # Check required CycloneDX fields
    local required_fields=("bomFormat" "specVersion" "serialNumber" "version" "components")
    
    for field in "${required_fields[@]}"; do
        if ! jq -e ".$field" "$sbom_file" > /dev/null 2>&1; then
            log_error "Missing required CycloneDX field: $field in $sbom_file"
            return 1
        fi
    done
    
    # Check components array
    local component_count=$(jq '.components | length' "$sbom_file")
    if [ "$component_count" -eq 0 ]; then
        log_warning "No components found in SBOM: $sbom_file"
    else
        log_success "Found $component_count components in $sbom_file"
    fi
    
    return 0
}

# Verify Syft JSON format
verify_syft_json() {
    local sbom_file="$1"
    
    log_info "Verifying Syft JSON format: $(basename "$sbom_file")"
    
    # Check if file exists and is readable
    if [ ! -f "$sbom_file" ] || [ ! -r "$sbom_file" ]; then
        log_error "SBOM file not found or not readable: $sbom_file"
        return 1
    fi
    
    # Check if file is valid JSON
    if ! jq empty "$sbom_file" 2>/dev/null; then
        log_error "Invalid JSON format: $sbom_file"
        return 1
    fi
    
    # Check required Syft fields
    local required_fields=("artifacts" "source" "distro")
    
    for field in "${required_fields[@]}"; do
        if ! jq -e ".$field" "$sbom_file" > /dev/null 2>&1; then
            log_error "Missing required Syft field: $field in $sbom_file"
            return 1
        fi
    done
    
    # Check artifacts array
    local artifact_count=$(jq '.artifacts | length' "$sbom_file")
    if [ "$artifact_count" -eq 0 ]; then
        log_warning "No artifacts found in SBOM: $sbom_file"
    else
        log_success "Found $artifact_count artifacts in $sbom_file"
    fi
    
    return 0
}

# Verify SBOM file based on format
verify_sbom_file() {
    local sbom_file="$1"
    local filename=$(basename "$sbom_file")
    
    log_info "Verifying SBOM file: $filename"
    
    case "$filename" in
        *.spdx-json)
            verify_spdx_json "$sbom_file"
            ;;
        *.cyclonedx.json)
            verify_cyclonedx_json "$sbom_file"
            ;;
        *.syft.json)
            verify_syft_json "$sbom_file"
            ;;
        *)
            log_warning "Unknown SBOM format: $filename"
            return 1
            ;;
    esac
}

# Verify all SBOMs in directory
verify_all_sboms() {
    local directory="$1"
    
    if [ ! -d "$directory" ]; then
        log_error "SBOM directory not found: $directory"
        return 1
    fi
    
    local sbom_files=($(find "$directory" -name "*.json" -type f))
    
    if [ ${#sbom_files[@]} -eq 0 ]; then
        log_warning "No SBOM files found in $directory"
        return 1
    fi
    
    log_info "Found ${#sbom_files[@]} SBOM files to verify"
    
    local verified_count=0
    local failed_count=0
    
    for sbom_file in "${sbom_files[@]}"; do
        if verify_sbom_file "$sbom_file"; then
            ((verified_count++))
        else
            ((failed_count++))
        fi
    done
    
    log_info "Verification results:"
    log_success "Verified: $verified_count files"
    if [ $failed_count -gt 0 ]; then
        log_error "Failed: $failed_count files"
    fi
    
    return $failed_count
}

# Generate verification report
generate_verification_report() {
    local report_file="$PHASE_DIR/verification_report.json"
    
    log_info "Generating verification report..."
    
    local sbom_files=($(find "$PHASE_DIR" -name "*.json" -type f | grep -v "summary\|report"))
    local total_files=${#sbom_files[@]}
    local verified_files=0
    
    # Count verified files
    for sbom_file in "${sbom_files[@]}"; do
        if verify_sbom_file "$sbom_file" > /dev/null 2>&1; then
            ((verified_files++))
        fi
    done
    
    cat > "$report_file" << EOF
{
    "verification_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_sbom_files": $total_files,
    "verified_files": $verified_files,
    "failed_files": $((total_files - verified_files)),
    "verification_status": "$(if [ $verified_files -eq $total_files ]; then echo "PASSED"; else echo "FAILED"; fi)",
    "files": [
EOF

    local first=true
    for sbom_file in "${sbom_files[@]}"; do
        local filename=$(basename "$sbom_file")
        local size=$(stat -f%z "$sbom_file" 2>/dev/null || stat -c%s "$sbom_file" 2>/dev/null || echo "0")
        local verified=false
        
        if verify_sbom_file "$sbom_file" > /dev/null 2>&1; then
            verified=true
        fi
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        
        cat >> "$report_file" << EOF
        {
            "filename": "$filename",
            "size_bytes": $size,
            "verified": $verified
        }
EOF
    done
    
    cat >> "$report_file" << EOF
    ]
}
EOF

    log_success "Verification report generated: $report_file"
}

# Main function
main() {
    log_info "Starting SBOM verification for Lucid API..."
    
    # Parse arguments
    local verify_all=false
    local directory=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                verify_all=true
                shift
                ;;
            --directory)
                directory="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--all] [--directory DIR] [--help]"
                echo "  --all        Verify all SBOMs in default directory"
                echo "  --directory  Verify SBOMs in specific directory"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_jq
    
    # Determine directory to verify
    if [ "$verify_all" = true ]; then
        directory="$PHASE_DIR"
    elif [ -z "$directory" ]; then
        directory="$PHASE_DIR"
    fi
    
    # Verify SBOMs
    if verify_all_sboms "$directory"; then
        log_success "All SBOMs verified successfully"
        
        # Generate report
        generate_verification_report
        
        echo ""
        log_success "SBOM verification completed successfully!"
        exit 0
    else
        log_error "Some SBOMs failed verification"
        exit 1
    fi
}

# Run main function
main "$@"