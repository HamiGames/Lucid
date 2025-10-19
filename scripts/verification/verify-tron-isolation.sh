#!/bin/bash

# TRON Isolation Verification Script (Simplified)
# Verifies that TRON payment system is completely isolated from blockchain core
# Part of Step 16: TRON Isolation Security Scan from docker-build-process-plan.md
#
# Requirements (exact from build plan):
# - No "tron" references in blockchain/
# - No "TronWeb" references
# - No "payment" in blockchain/core/
# - No "USDT" or "TRX" references
# - Verify payment-systems/tron/ exists and isolated
# - Verify no blockchain references in payment-systems/tron/
# - Exit 1 if any violations found

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
REPORT_FILE="$REPORTS_DIR/tron-isolation-report-$(date +%Y%m%d-%H%M%S).txt"

log "Starting TRON Isolation Verification"
log "Project Root: $PROJECT_ROOT"
log "Report File: $REPORT_FILE"

# Function to scan for TRON references in blockchain core
scan_blockchain_core() {
    log "Scanning blockchain core directory for TRON references..."
    
    local violations=0
    local files_scanned=0
    
    # Check if blockchain directory exists
    if [[ ! -d "$BLOCKCHAIN_DIR" ]]; then
        log_error "Blockchain directory not found: $BLOCKCHAIN_DIR"
        return 1
    fi
    
    # Scan for TRON-related keywords in blockchain core (exact requirements from build plan)
    local tron_keywords=("tron" "TRON" "TronWeb" "payment" "USDT" "TRX")
    
    for keyword in "${tron_keywords[@]}"; do
        log "Scanning for keyword: $keyword"
        
        # Search in Python files
        while IFS= read -r -d '' file; do
            files_scanned=$((files_scanned + 1))
            
            if grep -q -i "$keyword" "$file"; then
                violations=$((violations + 1))
                log_warning "TRON reference found in blockchain core: $file"
                echo "VIOLATION: $file contains '$keyword'" >> "$REPORT_FILE"
            fi
        done < <(find "$BLOCKCHAIN_DIR" -name "*.py" -type f -print0)
        
        # Search in configuration files
        while IFS= read -r -d '' file; do
            files_scanned=$((files_scanned + 1))
            
            if grep -q -i "$keyword" "$file"; then
                violations=$((violations + 1))
                log_warning "TRON reference found in blockchain config: $file"
                echo "VIOLATION: $file contains '$keyword'" >> "$REPORT_FILE"
            fi
        done < <(find "$BLOCKCHAIN_DIR" -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.toml" -type f -print0)
    done
    
    echo "Blockchain core scan: $violations violations found in $files_scanned files" >> "$REPORT_FILE"
    
    if [[ $violations -eq 0 ]]; then
        log_success "No TRON references found in blockchain core"
        return 0
    else
        log_error "Found $violations TRON violations in blockchain core"
        return 1
    fi
}

# Function to verify payment systems directory structure and isolation
scan_payment_systems() {
    log "Scanning payment systems directory for TRON files and isolation..."
    
    local tron_files=0
    local blockchain_references=0
    local files_scanned=0
    
    # Check if payment-systems directory exists
    if [[ ! -d "$PAYMENT_SYSTEMS_DIR" ]]; then
        log_error "Payment systems directory not found: $PAYMENT_SYSTEMS_DIR"
        return 1
    fi
    
    # Check if payment-systems/tron directory exists (required by build plan)
    local tron_dir="$PAYMENT_SYSTEMS_DIR/tron"
    if [[ ! -d "$tron_dir" ]]; then
        log_error "Required payment-systems/tron directory not found: $tron_dir"
        return 1
    fi
    log_success "payment-systems/tron directory exists and is isolated"
    
    # Find all TRON-related files
    while IFS= read -r -d '' file; do
        files_scanned=$((files_scanned + 1))
        tron_files=$((tron_files + 1))
        log "Found TRON file: $file"
    done < <(find "$PAYMENT_SYSTEMS_DIR" -type f \( -name "*tron*" -o -name "*TRON*" -o -name "*Tron*" \) -print0 2>/dev/null)
    
    # Check for blockchain references in payment-systems/tron (should be isolated)
    log "Checking for blockchain references in payment-systems/tron..."
    local blockchain_keywords=("blockchain" "consensus" "block" "mining" "node" "peer")
    
    for keyword in "${blockchain_keywords[@]}"; do
        while IFS= read -r -d '' file; do
            if grep -q -i "$keyword" "$file"; then
                blockchain_references=$((blockchain_references + 1))
                log_warning "Blockchain reference found in TRON payment system: $file"
                echo "VIOLATION: $file contains blockchain reference '$keyword'" >> "$REPORT_FILE"
            fi
        done < <(find "$tron_dir" -name "*.py" -type f -print0 2>/dev/null)
    done
    
    echo "Payment systems scan: $tron_files TRON files found, $blockchain_references blockchain references" >> "$REPORT_FILE"
    
    if [[ $tron_files -gt 0 ]]; then
        log_success "Found $tron_files TRON files in payment systems directory"
        if [[ $blockchain_references -eq 0 ]]; then
            log_success "No blockchain references found in payment-systems/tron (properly isolated)"
            return 0
        else
            log_error "Found $blockchain_references blockchain references in payment-systems/tron"
            return 1
        fi
    else
        log_warning "No TRON files found in payment systems directory"
        return 1
    fi
}

# Function to verify directory structure compliance
verify_directory_structure() {
    log "Verifying directory structure compliance..."
    
    local compliance_checks=0
    local total_checks=0
    
    # Check required directories exist
    local required_dirs=(
        "blockchain/core"
        "blockchain/api" 
        "payment-systems/tron"
    )
    
    for dir in "${required_dirs[@]}"; do
        total_checks=$((total_checks + 1))
        local full_path="$PROJECT_ROOT/$dir"
        if [[ -d "$full_path" ]]; then
            compliance_checks=$((compliance_checks + 1))
            log_success "Directory exists: $dir"
            echo "✓ $dir exists" >> "$REPORT_FILE"
        else
            log_error "Directory missing: $dir"
            echo "✗ $dir missing" >> "$REPORT_FILE"
        fi
    done
    
    # Check for forbidden TRON files in blockchain directory (exact requirements)
    total_checks=$((total_checks + 1))
    if find "$BLOCKCHAIN_DIR" -name "*tron*" -o -name "*TRON*" -o -name "*Tron*" -o -name "*payment*" -o -name "*USDT*" -o -name "*TRX*" 2>/dev/null | grep -q .; then
        log_error "TRON/payment files found in blockchain directory"
        echo "✗ TRON/payment files found in blockchain directory" >> "$REPORT_FILE"
    else
        compliance_checks=$((compliance_checks + 1))
        log_success "No TRON/payment files in blockchain directory"
        echo "✓ No TRON/payment files in blockchain directory" >> "$REPORT_FILE"
    fi
    
    echo "Directory structure: $compliance_checks/$total_checks checks passed" >> "$REPORT_FILE"
    return $((total_checks - compliance_checks))
}

# Function to generate final summary
generate_summary() {
    log "Generating verification summary..."
    
    # Read violations from report file
    local blockchain_violations=$(grep -c "VIOLATION.*blockchain core" "$REPORT_FILE" 2>/dev/null || echo "0")
    local tron_violations=$(grep -c "VIOLATION.*TRON payment system" "$REPORT_FILE" 2>/dev/null || echo "0")
    local total_violations=$((blockchain_violations + tron_violations))
    
    # Print summary
    log "=== TRON ISOLATION VERIFICATION SUMMARY ==="
    log "Blockchain Core Violations: $blockchain_violations"
    log "Blockchain References in TRON: $tron_violations"
    log "Total Violations: $total_violations"
    
    echo "=== TRON ISOLATION VERIFICATION SUMMARY ===" >> "$REPORT_FILE"
    echo "Blockchain Core Violations: $blockchain_violations" >> "$REPORT_FILE"
    echo "Blockchain References in TRON: $tron_violations" >> "$REPORT_FILE"
    echo "Total Violations: $total_violations" >> "$REPORT_FILE"
    
    # Exit with code 1 if any violations found (exact requirement from build plan)
    if [[ $total_violations -gt 0 ]]; then
        log_error "TRON isolation verification FAILED - Found $total_violations violations"
        log_error "Exit 1 if any violations found (as required by docker-build-process-plan.md)"
        echo "RESULT: FAILED - $total_violations violations found" >> "$REPORT_FILE"
        return 1
    else
        log_success "TRON isolation verification PASSED"
        echo "RESULT: PASSED - No violations found" >> "$REPORT_FILE"
        return 0
    fi
}

# Main execution
main() {
    log "=== TRON ISOLATION VERIFICATION ==="
    log "Step 16: TRON Isolation Security Scan"
    log "====================================="
    
    # Initialize report file
    echo "TRON Isolation Verification Report" > "$REPORT_FILE"
    echo "Generated: $(date)" >> "$REPORT_FILE"
    echo "Project Root: $PROJECT_ROOT" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Run all verification steps
    local exit_code=0
    
    scan_blockchain_core || exit_code=1
    scan_payment_systems || exit_code=1
    verify_directory_structure || exit_code=1
    generate_summary || exit_code=1
    
    log "Verification completed. Report saved to: $REPORT_FILE"
    log "Log file: $LOG_FILE"
    
    exit $exit_code
}

# Run main function
main "$@"
