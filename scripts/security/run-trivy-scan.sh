#!/bin/bash

# Trivy Vulnerability Scanner Script
# Scans all Lucid containers for security vulnerabilities
# Author: Lucid Development Team
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/security"
TRIVY_CACHE_DIR="$PROJECT_ROOT/.trivy-cache"
LOG_FILE="$REPORTS_DIR/trivy-scan-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        log_error "Trivy is not installed. Please install Trivy first."
        log_info "Installation instructions:"
        log_info "  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
        exit 1
    fi
    
    log_success "Trivy is installed: $(trivy --version)"
}

# Create reports directory
setup_reports_dir() {
    mkdir -p "$REPORTS_DIR"
    log_info "Reports directory: $REPORTS_DIR"
}

# Scan container images
scan_container_images() {
    local scan_type="$1"
    local output_format="$2"
    local severity_threshold="$3"
    
    log_info "Starting $scan_type scan with $output_format format..."
    
    # List of Lucid container images to scan
    local images=(
        "lucid-api-gateway:latest"
        "lucid-blockchain-engine:latest"
        "lucid-session-anchoring:latest"
        "lucid-block-manager:latest"
        "lucid-data-chain:latest"
        "lucid-auth-service:latest"
        "lucid-session-pipeline:latest"
        "lucid-session-recorder:latest"
        "lucid-session-processor:latest"
        "lucid-session-storage:latest"
        "lucid-session-api:latest"
        "lucid-rdp-server-manager:latest"
        "lucid-xrdp:latest"
        "lucid-session-controller:latest"
        "lucid-resource-monitor:latest"
        "lucid-node-management:latest"
        "lucid-admin-interface:latest"
        "lucid-tron-client:latest"
        "lucid-payout-router:latest"
        "lucid-wallet-manager:latest"
        "lucid-usdt-manager:latest"
        "lucid-trx-staking:latest"
        "lucid-payment-gateway:latest"
    )
    
    local total_vulnerabilities=0
    local critical_vulnerabilities=0
    local high_vulnerabilities=0
    local medium_vulnerabilities=0
    local low_vulnerabilities=0
    
    for image in "${images[@]}"; do
        log_info "Scanning image: $image"
        
        local image_report="$REPORTS_DIR/trivy-${scan_type}-${image//[:\/]/_}-$(date +%Y%m%d-%H%M%S).${output_format}"
        
        # Run Trivy scan
        if trivy "$scan_type" \
            --format "$output_format" \
            --output "$image_report" \
            --severity "$severity_threshold" \
            --cache-dir "$TRIVY_CACHE_DIR" \
            --quiet \
            "$image"; then
            
            log_success "Scan completed for $image"
            
            # Parse results for summary
            if [[ "$output_format" == "json" ]]; then
                local vuln_count=$(jq '.Results[]?.Vulnerabilities | length' "$image_report" 2>/dev/null || echo "0")
                local critical_count=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | length' "$image_report" 2>/dev/null || echo "0")
                local high_count=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | length' "$image_report" 2>/dev/null || echo "0")
                local medium_count=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | length' "$image_report" 2>/dev/null || echo "0")
                local low_count=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW") | length' "$image_report" 2>/dev/null || echo "0")
                
                total_vulnerabilities=$((total_vulnerabilities + vuln_count))
                critical_vulnerabilities=$((critical_vulnerabilities + critical_count))
                high_vulnerabilities=$((high_vulnerabilities + high_count))
                medium_vulnerabilities=$((medium_vulnerabilities + medium_count))
                low_vulnerabilities=$((low_vulnerabilities + low_count))
            fi
        else
            log_error "Scan failed for $image"
        fi
    done
    
    # Generate summary report
    generate_summary_report "$total_vulnerabilities" "$critical_vulnerabilities" "$high_vulnerabilities" "$medium_vulnerabilities" "$low_vulnerabilities"
}

