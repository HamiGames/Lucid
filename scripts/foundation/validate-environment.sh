#!/bin/bash
# LUCID Project Environment Validation Script
# Phase 1: Foundation Setup - Step 1
# Based on: BUILD_REQUIREMENTS_GUIDE.md - Section 1, Step 1
#
# Purpose: Validate the Lucid project environment after initialization
# Validates:
#   - Docker BuildKit enabled
#   - lucid-dev network exists (172.20.0.0/16)
#   - Python 3.11+ environment
#   - Git hooks configured
#   - Directory structure
#   - Required tools installed
#
# Usage: ./scripts/foundation/validate-environment.sh
# Exit Codes: 0 = Success, 1 = Validation Failed

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/configs/environment/foundation.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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

log_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

validate_required_tools() {
    log_header "Validating Required Tools"
    
    # Essential tools
    local essential_tools=("docker" "git" "python3")
    for tool in "${essential_tools[@]}"; do
        if check_command "$tool"; then
            local version=$($tool --version 2>&1 | head -n1)
            log_success "$tool is installed: $version"
        else
            log_error "$tool is NOT installed (REQUIRED)"
        fi
    done
    
    # Recommended tools
    local recommended_tools=("docker-compose" "pip" "curl" "jq")
    for tool in "${recommended_tools[@]}"; do
        if check_command "$tool"; then
            log_success "$tool is installed (recommended)"
        else
            log_warning "$tool is NOT installed (recommended)"
        fi
    done
    
    # Optional tools
    local optional_tools=("ruff" "markdownlint" "yamllint" "hadolint")
    for tool in "${optional_tools[@]}"; do
        if check_command "$tool"; then
            log_success "$tool is installed (optional)"
        else
            log_warning "$tool is NOT installed (optional - for linting)"
        fi
    done
}

validate_docker() {
    log_header "Validating Docker Configuration"
    
    # Check if Docker is running
    if docker info &> /dev/null; then
        log_success "Docker daemon is running"
        
        # Get Docker version
        local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
        log_success "Docker version: $docker_version"
    else
        log_error "Docker daemon is NOT running"
        return 1
    fi
    
    # Check Docker BuildKit
    if [ "${DOCKER_BUILDKIT:-0}" = "1" ]; then
        log_success "DOCKER_BUILDKIT environment variable is set"
    else
        log_warning "DOCKER_BUILDKIT environment variable is not set"
    fi
    
    # Check buildx
    if docker buildx version &> /dev/null; then
        local buildx_version=$(docker buildx version | awk '{print $2}')
        log_success "Docker buildx is available: $buildx_version"
        
        # Check for lucid-builder
        if docker buildx inspect lucid-builder &> /dev/null; then
            log_success "Docker buildx builder 'lucid-builder' exists"
        else
            log_warning "Docker buildx builder 'lucid-builder' not found"
        fi
    else
        log_warning "Docker buildx is not available"
    fi
    
    # Check Docker Compose
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null)
        log_success "Docker Compose is available: $compose_version"
    elif docker-compose --version &> /dev/null; then
        local compose_version=$(docker-compose --version | awk '{print $3}')
        log_success "Docker Compose (standalone) is available: $compose_version"
    else
        log_error "Docker Compose is NOT available"
    fi
}

