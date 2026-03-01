#!/bin/bash
# ========================================================================
# Lucid GUI API Bridge - GUI User Setup & Initialization
# File: gui-api-bridge/scripts/gui-user-setup.sh
# Purpose: Initialize GUI user environment for cross-platform support
# ========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[SETUP]${NC} $1"; }
log_success() { echo -e "${GREEN}[SETUP]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[SETUP]${NC} $1"; }
log_error() { echo -e "${RED}[SETUP]${NC} $1"; }

# ========================================================================
# CONFIGURATION SETUP
# ========================================================================

setup_gui_user_profile() {
    """Create .gui-user-profile configuration"""
    local profile_file="$PROJECT_DIR/.gui-user-profile"
    
    log_info "Creating GUI user profile: $profile_file"
    
    cat > "$profile_file" << 'EOF'
# ========================================================================
# Lucid GUI User Profile
# Auto-generated GUI user configuration
# ========================================================================

# GUI Application Configuration
GUI_APP_NAME="lucid-gui"
GUI_APP_PORT=3000
GUI_API_BACKEND="${LUCID_GUI_API_BRIDGE_URL:-http://localhost:8102}"

# User Information
GUI_USER_ID="${USER:-gui-user}"
GUI_USER_HOME="${HOME:-/home/gui-user}"

# Desktop Environment
GUI_DISPLAY="${DISPLAY:-:0}"
GUI_XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Security
GUI_TLS_ENABLED=true
GUI_VERIFY_SSL=true
GUI_AUTH_TOKEN_FILE="${HOME}/.lucid/gui-auth-token"

# Logging
GUI_LOG_LEVEL="INFO"
GUI_LOG_DIR="${HOME}/.lucid/logs"
GUI_LOG_FILE="${GUI_LOG_DIR}/gui-app.log"

# Cache
GUI_CACHE_ENABLED=true
GUI_CACHE_DIR="${HOME}/.lucid/cache"
GUI_CACHE_MAX_SIZE="500M"

# Development (optional)
GUI_DEV_MODE=false
GUI_HOT_RELOAD=false
GUI_DEBUG_CONSOLE=false

EOF
    
    log_success "GUI user profile created"
}

setup_gui_directories() {
    """Create required directories for GUI user"""
    log_info "Creating GUI user directories..."
    
    mkdir -p "$HOME/.lucid/logs"
    mkdir -p "$HOME/.lucid/cache"
    mkdir -p "$HOME/.lucid/config"
    mkdir -p "$HOME/.lucid/data"
    
    log_success "GUI directories created"
}

setup_gui_shell_integration() {
    """Add GUI CLI commands to shell profile"""
    local shell_profile=""
    
    # Detect shell
    if [ -n "${BASH_VERSION:-}" ]; then
        shell_profile="$HOME/.bashrc"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        shell_profile="$HOME/.zshrc"
    else
        shell_profile="$HOME/.profile"
    fi
    
    log_info "Adding GUI CLI integration to $shell_profile"
    
    # Check if already added
    if grep -q "LUCID_GUI_CLI_INTEGRATION" "$shell_profile" 2>/dev/null; then
        log_warning "GUI CLI integration already exists in $shell_profile"
        return 0
    fi
    
    cat >> "$shell_profile" << 'EOF'

# ========================================================================
# Lucid GUI CLI Integration
# LUCID_GUI_CLI_INTEGRATION
# ========================================================================

# Find GUI API Bridge scripts directory
GUI_BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lucid/gui-api-bridge/scripts" 2>/dev/null || \
              /opt/lucid/gui-api-bridge/scripts

export LUCID_GUI_API_BRIDGE_SCRIPTS="$GUI_BRIDGE_DIR"

# Add GUI commands to PATH
if [ -d "$GUI_BRIDGE_DIR" ]; then
    export PATH="$GUI_BRIDGE_DIR:$PATH"
fi

# Alias for common GUI commands
alias lucid-health='bash $GUI_BRIDGE_DIR/gui-exec.sh health'
alias lucid-logs='bash $GUI_BRIDGE_DIR/gui-exec.sh logs'
alias lucid-status='bash $GUI_BRIDGE_DIR/gui-exec.sh status'
alias lucid-api='bash $GUI_BRIDGE_DIR/gui-exec.sh api'

# Initialize Linux runtime on shell startup (optional)
if [ "${LUCID_AUTO_INIT_RUNTIME:-false}" = "true" ]; then
    bash "$GUI_BRIDGE_DIR/os-detector-linux-enforcer.sh" > /dev/null 2>&1 || true
fi

EOF
    
    log_success "GUI CLI integration added to $shell_profile"
    log_info "Reload shell with: source $shell_profile"
}

# ========================================================================
# DOCKER SETUP
# ========================================================================

