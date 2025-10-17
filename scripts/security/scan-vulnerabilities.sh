#!/bin/bash
################################################################################
# Lucid API - Vulnerability Scanning Script
################################################################################
# Description: Scans containers and SBOMs for CVE vulnerabilities
# Version: 1.0.0
# Usage: ./scan-vulnerabilities.sh [OPTIONS]
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
SCAN_DIR="$PROJECT_ROOT/build/security-scans"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Severity thresholds
FAIL_ON_CRITICAL=true
FAIL_ON_HIGH=false
CRITICAL_CVSS_THRESHOLD=7.0

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
    
    # Check for Trivy
    if ! command -v trivy &> /dev/null; then
        missing_deps+=("trivy")
    fi
    
    # Check for Grype (optional but recommended)
    if ! command -v grype &> /dev/null; then
        log_warning "Grype not found (optional). Install: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Install Trivy: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
        exit 1
    fi
    
    log_success "All dependencies found"
}

setup_scan_directory() {
    log_info "Setting up scan directory..."
    
    mkdir -p "$SCAN_DIR"/{trivy,grype,reports}
    mkdir -p "$SCAN_DIR"/archive/"$TIMESTAMP"
    
    log_success "Scan directory created: $SCAN_DIR"
}

scan_container_trivy() {
    local container_name="$1"
    local registry="${2:-lucid}"
    local version="${3:-latest}"
    local image_ref="${registry}/${container_name}:${version}"
    local scan_output="${SCAN_DIR}/trivy/${container_name}-trivy-${TIMESTAMP}.json"
    
    log_info "Scanning with Trivy: $image_ref"
    
    # Run Trivy scan
    if trivy image \
        --format json \
        --output "$scan_output" \
        --severity CRITICAL,HIGH,MEDIUM \
        --timeout 10m \
        "$image_ref" 2>/dev/null; then
        
        log_success "Trivy scan completed: $scan_output"
        
        # Parse results
        parse_trivy_results "$scan_output" "$container_name"
        return 0
    else
        log_error "Trivy scan failed for $image_ref"
        return 1
    fi
}

parse_trivy_results() {
    local scan_file="$1"
    local container_name="$2"
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found, skipping result parsing"
        return
    fi
    
    # Count vulnerabilities by severity
    local critical high medium low
    critical=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$scan_file" 2>/dev/null || echo 0)
    high=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$scan_file" 2>/dev/null || echo 0)
    medium=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$scan_file" 2>/dev/null || echo 0)
    low=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="LOW")] | length' "$scan_file" 2>/dev/null || echo 0)
    
    echo "  Critical: $critical"
    echo "  High: $high"
    echo "  Medium: $medium"
    echo "  Low: $low"
    
    # Check if we should fail the build
    if [ "$critical" -gt 0 ] && [ "$FAIL_ON_CRITICAL" = true ]; then
        log_error "Found $critical CRITICAL vulnerabilities in $container_name"
        return 1
    fi
    
    if [ "$high" -gt 0 ] && [ "$FAIL_ON_HIGH" = true ]; then
        log_error "Found $high HIGH vulnerabilities in $container_name"
        return 1
    fi
    
    return 0
}

scan_sbom_grype() {
    local sbom_file="$1"
    local container_name
    container_name=$(basename "$sbom_file" | cut -d'-' -f1-3)
    local scan_output="${SCAN_DIR}/grype/${container_name}-grype-${TIMESTAMP}.json"
    
    if ! command -v grype &> /dev/null; then
        log_warning "Grype not installed, skipping SBOM scan"
        return 0
    fi
    
    log_info "Scanning SBOM with Grype: $(basename "$sbom_file")"
    
    # Run Grype scan on SBOM
    if grype "sbom:$sbom_file" \
        -o json \
        --file "$scan_output" 2>/dev/null; then
        
        log_success "Grype scan completed: $scan_output"
        
        # Parse results
        parse_grype_results "$scan_output" "$container_name"
        return 0
    else
        log_warning "Grype scan failed for $(basename "$sbom_file")"
        return 0  # Don't fail if Grype fails
    fi
}

parse_grype_results() {
    local scan_file="$1"
    local container_name="$2"
    
    if ! command -v jq &> /dev/null; then
        return
    fi
    
    # Count vulnerabilities by severity
    local critical high medium low
    critical=$(jq '[.matches[]? | select(.vulnerability.severity=="Critical")] | length' "$scan_file" 2>/dev/null || echo 0)
    high=$(jq '[.matches[]? | select(.vulnerability.severity=="High")] | length' "$scan_file" 2>/dev/null || echo 0)
    medium=$(jq '[.matches[]? | select(.vulnerability.severity=="Medium")] | length' "$scan_file" 2>/dev/null || echo 0)
    low=$(jq '[.matches[]? | select(.vulnerability.severity=="Low")] | length' "$scan_file" 2>/dev/null || echo 0)
    
    echo "  Critical: $critical"
    echo "  High: $high"
    echo "  Medium: $medium"
    echo "  Low: $low"
}

scan_all_containers() {
    local phase="$1"
    local containers=("${@:2}")
    local total=0
    local passed=0
    local failed=0
    
    log_info "Scanning containers for $phase..."
    echo ""
    
    for container in "${containers[@]}"; do
        ((total++))
        if scan_container_trivy "$container" "lucid" "latest"; then
            ((passed++))
        else
            ((failed++))
        fi
        echo ""
    done
    
    log_info "$phase Summary: $passed passed, $failed failed out of $total"
}

