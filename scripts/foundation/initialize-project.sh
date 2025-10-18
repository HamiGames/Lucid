#!/bin/bash
# LUCID Project Environment Initialization Script
# Phase 1: Foundation Setup - Step 1
# Based on: BUILD_REQUIREMENTS_GUIDE.md - Section 1, Step 1
# 
# Purpose: Initialize the Lucid project environment
# Actions:
#   - Verify Docker BuildKit enabled
#   - Setup lucid-dev network (172.20.0.0/16)
#   - Initialize Python 3.11+ environment
#   - Configure git hooks and linting
#
# Usage: ./scripts/foundation/initialize-project.sh
# Validation: docker network ls | grep lucid-dev

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
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install $1 and try again."
        return 1
    fi
    return 0
}

# ============================================================================
# ENVIRONMENT VALIDATION
# ============================================================================

validate_environment() {
    log_info "Validating environment..."
    
    # Check required commands
    local required_commands=("docker" "python3" "git")
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            return 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)
    local required_version="3.11"
    
    if ! awk -v ver="$python_version" -v req="$required_version" 'BEGIN{exit(ver<req)}'; then
        log_error "Python version $python_version is less than required $required_version"
        return 1
    fi
    
    log_success "Environment validation passed"
    return 0
}

# ============================================================================
# DOCKER CONFIGURATION
# ============================================================================

verify_docker_buildkit() {
    log_info "Verifying Docker BuildKit..."
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker and try again."
        return 1
    fi
    
    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    # Verify BuildKit is available
    if docker buildx version &> /dev/null; then
        log_success "Docker BuildKit is available"
        
        # Create buildx builder if it doesn't exist
        if ! docker buildx inspect lucid-builder &> /dev/null; then
            log_info "Creating Docker buildx builder: lucid-builder"
            docker buildx create --name lucid-builder --use --bootstrap
            log_success "Docker buildx builder created"
        else
            log_info "Docker buildx builder already exists"
        fi
    else
        log_warning "Docker BuildKit is not available, but will use DOCKER_BUILDKIT=1"
    fi
    
    return 0
}

setup_docker_network() {
    log_info "Setting up Docker networks..."
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
    fi
    
    # Setup main development network
    local network_name="${LUCID_NETWORK_NAME:-lucid-dev}"
    local network_subnet="${LUCID_NETWORK_SUBNET:-172.20.0.0/16}"
    local network_gateway="${LUCID_NETWORK_GATEWAY:-172.20.0.1}"
    
    if docker network inspect "$network_name" &> /dev/null; then
        log_info "Network $network_name already exists"
    else
        log_info "Creating network: $network_name ($network_subnet)"
        docker network create \
            --driver bridge \
            --subnet="$network_subnet" \
            --gateway="$network_gateway" \
            "$network_name"
        log_success "Network $network_name created"
    fi
    
    # Setup isolated network for TRON payment services
    local isolated_network="${LUCID_NETWORK_ISOLATED:-lucid-network-isolated}"
    local isolated_subnet="${LUCID_NETWORK_ISOLATED_SUBNET:-172.21.0.0/16}"
    
    if docker network inspect "$isolated_network" &> /dev/null; then
        log_info "Isolated network $isolated_network already exists"
    else
        log_info "Creating isolated network: $isolated_network ($isolated_subnet)"
        docker network create \
            --driver bridge \
            --subnet="$isolated_subnet" \
            --internal \
            "$isolated_network"
        log_success "Isolated network $isolated_network created"
    fi
    
    return 0
}

# ============================================================================
# PYTHON ENVIRONMENT
# ============================================================================

