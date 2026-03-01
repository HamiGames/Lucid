#!/bin/bash

# Lucid System Full Validation Script
# 
# This script runs comprehensive validation of the complete Lucid system
# across all 10 clusters, validating:
# - Service Health (all services operational)
# - API Responses (all 47+ endpoints responding)
# - Integration Points (cross-cluster communication)
# - Container Status (all containers running)
#
# Usage:
#   ./scripts/validation/run-full-validation.sh [options]
#
# Options:
#   --auth-token TOKEN    Authentication token for protected endpoints
#   --output FILE         Output file for validation report
#   --quiet               Quiet mode (minimal console output)
#   --verbose             Verbose logging
#   --help                Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATION_DIR="$PROJECT_ROOT/tests/validation"
PYTHON_SCRIPT="$VALIDATION_DIR/validate_system.py"

# Default values
AUTH_TOKEN=""
OUTPUT_FILE=""
QUIET_MODE=false
VERBOSE_MODE=false
HELP_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$QUIET_MODE" == false ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$QUIET_MODE" == false ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    if [[ "$QUIET_MODE" == false ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $1"
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Help function
show_help() {
    cat << EOF
Lucid System Full Validation Script

This script runs comprehensive validation of the complete Lucid system
across all 10 clusters, validating:
- Service Health (all services operational)
- API Responses (all 47+ endpoints responding)
- Integration Points (cross-cluster communication)
- Container Status (all containers running)

Usage:
    $0 [options]

Options:
    --auth-token TOKEN    Authentication token for protected endpoints
    --output FILE         Output file for validation report (JSON format)
    --quiet               Quiet mode (minimal console output)
    --verbose             Verbose logging
    --help                Show this help message

Examples:
    # Run basic validation
    $0

    # Run with authentication token
    $0 --auth-token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    # Run with output to file
    $0 --output validation-report.json

    # Run in quiet mode
    $0 --quiet

Environment Variables:
    LUCID_AUTH_TOKEN      Default authentication token
    LUCID_VALIDATION_OUTPUT  Default output file

Exit Codes:
    0    All validations passed
    1    One or more validations failed
    2    Script error or invalid arguments

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auth-token)
                AUTH_TOKEN="$2"
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --quiet)
                QUIET_MODE=true
                shift
                ;;
            --verbose)
                VERBOSE_MODE=true
                shift
                ;;
            --help)
                HELP_MODE=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 2
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 2
    fi
    
    # Check if validation script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        log_error "Validation script not found: $PYTHON_SCRIPT"
        exit 2
    fi
    
    # Check if Docker is available (for container validation)
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found - container validation may fail"
    fi
    
    # Check if required Python packages are available
    if ! python3 -c "import aiohttp, asyncio" 2>/dev/null; then
        log_error "Required Python packages not found. Please install: pip install aiohttp asyncio"
        exit 2
    fi
    
    log_success "Prerequisites validated"
}

# Check system status
check_system_status() {
    log_info "Checking system status..."
    
    # Check if Docker is running
    if command -v docker &> /dev/null; then
        if ! docker info &> /dev/null; then
            log_warning "Docker is not running - container validation will fail"
        else
            log_success "Docker is running"
        fi
    fi
    
    # Check if required ports are available
    local required_ports=(8080 8083 8084 8085 8086 8087 8088 8089 8090 8091 8092 8093 8095 27017 6379 9200 8500)
    local occupied_ports=()
    
    for port in "${required_ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            occupied_ports+=("$port")
        fi
    done
    
    if [[ ${#occupied_ports[@]} -gt 0 ]]; then
        log_info "Required ports in use: ${occupied_ports[*]}"
    else
        log_warning "No services detected on required ports - validation may fail"
    fi
}

# Run validation
run_validation() {
    log_info "Starting comprehensive system validation..."
    
    # Build Python command
    local python_cmd="python3 $PYTHON_SCRIPT"
    
    # Add authentication token if provided
    if [[ -n "$AUTH_TOKEN" ]]; then
        python_cmd="$python_cmd --auth-token \"$AUTH_TOKEN\""
    fi
    
    # Add output file if provided
    if [[ -n "$OUTPUT_FILE" ]]; then
        python_cmd="$python_cmd --output \"$OUTPUT_FILE\""
    fi
    
    # Add quiet mode if requested
    if [[ "$QUIET_MODE" == true ]]; then
        python_cmd="$python_cmd --quiet"
    fi
    
    # Add verbose mode if requested
    if [[ "$VERBOSE_MODE" == true ]]; then
        python_cmd="$python_cmd --verbose"
    fi
    
    # Change to project root directory
    cd "$PROJECT_ROOT"
    
    # Run validation
    log_info "Executing validation command: $python_cmd"
    
    if eval "$python_cmd"; then
        log_success "System validation completed successfully"
        return 0
    else
        log_error "System validation failed"
        return 1
    fi
}

# Generate summary report
generate_summary() {
    local exit_code=$1
    
    log_info "Generating validation summary..."
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "🎉 ALL VALIDATIONS PASSED - System is fully operational!"
        echo ""
        echo "✅ Service Health: All services healthy"
        echo "✅ API Responses: All endpoints responding"
        echo "✅ Integrations: All cross-cluster communication working"
        echo "✅ Containers: All containers running and healthy"
        echo ""
        echo "The Lucid system is ready for production use."
    else
        log_error "❌ VALIDATION FAILED - System has issues that need attention"
        echo ""
        echo "Please review the validation report above for details."
        echo "Common issues:"
        echo "- Services not running (check docker-compose up)"
        echo "- API endpoints not responding (check service health)"
        echo "- Integration failures (check service mesh connectivity)"
        echo "- Container issues (check Docker logs)"
    fi
    
    if [[ -n "$OUTPUT_FILE" && -f "$OUTPUT_FILE" ]]; then
        log_info "Detailed report saved to: $OUTPUT_FILE"
    fi
}

# Main execution
main() {
    # Parse arguments
    parse_arguments "$@"
    
    # Show help if requested
    if [[ "$HELP_MODE" == true ]]; then
        show_help
        exit 0
    fi
    
    # Use environment variables as defaults
    if [[ -z "$AUTH_TOKEN" && -n "${LUCID_AUTH_TOKEN:-}" ]]; then
        AUTH_TOKEN="$LUCID_AUTH_TOKEN"
    fi
    
    if [[ -z "$OUTPUT_FILE" && -n "${LUCID_VALIDATION_OUTPUT:-}" ]]; then
        OUTPUT_FILE="$LUCID_VALIDATION_OUTPUT"
    fi
    
    # Print header
    if [[ "$QUIET_MODE" == false ]]; then
        echo "=========================================="
        echo "LUCID SYSTEM FULL VALIDATION"
        echo "=========================================="
        echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo "Project Root: $PROJECT_ROOT"
        echo "Validation Script: $PYTHON_SCRIPT"
        echo ""
    fi
    
    # Validate prerequisites
    validate_prerequisites
    
    # Check system status
    check_system_status
    
    # Run validation
    if run_validation; then
        generate_summary 0
        exit 0
    else
        generate_summary 1
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
