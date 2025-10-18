#!/bin/bash
# Lucid API - SBOM Generation Script
# Generates Software Bill of Materials for Phase 1 containers

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SBOM_DIR="$PROJECT_ROOT/build/sbom"
PHASE_DIR="$SBOM_DIR/phase1"
ARCHIVE_DIR="$SBOM_DIR/archive"

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

# Check if Syft is installed
check_syft() {
    if ! command -v syft &> /dev/null; then
        log_error "Syft is not installed. Please install it first:"
        echo "  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
        exit 1
    fi
    
    local syft_version=$(syft version | head -n1)
    log_info "Using Syft: $syft_version"
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

# Generate SBOM for a container
generate_container_sbom() {
    local container_name="$1"
    local output_file="$2"
    local format="$3"
    
    log_info "Generating SBOM for $container_name..."
    
    if ! check_container_exists "$container_name"; then
        log_warning "Container $container_name not found, skipping..."
        return 1
    fi
    
    # Generate SBOM with Syft
    syft "$container_name" \
        --output "$format" \
        --file "$output_file" \
        --quiet
    
    if [ $? -eq 0 ]; then
        log_success "SBOM generated: $output_file"
        return 0
    else
        log_error "Failed to generate SBOM for $container_name"
        return 1
    fi
}

# Generate SBOMs for Phase 1 containers
generate_phase1_sboms() {
    log_info "Generating SBOMs for Phase 1 containers..."
    
    # Create directories
    mkdir -p "$PHASE_DIR"
    mkdir -p "$ARCHIVE_DIR"
    
    # Phase 1 containers
    local containers=(
        "lucid-mongodb:latest"
        "lucid-redis:latest" 
        "lucid-elasticsearch:latest"
        "lucid-auth-service:latest"
    )
    
    local generated_count=0
    local total_count=${#containers[@]}
    
    for container in "${containers[@]}"; do
        local container_short=$(echo "$container" | cut -d: -f1 | sed 's/lucid-//')
        local base_name="$PHASE_DIR/${container_short}"
        
        # Generate multiple formats
        local formats=("spdx-json" "cyclonedx-json" "syft-json")
        
        for format in "${formats[@]}"; do
            local output_file="${base_name}-sbom.${format}"
            
            if generate_container_sbom "$container" "$output_file" "$format"; then
                ((generated_count++))
            fi
        done
    done
    
    log_success "Generated $generated_count SBOM files for Phase 1"
    return 0
}

# Archive old SBOMs
archive_old_sboms() {
    if [ -d "$PHASE_DIR" ] && [ "$(ls -A "$PHASE_DIR" 2>/dev/null)" ]; then
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local archive_path="$ARCHIVE_DIR/phase1_${timestamp}"
        
        log_info "Archiving old SBOMs to $archive_path..."
        mkdir -p "$archive_path"
        cp -r "$PHASE_DIR"/* "$archive_path/"
        
        log_success "SBOMs archived to $archive_path"
    fi
}

# Generate SBOM summary
generate_sbom_summary() {
    local summary_file="$PHASE_DIR/sbom_summary.json"
    
    log_info "Generating SBOM summary..."
    
    cat > "$summary_file" << EOF
{
    "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "1",
    "total_containers": 4,
    "sbom_files": [
EOF

    local first=true
    for sbom_file in "$PHASE_DIR"/*.spdx-json; do
        if [ -f "$sbom_file" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                echo "," >> "$summary_file"
            fi
            
            local filename=$(basename "$sbom_file")
            local size=$(stat -f%z "$sbom_file" 2>/dev/null || stat -c%s "$sbom_file" 2>/dev/null || echo "0")
            
            cat >> "$summary_file" << EOF
        {
            "filename": "$filename",
            "size_bytes": $size,
            "format": "spdx-json"
        }
EOF
        fi
    done
    
    cat >> "$summary_file" << EOF
    ],
    "generation_status": "completed"
}
EOF

    log_success "SBOM summary generated: $summary_file"
}

# Main function
main() {
    log_info "Starting SBOM generation for Lucid API Phase 1..."
    
    # Parse arguments
    local phase="1"
    local archive_old=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --phase)
                phase="$2"
                shift 2
                ;;
            --archive)
                archive_old=true
                shift
                ;;
            --help)
                echo "Usage: $0 [--phase PHASE] [--archive] [--help]"
                echo "  --phase PHASE    Generate SBOMs for specific phase (default: 1)"
                echo "  --archive       Archive old SBOMs before generating new ones"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_syft
    
    # Archive old SBOMs if requested
    if [ "$archive_old" = true ]; then
        archive_old_sboms
    fi
    
    # Generate SBOMs based on phase
    case "$phase" in
        "1")
            generate_phase1_sboms
            ;;
        *)
            log_error "Unsupported phase: $phase"
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_sbom_summary
    
    log_success "SBOM generation completed successfully!"
    
    # Show results
    echo ""
    log_info "Generated files:"
    if [ -d "$PHASE_DIR" ]; then
        ls -la "$PHASE_DIR"
    fi
    
    echo ""
    log_info "SBOM generation completed for Phase $phase"
}

# Run main function
main "$@"