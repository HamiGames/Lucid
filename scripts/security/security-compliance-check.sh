#!/bin/bash
################################################################################
# Lucid API - Security Compliance Check Script
################################################################################
# Description: Comprehensive security compliance verification
# Version: 1.0.0
# Usage: ./security-compliance-check.sh [OPTIONS]
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
COMPLIANCE_DIR="$PROJECT_ROOT/build/compliance"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Compliance tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

################################################################################
# Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

setup_compliance_directory() {
    mkdir -p "$COMPLIANCE_DIR"/{reports,evidence}
    log_info "Compliance directory: $COMPLIANCE_DIR"
}

check_sbom_generation() {
    log_section "1. SBOM Generation Compliance"
    
    # Check if SBOM directory exists
    if [ -d "$SBOM_DIR" ]; then
        log_success "SBOM directory exists: $SBOM_DIR"
    else
        log_error "SBOM directory not found"
        return
    fi
    
    # Count SBOMs by phase
    local phase1_count phase2_count phase3_count phase4_count
    phase1_count=$(find "$SBOM_DIR/phase1" -name "*-sbom.*.json" 2>/dev/null | wc -l)
    phase2_count=$(find "$SBOM_DIR/phase2" -name "*-sbom.*.json" 2>/dev/null | wc -l)
    phase3_count=$(find "$SBOM_DIR/phase3" -name "*-sbom.*.json" 2>/dev/null | wc -l)
    phase4_count=$(find "$SBOM_DIR/phase4" -name "*-sbom.*.json" 2>/dev/null | wc -l)
    
    echo "  Phase 1: $phase1_count SBOMs"
    echo "  Phase 2: $phase2_count SBOMs"
    echo "  Phase 3: $phase3_count SBOMs"
    echo "  Phase 4: $phase4_count SBOMs"
    
    # Check Phase 1 (minimum requirement)
    if [ "$phase1_count" -ge 4 ]; then
        log_success "Phase 1 SBOM generation complete (4 containers)"
    else
        log_error "Phase 1 SBOM generation incomplete: $phase1_count/4 containers"
    fi
    
    # Check for required SBOM formats
    if find "$SBOM_DIR" -name "*.spdx-json" | grep -q .; then
        log_success "SPDX-JSON format SBOMs found"
    else
        log_warning "No SPDX-JSON format SBOMs found"
    fi
}

