#!/bin/bash
################################################################################
# Lucid API - SBOM Generation Script
################################################################################
# Description: Generates Software Bill of Materials (SBOM) for all containers
# Version: 1.0.0
# Usage: ./generate-sbom.sh [container_name] [version]
# Example: ./generate-sbom.sh lucid-auth-service latest
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
REGISTRY="${REGISTRY:-lucid}"
SBOM_FORMAT="${SBOM_FORMAT:-spdx-json}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Container list for Phase 1 (Foundation)
PHASE1_CONTAINERS=(
    "lucid-mongodb"
    "lucid-redis"
    "lucid-elasticsearch"
    "lucid-auth-service"
)

# All containers by phase
PHASE2_CONTAINERS=(
    "lucid-api-gateway"
    "lucid-blockchain-engine"
    "lucid-session-anchoring"
    "lucid-block-manager"
    "lucid-data-chain"
    "lucid-service-mesh-controller"
)

PHASE3_CONTAINERS=(
    "lucid-session-pipeline"
    "lucid-session-recorder"
    "lucid-chunk-processor"
    "lucid-session-storage"
    "lucid-session-api"
    "lucid-rdp-server-manager"
    "lucid-xrdp-integration"
    "lucid-session-controller"
    "lucid-resource-monitor"
    "lucid-node-management"
)

PHASE4_CONTAINERS=(
    "lucid-admin-interface"
    "lucid-tron-client"
    "lucid-payout-router"
    "lucid-wallet-manager"
    "lucid-usdt-manager"
    "lucid-trx-staking"
    "lucid-payment-gateway"
)

################################################################################
# Function: log_info
################################################################################
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

################################################################################
# Function: log_success
################################################################################
log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

################################################################################
# Function: log_warning
################################################################################
log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

################################################################################
# Function: log_error
################################################################################
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# Function: check_dependencies
################################################################################
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for Syft
    if ! command -v syft &> /dev/null; then
        missing_deps+=("syft")
    fi
    
    # Check for Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # Check for jq
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Install Syft: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
        log_info "Install jq: apt-get install jq (or brew install jq on macOS)"
        exit 1
    fi
    
    log_success "All dependencies found"
}

################################################################################
# Function: setup_sbom_directory
################################################################################
setup_sbom_directory() {
    log_info "Setting up SBOM directory..."
    
    # Create SBOM directory structure
    mkdir -p "$SBOM_DIR"/{phase1,phase2,phase3,phase4,reports}
    mkdir -p "$SBOM_DIR"/archive/"$TIMESTAMP"
    
    log_success "SBOM directory created: $SBOM_DIR"
}

################################################################################
# Function: generate_sbom
# Arguments: $1 = container_name, $2 = version, $3 = phase
################################################################################
generate_sbom() {
    local container_name="$1"
    local version="${2:-latest}"
    local phase="${3:-phase1}"
    local image_ref="${REGISTRY}/${container_name}:${version}"
    local sbom_file="${SBOM_DIR}/${phase}/${container_name}-${version}-sbom.${SBOM_FORMAT}"
    
    log_info "Generating SBOM for: $image_ref"
    
    # Check if image exists locally
    if ! docker image inspect "$image_ref" &> /dev/null; then
        log_warning "Image not found locally: $image_ref"
        log_info "Attempting to pull image..."
        
        if ! docker pull "$image_ref" 2>/dev/null; then
            log_error "Failed to pull image: $image_ref"
            log_warning "Skipping SBOM generation for $container_name"
            return 1
        fi
    fi
    
    # Generate SBOM using Syft
    log_info "Running Syft scan on $image_ref..."
    if syft "$image_ref" -o "$SBOM_FORMAT" > "$sbom_file" 2>/dev/null; then
        log_success "SBOM generated: $sbom_file"
        
        # Generate additional formats
        log_info "Generating additional SBOM formats..."
        syft "$image_ref" -o cyclonedx-json > "${sbom_file%.json}.cyclonedx.json" 2>/dev/null || true
        syft "$image_ref" -o syft-json > "${sbom_file%.json}.syft.json" 2>/dev/null || true
        
        # Extract summary information
        extract_sbom_summary "$sbom_file" "$container_name" "$phase"
        
        return 0
    else
        log_error "Failed to generate SBOM for $image_ref"
        return 1
    fi
}