validate_docker_networks() {
    log_header "Validating Docker Networks"
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
    fi
    
    # Check main development network
    local network_name="${LUCID_NETWORK_NAME:-lucid-dev}"
    local expected_subnet="${LUCID_NETWORK_SUBNET:-172.20.0.0/16}"
    
    if docker network inspect "$network_name" &> /dev/null; then
        log_success "Network '$network_name' exists"
        
        # Validate subnet
        local actual_subnet=$(docker network inspect "$network_name" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
        if [ "$actual_subnet" = "$expected_subnet" ]; then
            log_success "Network subnet is correct: $actual_subnet"
        else
            log_warning "Network subnet mismatch: expected $expected_subnet, got $actual_subnet"
        fi
    else
        log_error "Network '$network_name' does NOT exist"
    fi
    
    # Check isolated network
    local isolated_network="${LUCID_NETWORK_ISOLATED:-lucid-network-isolated}"
    if docker network inspect "$isolated_network" &> /dev/null; then
        log_success "Isolated network '$isolated_network' exists"
        
        # Check if it's internal
        local is_internal=$(docker network inspect "$isolated_network" --format '{{.Internal}}')
        if [ "$is_internal" = "true" ]; then
            log_success "Isolated network is properly configured as internal"
        else
            log_warning "Isolated network is NOT configured as internal"
        fi
    else
        log_error "Isolated network '$isolated_network' does NOT exist"
    fi
}

validate_python_environment() {
    log_header "Validating Python Environment"
    
    # Check Python version
    if check_command "python3"; then
        local python_version=$(python3 --version | awk '{print $2}')
        local major_minor=$(echo "$python_version" | cut -d. -f1,2)
        
        if awk -v ver="$major_minor" 'BEGIN{exit(ver<3.11)}'; then
            log_success "Python version is sufficient: $python_version (>= 3.11)"
        else
            log_error "Python version is insufficient: $python_version (required >= 3.11)"
        fi
    else
        log_error "Python3 is NOT installed"
        return 1
    fi
    
    # Check pip
    if check_command "pip" || check_command "pip3"; then
        local pip_cmd=$(check_command "pip" && echo "pip" || echo "pip3")
        local pip_version=$($pip_cmd --version | awk '{print $2}')
        log_success "pip is installed: $pip_version"
    else
        log_warning "pip is NOT installed"
    fi
    
    # Check virtual environment
    if [ -d "${PROJECT_ROOT}/venv" ]; then
        log_success "Python virtual environment exists"
        
        # Check if it's activated
        if [ -n "${VIRTUAL_ENV:-}" ]; then
            log_success "Virtual environment is activated"
        else
            log_warning "Virtual environment is NOT activated"
        fi
    else
        log_warning "Python virtual environment does NOT exist"
    fi
    
    # Check for requirements.txt
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        log_success "requirements.txt exists"
    else
        log_warning "requirements.txt does NOT exist"
    fi
}

validate_git_configuration() {
    log_header "Validating Git Configuration"
    
    # Check if .git directory exists
    if [ -d "${PROJECT_ROOT}/.git" ]; then
        log_success "Git repository initialized"
        
        # Check remote
        if git remote -v &> /dev/null; then
            local remote_url=$(git remote get-url origin 2>/dev/null || echo "none")
            if [ "$remote_url" != "none" ]; then
                log_success "Git remote configured: $remote_url"
            else
                log_warning "Git remote NOT configured"
            fi
        fi
    else
        log_error "Git repository NOT initialized"
        return 1
    fi
    
    # Check Git hooks
    local hooks_dir="${PROJECT_ROOT}/.git/hooks"
    if [ -d "$hooks_dir" ]; then
        log_success "Git hooks directory exists"
        
        # Check pre-commit hook
        if [ -f "${hooks_dir}/pre-commit" ] && [ -x "${hooks_dir}/pre-commit" ]; then
            log_success "Pre-commit hook is configured and executable"
        else
            log_warning "Pre-commit hook is NOT configured or not executable"
        fi
    else
        log_warning "Git hooks directory does NOT exist"
    fi
}

validate_directory_structure() {
    log_header "Validating Directory Structure"
    
    # Required directories
    local required_dirs=(
        "configs/environment"
        "scripts/foundation"
        "data"
        "logs"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "${PROJECT_ROOT}/${dir}" ]; then
            log_success "Directory exists: $dir"
        else
            log_error "Directory MISSING: $dir"
        fi
    done
    
    # Data directories
    local data_dirs=(
        "data/mongodb"
        "data/redis"
        "data/elasticsearch"
        "data/chunks"
        "data/sessions"
        "data/merkle"
        "data/blocks"
    )
    
    for dir in "${data_dirs[@]}"; do
        if [ -d "${PROJECT_ROOT}/${dir}" ]; then
            log_success "Data directory exists: $dir"
        else
            log_warning "Data directory MISSING: $dir (will be created on first run)"
        fi
    done
}

validate_configuration_files() {
    log_header "Validating Configuration Files"
    
    # Check foundation environment file
    if [ -f "$ENV_FILE" ]; then
        log_success "Foundation environment file exists: foundation.env"
        
        # Validate key variables
        source "$ENV_FILE"
        
        local key_vars=("LUCID_PROJECT" "LUCID_VERSION" "LUCID_PHASE" "MONGODB_URI" "REDIS_URI")
        for var in "${key_vars[@]}"; do
            if [ -n "${!var:-}" ]; then
                log_success "Environment variable set: $var"
            else
                log_warning "Environment variable NOT set: $var"
            fi
        done
    else
        log_error "Foundation environment file MISSING: foundation.env"
    fi
    
    # Check devcontainer configuration
    if [ -f "${PROJECT_ROOT}/.devcontainer/devcontainer.json" ]; then
        log_success "Devcontainer configuration exists"
    else
        log_warning "Devcontainer configuration MISSING"
    fi
    
    # Check Docker Compose files
    if [ -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
        log_success "Docker Compose file exists"
    else
        log_warning "Docker Compose file MISSING"
    fi
}

validate_permissions() {
    log_header "Validating File Permissions"
    
    # Check script executability
    local scripts=(
        "scripts/foundation/initialize-project.sh"
        "scripts/foundation/validate-environment.sh"
    )
    
    for script in "${scripts[@]}"; do
        local script_path="${PROJECT_ROOT}/${script}"
        if [ -f "$script_path" ]; then
            if [ -x "$script_path" ]; then
                log_success "Script is executable: $script"
            else
                log_warning "Script is NOT executable: $script (run: chmod +x $script)"
            fi
        else
            log_warning "Script does NOT exist: $script"
        fi
    done
}

# ============================================================================
# SUMMARY REPORT
# ============================================================================

generate_summary() {
    log_header "Validation Summary"
    
    echo ""
    echo -e "${CYAN}Total Checks:${NC}    $TOTAL_CHECKS"
    echo -e "${GREEN}Passed:${NC}          $PASSED_CHECKS"
    echo -e "${YELLOW}Warnings:${NC}        $WARNING_CHECKS"
    echo -e "${RED}Failed:${NC}          $FAILED_CHECKS"
    echo ""
    
    local pass_percentage=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "============================================"
        log_success "Environment Validation PASSED ($pass_percentage%)"
        log_success "============================================"
        
        if [ $WARNING_CHECKS -gt 0 ]; then
            echo ""
            log_warning "There are $WARNING_CHECKS warnings that should be addressed"
        fi
        
        echo ""
        log_info "Next steps:"
        log_info "1. Address any warnings if needed"
        log_info "2. Proceed to Step 2: MongoDB Database Infrastructure"
        log_info "3. Review the BUILD_REQUIREMENTS_GUIDE.md for next steps"
        echo ""
        
        return 0
    else
        log_error "============================================"
        log_error "Environment Validation FAILED ($pass_percentage%)"
        log_error "============================================"
        echo ""
        log_error "Please fix the $FAILED_CHECKS failed checks before proceeding"
        log_error "Run: ./scripts/foundation/initialize-project.sh"
        echo ""
        
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  LUCID Project Environment Validation             ║${NC}"
    echo -e "${BLUE}║  Phase 1: Foundation Setup - Step 1                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "Project Root: $PROJECT_ROOT"
    
    # Run all validation checks
    validate_required_tools
    validate_docker
    validate_docker_networks
    validate_python_environment
    validate_git_configuration
    validate_directory_structure
    validate_configuration_files
    validate_permissions
    
    # Generate summary and exit
    if generate_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"