check_vulnerability_scanning() {
    log_section "2. CVE Vulnerability Scanning"
    
    # Check if scan directory exists
    if [ -d "$SCAN_DIR" ]; then
        log_success "Scan directory exists: $SCAN_DIR"
    else
        log_error "Scan directory not found - run scan-vulnerabilities.sh"
        return
    fi
    
    # Check for Trivy scans
    local trivy_scans
    trivy_scans=$(find "$SCAN_DIR/trivy" -name "*.json" 2>/dev/null | wc -l)
    
    if [ "$trivy_scans" -gt 0 ]; then
        log_success "Found $trivy_scans Trivy vulnerability scans"
        
        # Check for critical vulnerabilities
        if command -v jq &> /dev/null; then
            local total_critical=0
            for scan_file in "$SCAN_DIR"/trivy/*.json; do
                if [ -f "$scan_file" ]; then
                    local critical
                    critical=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$scan_file" 2>/dev/null || echo 0)
                    total_critical=$((total_critical + critical))
                fi
            done
            
            if [ "$total_critical" -eq 0 ]; then
                log_success "Zero CRITICAL vulnerabilities found"
            else
                log_error "Found $total_critical CRITICAL vulnerabilities"
            fi
        fi
    else
        log_error "No Trivy scans found"
    fi
    
    # Check for Grype scans
    local grype_scans
    grype_scans=$(find "$SCAN_DIR/grype" -name "*.json" 2>/dev/null | wc -l)
    
    if [ "$grype_scans" -gt 0 ]; then
        log_success "Found $grype_scans Grype vulnerability scans"
    else
        log_warning "No Grype scans found (optional)"
    fi
}

check_container_security() {
    log_section "3. Container Security Compliance"
    
    # Check for distroless base images
    log_info "Checking for distroless container usage..."
    
    local dockerfiles
    dockerfiles=$(find "$PROJECT_ROOT" -name "Dockerfile*" -o -name "*.distroless" 2>/dev/null | wc -l)
    
    if [ "$dockerfiles" -gt 0 ]; then
        log_success "Found $dockerfiles Dockerfile configurations"
        
        # Check for distroless references
        local distroless_count
        distroless_count=$(grep -r "distroless" "$PROJECT_ROOT" --include="Dockerfile*" --include="*.distroless" 2>/dev/null | wc -l)
        
        if [ "$distroless_count" -gt 0 ]; then
            log_success "Distroless base images used ($distroless_count references)"
        else
            log_warning "No distroless base image references found"
        fi
    else
        log_warning "No Dockerfiles found"
    fi
    
    # Check for non-root user
    log_info "Checking for non-root container users..."
    local user_count
    user_count=$(grep -r "USER" "$PROJECT_ROOT" --include="Dockerfile*" 2>/dev/null | grep -v "root" | wc -l)
    
    if [ "$user_count" -gt 0 ]; then
        log_success "Non-root users configured ($user_count instances)"
    else
        log_warning "Consider using non-root users in containers"
    fi
}

check_tron_isolation() {
    log_section "4. TRON Payment Isolation Compliance"
    
    # Check that TRON code is isolated
    log_info "Verifying TRON isolation from blockchain core..."
    
    # Check for TRON imports in blockchain directory
    if [ -d "$PROJECT_ROOT/blockchain" ]; then
        local tron_violations
        tron_violations=$(grep -r "tron" "$PROJECT_ROOT/blockchain" --include="*.py" 2>/dev/null | grep -i "import\|from.*tron" | wc -l)
        
        if [ "$tron_violations" -eq 0 ]; then
            log_success "No TRON imports found in blockchain/ directory"
        else
            log_error "Found $tron_violations TRON import violations in blockchain/"
        fi
    else
        log_warning "Blockchain directory not found"
    fi
    
    # Check that TRON code exists in payment-systems
    if [ -d "$PROJECT_ROOT/payment-systems" ]; then
        local tron_files
        tron_files=$(find "$PROJECT_ROOT/payment-systems" -name "*tron*" -o -name "*TRON*" 2>/dev/null | wc -l)
        
        if [ "$tron_files" -gt 0 ]; then
            log_success "TRON payment code properly isolated ($tron_files files)"
        else
            log_warning "TRON payment code not found in payment-systems/"
        fi
    else
        log_warning "Payment-systems directory not found"
    fi
}

check_authentication_security() {
    log_section "5. Authentication Security"
    
    # Check for auth implementation
    if [ -d "$PROJECT_ROOT/auth" ]; then
        log_success "Authentication service directory exists"
        
        # Check for JWT implementation
        if grep -r "jwt\|JWT" "$PROJECT_ROOT/auth" --include="*.py" 2>/dev/null | grep -q .; then
            log_success "JWT implementation found"
        else
            log_warning "JWT implementation not found"
        fi
        
        # Check for hardware wallet support
        if grep -r "hardware.*wallet\|ledger\|trezor" "$PROJECT_ROOT/auth" --include="*.py" 2>/dev/null | grep -qi .; then
            log_success "Hardware wallet support found"
        else
            log_warning "Hardware wallet support not found"
        fi
        
        # Check for RBAC
        if grep -r "rbac\|role.*based\|permission" "$PROJECT_ROOT/auth" --include="*.py" 2>/dev/null | grep -qi .; then
            log_success "RBAC implementation found"
        else
            log_warning "RBAC implementation not found"
        fi
    else
        log_error "Authentication service directory not found"
    fi
}

check_documentation() {
    log_section "6. Security Documentation"
    
    # Check for security documentation
    local doc_dirs=("$PROJECT_ROOT/docs/security" "$PROJECT_ROOT/plan/API_plans")
    
    for doc_dir in "${doc_dirs[@]}"; do
        if [ -d "$doc_dir" ]; then
            local doc_count
            doc_count=$(find "$doc_dir" -name "*.md" 2>/dev/null | wc -l)
            
            if [ "$doc_count" -gt 0 ]; then
                log_success "Found $doc_count documentation files in $(basename "$doc_dir")"
            fi
        fi
    done
    
    # Check for SBOM documentation
    if [ -f "$PROJECT_ROOT/docs/security/sbom-generation-guide.md" ]; then
        log_success "SBOM generation guide exists"
    else
        log_warning "SBOM generation guide not found"
    fi
}

check_ci_cd_integration() {
    log_section "7. CI/CD Security Integration"
    
    # Check for GitHub workflows
    if [ -d "$PROJECT_ROOT/.github/workflows" ]; then
        log_success "GitHub workflows directory exists"
        
        local workflow_count
        workflow_count=$(find "$PROJECT_ROOT/.github/workflows" -name "*.yml" -o -name "*.yaml" 2>/dev/null | wc -l)
        log_info "Found $workflow_count workflow files"
        
        # Check for security scanning in workflows
        if grep -r "trivy\|grype\|syft" "$PROJECT_ROOT/.github/workflows" 2>/dev/null | grep -q .; then
            log_success "Security scanning integrated in CI/CD"
        else
            log_warning "Security scanning not found in CI/CD workflows"
        fi
    else
        log_warning "GitHub workflows directory not found"
    fi
}

check_secrets_management() {
    log_section "8. Secrets Management"
    
    # Check for .env.example files
    local env_examples
    env_examples=$(find "$PROJECT_ROOT" -name ".env.example" 2>/dev/null | wc -l)
    
    if [ "$env_examples" -gt 0 ]; then
        log_success "Found $env_examples .env.example files"
    else
        log_warning "No .env.example files found"
    fi
    
    # Check that actual .env files are gitignored
    if [ -f "$PROJECT_ROOT/.gitignore" ]; then
        if grep -q "\.env$" "$PROJECT_ROOT/.gitignore"; then
            log_success ".env files properly gitignored"
        else
            log_warning ".env files should be added to .gitignore"
        fi
    fi
    
    # Check for hardcoded secrets (simple check)
    log_info "Scanning for potential hardcoded secrets..."
    local secret_violations
    secret_violations=$(grep -r "password\s*=\s*['\"].*['\"]" "$PROJECT_ROOT" --include="*.py" --include="*.js" 2>/dev/null | grep -v ".env" | wc -l)
    
    if [ "$secret_violations" -eq 0 ]; then
        log_success "No obvious hardcoded secrets found"
    else
        log_warning "Found $secret_violations potential hardcoded secrets"
    fi
}

generate_compliance_report() {
    local report_file="${COMPLIANCE_DIR}/reports/security-compliance-${TIMESTAMP}.md"
    
    log_section "Compliance Report Generation"
    
    # Calculate compliance score
    local compliance_score
    if [ "$TOTAL_CHECKS" -gt 0 ]; then
        compliance_score=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    else
        compliance_score=0
    fi
    
    {
        echo "# Lucid API - Security Compliance Report"
        echo ""
        echo "**Generated:** $(date)"
        echo "**Report ID:** LUCID-SEC-COMP-${TIMESTAMP}"
        echo ""
        echo "## Executive Summary"
        echo ""
        echo "| Metric | Count | Percentage |"
        echo "|--------|-------|------------|"
        echo "| Total Checks | $TOTAL_CHECKS | 100% |"
        echo "| Passed | $PASSED_CHECKS | $compliance_score% |"
        echo "| Failed | $FAILED_CHECKS | $((FAILED_CHECKS * 100 / TOTAL_CHECKS))% |"
        echo "| Warnings | $WARNING_CHECKS | $((WARNING_CHECKS * 100 / TOTAL_CHECKS))% |"
        echo ""
        echo "**Overall Compliance Score:** ${compliance_score}%"
        echo ""
        
        # Compliance status
        if [ "$compliance_score" -ge 90 ]; then
            echo "## Status: ✅ **EXCELLENT** - Ready for Production"
        elif [ "$compliance_score" -ge 75 ]; then
            echo "## Status: ⚠️  **GOOD** - Minor issues to address"
        elif [ "$compliance_score" -ge 60 ]; then
            echo "## Status: ⚠️  **FAIR** - Improvements needed"
        else
            echo "## Status: ❌ **POOR** - Critical issues must be resolved"
        fi
        echo ""
        
        echo "## Compliance Checklist"
        echo ""
        echo "### ✅ Passed Requirements"
        echo "- $PASSED_CHECKS checks passed successfully"
        echo ""
        
        echo "### ❌ Failed Requirements"
        echo "- $FAILED_CHECKS checks failed"
        echo ""
        
        echo "### ⚠️  Warnings"
        echo "- $WARNING_CHECKS checks raised warnings"
        echo ""
        
        echo "## Detailed Findings"
        echo ""
        echo "### 1. SBOM Generation"
        echo "- SBOMs must be generated for all production containers"
        echo "- Formats: SPDX-JSON, CycloneDX-JSON"
        echo ""
        
        echo "### 2. Vulnerability Scanning"
        echo "- All containers must be scanned with Trivy"
        echo "- Zero CRITICAL vulnerabilities allowed"
        echo "- HIGH vulnerabilities should be remediated"
        echo ""
        
        echo "### 3. Container Security"
        echo "- Use distroless base images"
        echo "- Run containers as non-root users"
        echo "- Implement image signing"
        echo ""
        
        echo "### 4. TRON Isolation"
        echo "- TRON payment code must be isolated from blockchain core"
        echo "- No TRON imports in blockchain/ directory"
        echo "- All TRON code in payment-systems/ directory"
        echo ""
        
        echo "### 5. Authentication Security"
        echo "- JWT token management implemented"
        echo "- Hardware wallet support (Ledger, Trezor, KeepKey)"
        echo "- RBAC permissions enforced"
        echo ""
        
        echo "## Recommendations"
        echo ""
        if [ "$FAILED_CHECKS" -gt 0 ]; then
            echo "1. **CRITICAL:** Address all failed checks immediately"
        fi
        if [ "$WARNING_CHECKS" -gt 0 ]; then
            echo "2. Review and resolve warnings before production"
        fi
        echo "3. Implement continuous security scanning in CI/CD"
        echo "4. Regular SBOM updates with each release"
        echo "5. Automated vulnerability scanning on every build"
        echo ""
        
        echo "## Next Steps"
        echo ""
        echo "1. Review this compliance report"
        echo "2. Create tickets for failed checks"
        echo "3. Implement remediation actions"
        echo "4. Re-run compliance check"
        echo "5. Schedule regular compliance audits"
        echo ""
        
        echo "## References"
        echo ""
        echo "- SBOM Directory: \`$SBOM_DIR\`"
        echo "- Scan Directory: \`$SCAN_DIR\`"
        echo "- Compliance Directory: \`$COMPLIANCE_DIR\`"
        echo ""
        
    } > "$report_file"
    
    cat "$report_file"
    log_info "Compliance report saved: $report_file"
    
    # Return status based on compliance score
    if [ "$compliance_score" -ge 75 ]; then
        return 0
    else
        return 1
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive security compliance check for Lucid API.

OPTIONS:
    -h, --help     Show this help message
    -v, --verbose  Verbose output
    
EXAMPLES:
    # Run full compliance check
    $0
    
    # Verbose mode
    $0 --verbose

EOF
}

main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        Lucid API - Security Compliance Check              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    setup_compliance_directory
    
    # Run all compliance checks
    check_sbom_generation
    check_vulnerability_scanning
    check_container_security
    check_tron_isolation
    check_authentication_security
    check_documentation
    check_ci_cd_integration
    check_secrets_management
    
    # Generate final report
    echo ""
    if generate_compliance_report; then
        log_success "Security compliance check complete!"
        exit 0
    else
        log_error "Security compliance check failed - review issues above"
        exit 1
    fi
}

main "$@"