################################################################################
# Function: extract_sbom_summary
# Arguments: $1 = sbom_file, $2 = container_name, $3 = phase
################################################################################
extract_sbom_summary() {
    local sbom_file="$1"
    local container_name="$2"
    local phase="$3"
    local summary_file="${SBOM_DIR}/${phase}/${container_name}-summary.txt"
    
    log_info "Extracting SBOM summary..."
    
    # Extract package count and critical information
    {
        echo "========================================="
        echo "SBOM Summary: $container_name"
        echo "Generated: $(date)"
        echo "========================================="
        echo ""
        
        # Count packages by type
        if command -v jq &> /dev/null && [ -f "$sbom_file" ]; then
            echo "Package Statistics:"
            
            # Try to extract package counts (format may vary)
            local total_packages
            total_packages=$(jq -r '.packages | length' "$sbom_file" 2>/dev/null || echo "N/A")
            echo "  Total Packages: $total_packages"
            
            # Extract package types
            if [ "$total_packages" != "N/A" ]; then
                echo "  Package Types:"
                jq -r '.packages[].type' "$sbom_file" 2>/dev/null | sort | uniq -c | sed 's/^/    /' || true
            fi
            
            echo ""
            echo "File Location: $sbom_file"
            echo "File Size: $(du -h "$sbom_file" | cut -f1)"
        fi
        
        echo ""
        echo "========================================="
    } > "$summary_file"
    
    log_success "Summary generated: $summary_file"
}

################################################################################
# Function: generate_phase_sboms
# Arguments: $1 = phase_name, $2 = container_array
################################################################################
generate_phase_sboms() {
    local phase_name="$1"
    shift
    local containers=("$@")
    local success_count=0
    local failure_count=0
    
    log_info "Generating SBOMs for $phase_name..."
    echo ""
    
    for container in "${containers[@]}"; do
        if generate_sbom "$container" "latest" "$phase_name"; then
            ((success_count++))
        else
            ((failure_count++))
        fi
        echo ""
    done
    
    log_info "$phase_name Summary: $success_count successful, $failure_count failed"
    return 0
}

################################################################################
# Function: generate_consolidated_report
################################################################################
generate_consolidated_report() {
    local report_file="${SBOM_DIR}/reports/sbom-generation-report-${TIMESTAMP}.txt"
    
    log_info "Generating consolidated SBOM report..."
    
    {
        echo "========================================="
        echo "Lucid API - SBOM Generation Report"
        echo "========================================="
        echo "Generated: $(date)"
        echo "SBOM Format: $SBOM_FORMAT"
        echo "Registry: $REGISTRY"
        echo ""
        
        # Count SBOMs by phase
        for phase in phase1 phase2 phase3 phase4; do
            if [ -d "${SBOM_DIR}/${phase}" ]; then
                local count
                count=$(find "${SBOM_DIR}/${phase}" -name "*-sbom.${SBOM_FORMAT}" 2>/dev/null | wc -l)
                echo "$phase: $count SBOMs generated"
            fi
        done
        
        echo ""
        echo "SBOM Directory: $SBOM_DIR"
        echo "Total Size: $(du -sh "$SBOM_DIR" 2>/dev/null | cut -f1 || echo 'N/A')"
        echo ""
        
        echo "========================================="
        echo "Next Steps:"
        echo "1. Run vulnerability scan: ./scripts/security/scan-vulnerabilities.sh"
        echo "2. Verify SBOMs: ./scripts/security/verify-sbom.sh"
        echo "3. Generate compliance report: ./scripts/security/security-compliance-check.sh"
        echo "========================================="
    } > "$report_file"
    
    cat "$report_file"
    log_success "Report generated: $report_file"
}

