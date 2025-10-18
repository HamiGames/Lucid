#!/bin/bash
# Lucid API - Security Compliance Check Script
# Comprehensive security compliance verification

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SBOM_DIR="$PROJECT_ROOT/build/sbom"
SCAN_DIR="$PROJECT_ROOT/build/security-scans"
REPORTS_DIR="$SCAN_DIR/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Compliance scoring
COMPLIANCE_SCORE=0
MAX_SCORE=100
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

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

# Check if required tools are installed
check_prerequisites() {
    local missing_tools=()
    
    # Check for jq
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    # Check for trivy
    if ! command -v trivy &> /dev/null; then
        missing_tools+=("trivy")
    fi
    
    # Check for syft
    if ! command -v syft &> /dev/null; then
        missing_tools+=("syft")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install missing tools and run again."
        exit 1
    fi
    
    log_success "All required tools are available"
}

# Check SBOM compliance
check_sbom_compliance() {
    log_info "Checking SBOM compliance..."
    
    local sbom_score=0
    local max_sbom_score=25
    
    # Check if SBOM directory exists
    if [ ! -d "$SBOM_DIR" ]; then
        log_error "SBOM directory not found: $SBOM_DIR"
        return 1
    fi
    
    # Check for Phase 1 SBOMs
    local phase1_dir="$SBOM_DIR/phase1"
    if [ -d "$phase1_dir" ]; then
        local sbom_files=($(find "$phase1_dir" -name "*.json" -type f | grep -v "summary\|report"))
        local sbom_count=${#sbom_files[@]}
        
        if [ $sbom_count -gt 0 ]; then
            sbom_score=$((sbom_score + 10))
            log_success "Found $sbom_count SBOM files"
        else
            log_warning "No SBOM files found"
        fi
        
        # Check SBOM formats
        local spdx_count=$(find "$phase1_dir" -name "*.spdx-json" -type f | wc -l)
        local cyclonedx_count=$(find "$phase1_dir" -name "*.cyclonedx.json" -type f | wc -l)
        local syft_count=$(find "$phase1_dir" -name "*.syft.json" -type f | wc -l)
        
        if [ $spdx_count -gt 0 ]; then
            sbom_score=$((sbom_score + 5))
            log_success "SPDX format SBOMs found: $spdx_count"
        fi
        
        if [ $cyclonedx_count -gt 0 ]; then
            sbom_score=$((sbom_score + 5))
            log_success "CycloneDX format SBOMs found: $cyclonedx_count"
        fi
        
        if [ $syft_count -gt 0 ]; then
            sbom_score=$((sbom_score + 5))
            log_success "Syft format SBOMs found: $syft_count"
        fi
    else
        log_warning "Phase 1 SBOM directory not found"
    fi
    
    log_info "SBOM compliance score: $sbom_score/$max_sbom_score"
    COMPLIANCE_SCORE=$((COMPLIANCE_SCORE + sbom_score))
}

# Check vulnerability scanning compliance
check_vulnerability_compliance() {
    log_info "Checking vulnerability scanning compliance..."
    
    local vuln_score=0
    local max_vuln_score=30
    
    # Check if scan directory exists
    if [ ! -d "$SCAN_DIR" ]; then
        log_error "Security scan directory not found: $SCAN_DIR"
        return 1
    fi
    
    # Check for Trivy scan results
    local trivy_dir="$SCAN_DIR/trivy"
    if [ -d "$trivy_dir" ]; then
        local scan_files=($(find "$trivy_dir" -name "*.json" -type f))
        local scan_count=${#scan_files[@]}
        
        if [ $scan_count -gt 0 ]; then
            vuln_score=$((vuln_score + 10))
            log_success "Found $scan_count vulnerability scan files"
            
            # Analyze scan results
            for scan_file in "${scan_files[@]}"; do
                if [ -f "$scan_file" ]; then
                    local critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$scan_file" 2>/dev/null || echo "0")
                    local high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$scan_file" 2>/dev/null || echo "0")
                    local medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$scan_file" 2>/dev/null || echo "0")
                    local low=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW")] | length' "$scan_file" 2>/dev/null || echo "0")
                    
                    CRITICAL_ISSUES=$((CRITICAL_ISSUES + critical))
                    HIGH_ISSUES=$((HIGH_ISSUES + high))
                    MEDIUM_ISSUES=$((MEDIUM_ISSUES + medium))
                    LOW_ISSUES=$((LOW_ISSUES + low))
                fi
            done
            
            # Score based on vulnerability counts
            if [ $CRITICAL_ISSUES -eq 0 ]; then
                vuln_score=$((vuln_score + 15))
                log_success "No CRITICAL vulnerabilities found"
            else
                log_error "Found $CRITICAL_ISSUES CRITICAL vulnerabilities"
                vuln_score=$((vuln_score - 20))  # Heavy penalty for critical issues
            fi
            
            if [ $HIGH_ISSUES -le 5 ]; then
                vuln_score=$((vuln_score + 5))
                log_success "Low number of HIGH vulnerabilities: $HIGH_ISSUES"
            else
                log_warning "High number of HIGH vulnerabilities: $HIGH_ISSUES"
            fi
        else
            log_warning "No vulnerability scan files found"
        fi
    else
        log_warning "Trivy scan directory not found"
    fi
    
    log_info "Vulnerability compliance score: $vuln_score/$max_vuln_score"
    COMPLIANCE_SCORE=$((COMPLIANCE_SCORE + vuln_score))
}

# Check container security compliance
check_container_security() {
    log_info "Checking container security compliance..."
    
    local container_score=0
    local max_container_score=25
    
    # Check for distroless base images
    local dockerfiles=($(find "$PROJECT_ROOT" -name "Dockerfile*" -type f | grep -v ".git"))
    local distroless_count=0
    local total_dockerfiles=${#dockerfiles[@]}
    
    if [ $total_dockerfiles -gt 0 ]; then
        for dockerfile in "${dockerfiles[@]}"; do
            if grep -qi "distroless" "$dockerfile"; then
                ((distroless_count++))
            fi
        done
        
        local distroless_percentage=$((distroless_count * 100 / total_dockerfiles))
        
        if [ $distroless_percentage -ge 80 ]; then
            container_score=$((container_score + 15))
            log_success "High distroless usage: $distroless_percentage%"
        elif [ $distroless_percentage -ge 50 ]; then
            container_score=$((container_score + 10))
            log_success "Moderate distroless usage: $distroless_percentage%"
        else
            log_warning "Low distroless usage: $distroless_percentage%"
        fi
        
        # Check for multi-stage builds
        local multistage_count=0
        for dockerfile in "${dockerfiles[@]}"; do
            if grep -qi "FROM.*AS" "$dockerfile"; then
                ((multistage_count++))
            fi
        done
        
        local multistage_percentage=$((multistage_count * 100 / total_dockerfiles))
        if [ $multistage_percentage -ge 50 ]; then
            container_score=$((container_score + 10))
            log_success "Multi-stage builds used: $multistage_percentage%"
        fi
    else
        log_warning "No Dockerfiles found"
    fi
    
    log_info "Container security score: $container_score/$max_container_score"
    COMPLIANCE_SCORE=$((COMPLIANCE_SCORE + container_score))
}

# Check security configuration compliance
check_security_config() {
    log_info "Checking security configuration compliance..."
    
    local config_score=0
    local max_config_score=20
    
    # Check for security-related configuration files
    local security_files=(
        "scripts/security/generate-sbom.sh"
        "scripts/security/verify-sbom.sh"
        "scripts/security/scan-vulnerabilities.sh"
        "scripts/security/security-compliance-check.sh"
    )
    
    local existing_security_files=0
    for file in "${security_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            ((existing_security_files++))
        fi
    done
    
    if [ $existing_security_files -eq ${#security_files[@]} ]; then
        config_score=$((config_score + 10))
        log_success "All security scripts present"
    else
        log_warning "Missing security scripts: $((existing_security_files - ${#security_files[@]}))"
    fi
    
    # Check for security documentation
    local security_docs=(
        "docs/security"
        "plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md"
    )
    
    local existing_docs=0
    for doc in "${security_docs[@]}"; do
        if [ -d "$PROJECT_ROOT/$doc" ] || [ -f "$PROJECT_ROOT/$doc" ]; then
            ((existing_docs++))
        fi
    done
    
    if [ $existing_docs -gt 0 ]; then
        config_score=$((config_score + 10))
        log_success "Security documentation present"
    fi
    
    log_info "Security configuration score: $config_score/$max_config_score"
    COMPLIANCE_SCORE=$((COMPLIANCE_SCORE + config_score))
}

# Generate compliance report
generate_compliance_report() {
    local report_file="$REPORTS_DIR/security_compliance_report.json"
    
    log_info "Generating security compliance report..."
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    # Calculate compliance percentage
    local compliance_percentage=$((COMPLIANCE_SCORE * 100 / MAX_SCORE))
    local compliance_status="FAILED"
    
    if [ $compliance_percentage -ge 90 ]; then
        compliance_status="EXCELLENT"
    elif [ $compliance_percentage -ge 80 ]; then
        compliance_status="GOOD"
    elif [ $compliance_percentage -ge 70 ]; then
        compliance_status="ACCEPTABLE"
    elif [ $compliance_percentage -ge 60 ]; then
        compliance_status="NEEDS_IMPROVEMENT"
    fi
    
    # Generate report
    cat > "$report_file" << EOF
{
    "compliance_check_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "compliance_score": $COMPLIANCE_SCORE,
    "max_score": $MAX_SCORE,
    "compliance_percentage": $compliance_percentage,
    "compliance_status": "$compliance_status",
    "vulnerability_summary": {
        "critical": $CRITICAL_ISSUES,
        "high": $HIGH_ISSUES,
        "medium": $MEDIUM_ISSUES,
        "low": $LOW_ISSUES,
        "total": $((CRITICAL_ISSUES + HIGH_ISSUES + MEDIUM_ISSUES + LOW_ISSUES))
    },
    "recommendations": [
EOF

    # Add recommendations based on findings
    local first=true
    
    if [ $CRITICAL_ISSUES -gt 0 ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        echo '        "Address CRITICAL vulnerabilities immediately"' >> "$report_file"
    fi
    
    if [ $HIGH_ISSUES -gt 10 ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        echo '        "Reduce HIGH vulnerability count"' >> "$report_file"
    fi
    
    if [ $COMPLIANCE_SCORE -lt 80 ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        echo '        "Improve overall security compliance"' >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF
    ]
}
EOF

    log_success "Security compliance report generated: $report_file"
}

# Main function
main() {
    log_info "Starting security compliance check for Lucid API..."
    
    # Check prerequisites
    check_prerequisites
    
    # Run compliance checks
    check_sbom_compliance
    check_vulnerability_compliance
    check_container_security
    check_security_config
    
    # Generate report
    generate_compliance_report
    
    # Print final results
    echo ""
    log_info "Security Compliance Results:"
    log_info "  Compliance Score: $COMPLIANCE_SCORE/$MAX_SCORE"
    log_info "  Compliance Percentage: $((COMPLIANCE_SCORE * 100 / MAX_SCORE))%"
    log_info "  CRITICAL Issues: $CRITICAL_ISSUES"
    log_info "  HIGH Issues: $HIGH_ISSUES"
    log_info "  MEDIUM Issues: $MEDIUM_ISSUES"
    log_info "  LOW Issues: $LOW_ISSUES"
    
    echo ""
    if [ $CRITICAL_ISSUES -eq 0 ] && [ $COMPLIANCE_SCORE -ge 80 ]; then
        log_success "Security compliance check PASSED"
        exit 0
    else
        log_error "Security compliance check FAILED"
        if [ $CRITICAL_ISSUES -gt 0 ]; then
            log_error "CRITICAL vulnerabilities must be addressed"
        fi
        exit 1
    fi
}

# Run main function
main "$@"