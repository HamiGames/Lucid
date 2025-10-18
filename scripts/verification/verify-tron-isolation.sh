#!/bin/bash

# TRON Isolation Verification Script
# Verifies that TRON payment system is completely isolated from blockchain core
# Part of Step 28: TRON Isolation Verification

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BLOCKCHAIN_DIR="$PROJECT_ROOT/blockchain"
PAYMENT_SYSTEMS_DIR="$PROJECT_ROOT/payment-systems"
REPORTS_DIR="$PROJECT_ROOT/reports/verification"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Logging
LOG_FILE="$REPORTS_DIR/tron-isolation-verification-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
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

# Initialize verification report
REPORT_FILE="$REPORTS_DIR/tron-isolation-report-$(date +%Y%m%d-%H%M%S).json"
cat > "$REPORT_FILE" << EOF
{
  "verification_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_root": "$PROJECT_ROOT",
  "verification_results": {
    "blockchain_core_scan": {
      "status": "pending",
      "violations": [],
      "files_scanned": 0
    },
    "payment_systems_scan": {
      "status": "pending", 
      "tron_files_found": 0,
      "files_scanned": 0
    },
    "network_isolation": {
      "status": "pending",
      "network_checks": []
    },
    "directory_structure": {
      "status": "pending",
      "compliance_checks": []
    }
  },
  "summary": {
    "total_violations": 0,
    "isolation_verified": false,
    "compliance_score": 0
  }
}
EOF

log "Starting TRON Isolation Verification"
log "Project Root: $PROJECT_ROOT"
log "Report File: $REPORT_FILE"

# Function to update JSON report
update_report() {
    local key="$1"
    local value="$2"
    local temp_file=$(mktemp)
    
    jq ".verification_results.$key = $value" "$REPORT_FILE" > "$temp_file" && mv "$temp_file" "$REPORT_FILE"
}