setup_docker_for_gui() {
    """Setup Docker for GUI user access"""
    log_info "Configuring Docker for GUI user..."
    
    # Check if user is in docker group
    if ! groups "$USER" | grep -q docker; then
        log_warning "User '$USER' is not in docker group"
        log_info "To fix this, run: sudo usermod -aG docker $USER"
        log_info "Then restart your shell"
    else
        log_success "Docker is properly configured for $USER"
    fi
}

# ========================================================================
# CREDENTIALS & SECURITY
# ========================================================================

setup_gui_credentials() {
    """Setup credentials for GUI user"""
    local creds_dir="$HOME/.lucid"
    local jwt_token_file="$creds_dir/gui-auth-token"
    
    mkdir -p "$creds_dir"
    
    log_info "Setting up GUI user credentials..."
    
    # Check if token already exists
    if [ -f "$jwt_token_file" ]; then
        log_warning "JWT token already exists: $jwt_token_file"
        return 0
    fi
    
    # Generate placeholder token (should be filled from environment)
    if [ -n "${LUCID_GUI_AUTH_TOKEN:-}" ]; then
        echo "$LUCID_GUI_AUTH_TOKEN" > "$jwt_token_file"
        chmod 600 "$jwt_token_file"
        log_success "GUI auth token configured"
    else
        log_warning "LUCID_GUI_AUTH_TOKEN not set"
        log_info "Set it with: export LUCID_GUI_AUTH_TOKEN=<your-token>"
    fi
}

# ========================================================================
# INITIALIZATION CHECK
# ========================================================================

check_initialization_status() {
    """Check GUI user initialization status"""
    echo ""
    echo "=========================================="
    echo "GUI User Initialization Status"
    echo "=========================================="
    echo ""
    
    local issues=0
    
    # Check profile
    if [ -f "$PROJECT_DIR/.gui-user-profile" ]; then
        log_success "GUI user profile exists"
    else
        log_warning "GUI user profile missing"
        ((issues++))
    fi
    
    # Check directories
    if [ -d "$HOME/.lucid" ]; then
        log_success "GUI user directories exist"
    else
        log_warning "GUI user directories missing"
        ((issues++))
    fi
    
    # Check shell integration
    local shell_profile="${BASH_SOURCE[0]:-$HOME/.bashrc}"
    if grep -q "LUCID_GUI_CLI_INTEGRATION" "$shell_profile" 2>/dev/null; then
        log_success "Shell integration is configured"
    else
        log_warning "Shell integration not configured"
        ((issues++))
    fi
    
    # Check Docker
    if command -v docker &>/dev/null; then
        log_success "Docker is installed"
        if docker ps &>/dev/null 2>&1; then
            log_success "Docker is running"
        else
            log_warning "Docker is not running"
            ((issues++))
        fi
    else
        log_warning "Docker is not installed"
        ((issues++))
    fi
    
    echo ""
    if [ $issues -eq 0 ]; then
        log_success "All checks passed!"
    else
        log_warning "$issues issue(s) detected"
    fi
    echo ""
}

# ========================================================================
# MAIN
# ========================================================================

show_usage() {
    cat <<EOF
Usage: gui-user-setup.sh [OPTIONS]

Options:
  --full                - Run all setup steps
  --profile             - Create GUI user profile
  --directories         - Create GUI directories
  --shell-integration   - Setup shell integration
  --docker              - Configure Docker
  --credentials         - Setup credentials
  --check               - Check initialization status
  --help                - Show this help

Examples:
  gui-user-setup.sh --full
  gui-user-setup.sh --profile --shell-integration
  gui-user-setup.sh --check

EOF
}

main() {
    log_info "=========================================="
    log_info "Lucid GUI User Initialization"
    log_info "=========================================="
    echo ""
    
    # Default: run all if no args
    if [ $# -eq 0 ]; then
        local run_all=true
    fi
    
    local run_profile=${run_all:-false}
    local run_dirs=${run_all:-false}
    local run_shell=${run_all:-false}
    local run_docker=${run_all:-false}
    local run_creds=${run_all:-false}
    local run_check=${run_all:-false}
    
    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --full)
                run_profile=true
                run_dirs=true
                run_shell=true
                run_docker=true
                run_creds=true
                run_check=true
                ;;
            --profile)
                run_profile=true
                ;;
            --directories)
                run_dirs=true
                ;;
            --shell-integration)
                run_shell=true
                ;;
            --docker)
                run_docker=true
                ;;
            --credentials)
                run_creds=true
                ;;
            --check)
                run_check=true
                ;;
            -h|--help|help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
        shift
    done
    
    # Run selected setup steps
    [ "$run_profile" = "true" ] && setup_gui_user_profile
    [ "$run_dirs" = "true" ] && setup_gui_directories
    [ "$run_shell" = "true" ] && setup_gui_shell_integration
    [ "$run_docker" = "true" ] && setup_docker_for_gui
    [ "$run_creds" = "true" ] && setup_gui_credentials
    [ "$run_check" = "true" ] && check_initialization_status
    
    echo ""
    log_success "GUI user setup completed!"
    echo ""
}

main "$@"