################################################################################
# Function: show_usage
################################################################################
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [CONTAINER_NAME] [VERSION]

Generate Software Bill of Materials (SBOM) for Lucid containers.

OPTIONS:
    -h, --help              Show this help message
    -a, --all               Generate SBOMs for all containers
    -p, --phase PHASE       Generate SBOMs for specific phase (1-4)
    -f, --format FORMAT     SBOM format (spdx-json, cyclonedx-json, syft-json)
    -r, --registry REGISTRY Container registry (default: lucid)
    
EXAMPLES:
    # Generate SBOM for single container
    $0 lucid-auth-service latest
    
    # Generate SBOMs for Phase 1
    $0 --phase 1
    
    # Generate SBOMs for all containers
    $0 --all
    
    # Use custom format
    $0 --format cyclonedx-json lucid-api-gateway

EOF
}

################################################################################
# Main Script
################################################################################
main() {
    log_info "Lucid API - SBOM Generation Script"
    echo ""
    
    # Parse arguments
    local generate_all=false
    local phase=""
    local container_name=""
    local version="latest"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -a|--all)
                generate_all=true
                shift
                ;;
            -p|--phase)
                phase="$2"
                shift 2
                ;;
            -f|--format)
                SBOM_FORMAT="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            *)
                if [ -z "$container_name" ]; then
                    container_name="$1"
                else
                    version="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Check dependencies
    check_dependencies
    
    # Setup directory structure
    setup_sbom_directory
    
    # Generate SBOMs based on arguments
    if [ "$generate_all" = true ]; then
        log_info "Generating SBOMs for ALL containers..."
        echo ""
        generate_phase_sboms "phase1" "${PHASE1_CONTAINERS[@]}"
        generate_phase_sboms "phase2" "${PHASE2_CONTAINERS[@]}"
        generate_phase_sboms "phase3" "${PHASE3_CONTAINERS[@]}"
        generate_phase_sboms "phase4" "${PHASE4_CONTAINERS[@]}"
        
    elif [ -n "$phase" ]; then
        case $phase in
            1|phase1)
                generate_phase_sboms "phase1" "${PHASE1_CONTAINERS[@]}"
                ;;
            2|phase2)
                generate_phase_sboms "phase2" "${PHASE2_CONTAINERS[@]}"
                ;;
            3|phase3)
                generate_phase_sboms "phase3" "${PHASE3_CONTAINERS[@]}"
                ;;
            4|phase4)
                generate_phase_sboms "phase4" "${PHASE4_CONTAINERS[@]}"
                ;;
            *)
                log_error "Invalid phase: $phase (must be 1-4)"
                exit 1
                ;;
        esac
        
    elif [ -n "$container_name" ]; then
        # Determine phase from container name
        local detected_phase="phase1"
        if [[ " ${PHASE2_CONTAINERS[*]} " =~ " ${container_name} " ]]; then
            detected_phase="phase2"
        elif [[ " ${PHASE3_CONTAINERS[*]} " =~ " ${container_name} " ]]; then
            detected_phase="phase3"
        elif [[ " ${PHASE4_CONTAINERS[*]} " =~ " ${container_name} " ]]; then
            detected_phase="phase4"
        fi
        
        generate_sbom "$container_name" "$version" "$detected_phase"
        
    else
        # Default: Generate Phase 1 SBOMs
        log_info "No arguments provided. Generating Phase 1 (Foundation) SBOMs..."
        echo ""
        generate_phase_sboms "phase1" "${PHASE1_CONTAINERS[@]}"
    fi
    
    # Generate consolidated report
    echo ""
    generate_consolidated_report
    
    log_success "SBOM generation complete!"
}

# Run main function
main "$@"

