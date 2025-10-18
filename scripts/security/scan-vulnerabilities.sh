#!/bin/bash
# Lucid API - Vulnerability Scanning Script
# Scans containers for vulnerabilities using Trivy

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCAN_DIR="$PROJECT_ROOT/build/security-scans"
TRIVY_DIR="$SCAN_DIR/trivy"
REPORTS_DIR="$SCAN_DIR/reports"

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

# Check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        log_error "Trivy is not installed. Please install it first:"
        echo "  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
        exit 1
    fi
    
    local trivy_version=$(trivy --version | head -n1)
    log_info "Using Trivy: $trivy_version"
}

# Check if container exists
check_container_exists() {
    local container_name="$1"
    
    if docker image inspect "$container_name" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Scan container for vulnerabilities
scan_container() {
    local container_name="$1"
    local output_file="$2"
    local format="$3"
    
    log_info "Scanning $container_name for vulnerabilities..."
    
    if ! check_container_exists "$container_name"; then
        log_warning "Container $container_name not found, skipping..."
        return 1
    fi
    
    # Create output directory
    mkdir -p "$(dirname "$output_file")"
    
    # Run Trivy scan
    trivy image \
        --format "$format" \
        --output "$output_file" \
        --severity "CRITICAL,HIGH,MEDIUM,LOW" \
        --no-progress \
        "$container_name"
    
    if [ $? -eq 0 ]; then
        log_success "Vulnerability scan completed: $output_file"
        return 0
    else
        log_error "Failed to scan $container_name"
        return 1
    fi
}

# Scan Phase 1 containers
scan_phase1_containers() {
    log_info "Scanning Phase 1 containers for vulnerabilities..."
    
    # Create directories
    mkdir -p "$TRIVY_DIR"
    mkdir -p "$REPORTS_DIR"
    
    # Phase 1 containers
    local containers=(
        "lucid-mongodb:latest"
        "lucid-redis:latest"
        "lucid-elasticsearch:latest"
        "lucid-auth-service:latest"
    )
    
    local scanned_count=0
    local total_count=${#containers[@]}
    
    for container in "${containers[@]}"; do
        local container_short=$(echo "$container" | cut -d: -f1 | sed 's/lucid-//')
        local base_name="$TRIVY_DIR/${container_short}"
        
        # Generate multiple formats
        local formats=("json" "table" "sarif")
        
        for format in "${formats[@]}"; do
            local output_file="${base_name}-scan.${format}"
            
            if scan_container "$container" "$output_file" "$format"; then
                ((scanned_count++))
            fi
        done
    done
    
    log_success "Scanned $scanned_count vulnerability reports for Phase 1"
    return 0
}

# Analyze scan results
analyze_scan_results() {
    local json_file="$1"
    
    if [ ! -f "$json_file" ]; then
        log_error "Scan results file not found: $json_file"
        return 1
    fi
    
    log_info "Analyzing scan results: $(basename "$json_file")"
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        log_warning "jq not available, skipping detailed analysis"
        return 0
    fi
    
    # Count vulnerabilities by severity
    local critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$json_file" 2>/dev/null || echo "0")
    local high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$json_file" 2>/dev/null || echo "0")
    local medium_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$json_file" 2>/dev/null || echo "0")
    local low_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW")] | length' "$json_file" 2>/dev/null || echo "0")
    
    log_info "Vulnerability summary:"
    log_info "  CRITICAL: $critical_count"
    log_info "  HIGH: $high_count"
    log_info "  MEDIUM: $medium_count"
    log_info "  LOW: $low_count"
    
    # Check for critical vulnerabilities
    if [ "$critical_count" -gt 0 ]; then
        log_error "Found $critical_count CRITICAL vulnerabilities!"
        return 1
    else
        log_success "No CRITICAL vulnerabilities found"
    fi
    
    return 0
}

# Generate vulnerability report
generate_vulnerability_report() {
    local report_file="$REPORTS_DIR/vulnerability_summary.json"
    
    log_info "Generating vulnerability report..."
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    # Find all JSON scan files
    local scan_files=($(find "$TRIVY_DIR" -name "*.json" -type f))
    local total_scans=${#scan_files[@]}
    local critical_vulns=0
    local high_vulns=0
    local medium_vulns=0
    local low_vulns=0
    
    # Analyze each scan file
    for scan_file in "${scan_files[@]}"; do
        if [ -f "$scan_file" ] && command -v jq &> /dev/null; then
            local critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$scan_file" 2>/dev/null || echo "0")
            local high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$scan_file" 2>/dev/null || echo "0")
            local medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$scan_file" 2>/dev/null || echo "0")
            local low=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW")] | length' "$scan_file" 2>/dev/null || echo "0")
            
            critical_vulns=$((critical_vulns + critical))
            high_vulns=$((high_vulns + high))
            medium_vulns=$((medium_vulns + medium))
            low_vulns=$((low_vulns + low))
        fi
    done
    
    # Generate report
    cat > "$report_file" << EOF
{
    "scan_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_scans": $total_scans,
    "vulnerability_summary": {
        "critical": $critical_vulns,
        "high": $high_vulns,
        "medium": $medium_vulns,
        "low": $low_vulns,
        "total": $((critical_vulns + high_vulns + medium_vulns + low_vulns))
    },
    "compliance_status": "$(if [ $critical_vulns -eq 0 ]; then echo "PASSED"; else echo "FAILED"; fi)",
    "scan_files": [
EOF

    local first=true
    for scan_file in "${scan_files[@]}"; do
        local filename=$(basename "$scan_file")
        local size=$(stat -f%z "$scan_file" 2>/dev/null || stat -c%s "$scan_file" 2>/dev/null || echo "0")
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        
        cat >> "$report_file" << EOF
        {
            "filename": "$filename",
            "size_bytes": $size
        }
EOF
    done
    
    cat >> "$report_file" << EOF
    ]
}
EOF

    log_success "Vulnerability report generated: $report_file"
    
    # Print summary
    echo ""
    log_info "Vulnerability Summary:"
    log_info "  Total scans: $total_scans"
    log_info "  CRITICAL: $critical_vulns"
    log_info "  HIGH: $high_vulns"
    log_info "  MEDIUM: $medium_vulns"
    log_info "  LOW: $low_vulns"
    
    if [ $critical_vulns -eq 0 ]; then
        log_success "No CRITICAL vulnerabilities found - compliance PASSED"
    else
        log_error "Found $critical_vulns CRITICAL vulnerabilities - compliance FAILED"
    fi
}

# Clean old scan results
clean_old_scans() {
    if [ -d "$SCAN_DIR" ]; then
        log_info "Cleaning old scan results..."
        rm -rf "$SCAN_DIR"
        log_success "Old scan results cleaned"
    fi
}

# Main function
main() {
    log_info "Starting vulnerability scanning for Lucid API..."
    
    # Parse arguments
    local container=""
    local clean=false
    local analyze=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --container)
                container="$2"
                shift 2
                ;;
            --clean)
                clean=true
                shift
                ;;
            --analyze)
                analyze=true
                shift
                ;;
            --help)
                echo "Usage: $0 [--container CONTAINER] [--clean] [--analyze] [--help]"
                echo "  --container CONTAINER  Scan specific container"
                echo "  --clean               Clean old scan results before scanning"
                echo "  --analyze             Analyze scan results and generate report"
                echo "  --help                Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_trivy
    
    # Clean old scans if requested
    if [ "$clean" = true ]; then
        clean_old_scans
    fi
    
    # Scan specific container or all Phase 1 containers
    if [ -n "$container" ]; then
        log_info "Scanning specific container: $container"
        local output_file="$TRIVY_DIR/$(echo "$container" | cut -d: -f1 | sed 's/lucid-//')-scan.json"
        scan_container "$container" "$output_file" "json"
    else
        scan_phase1_containers
    fi
    
    # Analyze results if requested
    if [ "$analyze" = true ]; then
        generate_vulnerability_report
    fi
    
    log_success "Vulnerability scanning completed!"
    
    # Show results
    echo ""
    log_info "Generated files:"
    if [ -d "$SCAN_DIR" ]; then
        find "$SCAN_DIR" -type f -name "*.json" -o -name "*.table" -o -name "*.sarif" | head -10
    fi
}

# Run main function
main "$@"