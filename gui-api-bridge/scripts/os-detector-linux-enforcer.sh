#!/bin/bash
# ========================================================================
# Lucid GUI API Bridge - OS Detector & Linux Runtime Enforcer
# File: gui-api-bridge/scripts/os-detector-linux-enforcer.sh
# Purpose: Detect user OS and ensure Linux background system is running
# Target: Windows (WSL2/Docker), macOS, Linux, Raspberry Pi
# ========================================================================

set -euo pipefail

# Script metadata
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { [ "${DEBUG:-false}" = "true" ] && echo -e "${CYAN}[DEBUG]${NC} $1" || true; }

# ========================================================================
# OS DETECTION FUNCTIONS
# ========================================================================

detect_os() {
    """Detect the user's operating system"""
    local os=""
    local kernel=$(uname -s 2>/dev/null || echo "Unknown")
    
    case "$kernel" in
        Linux)
            os="Linux"
            ;;
        Darwin)
            os="macOS"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            os="Windows"
            ;;
        *)
            os="Unknown"
            ;;
    esac
    
    echo "$os"
}

detect_linux_distribution() {
    """Detect Linux distribution if on Linux"""
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        echo "$DISTRIB_ID" | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

is_wsl2() {
    """Check if running in WSL2"""
    if grep -qi "microsoft\|wsl" /proc/version 2>/dev/null; then
        return 0
    fi
    return 1
}

is_wsl1() {
    """Check if running in WSL1"""
    if grep -qi "microsoft" /proc/version 2>/dev/null && ! is_wsl2; then
        return 0
    fi
    return 1
}

get_wsl_distro() {
    """Get the current WSL distro name"""
    if command -v wsl.exe &>/dev/null; then
        wsl.exe -e sh -c 'echo $WSL_DISTRO_NAME' 2>/dev/null | tr -d '\r'
    else
        echo "Unknown"
    fi
}

# ========================================================================
# LINUX RUNTIME DETECTION
# ========================================================================

check_docker_available() {
    """Check if Docker is available and running"""
    if ! command -v docker &>/dev/null; then
        log_debug "Docker command not found"
        return 1
    fi
    
    if ! docker ps &>/dev/null 2>&1; then
        log_debug "Docker daemon not running"
        return 1
    fi
    
    return 0
}

check_wsl2_available() {
    """Check if WSL2 is available"""
    if [ "$(detect_os)" != "Windows" ]; then
        return 1
    fi
    
    if ! command -v wsl.exe &>/dev/null; then
        log_debug "WSL command not found"
        return 1
    fi
    
    # Check if WSL2 distro exists
    if wsl.exe --list --verbose 2>/dev/null | grep -q "Running"; then
        return 0
    fi
    
    return 1
}

check_ssh_available() {
    """Check if SSH to Pi is available"""
    local pi_host="${PI_HOST:-192.168.0.75}"
    local pi_user="${PI_USER:-pickme}"
    
    if ! command -v ssh &>/dev/null; then
        log_debug "SSH command not found"
        return 1
    fi
    
    if timeout 5 ssh -o ConnectTimeout=3 -o BatchMode=yes "${pi_user}@${pi_host}" "exit 0" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# ========================================================================
# LINUX RUNTIME STARTUP
# ========================================================================

ensure_docker_running() {
    """Ensure Docker daemon is running"""
    log_info "Checking Docker status..."
    
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        return 1
    fi
    
    if docker ps &>/dev/null 2>&1; then
        log_success "Docker is running"
        return 0
    fi
    
    log_warning "Docker daemon is not running"
    log_info "Attempting to start Docker..."
    
    # Try different methods based on OS
    case "$(detect_os)" in
        Linux)
            if command -v systemctl &>/dev/null; then
                sudo systemctl start docker 2>/dev/null || true
            elif command -v service &>/dev/null; then
                sudo service docker start 2>/dev/null || true
            fi
            ;;
        macOS)
            # Docker Desktop on macOS
            open -a Docker 2>/dev/null || true
            ;;
        Windows)
            # PowerShell to start Docker Desktop
            powershell.exe -Command "Start-Process 'Docker Desktop'" 2>/dev/null || true
            ;;
    esac
    
    # Wait for Docker to start
    log_info "Waiting for Docker to start (up to 30 seconds)..."
    local timeout=30
    while [ $timeout -gt 0 ]; do
        if docker ps &>/dev/null 2>&1; then
            log_success "Docker is now running"
            return 0
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    log_error "Docker failed to start"
    return 1
}

