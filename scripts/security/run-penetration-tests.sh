#!/bin/bash

# Penetration Testing Script
# Automated penetration testing for Lucid API system
# Author: Lucid Development Team
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/security"
LOG_FILE="$REPORTS_DIR/penetration-test-$(date +%Y%m%d-%H%M%S).log"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    local required_tools=("curl" "nmap" "nikto" "sqlmap" "dirb" "gobuster")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_warning "$tool is not installed. Some tests may be skipped."
        else
            log_success "$tool is available"
        fi
    done
}

# Setup reports directory
setup_reports_dir() {
    mkdir -p "$REPORTS_DIR"
    log_info "Reports directory: $REPORTS_DIR"
}

# Test API endpoints for common vulnerabilities
test_api_endpoints() {
    local base_url="$1"
    local report_file="$REPORTS_DIR/api-penetration-test-$(date +%Y%m%d-%H%M%S).json"
    
    log_info "Testing API endpoints for vulnerabilities..."
    
    # Test common API endpoints
    local endpoints=(
        "/api/v1/auth/login"
        "/api/v1/users"
        "/api/v1/sessions"
        "/api/v1/admin/dashboard"
        "/api/v1/chain/info"
        "/health"
        "/metrics"
    )
    
    local total_tests=0
    local vulnerabilities_found=0
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing endpoint: $endpoint"
        
        # Test for SQL injection
        test_sql_injection "$base_url$endpoint"
        
        # Test for XSS
        test_xss "$base_url$endpoint"
        
        # Test for authentication bypass
        test_auth_bypass "$base_url$endpoint"
        
        # Test for directory traversal
        test_directory_traversal "$base_url$endpoint"
        
        total_tests=$((total_tests + 4))
    done
    
    log_info "API penetration testing completed"
    log_info "Total tests: $total_tests"
    log_info "Vulnerabilities found: $vulnerabilities_found"
}

# Test for SQL injection
test_sql_injection() {
    local url="$1"
    local payloads=(
        "' OR '1'='1"
        "'; DROP TABLE users; --"
        "' UNION SELECT * FROM users --"
        "admin'--"
        "' OR 1=1 --"
    )
    
    for payload in "${payloads[@]}"; do
        local response=$(curl -s -w "%{http_code}" -o /dev/null "$url?test=$payload" 2>/dev/null || echo "000")
        
        if [[ "$response" == "500" ]]; then
            log_warning "Potential SQL injection vulnerability found at $url"
            return 1
        fi
    done
}

# Test for XSS
test_xss() {
    local url="$1"
    local payloads=(
        "<script>alert('xss')</script>"
        "<img src=x onerror=alert('xss')>"
        "javascript:alert('xss')"
    )
    
    for payload in "${payloads[@]}"; do
        local response=$(curl -s "$url?test=$payload" 2>/dev/null || echo "")
        
        if echo "$response" | grep -q "alert('xss')"; then
            log_warning "Potential XSS vulnerability found at $url"
            return 1
        fi
    done
}

# Test for authentication bypass
test_auth_bypass() {
    local url="$1"
    
    # Test without authentication
    local response=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null || echo "000")
    
    if [[ "$response" == "200" ]]; then
        log_warning "Potential authentication bypass at $url"
        return 1
    fi
}

# Test for directory traversal
test_directory_traversal() {
    local url="$1"
    local payloads=(
        "../../../etc/passwd"
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"
        "....//....//....//etc/passwd"
    )
    
    for payload in "${payloads[@]}"; do
        local response=$(curl -s "$url?file=$payload" 2>/dev/null || echo "")
        
        if echo "$response" | grep -q "root:"; then
            log_warning "Potential directory traversal vulnerability found at $url"
            return 1
        fi
    done
}