initialize_python_environment() {
    log_info "Initializing Python environment..."
    
    # Check if virtual environment exists
    if [ ! -d "${PROJECT_ROOT}/venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "${PROJECT_ROOT}/venv"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "${PROJECT_ROOT}/venv/bin/activate"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install development dependencies
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        log_info "Installing Python dependencies..."
        pip install -r "${PROJECT_ROOT}/requirements.txt"
        log_success "Python dependencies installed"
    fi
    
    return 0
}

# ============================================================================
# GIT HOOKS CONFIGURATION
# ============================================================================

configure_git_hooks() {
    log_info "Configuring Git hooks..."
    
    local hooks_dir="${PROJECT_ROOT}/.git/hooks"
    
    # Create hooks directory if it doesn't exist
    mkdir -p "$hooks_dir"
    
    # Pre-commit hook for linting
    cat > "${hooks_dir}/pre-commit" << 'EOF'
#!/bin/bash
# Lucid pre-commit hook
# Runs linting before commit

set -e

echo "Running pre-commit checks..."

# Check if linting is enabled
if [ -f "configs/environment/foundation.env" ]; then
    source configs/environment/foundation.env
    if [ "${LINTING_ENABLED:-true}" = "true" ]; then
        echo "Running linters..."
        
        # Python linting (if ruff is available)
        if command -v ruff &> /dev/null; then
            echo "Running ruff..."
            ruff check . --fix || true
        fi
        
        # Markdown linting (if markdownlint is available)
        if command -v markdownlint &> /dev/null; then
            echo "Running markdownlint..."
            markdownlint '**/*.md' --ignore node_modules || true
        fi
    fi
fi

echo "Pre-commit checks passed"
EOF
    
    chmod +x "${hooks_dir}/pre-commit"
    log_success "Git hooks configured"
    
    return 0
}

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================

create_directory_structure() {
    log_info "Creating directory structure..."
    
    # Create required directories
    local directories=(
        "data/mongodb"
        "data/redis"
        "data/elasticsearch"
        "data/chunks"
        "data/sessions"
        "data/merkle"
        "data/blocks"
        "logs"
        "backups"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "${PROJECT_ROOT}/${dir}"
    done
    
    log_success "Directory structure created"
    return 0
}

# ============================================================================
# VALIDATION
# ============================================================================

validate_initialization() {
    log_info "Validating initialization..."
    
    local validation_passed=true
    
    # Check Docker network
    if docker network ls | grep -q "lucid-dev"; then
        log_success "Docker network lucid-dev exists"
    else
        log_error "Docker network lucid-dev not found"
        validation_passed=false
    fi
    
    # Check Python version
    if python3 --version | grep -q "3.11"; then
        log_success "Python 3.11+ is available"
    else
        log_warning "Python version check inconclusive"
    fi
    
    # Check Docker BuildKit
    if [ "${DOCKER_BUILDKIT:-0}" = "1" ]; then
        log_success "Docker BuildKit is enabled"
    else
        log_warning "Docker BuildKit environment variable not set"
    fi
    
    if [ "$validation_passed" = true ]; then
        log_success "Initialization validation passed"
        return 0
    else
        log_error "Initialization validation failed"
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log_info "Starting Lucid Project Initialization..."
    log_info "Project Root: $PROJECT_ROOT"
    echo ""
    
    # Step 1: Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    echo ""
    
    # Step 2: Verify Docker BuildKit
    if ! verify_docker_buildkit; then
        log_error "Docker BuildKit verification failed"
        exit 1
    fi
    echo ""
    
    # Step 3: Setup Docker networks
    if ! setup_docker_network; then
        log_error "Docker network setup failed"
        exit 1
    fi
    echo ""
    
    # Step 4: Initialize Python environment
    if ! initialize_python_environment; then
        log_error "Python environment initialization failed"
        exit 1
    fi
    echo ""
    
    # Step 5: Configure Git hooks
    if ! configure_git_hooks; then
        log_error "Git hooks configuration failed"
        exit 1
    fi
    echo ""
    
    # Step 6: Create directory structure
    if ! create_directory_structure; then
        log_error "Directory structure creation failed"
        exit 1
    fi
    echo ""
    
    # Step 7: Validate initialization
    if ! validate_initialization; then
        log_error "Initialization validation failed"
        exit 1
    fi
    echo ""
    
    log_success "============================================"
    log_success "Lucid Project Initialization Complete!"
    log_success "============================================"
    echo ""
    log_info "Next steps:"
    log_info "1. Review and update configs/environment/foundation.env"
    log_info "2. Run: ./scripts/foundation/validate-environment.sh"
    log_info "3. Proceed to Step 2: MongoDB Database Infrastructure"
    echo ""
    
    return 0
}

# Run main function
main "$@"