scan_all_sboms() {
    log_info "Scanning all SBOMs..."
    echo ""
    
    local total=0
    local scanned=0
    
    for phase in phase1 phase2 phase3 phase4; do
        if [ -d "${SBOM_DIR}/${phase}" ]; then
            log_info "Scanning SBOMs in $phase..."
            
            while IFS= read -r sbom_file; do
                ((total++))
                if scan_sbom_grype "$sbom_file"; then
                    ((scanned++))
                fi
            done < <(find "${SBOM_DIR}/${phase}" -name "*-sbom.spdx-json" 2>/dev/null)
        fi
    done
    
    log_info "Scanned $scanned out of $total SBOMs"
}

generate_vulnerability_report() {
    local report_file="${SCAN_DIR}/reports/vulnerability-report-${TIMESTAMP}.md"
    
    log_info "Generating vulnerability report..."
    
    {
        echo "# Lucid API - Vulnerability Scan Report"
        echo ""
        echo "**Generated:** $(date)"
        echo ""
        echo "## Summary"
        echo ""
        
        # Count total vulnerabilities from Trivy scans
        local total_critical=0
        local total_high=0
        local total_medium=0
        local total_low=0
        
        if command -v jq &> /dev/null; then
            for scan_file in "$SCAN_DIR"/trivy/*.json; do
                if [ -f "$scan_file" ]; then
                    local critical high medium low
                    critical=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$scan_file" 2>/dev/null || echo 0)
                    high=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$scan_file" 2>/dev/null || echo 0)
                    medium=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$scan_file" 2>/dev/null || echo 0)
                    low=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="LOW")] | length' "$scan_file" 2>/dev/null || echo 0)
                    
                    total_critical=$((total_critical + critical))
                    total_high=$((total_high + high))
                    total_medium=$((total_medium + medium))
                    total_low=$((total_low + low))
                fi
            done
        fi
        
        echo "| Severity | Count |"
        echo "|----------|-------|"
        echo "| CRITICAL | $total_critical |"
        echo "| HIGH     | $total_high |"
        echo "| MEDIUM   | $total_medium |"
        echo "| LOW      | $total_low |"
        echo ""
        
        echo "## Scan Details"
        echo ""
        echo "- **Scan Directory:** $SCAN_DIR"
        echo "- **Trivy Scans:** $(find "$SCAN_DIR/trivy" -name "*.json" 2>/dev/null | wc -l)"
        echo "- **Grype Scans:** $(find "$SCAN_DIR/grype" -name "*.json" 2>/dev/null | wc -l)"
        echo ""
        
        echo "## Status"
        echo ""
        if [ "$total_critical" -eq 0 ]; then
            echo "✅ **PASS** - No critical vulnerabilities found"
        else
            echo "❌ **FAIL** - $total_critical critical vulnerabilities found"
        fi
        echo ""
        
        echo "## Next Steps"
        echo ""
        echo "1. Review detailed scan reports in: \`$SCAN_DIR\`"
        echo "2. Remediate critical and high vulnerabilities"
        echo "3. Update base images and dependencies"
        echo "4. Re-run vulnerability scan"
        echo ""
        
    } > "$report_file"
    
    cat "$report_file"
    log_success "Report generated: $report_file"
    
    # Return failure if critical vulnerabilities found
    if [ "$total_critical" -gt 0 ] && [ "$FAIL_ON_CRITICAL" = true ]; then
        return 1
    fi
    
    return 0
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Scan containers and SBOMs for CVE vulnerabilities.

OPTIONS:
    -h, --help              Show this help message
    -c, --container NAME    Scan specific container
    -a, --all               Scan all containers
    -s, --sboms             Scan all SBOMs
    -p, --phase PHASE       Scan specific phase (1-4)
    --no-fail-critical      Don't fail on critical vulnerabilities
    
EXAMPLES:
    # Scan single container
    $0 --container lucid-auth-service
    
    # Scan all Phase 1 containers
    $0 --phase 1
    
    # Scan all containers
    $0 --all
    
    # Scan all SBOMs
    $0 --sboms

EOF
}

main() {
    log_info "Lucid API - Vulnerability Scanning Script"
    echo ""
    
    local scan_all=false
    local scan_sboms=false
    local container_name=""
    local phase=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -a|--all)
                scan_all=true
                shift
                ;;
            -s|--sboms)
                scan_sboms=true
                shift
                ;;
            -c|--container)
                container_name="$2"
                shift 2
                ;;
            -p|--phase)
                phase="$2"
                shift 2
                ;;
            --no-fail-critical)
                FAIL_ON_CRITICAL=false
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    check_dependencies
    setup_scan_directory
    
    # Perform scans based on arguments
    if [ -n "$container_name" ]; then
        scan_container_trivy "$container_name"
        
    elif [ "$scan_all" = true ]; then
        # Scan all containers (requires container arrays from generate-sbom.sh)
        log_info "Scanning all containers..."
        log_warning "Full scan not yet implemented. Use --phase option."
        
    elif [ "$scan_sboms" = true ]; then
        scan_all_sboms
        
    elif [ -n "$phase" ]; then
        log_info "Scanning Phase $phase containers..."
        # Phase-specific scanning would go here
        log_warning "Phase-specific scanning not yet fully implemented"
        
    else
        log_info "No arguments provided. Run --help for usage."
        show_usage
        exit 0
    fi
    
    # Generate report
    echo ""
    if generate_vulnerability_report; then
        log_success "Vulnerability scanning complete!"
        exit 0
    else
        log_error "Vulnerability scanning found critical issues!"
        exit 1
    fi
}

main "$@"