# Generate summary report
generate_summary_report() {
    local total="$1"
    local critical="$2"
    local high="$3"
    local medium="$4"
    local low="$5"
    
    local summary_report="$REPORTS_DIR/trivy-summary-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$summary_report" << EOF
# Trivy Security Scan Summary

**Scan Date:** $(date)
**Total Images Scanned:** ${#images[@]}
**Total Vulnerabilities:** $total

## Vulnerability Breakdown

| Severity | Count |
|----------|-------|
| CRITICAL | $critical |
| HIGH     | $high |
| MEDIUM   | $medium |
| LOW      | $low |

## Compliance Status

EOF

    if [[ $critical -gt 0 ]]; then
        cat >> "$summary_report" << EOF
❌ **NON-COMPLIANT** - Critical vulnerabilities found

**Action Required:** Fix all critical vulnerabilities before deployment.
EOF
        log_error "CRITICAL vulnerabilities found: $critical"
        return 1
    elif [[ $high -gt 0 ]]; then
        cat >> "$summary_report" << EOF
⚠️ **CONDITIONAL COMPLIANCE** - High severity vulnerabilities found

**Action Required:** Review and fix high severity vulnerabilities.
EOF
        log_warning "HIGH vulnerabilities found: $high"
    else
        cat >> "$summary_report" << EOF
✅ **COMPLIANT** - No critical or high severity vulnerabilities

**Status:** Ready for deployment.
EOF
        log_success "No critical or high severity vulnerabilities found"
    fi
    
    log_info "Summary report generated: $summary_report"
}

# Scan filesystem
scan_filesystem() {
    log_info "Scanning filesystem for vulnerabilities..."
    
    local fs_report="$REPORTS_DIR/trivy-fs-$(date +%Y%m%d-%H%M%S).json"
    
    trivy fs \
        --format json \
        --output "$fs_report" \
        --severity "CRITICAL,HIGH" \
        --cache-dir "$TRIVY_CACHE_DIR" \
        --quiet \
        "$PROJECT_ROOT"
    
    if [[ -f "$fs_report" ]]; then
        local vuln_count=$(jq '.Results[]?.Vulnerabilities | length' "$fs_report" 2>/dev/null || echo "0")
        if [[ $vuln_count -gt 0 ]]; then
            log_warning "Filesystem vulnerabilities found: $vuln_count"
        else
            log_success "No filesystem vulnerabilities found"
        fi
    fi
}

# Scan SBOM files
scan_sbom() {
    log_info "Scanning SBOM files for vulnerabilities..."
    
    local sbom_dir="$PROJECT_ROOT/build/sbom"
    if [[ -d "$sbom_dir" ]]; then
        for sbom_file in "$sbom_dir"/*.json; do
            if [[ -f "$sbom_file" ]]; then
                log_info "Scanning SBOM: $(basename "$sbom_file")"
                
                local sbom_report="$REPORTS_DIR/trivy-sbom-$(basename "$sbom_file" .json)-$(date +%Y%m%d-%H%M%S).json"
                
                trivy sbom \
                    --format json \
                    --output "$sbom_report" \
                    --severity "CRITICAL,HIGH" \
                    --cache-dir "$TRIVY_CACHE_DIR" \
                    --quiet \
                    "$sbom_file"
            fi
        done
    else
        log_warning "SBOM directory not found: $sbom_dir"
    fi
}

# Clean up old reports
cleanup_old_reports() {
    log_info "Cleaning up old reports (older than 30 days)..."
    
    find "$REPORTS_DIR" -name "trivy-*" -type f -mtime +30 -delete 2>/dev/null || true
    
    log_success "Old reports cleaned up"
}

# Main function
main() {
    log_info "Starting Trivy security scan..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Reports directory: $REPORTS_DIR"
    
    # Check prerequisites
    check_trivy
    setup_reports_dir
    
    # Parse command line arguments
    local scan_type="image"
    local output_format="json"
    local severity_threshold="CRITICAL,HIGH,MEDIUM,LOW"
    local scan_filesystem=false
    local scan_sbom_files=false
    local cleanup=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                scan_type="$2"
                shift 2
                ;;
            --format)
                output_format="$2"
                shift 2
                ;;
            --severity)
                severity_threshold="$2"
                shift 2
                ;;
            --filesystem)
                scan_filesystem=true
                shift
                ;;
            --sbom)
                scan_sbom_files=true
                shift
                ;;
            --cleanup)
                cleanup=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --type TYPE          Scan type (image, fs, sbom)"
                echo "  --format FORMAT       Output format (json, table, sarif)"
                echo "  --severity LEVELS     Severity levels (CRITICAL,HIGH,MEDIUM,LOW)"
                echo "  --filesystem          Scan filesystem"
                echo "  --sbom                Scan SBOM files"
                echo "  --cleanup             Clean up old reports"
                echo "  --help                Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Perform scans
    if [[ "$scan_type" == "image" ]]; then
        scan_container_images "$scan_type" "$output_format" "$severity_threshold"
    fi
    
    if [[ "$scan_filesystem" == true ]]; then
        scan_filesystem
    fi
    
    if [[ "$scan_sbom_files" == true ]]; then
        scan_sbom
    fi
    
    if [[ "$cleanup" == true ]]; then
        cleanup_old_reports
    fi
    
    log_success "Trivy security scan completed"
    log_info "Reports available in: $REPORTS_DIR"
}

# Run main function with all arguments
main "$@"