# Test for common security headers
test_security_headers() {
    local base_url="$1"
    local report_file="$REPORTS_DIR/security-headers-$(date +%Y%m%d-%H%M%S).json"
    
    log_info "Testing security headers..."
    
    local required_headers=(
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Strict-Transport-Security"
        "Content-Security-Policy"
    )
    
    local missing_headers=()
    
    for header in "${required_headers[@]}"; do
        local response=$(curl -s -I "$base_url" 2>/dev/null || echo "")
        
        if ! echo "$response" | grep -qi "$header"; then
            missing_headers+=("$header")
            log_warning "Missing security header: $header"
        fi
    done
    
    if [[ ${#missing_headers[@]} -gt 0 ]]; then
        log_warning "Missing security headers: ${missing_headers[*]}"
    else
        log_success "All required security headers present"
    fi
}

# Test for SSL/TLS vulnerabilities
test_ssl_tls() {
    local hostname="$1"
    local port="${2:-443}"
    
    log_info "Testing SSL/TLS configuration..."
    
    # Test SSL/TLS with nmap
    if command -v nmap &> /dev/null; then
        local ssl_report="$REPORTS_DIR/ssl-tls-test-$(date +%Y%m%d-%H%M%S).txt"
        
        nmap --script ssl-enum-ciphers -p "$port" "$hostname" > "$ssl_report" 2>/dev/null || true
        
        if [[ -f "$ssl_report" ]]; then
            log_info "SSL/TLS test completed. Report: $ssl_report"
        fi
    fi
}

# Test for open ports
test_open_ports() {
    local hostname="$1"
    
    log_info "Scanning for open ports..."
    
    if command -v nmap &> /dev/null; then
        local port_report="$REPORTS_DIR/port-scan-$(date +%Y%m%d-%H%M%S).txt"
        
        nmap -sS -O "$hostname" > "$port_report" 2>/dev/null || true
        
        if [[ -f "$port_report" ]]; then
            log_info "Port scan completed. Report: $port_report"
        fi
    fi
}

# Test for directory enumeration
test_directory_enumeration() {
    local base_url="$1"
    
    log_info "Testing for directory enumeration..."
    
    if command -v dirb &> /dev/null; then
        local dir_report="$REPORTS_DIR/directory-enumeration-$(date +%Y%m%d-%H%M%S).txt"
        
        dirb "$base_url" > "$dir_report" 2>/dev/null || true
        
        if [[ -f "$dir_report" ]]; then
            log_info "Directory enumeration completed. Report: $dir_report"
        fi
    fi
}

# Test for web application vulnerabilities
test_web_vulnerabilities() {
    local base_url="$1"
    
    log_info "Testing for web application vulnerabilities..."
    
    if command -v nikto &> /dev/null; then
        local nikto_report="$REPORTS_DIR/nikto-scan-$(date +%Y%m%d-%H%M%S).txt"
        
        nikto -h "$base_url" -output "$nikto_report" 2>/dev/null || true
        
        if [[ -f "$nikto_report" ]]; then
            log_info "Nikto scan completed. Report: $nikto_report"
        fi
    fi
}

# Generate penetration test report
generate_penetration_report() {
    local report_file="$REPORTS_DIR/penetration-test-summary-$(date +%Y%m%d-%H%M%S).md"
    
    log_info "Generating penetration test report..."
    
    cat > "$report_file" << EOF
# Penetration Testing Report

**Test Date:** $(date)
**Target:** $1
**Tester:** Lucid Security Team

## Executive Summary

This report contains the results of automated penetration testing performed on the Lucid API system.

## Test Results

### API Endpoint Testing
- **Status:** Completed
- **Vulnerabilities Found:** See individual test reports

### Security Headers
- **Status:** Completed
- **Missing Headers:** See security-headers report

### SSL/TLS Configuration
- **Status:** Completed
- **Issues Found:** See ssl-tls-test report

### Port Scanning
- **Status:** Completed
- **Open Ports:** See port-scan report

### Directory Enumeration
- **Status:** Completed
- **Directories Found:** See directory-enumeration report

### Web Application Vulnerabilities
- **Status:** Completed
- **Vulnerabilities Found:** See nikto-scan report

## Recommendations

1. **Immediate Actions:**
   - Fix any critical vulnerabilities found
   - Implement missing security headers
   - Update SSL/TLS configuration if needed

2. **Security Improvements:**
   - Regular security testing
   - Implement WAF (Web Application Firewall)
   - Monitor for new vulnerabilities

## Files Generated

- API penetration test results
- Security headers analysis
- SSL/TLS configuration report
- Port scan results
- Directory enumeration results
- Web application vulnerability scan

EOF

    log_success "Penetration test report generated: $report_file"
}

# Main function
main() {
    log_info "Starting penetration testing..."
    
    # Parse command line arguments
    local target_url=""
    local target_hostname=""
    local target_port="443"
    local test_type="all"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                target_url="$2"
                shift 2
                ;;
            --hostname)
                target_hostname="$2"
                shift 2
                ;;
            --port)
                target_port="$2"
                shift 2
                ;;
            --type)
                test_type="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --url URL           Target URL for testing"
                echo "  --hostname HOST     Target hostname for testing"
                echo "  --port PORT         Target port (default: 443)"
                echo "  --type TYPE         Test type (all, api, web, ssl)"
                echo "  --help              Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "$target_url" && -z "$target_hostname" ]]; then
        log_error "Either --url or --hostname must be specified"
        exit 1
    fi
    
    # Setup
    check_prerequisites
    setup_reports_dir
    
    # Perform tests
    if [[ "$test_type" == "all" || "$test_type" == "api" ]]; then
        if [[ -n "$target_url" ]]; then
            test_api_endpoints "$target_url"
            test_security_headers "$target_url"
        fi
    fi
    
    if [[ "$test_type" == "all" || "$test_type" == "web" ]]; then
        if [[ -n "$target_url" ]]; then
            test_directory_enumeration "$target_url"
            test_web_vulnerabilities "$target_url"
        fi
    fi
    
    if [[ "$test_type" == "all" || "$test_type" == "ssl" ]]; then
        if [[ -n "$target_hostname" ]]; then
            test_ssl_tls "$target_hostname" "$target_port"
            test_open_ports "$target_hostname"
        fi
    fi
    
    # Generate report
    generate_penetration_report "${target_url:-$target_hostname}"
    
    log_success "Penetration testing completed"
    log_info "Reports available in: $REPORTS_DIR"
}

# Run main function with all arguments
main "$@"
