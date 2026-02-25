#!/bin/bash
# ========================================================================
# Lucid GUI API Bridge - GUI User Command Wrapper
# File: gui-api-bridge/scripts/gui-exec.sh
# Purpose: Wrapper for GUI applications to execute commands in Linux context
# Usage: gui-exec <command> [args...]
# ========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source the OS detector
source "$SCRIPT_DIR/os-detector-linux-enforcer.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[GUI-EXEC]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[GUI-EXEC]${NC} $1" >&2; }
log_error() { echo -e "${RED}[GUI-EXEC]${NC} $1" >&2; }

# ========================================================================
# COMMAND EXECUTION ROUTING
# ========================================================================

execute_in_runtime() {
    """Execute command in the appropriate Linux runtime"""
    local runtime=$1
    shift
    local cmd="$@"
    
    log_info "Executing in $runtime: $cmd"
    
    case "$runtime" in
        docker)
            execute_in_docker "$cmd"
            ;;
        wsl2)
            execute_in_wsl2 "$cmd"
            ;;
        pi-native)
            execute_native "$cmd"
            ;;
        ssh)
            execute_via_ssh "$cmd"
            ;;
        *)
            log_error "Unknown runtime: $runtime"
            return 1
            ;;
    esac
}

execute_in_docker() {
    """Execute command in Docker container"""
    local cmd="$1"
    
    # Ensure container is running
    if ! docker ps | grep -q "lucid-gui-api-bridge"; then
        log_error "GUI API Bridge container not running"
        return 1
    fi
    
    docker exec -i lucid-gui-api-bridge bash -c "$cmd"
}

execute_in_wsl2() {
    """Execute command in WSL2"""
    local cmd="$1"
    local distro="${LUCID_WSL2_DISTRO:-Ubuntu}"
    
    # Convert Windows paths to WSL2 paths if needed
    local wsl_cmd="$cmd"
    
    wsl.exe -d "$distro" -e bash -c "$wsl_cmd"
}

execute_via_ssh() {
    """Execute command via SSH to Pi"""
    local cmd="$1"
    local pi_host="${PI_HOST:-192.168.0.75}"
    local pi_user="${PI_USER:-pickme}"
    local pi_port="${PI_SSH_PORT:-22}"
    
    ssh -p "$pi_port" "${pi_user}@${pi_host}" "cd /opt/lucid && $cmd"
}

execute_native() {
    """Execute command natively (already on Linux)"""
    local cmd="$1"
    
    bash -c "$cmd"
}

# ========================================================================
# HIGH-LEVEL API OPERATIONS
# ========================================================================

api_health_check() {
    """Check API health"""
    local url="${LUCID_GUI_API_BRIDGE_URL:-http://localhost:8102}/health"
    
    log_info "Checking API health: $url"
    
    if curl -sf "$url" > /dev/null 2>&1; then
        log_success "API is healthy"
        return 0
    else
        log_error "API health check failed"
        return 1
    fi
}

api_call() {
    """Make API call"""
    local method="${1:-GET}"
    local endpoint="$2"
    shift 2
    local extra_args="$@"
    
    local url="${LUCID_GUI_API_BRIDGE_URL:-http://localhost:8102}${endpoint}"
    
    log_info "API $method: $url"
    
    curl -X "$method" "$url" $extra_args
}

docker_logs() {
    """Stream Docker container logs"""
    log_info "Streaming GUI API Bridge logs..."
    docker logs -f lucid-gui-api-bridge
}

docker_stats() {
    """Show Docker container stats"""
    log_info "GUI API Bridge container stats:"
    docker stats lucid-gui-api-bridge --no-stream
}

# ========================================================================
# MAIN
# ========================================================================

show_usage() {
    cat <<EOF
Usage: gui-exec <command> [options]

Commands:
  health                - Check API health
  logs                  - Stream container logs
  stats                 - Show container statistics
  api GET <endpoint>    - Make GET request
  api POST <endpoint>   - Make POST request
  exec <cmd>            - Execute command in Linux runtime
  status                - Show system status
  
Examples:
  gui-exec health
  gui-exec api GET /health
  gui-exec logs
  gui-exec exec "docker ps"
  gui-exec status

Environment Variables:
  LUCID_OS              - Detected OS
  LUCID_RUNTIME         - Linux runtime (docker/wsl2/pi-native/ssh)
  LUCID_GUI_API_BRIDGE_URL - API URL
  DEBUG                 - Enable debug output (true/false)

EOF
}

main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    local cmd="$1"
    shift
    
    # Ensure Linux runtime is ready
    if ! ensure_linux_runtime_ready > /dev/null 2>&1; then
        log_error "Failed to ensure Linux runtime is ready"
        exit 1
    fi
    
    # Get available runtime
    local runtime
    if ! runtime=$(detect_available_runtime); then
        log_error "Could not detect available runtime"
        exit 1
    fi
    
    # Export environment
    export_runtime_env "$runtime"
    
    # Route command
    case "$cmd" in
        health)
            api_health_check
            ;;
        logs)
            docker_logs "$@"
            ;;
        stats)
            docker_stats "$@"
            ;;
        api)
            api_call "$@"
            ;;
        exec)
            execute_in_runtime "$runtime" "$@"
            ;;
        status)
            echo ""
            echo "Lucid GUI API Bridge - System Status"
            echo "======================================"
            echo "OS: $LUCID_OS"
            echo "Runtime: $LUCID_RUNTIME"
            echo "API URL: $LUCID_GUI_API_BRIDGE_URL"
            echo ""
            api_health_check
            echo ""
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            log_error "Unknown command: $cmd"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