ensure_wsl2_running() {
    """Ensure WSL2 is running"""
    local distro="${1:-Ubuntu}"
    
    log_info "Checking WSL2 status..."
    
    if ! command -v wsl.exe &>/dev/null; then
        log_error "WSL is not installed"
        return 1
    fi
    
    # Check if distro is running
    if wsl.exe -d "$distro" -e true 2>/dev/null; then
        log_success "WSL2 ($distro) is running"
        return 0
    fi
    
    log_warning "WSL2 distro is not running"
    log_info "Starting WSL2 ($distro)..."
    
    # Launch default WSL2 distro
    wsl.exe -d "$distro" -e echo "WSL2 started" > /dev/null 2>&1
    
    # Wait for WSL2 to be ready
    local timeout=15
    while [ $timeout -gt 0 ]; do
        if wsl.exe -d "$distro" -e true 2>/dev/null; then
            log_success "WSL2 ($distro) is now running"
            return 0
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    log_error "WSL2 failed to start"
    return 1
}

ensure_ssh_connected() {
    """Ensure SSH connection to Pi is available"""
    local pi_host="${PI_HOST:-192.168.0.75}"
    local pi_user="${PI_USER:-pickme}"
    local pi_port="${PI_SSH_PORT:-22}"
    
    log_info "Checking SSH connection to ${pi_user}@${pi_host}:${pi_port}..."
    
    if ! command -v ssh &>/dev/null; then
        log_error "SSH is not installed"
        return 1
    fi
    
    if timeout 10 ssh -o ConnectTimeout=5 -o BatchMode=yes -p "$pi_port" "${pi_user}@${pi_host}" "exit 0" 2>/dev/null; then
        log_success "SSH connection to Pi is available"
        return 0
    fi
    
    log_warning "SSH connection to Pi failed"
    log_info "Ensure Pi is running and SSH is enabled"
    return 1
}

# ========================================================================
# RUNTIME DETECTION & STARTUP
# ========================================================================

detect_available_runtime() {
    """Detect which Linux runtime is available"""
    local os=$(detect_os)
    
    case "$os" in
        Windows)
            if check_wsl2_available; then
                echo "wsl2"
                return 0
            elif check_docker_available; then
                echo "docker"
                return 0
            fi
            ;;
        macOS)
            if check_docker_available; then
                echo "docker"
                return 0
            fi
            ;;
        Linux)
            # Check if Pi (running natively)
            if grep -qi "raspberry" /proc/cpuinfo 2>/dev/null; then
                echo "pi-native"
                return 0
            elif check_docker_available; then
                echo "docker"
                return 0
            fi
            ;;
    esac
    
    return 1
}

ensure_linux_runtime_ready() {
    """Ensure Linux runtime is available and running"""
    local runtime=""
    
    log_info "=========================================="
    log_info "Lucid GUI API Bridge - Linux Runtime Setup"
    log_info "=========================================="
    echo ""
    
    # Detect OS
    local os=$(detect_os)
    log_info "Detected OS: $os"
    
    # Try to detect available runtime
    if runtime=$(detect_available_runtime); then
        log_success "Available runtime detected: $runtime"
    else
        log_warning "No Linux runtime currently available"
        runtime=""
    fi
    echo ""
    
    # Ensure runtime is running
    case "$runtime" in
        wsl2)
            log_info "Using WSL2 as Linux runtime"
            ensure_wsl2_running "Ubuntu"
            ;;
        docker)
            log_info "Using Docker as Linux runtime"
            ensure_docker_running
            ;;
        pi-native)
            log_success "Running natively on Raspberry Pi"
            return 0
            ;;
        *)
            log_warning "No Linux runtime configured"
            log_info "Please ensure one of the following is available:"
            log_info "  • WSL2 (Windows)"
            log_info "  • Docker Desktop (Windows/macOS)"
            log_info "  • Native Linux installation"
            return 1
            ;;
    esac
    
    echo ""
    log_success "Linux runtime is ready!"
    return 0
}

# ========================================================================
# SERVICE MANAGEMENT
# ========================================================================

