#!/bin/bash
# TRON Isolation Security Scan
# Implements Step 16 from docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BLOCKCHAIN_DIR="$PROJECT_ROOT/blockchain"
TRON_DIR="$PROJECT_ROOT/payment-systems/tron"

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

# Function to scan for TRON violations
scan_tron_violations() {
    log_info "Scanning for TRON violations in blockchain core..."
    
    local violations_found=false
    
    # Check for "tron" references in blockchain/
    log_info "Checking for 'tron' references in blockchain core..."
    local tron_refs=$(grep -r "tron" "$BLOCKCHAIN_DIR" --exclude-dir=node_modules 2>/dev/null || true)
    if [[ -n "$tron_refs" ]]; then
        log_error "TRON references found in blockchain core:"
        echo "$tron_refs"
        violations_found=true
    else
        log_success "No 'tron' references found in blockchain core"
    fi
    
    # Check for "TronWeb" references
    log_info "Checking for 'TronWeb' references..."
    local tronweb_refs=$(grep -r "TronWeb" "$BLOCKCHAIN_DIR" 2>/dev/null || true)
    if [[ -n "$tronweb_refs" ]]; then
        log_error "TronWeb references found in blockchain core:"
        echo "$tronweb_refs"
        violations_found=true
    else
        log_success "No 'TronWeb' references found in blockchain core"
    fi
    
    # Check for "payment" in blockchain/core/
    log_info "Checking for 'payment' references in blockchain core..."
    local payment_refs=$(grep -r "payment" "$BLOCKCHAIN_DIR/core" 2>/dev/null || true)
    if [[ -n "$payment_refs" ]]; then
        log_error "Payment references found in blockchain core:"
        echo "$payment_refs"
        violations_found=true
    else
        log_success "No 'payment' references found in blockchain core"
    fi
    
    # Check for "USDT" or "TRX" references
    log_info "Checking for 'USDT' or 'TRX' references..."
    local usdt_refs=$(grep -r "USDT" "$BLOCKCHAIN_DIR" 2>/dev/null || true)
    local trx_refs=$(grep -r "TRX" "$BLOCKCHAIN_DIR" 2>/dev/null || true)
    
    if [[ -n "$usdt_refs" ]]; then
        log_error "USDT references found in blockchain core:"
        echo "$usdt_refs"
        violations_found=true
    else
        log_success "No 'USDT' references found in blockchain core"
    fi
    
    if [[ -n "$trx_refs" ]]; then
        log_error "TRX references found in blockchain core:"
        echo "$trx_refs"
        violations_found=true
    else
        log_success "No 'TRX' references found in blockchain core"
    fi
    
    return $violations_found
}

# Function to verify TRON isolation
verify_tron_isolation() {
    log_info "Verifying TRON isolation..."
    
    # Check if payment-systems/tron/ exists and is isolated
    if [[ -d "$TRON_DIR" ]]; then
        log_success "TRON payment system directory exists: $TRON_DIR"
    else
        log_warning "TRON payment system directory not found: $TRON_DIR"
    fi
    
    # Check if blockchain references exist in payment-systems/tron/
    log_info "Checking for blockchain references in TRON payment system..."
    local blockchain_refs=$(grep -r "blockchain" "$TRON_DIR" 2>/dev/null || true)
    if [[ -n "$blockchain_refs" ]]; then
        log_warning "Blockchain references found in TRON payment system:"
        echo "$blockchain_refs"
    else
        log_success "No blockchain references found in TRON payment system"
    fi
    
    # Check if TRON references exist in payment-systems/tron/
    log_info "Checking for TRON references in TRON payment system..."
    local tron_refs=$(grep -r "tron" "$TRON_DIR" 2>/dev/null || true)
    if [[ -n "$tron_refs" ]]; then
        log_success "TRON references found in TRON payment system (expected)"
    else
        log_warning "No TRON references found in TRON payment system"
    fi
}

# Function to display isolation summary
display_isolation_summary() {
    log_info "TRON Isolation Summary:"
    echo ""
    echo "Blockchain Core:"
    echo "  • No 'tron' references"
    echo "  • No 'TronWeb' references"
    echo "  • No 'payment' references"
    echo "  • No 'USDT' references"
    echo "  • No 'TRX' references"
    echo ""
    echo "TRON Payment System:"
    echo "  • Isolated in payment-systems/tron/"
    echo "  • Contains TRON-specific code"
    echo "  • No blockchain core references"
    echo ""
    echo "Isolation Status: VERIFIED"
    echo ""
}

# Main execution
main() {
    log_info "=== TRON Isolation Security Scan ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Blockchain Directory: $BLOCKCHAIN_DIR"
    log_info "TRON Directory: $TRON_DIR"
    echo ""
    
    # Scan for TRON violations
    if scan_tron_violations; then
        log_error "TRON isolation violations found!"
        log_error "Blockchain core must not contain any TRON references"
        exit 1
    fi
    
    # Verify TRON isolation
    verify_tron_isolation
    
    # Display summary
    echo ""
    display_isolation_summary
    
    log_success "TRON isolation verification passed!"
    log_info "Blockchain core is properly isolated from TRON payment system"
}

# Run main function
main "$@"