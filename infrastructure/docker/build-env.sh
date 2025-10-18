#!/bin/bash
# Path: infrastructure/docker/build-env.sh
# Master Build Environment Script for Lucid Docker Services
# Orchestrates all service-specific build-env scripts

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}[HEADER]${NC} $1"; }
log_service() { echo -e "${CYAN}[SERVICE]${NC} $1"; }

# Service directories
SERVICE_DIRS=(
    "admin"
    "auth"
    "blockchain"
    "common"
    "gui"
    "node"
    "payment-systems"
    "rdp"
    "sessions"
    "tools"
    "users"
    "vm"
    "wallet"
)

# Function to run a service's build-env script
run_service_script() {
    local service_dir="$1"
    local script_path="$SCRIPT_DIR/$service_dir/build-env.sh"
    
    if [[ -f "$script_path" ]]; then
        log_service "Running build-env script for $service_dir..."
        if bash "$script_path"; then
            log_success "✅ $service_dir build-env script completed successfully"
        else
            log_error "❌ $service_dir build-env script failed"
            return 1
        fi
    else
        log_warning "⚠️  No build-env script found for $service_dir at $script_path"
    fi
}

# Function to display usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SERVICE_DIRS...]

Master Build Environment Script for Lucid Docker Services

OPTIONS:
    -h, --help              Show this help message
    -l, --list              List all available services
    -a, --all               Run build-env for all services (default)
    -s, --services DIRS     Run build-env for specific service directories
    -v, --verbose           Enable verbose output
    -d, --dry-run           Show what would be executed without running

SERVICE_DIRS:
    ${SERVICE_DIRS[*]}

EXAMPLES:
    $0                      # Run all services
    $0 --all                # Run all services
    $0 blockchain tools     # Run only blockchain and tools
    $0 --list               # List available services
    $0 --dry-run            # Show what would be executed

EOF
}

# Function to list available services
list_services() {
    log_header "Available Lucid Docker Services:"
    echo
    for service in "${SERVICE_DIRS[@]}"; do
        local script_path="$SCRIPT_DIR/$service/build-env.sh"
        if [[ -f "$script_path" ]]; then
            log_success "✅ $service"
        else
            log_warning "⚠️  $service (no build-env script)"
        fi
    done
}

# Function to create a summary report
create_summary_report() {
    local report_file="$SCRIPT_DIR/build-env-summary.md"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_info "Creating summary report: $report_file"
    
    cat > "$report_file" << EOF
# Lucid Docker Build Environment Summary

**Generated:** $timestamp  
**Build Timestamp:** $BUILD_TIMESTAMP  
**Git SHA:** $GIT_SHA  

## Services Processed

EOF

    for service in "${SERVICE_DIRS[@]}"; do
        local script_path="$SCRIPT_DIR/$service/build-env.sh"
        local env_dir="$SCRIPT_DIR/$service/env"
        
        if [[ -f "$script_path" ]]; then
            echo "### $service" >> "$report_file"
            echo "- ✅ Build script: \`$script_path\`" >> "$report_file"
            
            if [[ -d "$env_dir" ]]; then
                local env_files=$(find "$env_dir" -name "*.env" 2>/dev/null | wc -l)
                echo "- ✅ Environment files: $env_files files in \`$env_dir\`" >> "$report_file"
                
                # List individual env files
                find "$env_dir" -name "*.env" 2>/dev/null | while read -r env_file; do
                    local filename=$(basename "$env_file")
                    echo "  - \`$filename\`" >> "$report_file"
                done
            else
                echo "- ❌ No environment directory found" >> "$report_file"
            fi
            echo >> "$report_file"
        else
            echo "### $service" >> "$report_file"
            echo "- ❌ No build script found" >> "$report_file"
            echo >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

## Usage Instructions

To use these environment files in Docker builds:

\`\`\`bash
# Example for blockchain-api service
docker build --env-file infrastructure/docker/blockchain/env/blockchain-api.env \\
    -f infrastructure/docker/blockchain/Dockerfile.blockchain-api \\
    -t pickme/lucid:blockchain-api .

# Example for admin-ui service
docker build --env-file infrastructure/docker/admin/env/admin-ui.env \\
    -f infrastructure/docker/admin/Dockerfile.admin-ui \\
    -t pickme/lucid:admin-ui .
\`\`\`

## Next Steps

1. Review generated environment files
2. Customize environment variables as needed
3. Use environment files in Docker builds
4. Deploy containers with proper environment configuration

EOF

    log_success "Summary report created: $report_file"
}

# Main execution
main() {
    local run_all=true
    local verbose=false
    local dry_run=false
    local specific_services=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -l|--list)
                list_services
                exit 0
                ;;
            -a|--all)
                run_all=true
                shift
                ;;
            -s|--services)
                run_all=false
                shift
                while [[ $# -gt 0 && ! "$1" =~ ^- ]]; do
                    specific_services+=("$1")
                    shift
                done
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -d|--dry-run)
                dry_run=true
                shift
                ;;
            *)
                if [[ "$1" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                    specific_services+=("$1")
                    run_all=false
                else
                    log_error "Unknown option: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Set verbose mode
    if [[ "$verbose" == "true" ]]; then
        set -x
    fi
    
    # Display header
    log_header "Lucid Docker Build Environment Master Script"
    log_info "Build timestamp: $BUILD_TIMESTAMP"
    log_info "Git SHA: $GIT_SHA"
    log_info "Project root: $PROJECT_ROOT"
    echo
    
    # Determine which services to run
    local services_to_run=()
    
    if [[ "$run_all" == "true" ]]; then
        services_to_run=("${SERVICE_DIRS[@]}")
        log_info "Running build-env for all services..."
    else
        if [[ ${#specific_services[@]} -eq 0 ]]; then
            log_error "No services specified. Use --all or specify service directories."
            show_usage
            exit 1
        fi
        
        # Validate specified services
        for service in "${specific_services[@]}"; do
            if [[ " ${SERVICE_DIRS[*]} " =~ " $service " ]]; then
                services_to_run+=("$service")
            else
                log_error "Unknown service: $service"
                log_info "Available services: ${SERVICE_DIRS[*]}"
                exit 1
            fi
        done
        
        log_info "Running build-env for specified services: ${services_to_run[*]}"
    fi
    
    # Dry run mode
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN MODE - No scripts will be executed"
        echo
        for service in "${services_to_run[@]}"; do
            local script_path="$SCRIPT_DIR/$service/build-env.sh"
            if [[ -f "$script_path" ]]; then
                log_service "Would run: $script_path"
            else
                log_warning "Would skip: $service (no build-env script)"
            fi
        done
        exit 0
    fi
    
    # Run build-env scripts
    local success_count=0
    local total_count=${#services_to_run[@]}
    
    echo
    for service in "${services_to_run[@]}"; do
        if run_service_script "$service"; then
            ((success_count++))
        fi
        echo
    done
    
    # Display results
    log_header "Build Environment Generation Complete"
    log_info "Successfully processed: $success_count/$total_count services"
    
    if [[ $success_count -eq $total_count ]]; then
        log_success "🎉 All services processed successfully!"
    else
        log_warning "⚠️  Some services failed to process"
    fi
    
    # Create summary report
    create_summary_report
    
    echo
    log_info "Environment files are ready for Docker builds!"
    log_info "Check individual service directories for generated .env files"
    
    # Exit with appropriate code
    if [[ $success_count -eq $total_count ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