ensure_gui_api_bridge_running() {
    """Ensure GUI API Bridge service is running"""
    local runtime=$1
    
    log_info "Checking GUI API Bridge service..."
    
    case "$runtime" in
        docker)
            if docker ps | grep -q "lucid-gui-api-bridge"; then
                log_success "GUI API Bridge container is running"
                return 0
            fi
            
            log_warning "GUI API Bridge container not running"
            log_info "Starting GUI API Bridge with Docker Compose..."
            
            cd "$WORKSPACE_DIR"
            docker-compose -f gui-api-bridge/docker-compose.yml up -d lucid-gui-api-bridge
            
            # Wait for service to be healthy
            log_info "Waiting for service health check..."
            local timeout=60
            while [ $timeout -gt 0 ]; do
                if curl -sf http://localhost:8102/health > /dev/null 2>&1; then
                    log_success "GUI API Bridge is healthy"
                    return 0
                fi
                sleep 2
                timeout=$((timeout - 2))
            done
            
            log_warning "GUI API Bridge health check timed out"
            return 1
            ;;
        
        wsl2)
            log_info "Checking GUI API Bridge in WSL2..."
            # WSL2 command execution
            # TODO: Implement WSL2-specific service check
            ;;
        
        pi-native|ssh)
            log_info "Checking GUI API Bridge on Pi..."
            if check_ssh_available; then
                if ssh -o BatchMode=yes "pickme@${PI_HOST:-192.168.0.75}" "docker ps | grep -q lucid-gui-api-bridge"; then
                    log_success "GUI API Bridge is running on Pi"
                    return 0
                fi
            fi
            ;;
    esac
    
    return 0
}

# ========================================================================
# ENVIRONMENT SETUP
# ========================================================================

export_runtime_env() {
    """Export environment variables for the detected runtime"""
    local runtime=$1
    local os=$(detect_os)
    
    log_debug "Setting up environment for runtime: $runtime"
    
    # Common environment
    export LUCID_OS="$os"
    export LUCID_RUNTIME="$runtime"
    export LUCID_GUI_API_BRIDGE_URL="http://localhost:8102"
    
    case "$runtime" in
        wsl2)
            # WSL2-specific environment
            export LUCID_WSL2_DISTRO="$(get_wsl_distro)"
            export LUCID_BACKEND_HOST="localhost"
            export LUCID_BACKEND_PORT="8102"
            ;;
        docker)
            # Docker-specific environment
            export DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"
            export LUCID_BACKEND_HOST="localhost"
            export LUCID_BACKEND_PORT="8102"
            ;;
        pi-native|ssh)
            # Pi/SSH-specific environment
            export PI_HOST="${PI_HOST:-192.168.0.75}"
            export PI_USER="${PI_USER:-pickme}"
            export PI_SSH_PORT="${PI_SSH_PORT:-22}"
            export LUCID_BACKEND_HOST="$PI_HOST"
            export LUCID_BACKEND_PORT="8102"
            ;;
    esac
    
    log_debug "Environment variables exported"
}

# ========================================================================
# MAIN EXECUTION
# ========================================================================

main() {
    echo ""
    
    # Load .env if exists
    if [ -f "$WORKSPACE_DIR/.env" ]; then
        log_debug "Loading environment from $WORKSPACE_DIR/.env"
        set -a
        source "$WORKSPACE_DIR/.env" 2>/dev/null || true
        set +a
    fi
    
    # Check debug mode
    DEBUG="${DEBUG:-false}"
    
    # Ensure Linux runtime
    if ! ensure_linux_runtime_ready; then
        log_error "Failed to ensure Linux runtime"
        exit 1
    fi
    
    # Detect runtime
    local runtime=""
    if runtime=$(detect_available_runtime); then
        log_success "Runtime: $runtime"
    else
        log_error "Could not detect available runtime"
        exit 1
    fi
    
    # Export environment
    export_runtime_env "$runtime"
    
    # Ensure GUI API Bridge is running
    if ! ensure_gui_api_bridge_running "$runtime"; then
        log_warning "GUI API Bridge may not be fully operational"
    fi
    
    echo ""
    echo "=========================================="
    log_success "Linux Runtime Enforcer Complete!"
    echo "=========================================="
    echo ""
    log_info "System Information:"
    echo "  OS: $LUCID_OS"
    echo "  Runtime: $LUCID_RUNTIME"
    echo "  Backend URL: $LUCID_GUI_API_BRIDGE_URL"
    echo ""
    log_info "Environment variables exported:"
    echo "  LUCID_OS=$LUCID_OS"
    echo "  LUCID_RUNTIME=$LUCID_RUNTIME"
    echo "  LUCID_GUI_API_BRIDGE_URL=$LUCID_GUI_API_BRIDGE_URL"
    echo ""
    
    log_success "Ready for GUI application execution!"
    echo ""
}

# Run main if script is executed directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi

# Export functions for sourcing
export -f detect_os
export -f detect_available_runtime
export -f ensure_linux_runtime_ready
export -f export_runtime_env