# Function to scan for TRON references in blockchain core
scan_blockchain_core() {
    log "Scanning blockchain core directory for TRON references..."
    
    local violations=()
    local files_scanned=0
    
    # Check if blockchain directory exists
    if [[ ! -d "$BLOCKCHAIN_DIR" ]]; then
        log_error "Blockchain directory not found: $BLOCKCHAIN_DIR"
        return 1
    fi
    
    # Scan for TRON-related keywords in blockchain core
    local tron_keywords=("tron" "TRON" "TronNode" "TronClient" "tron_client" "tron-node" "tron-client" "usdt" "USDT" "TRX" "trx")
    
    for keyword in "${tron_keywords[@]}"; do
        log "Scanning for keyword: $keyword"
        
        # Search in Python files
        while IFS= read -r -d '' file; do
            files_scanned=$((files_scanned + 1))
            
            if grep -q -i "$keyword" "$file"; then
                local line_numbers=$(grep -n -i "$keyword" "$file" | cut -d: -f1)
                violations+=("$file:$line_numbers:$keyword")
                log_warning "TRON reference found in blockchain core: $file"
            fi
        done < <(find "$BLOCKCHAIN_DIR" -name "*.py" -type f -print0)
        
        # Search in configuration files
        while IFS= read -r -d '' file; do
            files_scanned=$((files_scanned + 1))
            
            if grep -q -i "$keyword" "$file"; then
                local line_numbers=$(grep -n -i "$keyword" "$file" | cut -d: -f1)
                violations+=("$file:$line_numbers:$keyword")
                log_warning "TRON reference found in blockchain config: $file"
            fi
        done < <(find "$BLOCKCHAIN_DIR" -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.toml" -type f -print0)
    done
    
    # Update report
    local violations_json=$(printf '%s\n' "${violations[@]}" | jq -R . | jq -s .)
    update_report "blockchain_core_scan" "{\"status\": \"completed\", \"violations\": $violations_json, \"files_scanned\": $files_scanned}"
    
    if [[ ${#violations[@]} -eq 0 ]]; then
        log_success "No TRON references found in blockchain core"
        return 0
    else
        log_error "Found ${#violations[@]} TRON violations in blockchain core"
        return 1
    fi
}

# Function to verify payment systems directory structure
scan_payment_systems() {
    log "Scanning payment systems directory for TRON files..."
    
    local tron_files=()
    local files_scanned=0
    
    # Check if payment-systems directory exists
    if [[ ! -d "$PAYMENT_SYSTEMS_DIR" ]]; then
        log_error "Payment systems directory not found: $PAYMENT_SYSTEMS_DIR"
        return 1
    fi
    
    # Find all TRON-related files
    while IFS= read -r -d '' file; do
        files_scanned=$((files_scanned + 1))
        tron_files+=("$file")
        log "Found TRON file: $file"
    done < <(find "$PAYMENT_SYSTEMS_DIR" -type f \( -name "*tron*" -o -name "*TRON*" -o -name "*Tron*" \) -print0)
    
    # Update report
    local tron_files_json=$(printf '%s\n' "${tron_files[@]}" | jq -R . | jq -s .)
    update_report "payment_systems_scan" "{\"status\": \"completed\", \"tron_files_found\": ${#tron_files[@]}, \"files_scanned\": $files_scanned, \"files\": $tron_files_json}"
    
    if [[ ${#tron_files[@]} -gt 0 ]]; then
        log_success "Found ${#tron_files[@]} TRON files in payment systems directory"
        return 0
    else
        log_warning "No TRON files found in payment systems directory"
        return 1
    fi
}

# Function to verify network isolation
verify_network_isolation() {
    log "Verifying network isolation..."
    
    local network_checks=()
    
    # Check Docker networks
    if command -v docker &> /dev/null; then
        log "Checking Docker networks..."
        
        # Check for lucid-dev network (main network)
        if docker network ls | grep -q "lucid-dev"; then
            network_checks+=("lucid-dev network exists")
            log_success "lucid-dev network found"
        else
            network_checks+=("lucid-dev network missing")
            log_warning "lucid-dev network not found"
        fi
        
        # Check for lucid-network-isolated network (TRON isolation)
        if docker network ls | grep -q "lucid-network-isolated"; then
            network_checks+=("lucid-network-isolated network exists")
            log_success "lucid-network-isolated network found"
        else
            network_checks+=("lucid-network-isolated network missing")
            log_warning "lucid-network-isolated network not found"
        fi
    else
        network_checks+=("Docker not available for network verification")
        log_warning "Docker not available"
    fi
    
    # Update report
    local network_checks_json=$(printf '%s\n' "${network_checks[@]}" | jq -R . | jq -s .)
    update_report "network_isolation" "{\"status\": \"completed\", \"network_checks\": $network_checks_json}"
}

# Function to verify directory structure compliance
verify_directory_structure() {
    log "Verifying directory structure compliance..."
    
    local compliance_checks=()
    
    # Check required directories exist
    local required_dirs=(
        "blockchain/core"
        "blockchain/api" 
        "payment-systems/tron"
        "payment-systems/tron/services"
        "payment-systems/tron/api"
        "payment-systems/tron/models"
    )
    
    for dir in "${required_dirs[@]}"; do
        local full_path="$PROJECT_ROOT/$dir"
        if [[ -d "$full_path" ]]; then
            compliance_checks+=("✓ $dir exists")
            log_success "Directory exists: $dir"
        else
            compliance_checks+=("✗ $dir missing")
            log_error "Directory missing: $dir"
        fi
    done
    
    # Check for forbidden TRON files in blockchain directory
    local forbidden_patterns=(
        "blockchain/**/*tron*"
        "blockchain/**/*TRON*"
        "blockchain/**/*Tron*"
    )
    
    for pattern in "${forbidden_patterns[@]}"; do
        if find "$BLOCKCHAIN_DIR" -name "*tron*" -o -name "*TRON*" -o -name "*Tron*" 2>/dev/null | grep -q .; then
            compliance_checks+=("✗ TRON files found in blockchain directory")
            log_error "TRON files found in blockchain directory"
        else
            compliance_checks+=("✓ No TRON files in blockchain directory")
            log_success "No TRON files in blockchain directory"
        fi
    done
    
    # Update report
    local compliance_checks_json=$(printf '%s\n' "${compliance_checks[@]}" | jq -R . | jq -s .)
    update_report "directory_structure" "{\"status\": \"completed\", \"compliance_checks\": $compliance_checks_json}"
}

# Function to generate final summary
generate_summary() {
    log "Generating verification summary..."
    
    # Count violations
    local blockchain_violations=$(jq '.verification_results.blockchain_core_scan.violations | length' "$REPORT_FILE")
    local total_violations=$blockchain_violations
    
    # Calculate compliance score
    local total_checks=4  # blockchain_scan, payment_scan, network, directory
    local passed_checks=0
    
    if [[ $(jq '.verification_results.blockchain_core_scan.violations | length' "$REPORT_FILE") -eq 0 ]]; then
        passed_checks=$((passed_checks + 1))
    fi
    
    if [[ $(jq '.verification_results.payment_systems_scan.tron_files_found' "$REPORT_FILE") -gt 0 ]]; then
        passed_checks=$((passed_checks + 1))
    fi
    
    if [[ $(jq '.verification_results.network_isolation.network_checks | length' "$REPORT_FILE") -gt 0 ]]; then
        passed_checks=$((passed_checks + 1))
    fi
    
    if [[ $(jq '.verification_results.directory_structure.compliance_checks | length' "$REPORT_FILE") -gt 0 ]]; then
        passed_checks=$((passed_checks + 1))
    fi
    
    local compliance_score=$((passed_checks * 100 / total_checks))
    local isolation_verified=$([[ $total_violations -eq 0 && $compliance_score -ge 75 ]] && echo "true" || echo "false")
    
    # Update final summary
    jq ".summary = {
        \"total_violations\": $total_violations,
        \"isolation_verified\": $isolation_verified,
        \"compliance_score\": $compliance_score,
        \"passed_checks\": $passed_checks,
        \"total_checks\": $total_checks
    }" "$REPORT_FILE" > "${REPORT_FILE}.tmp" && mv "${REPORT_FILE}.tmp" "$REPORT_FILE"
    
    # Print summary
    log "=== TRON ISOLATION VERIFICATION SUMMARY ==="
    log "Total Violations: $total_violations"
    log "Compliance Score: $compliance_score%"
    log "Isolation Verified: $isolation_verified"
    log "Passed Checks: $passed_checks/$total_checks"
    
    if [[ "$isolation_verified" == "true" ]]; then
        log_success "TRON isolation verification PASSED"
        return 0
    else
        log_error "TRON isolation verification FAILED"
        return 1
    fi
}

# Main execution
main() {
    log "=== TRON ISOLATION VERIFICATION ==="
    log "Step 28: TRON Isolation Verification"
    log "====================================="
    
    # Run all verification steps
    scan_blockchain_core
    scan_payment_systems  
    verify_network_isolation
    verify_directory_structure
    generate_summary
    
    local exit_code=$?
    
    log "Verification completed. Report saved to: $REPORT_FILE"
    log "Log file: $LOG_FILE"
    
    exit $exit_code
}

# Run main function
main "$@"
